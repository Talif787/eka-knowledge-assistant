# Generation

The generation context turns a question into a grounded, cited answer streamed to
the client. It builds directly on retrieval: the passages that ground the answer
are exactly what `/v1/search` returns, scoped to the tenant.

## Flow

1. Retrieve tenant-scoped passages for the question (the Phase 3 search handler).
2. Sanitize each passage against prompt injection.
3. Assemble a grounded prompt: a hardened system instruction plus the passages,
   each tagged with a citation marker [n], plus the question.
4. Stream the answer from the language model.
5. Emit a sources event first (citations and a flagged indicator), then token
   events, then a done event.

## Streaming protocol

`POST /v1/answer` returns Server-Sent Events (`text/event-stream`). Each line is
`data: {json}`. Three event types, in order:

- `sources`: the citations (marker, chunk_id, document_id) and a `flagged`
  boolean indicating whether the injection guard redacted anything. Sent first so
  a client can render sources before tokens arrive.
- `token`: one chunk of answer text. Many of these.
- `done`: end of stream.

## Grounding and the language model

The `LanguageModel` port streams answer tokens for a `GroundedPrompt`. The
default `LocalTemplateLanguageModel` is a deterministic, dependency-free stand-in
for development: it composes the answer strictly from the retrieved passages
(selecting the sentence in each that best matches the question) and cites them
inline with [n]. A real provider (OpenAI, Anthropic, Bedrock) implements the same
port; nothing else in the pipeline changes. Because the stand-in only emits text
drawn from the passages, grounding is structural rather than hoped for.

## Prompt-injection guardrail

Retrieved passages are untrusted input: a stored document can contain text that
tries to hijack the model, such as "ignore all previous instructions". The guard
is defense in depth:

- The `PromptInjectionGuard` redacts known override phrasings from passage text
  before it reaches the prompt, and reports whether anything was flagged.
- The system prompt instructs the model to treat the context strictly as data and
  never follow instructions found inside it.

Neither layer is sufficient alone; a real deployment would add output-side checks
and provider-level safety as further layers.

## Extending

Swapping in a hosted model is a one-adapter change: implement `LanguageModel`
against the provider's streaming API and register it in place of the local
stand-in during app startup. The handler, prompt assembly, guardrail, and SSE
protocol are unchanged.
