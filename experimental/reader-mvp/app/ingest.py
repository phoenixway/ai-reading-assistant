from __future__ import annotations
import re
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
import zipfile
from .db import tx
from .llama import LlamaClient
from .segmenter import parse_paras, plan_segments
from .config import settings

GUT_START = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S)
GUT_END = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*", re.I | re.S)

def clean_gutenberg(text: str) -> str:
    m = GUT_START.search(text)
    if m:
        text = text[m.end():]
    text = GUT_END.sub('', text)
    return text.strip()

def read_epub(path: Path) -> str:
    chunks = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(('.xhtml','.html','.htm'))]
        for name in names:
            try:
                raw = z.read(name)
                soup = BeautifulSoup(raw, 'html.parser')
                txt = soup.get_text('\n', strip=True)
                if len(txt) > 40:
                    chunks.append(txt)
            except Exception:
                continue
    return '\n\n'.join(chunks)

def extract_url(url: str) -> str:
    r = httpx.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": "ReaderMVP/0.1"})
    r.raise_for_status()
    ctype = r.headers.get('content-type', '')
    if 'text/plain' in ctype or url.lower().endswith('.txt'):
        return clean_gutenberg(r.text)
    soup = BeautifulSoup(r.text, 'html.parser')
    for bad in soup(['script','style','nav','header','footer','aside','form']):
        bad.decompose()
    root = soup.find('article') or soup.find('main') or soup.body or soup
    return root.get_text('\n', strip=True).strip()

def ingest_text(title: str, text: str, *, author: str = '', source_type: str = 'text', source_ref: str = '') -> int:
    llama = LlamaClient()
    paras = parse_paras(clean_gutenberg(text), llama)
    plans = plan_segments(paras, settings.target_segment_tokens)
    with tx() as con:
        cur = con.execute("INSERT INTO books(title,author,source_type,source_ref) VALUES(?,?,?,?)", (title, author, source_type, source_ref))
        book_id = int(cur.lastrowid)
        pos = 0
        span_ids_by_obj = {}
        for p in paras:
            pos += 1
            sid = f"b{book_id}.ch{p.chapter:03}.s{p.scene:03}.p{p.para:03}.x{pos:05}"
            span_ids_by_obj[id(p)] = (sid, pos)
            con.execute("INSERT INTO spans(id,book_id,pos,chapter,scene,para,tok_len,text) VALUES(?,?,?,?,?,?,?,?)",
                        (sid, book_id, pos, p.chapter, p.scene, p.para, p.tok_len, p.text))
            con.execute("INSERT INTO spans_fts(span_id,book_id,text) VALUES(?,?,?)", (sid, book_id, p.text))
        for idx, plan in enumerate(plans, 1):
            refs = [span_ids_by_obj[id(p)] for p in plan.paras]
            seg_id = f"b{book_id}.seg{idx:04}"
            con.execute("INSERT INTO segments(id,book_id,idx,chapter,start_pos,end_pos,tok_len) VALUES(?,?,?,?,?,?,?)",
                        (seg_id, book_id, idx, plan.chapter, refs[0][1], refs[-1][1], plan.tok_len))
            for local_no, (sid, _) in enumerate(refs, 1):
                con.execute("INSERT INTO segment_spans(seg_id,span_id,local_no) VALUES(?,?,?)", (seg_id, sid, local_no))
    return book_id
