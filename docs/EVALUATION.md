# Evaluation

The system ships with an answer-quality harness and a CI gate. The goal is to
catch regressions in retrieval and grounding before they reach users, the same
way unit tests catch regressions in logic.

## What is measured

Four metrics, computed per case and averaged across the dataset. They are
deterministic lexical proxies for the LLM-judged RAGAS metrics of the same name.
They are not a replacement for model-graded evaluation, but they are stable,
fast, and free, which is what a per-commit gate needs.

- **context_recall**: fraction of the expected answer keywords that appear in the
  retrieved passages. Low recall means retrieval failed to surface the evidence.
- **context_precision**: fraction of retrieved passages that share content with
  the question. Low precision means retrieval returned noise.
- **faithfulness**: fraction of the answer's content tokens that are supported by
  the retrieved passages. Low faithfulness means the answer drifted from its
  sources (a hallucination signal).
- **answer_relevance**: fraction of the expected keywords that appear in the
  answer. Low relevance means the answer did not address the question.

A production setup would layer model-graded scores on top of these proxies. The
proxies exist so the gate can run offline, deterministically, on every commit.

## How the harness runs

The harness runs each case through the same pieces the live answer path uses:
retrieve, sanitize against prompt injection, assemble a grounded prompt, and
generate. It then scores the answer and the retrieved contexts.

Retrieval in the harness uses an in-memory searcher rather than a database. It
indexes the eval corpus in memory and runs the same algorithm as the production
retriever (dense cosine plus keyword overlap, fused with reciprocal rank fusion,
then reranked). This keeps the gate hermetic: no Postgres, no Redis, no network,
and fully deterministic because the embedder, reranker, and local model are all
deterministic.

## Running it

```bash
python scripts/run_eval.py
```

It prints per-case and aggregate scores, then applies thresholds and exits
non-zero if any aggregate falls below its minimum. The thresholds are set with
headroom above the current deterministic pipeline, so an honest regression (for
example a broken reranker, or retrieval returning nothing) drops the relevant
metric below its floor and fails the build.

## The dataset

`src/eka/modules/evaluation/datasets/smoke.json` holds a small corpus (relevant
documents plus distractors) and a set of questions with expected keywords. The
distractors matter: with only relevant documents, precision and recall would be
trivially high. To extend the suite, add corpus documents and cases to the JSON.
No code changes are needed.

## CI

The `Evaluate` step in `.github/workflows/ci.yml` runs the gate after the tests.
Because the gate is hermetic, it needs no database service and finishes quickly.
