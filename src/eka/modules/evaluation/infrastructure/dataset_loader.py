"""Load an evaluation dataset from JSON."""

from __future__ import annotations

import json
from pathlib import Path

from eka.modules.evaluation.domain.dataset import CorpusDoc, EvalCase, EvalDataset


def load_dataset(path: Path) -> EvalDataset:
    data = json.loads(path.read_text())
    corpus = tuple(
        CorpusDoc(id=str(doc["id"]), text=str(doc["text"])) for doc in data["corpus"]
    )
    cases = tuple(
        EvalCase(
            id=str(case["id"]),
            question=str(case["question"]),
            expected_keywords=tuple(str(k) for k in case["expected_keywords"]),
        )
        for case in data["cases"]
    )
    return EvalDataset(corpus=corpus, cases=cases)
