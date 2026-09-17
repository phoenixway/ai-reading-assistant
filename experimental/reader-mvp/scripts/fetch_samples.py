from pathlib import Path
import re, httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'samples'
OUT.mkdir(exist_ok=True)
SOURCES = {
  'irene_iddesleigh.txt': 'https://www.gutenberg.org/cache/epub/34181/pg34181.txt',
  'sherlock_holmes.txt': 'https://www.gutenberg.org/cache/epub/48320/pg48320.txt',
}
for name,url in SOURCES.items():
    print('GET', url)
    r=httpx.get(url,follow_redirects=True,timeout=60,headers={'User-Agent':'reader-mvp/0.1'})
    r.raise_for_status()
    (OUT/name).write_text(r.text,encoding='utf-8')
    print(' ->', OUT/name, len(r.text), 'chars')
