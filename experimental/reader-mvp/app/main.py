from __future__ import annotations
from pathlib import Path
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .db import init_db, connect
from .ingest import ingest_text, extract_url, read_epub
from .reader import analyze_next
from .query import ask
from .llama import LlamaClient

app = FastAPI(title="AI Reading Assistant MVP")
STATIC = Path(__file__).parent / 'static'
app.mount('/static', StaticFiles(directory=STATIC), name='static')

@app.on_event('startup')
def startup():
    init_db()

@app.get('/')
def index():
    return FileResponse(STATIC / 'index.html')

@app.get('/api/health')
def health():
    return {"app": True, "llama": LlamaClient().health()}

@app.get('/api/books')
def books():
    with connect() as con:
        rows = con.execute("""SELECT b.*,
          (SELECT count(*) FROM segments s WHERE s.book_id=b.id) segment_count,
          (SELECT count(*) FROM segments s WHERE s.book_id=b.id AND s.status='done') done_count,
          (SELECT count(*) FROM observations o WHERE o.book_id=b.id) obs_count
          FROM books b ORDER BY b.id DESC""").fetchall()
        return [dict(r) for r in rows]

class UrlIn(BaseModel):
    url: str
    title: str | None = None
    author: str = ''

@app.post('/api/import/url')
def import_url(inp: UrlIn):
    try:
        text = extract_url(inp.url)
        if len(text) < 500:
            raise ValueError('extracted text is too short')
        bid = ingest_text(inp.title or inp.url, text, author=inp.author, source_type='url', source_ref=inp.url)
        return {"book_id": bid}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post('/api/import/file')
async def import_file(file: UploadFile = File(...), title: str = Form(''), author: str = Form('')):
    suffix = Path(file.filename or '').suffix.lower()
    data = await file.read()
    try:
        if suffix == '.epub':
            with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as f:
                f.write(data); p = Path(f.name)
            text = read_epub(p); p.unlink(missing_ok=True)
        else:
            text = data.decode('utf-8', errors='replace')
        bid = ingest_text(title or (file.filename or 'Untitled'), text, author=author, source_type='file', source_ref=file.filename or '')
        return {"book_id": bid}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get('/api/books/{book_id}/segments')
def segments(book_id: int):
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM segments WHERE book_id=? ORDER BY idx", (book_id,)).fetchall()]

@app.get('/api/books/{book_id}/observations')
def observations(book_id: int, limit: int = 200):
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM observations WHERE book_id=? ORDER BY pos,id LIMIT ?", (book_id, limit)).fetchall()]

@app.post('/api/books/{book_id}/analyze-next')
def api_analyze_next(book_id: int):
    try:
        return analyze_next(book_id)
    except Exception as e:
        raise HTTPException(500, str(e))

class AskIn(BaseModel):
    question: str

@app.post('/api/books/{book_id}/ask')
def api_ask(book_id: int, inp: AskIn):
    try:
        return ask(book_id, inp.question)
    except Exception as e:
        raise HTTPException(500, str(e))
