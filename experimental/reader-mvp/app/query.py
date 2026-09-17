from __future__ import annotations
from .db import connect
from .llama import LlamaClient
from .textutil import fts_query

SYSTEM = """You answer questions about a book using ONLY the supplied evidence.
Separate explicit textual evidence from interpretation. If evidence is insufficient, say so.
Cite supporting span IDs in square brackets, e.g. [b1.ch001.s001.p003.x00003]."""

def ask(book_id: int, question: str) -> dict:
    q = fts_query(question)
    with connect() as con:
        book = con.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not book:
            raise KeyError(book_id)
        spans = []
        if q:
            try:
                spans = con.execute("SELECT span_id,text,bm25(spans_fts) rank FROM spans_fts WHERE book_id=? AND spans_fts MATCH ? ORDER BY rank LIMIT 10", (str(book_id), q)).fetchall()
            except Exception:
                spans = []
        if not spans:
            spans = con.execute("SELECT id span_id,text FROM spans WHERE book_id=? ORDER BY pos DESC LIMIT 8", (book_id,)).fetchall()
        obs = []
        if q:
            try:
                obs = con.execute("SELECT obs_id,payload,bm25(observations_fts) rank FROM observations_fts WHERE book_id=? AND observations_fts MATCH ? ORDER BY rank LIMIT 12", (str(book_id), q)).fetchall()
            except Exception:
                pass
        evidence = '\n\n'.join(f"[{r['span_id']}] {r['text']}" for r in spans)
        memories = '\n'.join(f"OBS {r['obs_id']}: {r['payload']}" for r in obs)
    user = f"BOOK: {book['title']}\nQUESTION: {question}\n\nSTRUCTURED MEMORY:\n{memories or '(none)'}\n\nRAW EVIDENCE:\n{evidence}"
    text, elapsed = LlamaClient().chat([{"role":"developer","content":SYSTEM},{"role":"user","content":user}], max_tokens=900, reasoning='low')
    return {"answer": text, "elapsed": elapsed, "evidence": [r['span_id'] for r in spans]}
