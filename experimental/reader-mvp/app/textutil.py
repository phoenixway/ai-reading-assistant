from __future__ import annotations
import re
import unicodedata

CHAPTER_RE = re.compile(r"^\s*(?:chapter|глава|розділ|частина)\s+([\divxlcdm]+)\b", re.I)
SCENE_BREAK_RE = re.compile(r"^\s*(?:\*\s*\*\s*\*|\*{3,}|—{3,}|-{3,}|⁂)\s*$")

STOP = {
    'the','a','an','and','or','but','to','of','in','on','at','for','with','from','by','is','was','were','be','been',
    'this','that','these','those','he','she','it','they','we','i','you','his','her','their','our','my','your',
    'і','й','та','або','але','в','у','на','до','з','із','зі','від','для','про','що','це','той','та','він','вона','вони'
}

def norm(s: str) -> str:
    s = unicodedata.normalize('NFKC', s).casefold()
    s = re.sub(r"[^\w'’-]+", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()

def slug(s: str) -> str:
    x = norm(s).replace(' ', '_')
    return x[:64] or 'entity'

def paragraphs(text: str) -> list[str]:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Preserve headings as standalone blocks; collapse wrapped prose lines inside blocks.
    blocks = re.split(r"\n\s*\n+", text)
    out = []
    for b in blocks:
        b = re.sub(r"[ \t]+", " ", b.strip())
        b = re.sub(r"\n(?=\S)", " ", b)
        if b:
            out.append(b)
    return out

def fts_query(text: str, limit: int = 8) -> str:
    toks = [norm(x) for x in re.findall(r"[\w'’-]+", text, re.UNICODE)]
    toks = [t for t in toks if len(t) >= 3 and t not in STOP]
    uniq = []
    for t in toks:
        if t not in uniq:
            uniq.append(t)
    return ' OR '.join(f'"{t.replace(chr(34), "")}"' for t in uniq[:limit])
