# Chat Pipeline Investigation: Tool-Call Leakage & Inconsistent Sourcing

Investigation only — no code was modified. Findings are cited as `file:line` against the
current tree under `backend/onyx/` and `web/src/`.

## 0. Unifying root cause (read this first)

There are **two separate, compounding bugs**, not one:

**Bug A — the model hallucinates tool calls that were never offered to it.**
`open_url` and `python` are hard-disabled in code:

```python
# backend/onyx/tools/tool_implementations/open_url/open_url_tool.py:462-466
@classmethod
def is_available(cls, db_session: Session) -> bool:
    """Disabled: external URL fetching is not allowed in this deployment.
    Only local document search is permitted."""
    return False
```
```python
# backend/onyx/tools/tool_implementations/python/python_tool.py:257-261
@classmethod
def is_available(cls, db_session: Session) -> bool:
    """Disabled: Python code execution is not allowed in this deployment."""
    return False
```

`tool_constructor.py:_construct_tools_impl` (line ~219-235) skips any tool whose `is_available()`
returns `False` *before* it is added to `final_tools`. Because of this, neither tool's JSON schema
is ever placed in the `tools=[...]` payload sent to LiteLLM/Ollama (`onyx/llm/multi_llm.py:788-802`),
and neither tool's usage guidance is ever injected into the system prompt (`prompt_utils.py`
gates guidance strictly on tool-instance presence in the already-filtered list).

**This means the app is not the source of the `open_url`/`python` vocabulary the model is using.**
The model is emitting these tool names from its own pretraining/instruction-tuning distribution —
almost every openly-tuned "agentic" model (Hermes, Qwen-Agent variants, gpt-oss, DeepSeek-agent
tunes, granite, etc.) was fine-tuned on synthetic tool-use data that includes a near-universal
tool taxonomy: `browse`/`open_url`, `python`/`code_interpreter`, `search`, `bash`. Some Ollama
`Modelfile` templates for these models even hardcode a tool-description system message as part of
the model's own chat template, independent of anything the app sends. **Once `tool_choice=AUTO`
is set and *any* tools are attached** (e.g. `internal_search`), many local models default into
"tool-considering mode" and free-associate a tool call using their own internalized names rather
than the schema actually provided — because Ollama, unlike OpenAI's/Anthropic's hosted APIs, does
not enforce a strict "you may only emit tool calls matching the schema I gave you" grammar for
every model/template combination.

**Bug B — even a legitimate or hallucinated tool-call-shaped output is never intercepted before
being shown to the user.** The one live content filter that exists,
`_XmlToolCallContentFilter` (`backend/onyx/chat/llm_step.py:81-140`), only recognizes
Anthropic-style `<function_calls><invoke>` XML. It does **not** recognize JSON tool-call syntax
(`{"name": "...", "parameters": {...}}`) at all. The JSON-oriented fallback parser,
`extract_tool_calls_from_response_text` (`llm_step.py:417-510`), is only invoked by
`_try_fallback_tool_extraction` (`llm_loop.py:142-228`) when:

```python
should_try_fallback = (
    (tool_choice == ToolChoiceOptions.REQUIRED and no_tool_calls)
    or reasoning_but_no_answer_or_tools
    or xml_tool_call_text_detected
)
```

Under the ordinary chat turn (`tool_choice=AUTO`, the model produces a non-empty "answer" — which
*is* the raw JSON) none of these three conditions is true, so **the JSON is never even inspected**.
It streams live via `AgentResponseDelta` (`llm_step.py:1256-1268`) straight to the SSE connection,
the frontend renders it as plain markdown text with zero filtering
(`web/src/app/app/message/messageComponents/renderers/MessageTextRenderer.tsx:130-140`), and it is
persisted verbatim as `assistant_message.message` (`backend/onyx/chat/save_chat.py:210`) — so a
single detection miss is permanent in that conversation's history.

Everything below traces the supporting evidence and answers your 11 questions individually, then
proposes the target architecture.

