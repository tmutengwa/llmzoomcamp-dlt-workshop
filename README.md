# LLM Zoomcamp — dlt Workshop Homework

FAQ agent (Pydantic AI) instrumented with Pydantic Logfire, with traces pulled
back out into DuckDB using dlt.

Homework spec: https://github.com/DataTalksClub/llm-zoomcamp/blob/main/cohorts/2026/workshops/dlt.md

## Files

- `agent.py` — the FAQ teaching-assistant agent (Pydantic AI)
- `ingest.py` — downloads the course FAQ and builds the minsearch index
- `main.py` — entry point; instruments the agent with Logfire and runs a question
- `logfire_to_duckdb.py` — dlt pipeline that pulls trace data from the Logfire
  Query API into DuckDB

## Setup

```bash
uv sync
cp .env.example .env   # if starting fresh; otherwise edit the existing .env
```

Fill in `.env`:

```
OPENAI_API_KEY=sk-...
LOGFIRE_TOKEN=...        # write token, from your Logfire project settings
LOGFIRE_READ_TOKEN=...   # read token, for the dlt pipeline
```

## Running the agent

```bash
uv run python main.py "How do I run Ollama locally?"
```

Omit the argument to use the default question. Each run streams spans live to
your Logfire project (URL printed on startup) and prints the agent's answer.

### Note on `os._exit(0)`

`main.py` ends with `logfire.force_flush()` + `os._exit(0)` instead of a plain
return. Without this, the process reliably segfaults (exit 139) during
Python's interpreter shutdown. Root-caused with `lldb`: the crash is inside
`pydantic_core`'s Rust extension, triggered by a weakref/finalizer callback on
a `datetime` object that fires during CPython's `finalize_modules()` step,
after some of pydantic-core's internal state has already been torn down — a
known class of PyO3-extension shutdown bug, not something fixable from
application code. `force_flush()` guarantees spans are shipped before we skip
normal finalization, so no trace data is lost.

## Pulling traces into DuckDB

```bash
uv run python logfire_to_duckdb.py
```

Queries the Logfire Query API (`POST https://logfire-us.pydantic.dev/v2/query`)
for everything in the `records` table and loads it into
`logfire_traces.duckdb`, dataset `agent_traces`. dlt normalizes the nested
span attributes (gen_ai messages, tool definitions, token usage, etc.) into
child tables automatically.

## Homework Answers

**Q1 — How many spans does a single agent run produce?**
Answer: **5**
Confirmed by expanding the trace tree in the Logfire UI for
"How do I run Ollama locally?" runs: each run is 1 root `invoke_agent` span
plus a `chat`/`execute_tool` span per LLM call and tool call (varies with how
many searches the model makes — observed 4–6 total spans across three runs).

**Q2 — How many tables did dlt create in the `agent_traces` schema?**
Answer: **24**

```sql
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'agent_traces';
-- 24
```

3 dlt-internal tables (`_dlt_loads`, `_dlt_pipeline_state`, `_dlt_version`)
+ `records` + 20 child tables from normalizing nested attributes such as
`gen_ai_input_messages`, `gen_ai_output_messages`, `gen_ai_tool_definitions`,
`pydantic_ai_all_messages`, and their nested `parts`/`result` sub-structures.

**Q3 — Input token usage range for the Q1 agent run**
Answer: **1500 - 5000**

Summed `attributes__gen_ai_usage_input_tokens` across all `chat gpt-5.4-mini`
spans, grouped by `trace_id`, for the three Ollama-question runs:

| run          | input tokens |
|--------------|-------------:|
| run 1        |         1737 |
| run 2        |         4140 |
| run 3        |         1735 |

All three fall in the 1500–5000 bucket.
