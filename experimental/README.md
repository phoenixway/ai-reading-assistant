# AI Reading Assistant MVP v0.1

Local-first experimental reader for long fiction. The LLM does **extraction**, while code owns memory.

## Stack

- Python 3.11+
- FastAPI, zero-build vanilla web UI
- SQLite + FTS5
- `llama-server` via `/v1/chat/completions` and `/tokenize`
- tagged append-only observation protocol

This deliberately avoids React/Tauri/vector DB in v0.1. If the extraction benchmark works, the same HTTP app can later be wrapped in Tauri or replaced with a native client without changing the memory engine.

## 1. Start llama.cpp

Use your existing server. The app defaults to `http://127.0.0.1:8080`.
For gpt-oss-20b on an 8 GB GPU, start conservatively with more MoE layers on CPU and lower `--n-cpu-moe` until the next step no longer fits comfortably.

Example (tune `--n-cpu-moe` on your machine):

```bash
llama-server \
  -m /path/to/gpt-oss-20b-MXFP4.gguf \
  --ctx-size 8192 \
  --n-cpu-moe 22 \
  --parallel 1 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --flash-attn on \
  --cache-prompt \
  -ub 2048 -b 2048 --jinja
```

## 2. Install/run

```bash
cd reader-mvp
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Open http://127.0.0.1:8765

## 3. Immediate offline smoke test

Upload `samples/smoke_story.txt` in the UI. It is synthetic and designed to contain SAY vs fact, secret B17 detail, knowledge changes, relationship changes, a scene break, and a callback.

## 4. Real benchmark texts

Fetch two public-domain books:

```bash
python scripts/fetch_samples.py
python scripts/import_samples.py
```

- `Irene Iddesleigh` — Amanda McKittrick Ros (1897), deliberately useful as the “difficult/bad prose” stress text.
- `The Adventures of Sherlock Holmes` — Arthur Conan Doyle (1892), control text with clear narration/dialogue and many claims/deductions.

Then use **Analyze next segment** and inspect `Observation ledger` + raw model output.

## What v0.1 already does

1. TXT/URL/EPUB ingestion.
2. Paragraph-addressed immutable SOURCE.
3. Dynamic-ish token-budget segmentation using the **actual llama.cpp tokenizer** when the server is online.
4. `[NN]` paragraph numbering for provenance.
5. FAST tagged extraction: `SUM WHO LOC TIME EV SAY ST KN REL TH+ TH- DET Q END`.
6. Append-only LEDGER in SQLite.
7. `END:` transition state.
8. Entities/aliases, dangling details, threads.
9. Parser contract + automatic FAST→ROBUST-A fallback + quarantine + run metrics.
10. Minimal source-grounded chat over FTS-selected raw evidence + observations.

## Intentionally not in v0.1

- `BEL/PER/DOC` extraction tags
- contradiction/claim-status engine
- arc summaries
- embeddings
- narrative-debugger UI
- Tauri packaging

## Useful endpoints

- `GET /api/health`
- `GET /api/books`
- `POST /api/import/file`
- `POST /api/import/url`
- `POST /api/books/{id}/analyze-next`
- `GET /api/books/{id}/observations`
- `POST /api/books/{id}/ask`

## Run tests

```bash
pip install -e '.[dev]'
pytest -q
```