---

## 1. Why is the model deciding to call `open_url`?

- **Root cause:** The model is not being given `open_url` through any legitimate app-level channel
  (schema or prompt) — `OpenURLTool.is_available()` unconditionally returns `False`
  (`open_url_tool.py:462-466`), so `tool_constructor.py` never includes it in `final_tools`. The
  name is coming from the base model's own pretrained tool vocabulary, surfacing because
  `tool_choice=AUTO` + at least one real tool (`internal_search`) is enough to put many local
  instruct models into "I might need a tool" mode, and Ollama's chat templates don't uniformly
  constrain generated tool-call syntax to only the schema actually supplied.
- **Responsible files:** `backend/onyx/tools/tool_implementations/open_url/open_url_tool.py`,
  `backend/onyx/tools/tool_constructor.py`, `backend/onyx/chat/llm_loop.py` (tool_choice policy,
  lines ~769-782), `backend/onyx/llm/multi_llm.py` (`_completion`, lines 748-803).
- **Execution flow:** persona tools loaded → `_construct_tools_impl` filters by `is_available()`
  → `open_url` excluded → `run_llm_loop` builds `tool_defs` from the *filtered* list only →
  `litellm.completion(..., tools=tool_defs)` is sent to Ollama without `open_url` present →
  model still emits `{"name": "open_url", ...}` as free text → nothing intercepts it (see §3) →
  it streams to the user.
- **Why it happens:** model behavior, not app misconfiguration. The app correctly refuses to wire
  the tool up; the leak is a **content-filtering gap**, not a **tool-registration gap**.
- **Correct behavior:** the app should never trust that "the model only calls tools we listed."
  It should validate every emitted tool-call-shaped span (JSON or XML) against the *actual* set of
  tools that were sent this turn, and treat anything referencing an unknown tool name as
  disallowed content to be stripped/rejected outright, never displayed as prose.

## 2. Why is the model deciding to call `python` for plain text?

- **Root cause:** identical mechanism to §1 — `PythonTool.is_available()` is hardcoded `False`
  (`python_tool.py:257-261`), so `python` is never in the schema sent to the model. The
  "plain text wrapped in a fake tool call" pattern (e.g. `{"name": "python", "parameters":
  {"code": "print(...)"}}` where the "code" is really just the answer) is a known failure mode of
  models instruction-tuned to always route substantive output through a code/interpreter channel —
  this is baked into weights, not into your prompt.
