"""Read-only offline guide checks; these are not product qualification tests."""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from html import unescape
import json
import os
from pathlib import Path
import re
import subprocess

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "25ade1c7add9a5701a511e07f79a619a3cb21b51"
PROTECTED = "301caf55085280f12197e393ab6b4735ef4046c3"
BASELINE = "e0b67afeac133c48be4cabbdb6012442b6be3fc4"
EVIDENCE = "96329db1347c0e8b555282e22a35785643020d04"
GATE = "693f9ec5d4c2df6353a15f002ffb601bf765d13a"
DOCS = ["README.md", "README.html", "FEATURES.md", "FEATURES.html",
        "demo/DEMO.md", "demo/VIDEO-STORYBOARD.md", "demo/SUBMISSION-DRAFT.md",
        "demo/presentation.html", "demo/HISTORY.md"]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src"):
                self.links.append(value)


def main():
    attempt = ROOT / "demo/checks" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-guide-consolidation")
    attempt.mkdir(parents=True)
    results = []
    result = {"kind": "documentation-only", "product_candidate": CANDIDATE,
              "head_before_check": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "results": results,
              "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in DOCS + ["demo/check_guides.py", "demo/render_docs.py"]}}
    try:
        parser_links = []
        for name in DOCS:
            path = ROOT / name
            source = path.read_text()
            parsed = Links()
            parsed.feed(markdown.markdown(source, extensions=["tables", "fenced_code"]) if path.suffix == ".md" else source)
            for link in parsed.links:
                if link.startswith(("http:", "https:", "data:", "#", "mailto:")):
                    continue
                target = (path.parent / link.split("#", 1)[0]).resolve()
                assert target.exists(), (name, link)
                parser_links.append({"source": name, "target": link})
            assert all(v in source for v in (CANDIDATE, EVIDENCE, GATE)), name
            if name.endswith('.html'):
                assert not re.search(r'(?:src|href)=["\']https?://', source), name
        results.append({"check": "local-links-and-current-status", "links": len(parser_links), "status": "PASS"})
        result["links"] = parser_links
        endpoints = lambda name: set(re.findall(r"\| `(GET|POST|PATCH) ([^`]+)` \|", (ROOT / name).read_text()))
        assert endpoints("README.md") == endpoints("FEATURES.md")
        assert len(endpoints("README.md")) == 24
        for name in ("README.html", "FEATURES.html"):
            html_routes = set(re.findall(r'<code>(GET|POST|PATCH) ([^<]+)</code>', (ROOT / name).read_text()))
            html_routes = {(method, unescape(path)) for method, path in html_routes}
            assert endpoints("README.md") <= html_routes, name
            assert all(route in (ROOT / name).read_text() for route in ("/signup", "/login", "/lookup", "204 No Content")), name
        results.append({"check": "english-russian-markdown-html-endpoint-parity", "routes": 24, "screen_routes": 4, "status": "PASS"})
        result["endpoint_catalog"] = sorted(endpoints("README.md"))
        stages = ["stage-1", "stage-2", "stage-3", "stage-4"]
        subprocess.run(["git", "diff", "--exit-code", CANDIDATE, "--", *stages], cwd=ROOT, check=True, capture_output=True)
        assert not subprocess.check_output(["git", "status", "--porcelain", "--", *stages], cwd=ROOT, text=True)
        subprocess.run(["git", "diff", "--exit-code", PROTECTED, "--", "stage-1", "stage-2", "stage-3"], cwd=ROOT, check=True, capture_output=True)
        results.append({"check": "candidate-contexts-and-protected-stages-unchanged", "status": "PASS"})
        old_sources = {name: subprocess.check_output(["git", "show", BASELINE + ":" + name], cwd=ROOT).decode()
                       for name in DOCS if name != "demo/HISTORY.md"}
        before = {"revision": BASELINE,
                  "hashes": {name: hashlib.sha256(source.encode()).hexdigest() for name, source in old_sources.items()},
                  "commit_references": sorted(set(re.findall(r"\b[0-9a-f]{40}\b", "\n".join(old_sources.values())))),
                  "embedded_image_hashes": [hashlib.sha256(x.encode()).hexdigest() for x in re.findall(r'data:image/[^"\s]+', old_sources["demo/presentation.html"])]}
        current = "\n".join((ROOT / p).read_text() for p in DOCS)
        assert set(before["commit_references"]) <= set(re.findall(r"\b[0-9a-f]{40}\b", current))
        image_hashes = [hashlib.sha256(x.encode()).hexdigest() for x in re.findall(r'data:image/[^"\s]+', (ROOT / "demo/presentation.html").read_text())]
        assert image_hashes == before["embedded_image_hashes"]
        result["before"] = before
        results.append({"check": "historical-revisions-and-real-capture-retained", "revision_references": len(before["commit_references"]), "status": "PASS"})
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            result["browser"] = browser.version
            for width in (375, 1360):
                page = browser.new_page(viewport={"width": width, "height": 900})
                for name in ("README.html", "FEATURES.html", "demo/presentation.html"):
                    page.goto((ROOT / name).as_uri())
                    for slide in range(1, 7 if name.endswith("presentation.html") else 2):
                        if slide > 1:
                            page.locator("#next").click()
                        dims = page.evaluate("({width: innerWidth, scroll: document.documentElement.scrollWidth})")
                        assert dims["scroll"] == dims["width"], (name, width, slide, dims)
                        results.append({"check": "browser-width", "file": name, "width": width, "page": slide, "geometry": dims, "status": "PASS"})
                    if name.endswith("presentation.html"):
                        page.screenshot(path=str(attempt / f"last-slide-{width}.png"), full_page=True)
                    else:
                        page.screenshot(path=str(attempt / f"{Path(name).stem}-{width}.png"))
                page.close()
            browser.close()
        result["status"] = "PASS"
    except BaseException as error:
        result["status"] = "ERROR"
        result["error"] = repr(error)
        raise
    finally:
        (attempt / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(attempt)


if __name__ == "__main__":
    main()
