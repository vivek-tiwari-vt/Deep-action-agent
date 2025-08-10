# Deep Action Agent — Upgrade Plan to Agent-Mode Parity

This plan captures the immediate fixes, critical gaps, and staged upgrades to bring the project toward ChatGPT Agent Mode–level capabilities. It includes what to fix, what to add, and how to implement.

## 0) Principles
- All secrets via `.env` only; never hardcode. Keys: OpenRouter, Gemini, connectors (Gmail, Slack, GitHub, etc.).
- Strong safety defaults: domain allowlists, file type/size limits, timeouts, resource limits.
- Iterative planner–executor loop with tools, reflection, retries, and stop conditions.
- Observability: structured logs, progress, and streaming UX.

## 1) Immediate Fixes (Done)
- Add `tools/file_system_tools.py` facade over `FileManager` so sub-agents stop failing.
- Add `tools/web_tools.py` facade over `WebResearch` for a stable async API.
- Remove duplicate `_call_llm` in `agents/manager_agent.py`; keep provider-aware version.
- Normalize async tool calls in `ManagerAgent._execute_tool_call` for web research.
- Introduce iterative `execute_task_iterative` loop in `ManagerAgent` to enable multi-step planning.

## 2) Core New Tools (Initial)
- `tools/http_client.py`: Safe HTTP(S) requests with domain allowlist, timeouts, and JSON/text handling. Exposed as function tool `http_request`.
- `tools/memory.py`: Lightweight file-backed memory with simple search (placeholder). Expose `memory_remember`, `memory_search`. Later replace with FAISS/Chroma.

Future additions:
- Document ingestion (PDF, DOCX, HTML, OCR), structured extraction (JSON schema), spreadsheet tool (read/write CSV/XLSX), connectors (email, calendar, Slack, GitHub, Drive/Docs/Sheets, Notion).

## 3) Planner–Executor Upgrades
- Replace one-shot plan with iterative loop:
  - Messages: system + user task
  - LLM cycles: think → propose tool calls → observe → reflect → continue until finish or budget exceeded.
  - Keep scratchpad in `workspace/<task>/metadata/` for self-notes and plan state (TBD).
  - Add stop conditions: max steps, no tool calls and final content, or explicit stop.
  - Introduce reflection: after each 2–3 steps, ask model to evaluate progress and gaps; consult `critic` agent for QC before finalization (TBD).
- Parallelism:
  - Short-term: sequential tool calls per response (safer).
  - Mid-term: parallel independent actions (e.g., fan-out web searches) using `asyncio.gather` and merge results.

## 4) Runtime & Safety
- Per-task virtual environment (later): create isolated venv under `workspace/<task>/venv`, install deps on demand, and run interpreter subprocess bound to that venv. Enforce CPU/memory/time limits (ulimits or subprocess timeouts). Ensure cancellation kills subprocess tree.
- File I/O restrictions: Already in `FileManager` path resolution; extend with size/type allowlist from `config.ALLOWED_FILE_EXTENSIONS` and `MAX_FILE_SIZE_MB` on write/append.
- HTTP allowlists: `HTTP_ALLOWED_DOMAINS` env, `ALLOW_ALL_HTTP=false` by default. Timeouts sourced from config.

## 5) Observability & UX
- Keep current progress tracker and logs; add WebSocket/SSE streaming endpoints for:
  - Token streams from LLM (requires streaming provider integration)
  - Tool call events (start/finish, args, result status)
  - Progress steps

## 6) Milestone Plan

### Week 1
- [x] Add wrappers `file_system_tools.py`, `web_tools.py`.
- [x] Fix `_call_llm` duplication; normalize async tool usage.
- [x] Add `http_client` + `memory` tools; register in `ManagerAgent` tool list.
- [x] Implement iterative `execute_task_iterative` in `ManagerAgent`.
- [ ] Smoke tests: run a research task end-to-end; confirm reports generated.

### Week 2
- [ ] Add document ingestion tool (PDF, DOCX, HTML, OCR via unstructured or docling).
- [ ] Add spreadsheet tool (pandas) for CSV/XLSX read/write and basic aggregations.
- [ ] Upgrade memory to a real vector DB (Chroma/FAISS) with embeddings provider via OpenRouter/Gemini.
- [ ] Implement per-task venv for code execution; honor cancellation.

### Week 3
- [ ] Add connectors: Email (IMAP/SMTP or Gmail API), Calendar, Slack, GitHub minimal CRUD.
- [ ] Add structured extraction tool (JSON schema guided) and HTML/PDF report rendering.
- [ ] Add WebSocket/SSE streaming endpoints and a client example.

## 7) Environment Variables (Examples)
```
# HTTP
HTTP_ALLOWED_DOMAINS=api.github.com,docs.github.com,example.com
ALLOW_ALL_HTTP=false
HTTP_DEFAULT_TIMEOUT=30

# Memory / Embeddings (future)
EMBEDDINGS_PROVIDER=openrouter

# Connectors (future)
GMAIL_API_KEY=...
SLACK_BOT_TOKEN=...
GITHUB_TOKEN=...
```

## 8) Security Notes
- Never hardcode API keys (avoid tutorial patterns that suggest in-code keys).
- Restrict outbound HTTP by default; maintain explicit allowlist.
- Validate file types and sizes; sanitize paths (already in place via FileManager resolution).

## 9) Testing Strategy
- Unit tests for tools (HTTP, Memory, File ops) with fixtures and mocks.
- Integration tests for planner—execute loop using canned tool results.
- E2E tests: start FastAPI, run `execute` with sample tasks, verify artifacts.

---
This plan evolves as capabilities land. The immediate next steps are smoke-testing the new wrappers and iterative loop, then layering ingestion, memory, venv isolation, and connectors.

