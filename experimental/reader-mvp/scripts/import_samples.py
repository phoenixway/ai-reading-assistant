from pathlib import Path
from app.db import init_db
from app.ingest import ingest_text
ROOT=Path(__file__).resolve().parents[1]
init_db()
for fn,title,author in [
 ('irene_iddesleigh.txt','Irene Iddesleigh','Amanda McKittrick Ros'),
 ('sherlock_holmes.txt','The Adventures of Sherlock Holmes','Arthur Conan Doyle'),
]:
 p=ROOT/'samples'/fn
 if not p.exists():
  print('missing',p,'; run scripts/fetch_samples.py first'); continue
 bid=ingest_text(title,p.read_text(encoding='utf-8'),author=author,source_type='sample',source_ref=str(p))
 print('imported',title,'as book',bid)
