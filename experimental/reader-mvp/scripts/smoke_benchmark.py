"""One-command Stage-1 smoke: ingest synthetic story and analyze one segment."""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.db import init_db, connect
from app.ingest import ingest_text
from app.reader import analyze_next
from app.llama import LlamaClient
from app.protocol import DEVELOPER_FAST

run_id = f"smoke-{time.time_ns()}"
prompt_sha = hashlib.sha256(DEVELOPER_FAST.encode("utf-8")).hexdigest()

print("run_id:", run_id)
print("prompt_sha256:", prompt_sha)

init_db()
health=LlamaClient().health()
print('llama:', health)
if not health.get('ok'):
    raise SystemExit('llama-server is offline; start it first')
text=(ROOT/'samples'/'smoke_story.txt').read_text(encoding='utf-8')
bid=ingest_text(
    'Synthetic B17 smoke story',
    text,
    author='OpenAI test fixture',
    source_type='sample',
    source_ref=run_id,
)
print('book_id:', bid)
print('source_ref:', run_id)
res=analyze_next(bid)
print(json.dumps({k:v for k,v in res.items() if k!='output'},indent=2,ensure_ascii=False))
print('\n--- RAW MODEL OUTPUT ---\n'+res.get('output',''))
with connect() as con:
    print('\n--- OBSERVATIONS ---')
    for r in con.execute('SELECT tag,payload,spans,epistemic FROM observations WHERE book_id=? ORDER BY id',(bid,)):
        print(f"{r['tag']}: {r['payload']} [{r['spans']}] {r['epistemic']}")
