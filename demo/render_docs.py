"""Regenerate offline documentation with Python-Markdown 3.11 (authoring only)."""
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]
CSS = '''
:root{color-scheme:light;--paper:#f5f1e8;--ink:#243a31;--muted:#59675e;--line:#d5d8cc;--accent:#8a4833}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);overflow-wrap:anywhere;font:17px/1.7 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.brand{max-width:840px;margin:0 auto;padding:42px 28px 22px;display:flex;gap:14px;align-items:center;border-bottom:1px solid var(--line);letter-spacing:.13em;font-size:12px;text-transform:uppercase;font-weight:750}
.brand svg{width:32px;height:40px;flex:none}main{max-width:840px;padding:32px 28px 80px;margin:auto}h1{font-family:Georgia,serif;font-size:clamp(36px,7vw,58px);font-weight:400;line-height:1.08;letter-spacing:-.04em;margin:10px 0 30px}h2{font-family:Georgia,serif;font-size:29px;font-weight:400;line-height:1.25;margin:46px 0 18px}p{margin:0 0 19px}a{color:var(--accent);text-underline-offset:3px}a:focus-visible{outline:3px solid var(--accent);outline-offset:4px}code{font-size:.85em;background:#e8eadf;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{padding:20px;background:#e8eadf;white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid var(--line)}pre code{padding:0}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.55;margin:28px 0}th:first-child{min-width:4em}th{text-align:left;font-size:12px;letter-spacing:.03em;background:#e8eadf}th,td{padding:13px 10px;vertical-align:top;border-bottom:1px solid var(--line);overflow-wrap:anywhere}li{margin-bottom:9px}footer{max-width:784px;margin:0 auto 40px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}@media(max-width:500px){body{font-size:16px}.brand{padding:26px 20px 18px}main{padding:24px 20px 50px}h2{font-size:26px}table{font-size:12px}th,td{padding:10px 6px}footer{margin:0 20px 30px}}@media print{body{background:white}main{padding-top:0}a{color:inherit}h2{break-after:avoid}tr{break-inside:avoid}}
'''

for name, lang in [('FEATURES', 'ru'), ('README', 'en')]:
    content = markdown.markdown((ROOT / (name + '.md')).read_text(), extensions=['tables', 'fenced_code', 'sane_lists'])
    html = f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Juniper Tablekeeper · {name}</title><style>{CSS}</style></head>
<body><div class="brand"><svg viewBox="0 0 32 40" aria-hidden="true"><path d="M16 37V6M16 18C4 18 3 8 4 3c9 1 13 7 12 15Zm0 10c12 0 13-10 12-15-9 1-13 7-12 15Z" fill="none" stroke="currentColor" stroke-width="1.7"/></svg><span>Juniper · Tablekeeper<br>Dark Factory / Local delivery</span></div><main>{content}</main><footer>Fresh BAND room · e04c2728-8535-41c8-be50-88eb8068fa09 · Offline document</footer></body></html>'''
    (ROOT / (name + '.html')).write_text(html)
    assert 'https://' not in html and '<script src=' not in html
    print(name + '.html', len(html.encode()), 'bytes')