- **Responsible files:** `backend/onyx/tools/tool_implementations/python/python_tool.py`,
  `backend/onyx/tools/constants.py` (`PYTHON_TOOL_NAME = "run_python"`, note the class's actual
  wire name is `"python"`, `python_tool.py:225` — a naming mismatch worth cleaning up regardless),
  `backend/onyx/chat/llm_step.py` (the only place that could intercept this and doesn't for JSON).
- **Note on the sibling risk:** `BashTool`/`CodingAgentTool` are **not** hardcoded off — their
  `is_available()` (`bash_tool.py:79-100`) is a live check against `CODE_INTERPRETER_BASE_URL`
  (defaults to a non-empty `"http://localhost:8000"`, `app_configs.py:1478-1479`) plus a container
  health check. If a code-interpreter container is ever started (referenced in
  `backend/scripts/restart_containers.sh:107`), `coding_agent` silently becomes real and callable —
  this is a live risk distinct from the pure-hallucination case above.
- **Correct behavior:** same as §1 — validate tool-call-shaped output against the actual offered
  tool set and never surface unmatched ones as text. Additionally, verify the Ollama model's own
  `Modelfile`/template (`ollama show <model> --modelfile`) doesn't hardcode a tool-description
  system message; if it does, that message must be stripped or the model swapped for a
  plain-instruct variant with no baked-in agent template.

## 3. Why are tool calls leaking directly to the UI?

- **Root cause:** there is exactly one live content filter
  (`_XmlToolCallContentFilter`, `llm_step.py:81-140`) and it only recognizes Anthropic-style
  `<function_calls><invoke>` XML markers (`_looks_like_xml_tool_call_payload`,
  `llm_step.py:176-188`: `"<function_calls" in lowered and "<invoke" in lowered`). There is no
  equivalent live filter for JSON-shaped tool calls. The JSON post-hoc extractor
  (`extract_tool_calls_from_response_text`, `llm_step.py:417-510`) only runs when `tool_choice ==
  REQUIRED` with no native tool calls, or when there's "reasoning but no answer" — neither
  condition holds for a normal `AUTO` turn where the JSON *is* the answer.
- **Responsible files:** `backend/onyx/chat/llm_step.py` (streaming + filtering + fallback
  extraction), `backend/onyx/chat/llm_loop.py` (`_try_fallback_tool_extraction`, gating logic),
  `backend/onyx/chat/save_chat.py` (persists the raw streamed text verbatim, line 210),
  `web/src/app/app/message/messageComponents/renderers/MessageTextRenderer.tsx` (frontend renders
  `message_delta`/`message_start` content with zero validation, lines 130-140).
- **Execution flow:** `run_llm_step_pkt_generator` reads `delta.content` per token
  (`llm_step.py:1347-1353`) → passes through `_XmlToolCallContentFilter.process()` (no-op for
  JSON) → emitted immediately via `AgentResponseDelta` → SSE to browser → rendered as markdown →
  saved verbatim to DB.
- **Why it happens:** the filter was purpose-built for one specific tool-call *encoding*
  (Anthropic XML — see the code comment at `llm_step.py:59`: *"NOTE: DO NOT TOUCH THIS FUNCTION
  BEFORE ASKING YUHONG, this is very finicky and delicate logic"*), evidently patched reactively
  for a specific provider incident rather than designed as a general "never show unexecuted tool
  syntax" guarantee. JSON-shaped leakage from Ollama models was apparently never hit in whatever
  environment this filter was built against (likely Anthropic/OpenAI hosted models where native
  function-calling is reliable and this scenario doesn't arise).
- **Correct behavior:** treat "content that looks like a tool invocation" as a single class of
  problem regardless of encoding (JSON, XML, or anything else), detected and buffered **live**
  during streaming (not post-hoc), and never emitted to the content channel — either it resolves
  to a real, permitted tool call, or it is dropped/replaced with a clarifying failure, never shown
  raw.

## 4. Why do sources appear inconsistently?

- **Root cause:** retrieval is not always-on. `SearchTool` (`NAME = "internal_search"`,
  `search_tool.py:262-264`) is exposed to the model as an ordinary `tool_choice=AUTO` option
  (`llm_loop.py:709-782`) — the model decides per turn whether to call it. Separately, whether
  "Sources" get attached to the final message is **decoupled from whether the model actually used
  or cited the retrieved content**:

  ```python
  # backend/onyx/chat/llm_loop.py:1017-1026
  if isinstance(tool_response.rich_response, SearchDocsResponse):
      search_docs = tool_response.rich_response.search_docs
      ...
      if search_docs:
          state_container.add_search_docs(search_docs)
  ```

  This fires purely because the tool returned non-empty results — with no check against whether
  the model's final answer text referenced them at all. Meanwhile inline citation markers
  (`[1]`, `[2]`) are matched via `DynamicCitationProcessor`
  (`backend/onyx/chat/citation_processor.py:69,211-213,426-531`) and filtered by
  `emitted_citations` in `save_chat.py:270-315` — a **separate** dataset from `context_docs`.
- **Responsible files:** `backend/onyx/chat/llm_loop.py` (tool_choice policy + `add_search_docs`),
  `backend/onyx/tools/tool_implementations/search/search_tool.py` (`is_available`, lines 515-535),
  `backend/onyx/chat/process_message.py` (`determine_search_params`, lines 507-547),
  `backend/onyx/chat/citation_processor.py`, `backend/onyx/chat/save_chat.py` (lines 210-324),
  `backend/onyx/chat/chat_state.py` (`ChatStateContainer._all_search_docs`, lines 141-155).
- **Why sources sometimes don't appear:** (a) the model simply never calls `internal_search`
  under `AUTO` — the single biggest cause; (b) the persona doesn't have `SearchTool` attached, or
  its `is_available()` is false (`DISABLE_VECTOR_DB`, no connectors/user files); (c) search legitimately
  returns zero relevant chunks; (d) even when documents were retrieved, unreliable citation-marker
  emission from local/Ollama models (soft `CITATION_REMINDER` prompt, `prompt_utils.py:125-139`,
  is advisory only) means inline `[n]` links can be empty — but this does **not** hide the Sources
  panel itself, since that's driven by (a)-(c), not by citation markers.
- **Why sources sometimes appear when they shouldn't:** if the model calls `internal_search`,
  receives documents, but then answers substantially from its own internal knowledge without
  meaningfully using them, the raw retrieved set is still attached as "Sources" — there is no
  check correlating final-answer content against which documents were actually used.
- **Correct behavior:** for an enterprise RAG assistant, retrieval should be a deterministic
  pipeline step (always run, or run based on a lightweight deterministic router), not a
  model-chosen `AUTO` tool call. Sources should be attached if and only if the final answer
  actually draws on retrieved content — enforced by requiring citation markers to gate the Sources
  panel (not just the inline links), or by having the answer-generation step explicitly told
  "you were given documents; cite them or state that you're answering from general knowledge."

---

## 5–11. Consolidated file/class map

| Question | Where it lives |
|---|---|
| **5. Where is this implemented?** | Core chain: `backend/onyx/server/query_and_chat/chat_backend.py:565` (`handle_send_chat_message`) → `backend/onyx/chat/process_message.py:572` (`build_chat_turn`) → `_run_models`/`_run_model` (lines 1056, 1203) → `backend/onyx/chat/llm_loop.py:637` (`run_llm_loop`) → `backend/onyx/chat/llm_step.py:1037` (`run_llm_step_pkt_generator`) → `backend/onyx/llm/multi_llm.py:748` (`LitellmLLM._completion`). Deep Research is a parallel path: `backend/onyx/deep_research/dr_loop.py:196` (`run_deep_research_llm_loop`), invoked at `process_message.py:1260-1263` only when the client sets `new_msg_req.deep_research=true`. |
| **6. Legacy Onyx vs custom fork** | Legacy/stock Onyx: `chat/`, `llm/`, `context/search/`, `document_index/`, `tools/tool_implementations/search`, `tools/tool_implementations/web_search` (`is_available` correctly gates on configured provider), citation processing. **Fork-specific additions, not in upstream Onyx**: `onyx/coding_agent/`, `onyx/deep_research/`, `onyx/mcp_server/` (standalone FastMCP server — separate from `onyx/server/features/mcp/`, which *is* the legitimate admin API for user-configured MCP client connections), `onyx/sandbox_proxy/`, `onyx/skills/`, `onyx/tools/fake_tools/` (nested sub-agent loops exposed as a single outer tool call: `coding_agent`, `research_agent`), and the entire `onyx/server/features/build/` ("Craft"/Build sandbox-agent product, which owns `sandbox_proxy` and `skills` and is **not** wired into the primary chat LLM loop at all). |
| **7. Files controlling tool registration** | `backend/onyx/tools/built_in_tools.py` (`BUILT_IN_TOOL_MAP`), `backend/onyx/db/models.py:3909-3913` (`Persona.tools` many-to-many), `backend/onyx/db/tools.py` (enabled/disabled list queries), Alembic seed migrations (`alembic/versions/4f8a2b3c1d9e_add_open_url_tool.py`, `.../57122d037335_add_python_tool_on_default.py`, `.../f3c9e59c3b07_seed_coding_agent_tool.py`, `.../d09fc20a3c66_seed_builtin_tools.py`). |
| **8. Files controlling tool exposure to the model** | `backend/onyx/tools/tool_constructor.py` (`_construct_tools_impl`, the `is_available()` gate), each tool's own `is_available()` override (`open_url_tool.py:462`, `python_tool.py:257`, `bash_tool.py:79`, `coding_agent_tool.py:77`, `image_generation_tool.py:92`, `web_search_tool.py:139`, `search_tool.py:515`), `backend/onyx/chat/llm_loop.py:769-782` (`tool_choice`/`final_tools` assembly per cycle). |
| **9. Files deciding whether sources are attached** | `backend/onyx/chat/llm_loop.py:1017-1026` (`add_search_docs`, unconditional on tool-call result), `backend/onyx/chat/chat_state.py:141-155`, `backend/onyx/chat/save_chat.py:210-324` (`context_docs` vs `citations` split), `backend/onyx/db/chat.py:949-966` (`translate_db_message_to_chat_message_detail`). |
| **10. Files parsing tool calls into final responses** | `backend/onyx/chat/llm_step.py:81-140` (`_XmlToolCallContentFilter`, live, XML-only), `llm_step.py:417-510` (`extract_tool_calls_from_response_text`, post-hoc, JSON+XML, narrowly gated), `backend/onyx/chat/llm_loop.py:142-228` (`_try_fallback_tool_extraction`, the gating conditions), `backend/onyx/utils/jsonriver/` (incremental JSON parser used only for streaming *argument* deltas of already-recognized native tool calls, not for detection — `backend/onyx/chat/tool_call_args_streaming.py:26-77`). |
| **11. Files deciding text vs tool-call vs agent execution** | `backend/onyx/chat/llm_step.py:1293,1347-1366` (native `delta.content` vs `delta.tool_calls` split — the only *reliable* discriminator, driven by the provider's own structured channel), `backend/onyx/chat/process_message.py:1260-1263` (deep-research vs normal chat, a hardcoded client-supplied boolean, not a classifier), `backend/onyx/deep_research/orchestration_layer.py:71` (forces `tool_choice=REQUIRED` inside deep research's orchestrator stage). There is **no LLM-based or heuristic router** deciding "should this turn use RAG / a tool / plain chat" — the model always freely chooses among whatever was constructed, via `tool_choice=AUTO`. |

**Dead code worth knowing about:** `backend/onyx/tools/utils.py:17-27`
(`explicit_tool_calling_supported(model_provider, model_name)`) reads exactly the
`supports_function_calling` flags seeded per Ollama tag in
`backend/onyx/llm/litellm_singleton/config.py:22-110`, but is **never called** from any
production code path (only its own unit test references it). This is the capability gate that
should exist and doesn't — see the proposed architecture below.

**Stale planning artifact:** `STRIPPING_METHODOLOGY.md` at the repo root is your own prior lockdown
plan. Its checklist shows Phase 1 (config lockdown) checked off, but Phases 2-5 — including
**Phase 3, "Unregister the Tools... Remove all tools except Search and WebSearch"**, and
**Phase 5, "Delete `code-interpreter` service", "Delete `mcp_server` service"** — are unchecked,
and the file's own status footer still reads "Waiting to start Phase 1," which is inconsistent
with the checked Phase-1 boxes. This confirms the current state is a **partially-executed
migration**, not a fully-locked-down deployment — several of the gaps documented above (e.g. the
`CODE_INTERPRETER_BASE_URL` default being non-empty, the `mcp_server` FastMCP process still
being present in Helm charts) are exactly what Phase 5 was written to close.

---

## Proposed clean architecture

Do not implement yet — this is the target design to review before any code changes.

### A. Deterministic, minimal tool policy (replaces implicit `is_available()` scattering)
Introduce a single **allowlist** evaluated once per chat turn, e.g.
`ALLOWED_TOOL_NAMES = {"internal_search"}` (add `web_search`/`generate_image` only if/when you
explicitly want them). Every tool construction path (`tool_constructor.py`, deep research's
`dr_loop.py` tool wiring, the MCP server) must intersect against this allowlist, not rely solely
on each tool class's own `is_available()`. This turns "disabled" into one auditable place instead
of N separate hardcoded returns scattered across tool classes, and removes the DB-seeded
`persona__tool` rows (`open_url`, `python`) as a source of confusion — they should either be
deleted via migration or simply never matter because the allowlist is authoritative.

### B. Capability-gated tool_choice (wire up the dead check)
Before ever setting `tool_choice=AUTO` and attaching `tools=[...]`, call (a resurrected, actually
wired-in) `explicit_tool_calling_supported(provider, model)`. If the configured Ollama model/tag
isn't verified to support native tool calling:
- Do not send a `tools=` payload with `tool_choice=AUTO` at all, OR
- Force `tool_choice=NONE` and run retrieval as a deterministic non-model-gated pipeline step
  instead of a model-chosen tool (see D).

This directly prevents the "any attached tool nudges the model into tool-considering mode, which
it can't execute properly" failure mode that's the likely trigger for hallucinated `open_url`/
`python` calls.

### C. A single, encoding-agnostic "never show unexecuted tool syntax" guardrail
Replace the XML-only `_XmlToolCallContentFilter` with a general live filter that:
1. Buffers content when it looks like the *start* of a structured payload (JSON opening brace at
   plausible position, XML tool markers, etc.) rather than streaming immediately.
2. Once a candidate span closes, checks it against the allowlist from (A) and the schemas
   actually sent this turn.
3. If it matches a real, permitted tool → route to the tool-call channel (`ToolCallArgumentDelta`
   / native tool_calls), execute normally.
4. If it doesn't match anything permitted (hallucinated tool, wrong name, malformed) → drop it
   from the visible channel entirely and substitute either nothing (if there's remaining valid
   answer text) or a short deterministic fallback message — **never** the raw payload.
5. This must run **before** any content reaches `AgentResponseDelta`/persistence, not after
   (fixes the "already streamed, can't retract" problem in `save_chat.py`).

### D. Decouple retrieval from model choice; decouple citations from Sources
- Make retrieval either always-on for RAG-flagged personas, or gated by a cheap deterministic
  classifier/heuristic (not the primary chat model's free `tool_choice=AUTO` judgment) — this is
  what makes "sources appear consistently when relevant docs exist" achievable.
- Gate the "Sources" panel on the same signal as citations: only show a document as a Source if a
  citation marker in the final answer actually references it (or, if you want a softer rule,
  require the model to explicitly state whether it used retrieved context, and use that as the
  gate) — not merely "the search tool returned something."
- When no documents are retrieved/relevant, answer from internal knowledge with **zero** Sources
  UI, deterministically.

### E. Finish the existing lockdown plan
Your own `STRIPPING_METHODOLOGY.md` Phase 3 and Phase 5 already describe most of (A): "remove all
tools except Search and WebSearch," and removing the `code-interpreter`/`mcp_server` containers
closes the `CodingAgentTool`/`BashTool` live-risk path noted in §2. Recommend finishing Phases 2-5
in order, then layering B/C/D above on the reduced surface — much less to guardrail once
`coding_agent`, `deep_research`'s tool wiring, `mcp_server`, and `sandbox_proxy`/`skills` are
actually disconnected rather than merely `is_available()`-gated.

### F. Frontend defense-in-depth (optional but cheap)
`MessageTextRenderer.tsx` currently trusts all `message_delta` content unconditionally. Even with
B/C/D fixed server-side, add a client-side heuristic check (e.g. content that parses as JSON with
a `name`+`parameters`/`arguments` shape) that renders as a visibly-flagged "unexpected model
output" block instead of normal markdown — a last-resort net, not a substitute for the backend fix.
