#!/usr/bin/env python3
"""Build a searchable, offline HTML reader from complete page-paired notebooks.

The HTML references the notebooks' existing local page-image folders. It never
rewrites the notebooks or images. Run with `uv run --with markdown-it-py`.
"""

import argparse
import html
import json
import re
from pathlib import Path

from markdown_it import MarkdownIt


IMAGE = re.compile(r"!\[[^]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^##\s+(.+)$", re.M)
ANCHOR = re.compile(r"<a\s+id=[\"'][^\"']+[\"']\s*></a>")


def cell_text(cell):
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


def notebook_pages(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = data.get("cells", [])
    if not cells or len(cells) % 2 != 1:
        raise ValueError(f"Expected introduction plus page pairs: {path}")
    intro = cell_text(cells[0])
    pairs = []
    for offset in range(1, len(cells), 2):
        original = cell_text(cells[offset])
        translation = cell_text(cells[offset + 1])
        image_paths = IMAGE.findall(original)
        if len(image_paths) != 1 or not translation.strip():
            raise ValueError(f"Invalid page pair at cells {offset}-{offset + 1}: {path}")
        image = path.parent / image_paths[0]
        if not image.is_file() or image.is_symlink():
            raise FileNotFoundError(f"Missing or linked original image: {image}")
        heading = HEADING.search(original)
        if not heading:
            raise ValueError(f"Page heading missing at cell {offset}: {path}")
        pairs.append((heading.group(1), ANCHOR.sub("", original), translation))
    return intro, pairs


def build(title, output, inputs):
    md = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable("table")
    sections = []
    total = 0
    for chapter_index, path in enumerate(inputs, 1):
        if path.parent != output.parent:
            raise ValueError("Reader must be beside all notebooks and their image folders")
        intro, pages = notebook_pages(path)
        label = re.search(r"^#\s+(.+)$", intro, re.M)
        label = label.group(1) if label else path.stem
        chapter_id = f"chapter-{chapter_index}"
        page_html = []
        page_links = []
        for index, (heading, original, translation) in enumerate(pages, 1):
            page_id = f"{chapter_id}-page-{index}"
            page_links.append(f'<a href="#{page_id}">{html.escape(heading)}</a>')
            page_html.append(
                f'<article class="page-card" id="{page_id}" data-search="{html.escape((heading + " " + translation).lower(), quote=True)}">'
                f'<div class="page-head"><span>{html.escape(label)}</span><strong>{html.escape(heading)}</strong></div>'
                f'<div class="original">{md.render(original)}</div>'
                f'<div class="translation">{md.render(translation)}</div>'
                '</article>'
            )
        sections.append((chapter_id, label, intro, page_links, page_html, path.name))
        total += len(pages)

    navigation = "".join(
        f'<details><summary><a href="#{cid}">{html.escape(label)}</a> <small>{len(pages)} 页</small></summary>'
        f'<div class="page-links">{"".join(links)}</div></details>'
        for cid, label, _, links, pages, _ in sections
    )
    content = "".join(
        f'<section class="chapter" id="{cid}"><header><p class="eyebrow">来源 Notebook：{html.escape(filename)}</p>'
        f'<h2>{html.escape(label)}</h2><details class="source-note"><summary>查看原 Notebook 的来源与使用说明</summary>{md.render(intro)}</details></header>'
        f'{"".join(pages)}</section>'
        for cid, label, intro, _, pages, filename in sections
    )
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--ink:#182433;--muted:#5e6c7b;--line:#d8e0e8;--paper:#fff;--bg:#f5f7fa;--accent:#325eaa}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.layout{{display:grid;grid-template-columns:290px minmax(0,1fr);max-width:1700px;margin:auto}}aside{{position:sticky;top:0;height:100vh;overflow:auto;background:#fff;border-right:1px solid var(--line);padding:24px 18px}}
aside h1{{font-size:1.1rem;line-height:1.35;margin:0 0 10px}}aside p,.eyebrow{{color:var(--muted);font-size:.85rem}}input{{width:100%;padding:11px 12px;border:1px solid #aebbc8;border-radius:8px;font:inherit}}
aside details{{border-top:1px solid var(--line);padding:9px 0}}summary{{cursor:pointer}}aside summary{{font-weight:650}}aside summary a{{color:inherit;text-decoration:none}}small{{font-weight:400;color:var(--muted)}}.page-links{{display:grid;margin:8px 0 4px 10px;gap:4px}}
.page-links a{{color:#42556d;text-decoration:none;font-size:.83rem;padding:3px 5px;border-radius:5px}}.page-links a:hover{{background:#eaf0f8}}main{{min-width:0;padding:34px clamp(20px,4vw,70px)}}main>header{{max-width:1000px;margin:0 auto 46px}}main>header h1{{font-size:clamp(1.7rem,3vw,2.5rem);line-height:1.25}}
.chapter{{max-width:1100px;margin:0 auto 70px}}.chapter>header{{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:22px}}.chapter h2{{font-size:1.8rem;line-height:1.3}}.source-note{{background:#ecf2f9;padding:9px 15px;border-radius:9px}}
.page-card{{background:var(--paper);border:1px solid var(--line);border-radius:12px;margin:20px 0;padding:24px;box-shadow:0 3px 14px #23374b0a;scroll-margin-top:18px}}.page-head{{display:grid;gap:4px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:18px}}.page-head span{{color:var(--muted);font-size:.8rem}}.page-head strong{{font-size:1.08rem}}
.original img{{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:5px}}.original h2{{display:none}}.translation{{border-top:1px solid var(--line);padding-top:14px;margin-top:16px}}.translation h3{{margin-top:0}}p,li{{overflow-wrap:anywhere}}table{{border-collapse:collapse;display:block;overflow:auto;max-width:100%}}th,td{{border:1px solid var(--line);padding:7px 10px;text-align:left;min-width:70px}}th{{background:#f0f4f8}}pre{{overflow:auto;background:#14253a;color:#f7fbff;padding:14px;border-radius:7px}}code{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}a{{color:var(--accent)}}.hidden{{display:none!important}}.status{{font-size:.85rem;color:var(--muted);margin:8px 0 14px}}
@media(max-width:850px){{.layout{{display:block}}aside{{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}}aside details{{display:none}}main{{padding:20px 12px}}.page-card{{padding:14px}}}}
</style></head><body><div class="layout"><aside><h1>{html.escape(title)}</h1><p>原页图片紧邻可编辑中文；共 {total} 页。图片引用同目录实体资源，不访问网络。</p><label for="search">搜索页标题或中文内容</label><input id="search" type="search" placeholder="输入概念、术语或页码"><div class="status" id="status">显示全部 {total} 页</div><nav>{navigation}</nav></aside>
<main><header><p class="eyebrow">课程资料 · 逐页阅读总册</p><h1>{html.escape(title)}</h1><p>每页先显示教师原页图片，再显示既有 Notebook 中可选择、可搜索的中文文字。页码与来源保留在原 Notebook 的每章说明中；这是阅读版本，不替换原始课件或 Notebook。</p></header>{content}</main></div>
<script>const cards=[...document.querySelectorAll('.page-card')],search=document.querySelector('#search'),status=document.querySelector('#status');search.addEventListener('input',()=>{{const q=search.value.trim().toLowerCase();let visible=0;for(const card of cards){{const show=!q||card.dataset.search.includes(q);card.classList.toggle('hidden',!show);if(show)visible++}}status.textContent=`显示 ${{visible}} / ${{cards.length}} 页`;}});</script></body></html>'''
    output.write_text(document, encoding="utf-8")
    print(f"output={output} chapters={len(sections)} pages={total} bytes={output.stat().st_size}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("notebooks", nargs="+", type=Path)
    args = parser.parse_args()
    build(args.title, args.output, args.notebooks)
