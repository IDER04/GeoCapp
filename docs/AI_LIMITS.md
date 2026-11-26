# GeoCapp — AI Analyst Question Limit (per session)

> Priority 5, Phase 1. Implementation: `geocapital/limits.py`,
> wired into `views/analyst_page.py`. Configuration: `data/meta.json` →
> `ai_limits`.

## 1. What the limit does

The AI Analyst accepts at most **`ai_limits.max_questions_per_session`
questions per Streamlit session** (starting value: **8**; editable in
`data/meta.json`, validated as an integer ≥ 1 — a violation raises
`ConfigError`, with no silent fallback).

- The counter is **server-side** (`st.session_state`): the browser holds
  no counter that could be tampered with on the client side.
- Once the limit is reached, input is disabled
  (`st.chat_input(disabled=True)`), a notice explains the situation
  (FR/EN), and the server-side guard `_handle_question` rejects any
  submission — **no call to the AI provider is made**.
- Otherwise, a discreet label continuously displays `remaining/total`.

## 2. Counting policy (chosen and tested)

**Each submitted question counts as exactly one unit, whatever the
outcome**:

| Case | Counted? |
|---|---|
| Response received from the provider (OpenRouter) | Yes |
| Provider failure (network, missing key, HTTP) → deterministic editorial answer instead | Yes |
| Editorial mode from the start (no API key) | Yes |
| Question blocked by the limit (input disabled) | No — nothing is submitted |

Rationale: the limit targets how often a user queries the analyst within
a session, not the provider's billing. Every conversation turn produces
an answer (AI or editorial) and uses up one turn; counting them all
gives predictable behavior, prevents an unavailable service from
"allowing" unlimited submissions, and remains simple to explain in the
app.

## 3. Avoiding double counting (Streamlit reruns)

The increment lives in `_handle_question(prompt)`, which is called only
when `st.chat_input` returns a *new* submitted value. On a simple rerun
(page change, selector, language), `chat_input` returns `None`, so
nothing is incremented. Tested: submission → rerun with no new value →
counter unchanged.

## 4. Scope: what the limit is NOT

- **Not a global account cap**: nothing is shared across sessions,
  accounts or browsers; opening a new session resets the counter to
  zero. The limit-reached message explains this explicitly in the app.
- **Not a spending guarantee**: the actual cost depends on the chosen
  OpenRouter model (`GEOCAPITAL_MODEL`, default `openai/gpt-4o`) and on
  response length (`MAX_TOKENS = 700` per response). The limit bounds
  the *number of turns*, not the exact billing.
- *Exact scope*: per Streamlit browser session (server-side session
  identity). Questions asked on the *other* pages (profiles, quiz,
  decoder: `ai.country_brief`, `explain_verdict` calls, etc.) do not go
  through this counter — they remain governed by their individual
  interactive use and are out of scope for this increment.

## 5. Tests

`tests/test_limits.py` covers: configuration validation (missing
section, 0, negative, non-integer, boolean), exact boundaries
(`can_ask`/`remaining` at `limit-1` and at `limit`), unit incrementing,
end-to-end AppTest behavior (normal submission, rerun without double
counting, exact limit reached and then blocked — no `ai.chat` call
beyond it), the counting policy for provider failures (an editorial
fallback still counts), and FR and EN labels.
