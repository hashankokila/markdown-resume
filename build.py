#!/usr/bin/env python3
"""Markdown Resume Generator: resume.md -> dist/index.html (+ optional PDF)."""
import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path
from string import Template

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]


def parse(path: Path):
    """Read markdown and extract front matter metadata."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    meta = (yaml.safe_load(m.group(1)) if m else {}) or {}
    return meta, text[m.end():] if m else text


def contact_html(meta: dict) -> str:
    """Build HTML links for contact details."""
    def link(label, url):
        return f'<span><a href="{html.escape(url)}">{html.escape(label)}</a></span>'

    parts = []
    if meta.get("email"):
        parts.append(link(meta["email"], f"mailto:{meta['email']}"))
    if meta.get("phone"):
        parts.append(f"<span>{html.escape(str(meta['phone']))}</span>")
    if meta.get("location"):
        parts.append(f"<span>{html.escape(meta['location'])}</span>")
    if meta.get("website"):
        parts.append(link(re.sub(r"^https?://", "", meta["website"]).rstrip("/"), meta["website"]))
    if meta.get("github"):
        parts.append(link(f"github.com/{meta['github']}", f"https://github.com/{meta['github']}"))
    if meta.get("linkedin"):
        parts.append(link(f"linkedin.com/in/{meta['linkedin']}", f"https://linkedin.com/in/{meta['linkedin']}"))
    return "".join(parts)


def render(src: Path, theme: str) -> str:
    """Compile markdown into the HTML template using the selected theme CSS."""
    meta, body = parse(src)
    theme_file = ROOT / "themes" / f"{theme}.css"
    
    if not theme_file.exists():
        available = ", ".join(p.stem for p in (ROOT / "themes").glob("*.css"))
        sys.exit(f"Unknown theme '{theme}'. Available: {available}")
        
    content = markdown.markdown(body, extensions=["extra", "sane_lists", "smarty"])
    name = html.escape(meta.get("name", "Resume"))
    subtitle = f'<p class="subtitle">{html.escape(meta["title"])}</p>' if meta.get("title") else ""
    
    return Template((ROOT / "templates" / "resume.html").read_text(encoding="utf-8")).substitute(
        title=f"{name} – Resume",
        name=name,
        subtitle=subtitle,
        contact=contact_html(meta),
        css=theme_file.read_text(encoding="utf-8"),
        content=content,
    )


def make_pdf(html_path: Path, pdf_path: Path):
    """Export HTML to PDF using Chrome headless mode."""
    chrome = next((shutil.which(n) for n in CHROME_NAMES if shutil.which(n)), None)
    if not chrome:
        sys.exit("PDF export needs Chrome/Chromium on your PATH.")
    subprocess.run(
        [chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def main():
    """Handle command-line options and run the generator."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--input", default="resume.md", type=Path)
    ap.add_argument("-o", "--outdir", default="dist", type=Path)
    ap.add_argument("-t", "--theme", default="classic", help="classic | modern | your own in themes/")
    ap.add_argument("--pdf", action="store_true", help="also export resume.pdf (needs Chrome)")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    out_html = args.outdir / "index.html"
    
    # Save compiled HTML
    out_html.write_text(render(args.input, args.theme), encoding="utf-8")
    print(f"Wrote {out_html}")
    
    # Save optional PDF
    if args.pdf:
        out_pdf = args.outdir / "resume.pdf"
        make_pdf(out_html.resolve(), out_pdf.resolve())
        print(f"Wrote {out_pdf}")


if __name__ == "__main__":
    main()