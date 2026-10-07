#!/usr/bin/env python3
"""Build a single-file, offline exam-briefing HTML page from a JSON data file.

Usage:
    python3 build_exam_briefing.py DATA.json OUTPUT.html [--max-width 1400]

The data file describes one course exam (see references/report-contract.md of
the exam-briefing sub-skill). Image paths inside the data file are resolved
relative to the data file and embedded as base64, so the output opens offline
and can be moved without breaking. Nothing course-specific lives in this script.

Inline text supports a tiny markup: **bold**, `code`, [label](url) and line
breaks written as "\n".
"""
import argparse
import base64
import html
import io
import json
import mimetypes
import os
import re
import sys

SOURCE_TYPES = {
    "official": ("官方书面", "badge-official"),
    "oral": ("课堂口头", "badge-oral"),
    "previous": ("往届录播", "badge-previous"),
    "local": ("本地判断", "badge-local"),
    "user": ("用户转述", "badge-user"),
}


def inline(text):
    """Escape text, then apply the tiny inline markup."""
    if text is None:
        return ""
    s = html.escape(str(text), quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
               lambda m: '<a href="%s" target="_blank" rel="noopener">%s</a>'
               % (html.escape(m.group(2), quote=True), m.group(1)), s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s.replace("\n", "<br>")


def badge(kind):
    label, cls = SOURCE_TYPES.get(kind, (kind or "", "badge-local"))
    return '<span class="badge %s">%s</span>' % (cls, html.escape(label))


def embed_image(path, max_width):
    with open(path, "rb") as fh:
        raw = fh.read()
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    try:
        from PIL import Image  # optional: shrink oversized images
        im = Image.open(io.BytesIO(raw))
        if im.width > max_width:
            im = im.convert("RGB")
            im = im.resize((max_width, round(im.height * max_width / im.width)))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=84)
            raw, mime = buf.getvalue(), "image/jpeg"
    except Exception:
        pass
    return "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))


def render_table(tbl):
    out = ['<div class="table-wrap"><table>']
    if tbl.get("caption"):
        out.append("<caption>%s</caption>" % inline(tbl["caption"]))
    out.append("<thead><tr>%s</tr></thead><tbody>" %
               "".join("<th>%s</th>" % inline(c) for c in tbl["columns"]))
    for row in tbl["rows"]:
        cells = []
        for cell in row:
            if isinstance(cell, dict) and "badge" in cell:
                cells.append("<td>%s</td>" % badge(cell["badge"]))
            else:
                cells.append("<td>%s</td>" % inline(cell))
        out.append("<tr>%s</tr>" % "".join(cells))
    out.append("</tbody></table></div>")
    return "".join(out)


def render_figures(figs, base_dir, max_width, counter):
    if not figs:
        return ""
    out = ['<div class="figs">']
    for fig in figs:
        counter[0] += 1
        fid = "fig%d" % counter[0]
        src = embed_image(os.path.join(base_dir, fig["src"]), max_width)
        cap = inline(fig.get("caption", ""))
        meta = []
        if fig.get("source"):
            meta.append(inline(fig["source"]))
        if fig.get("link"):
            meta.append('<a href="%s" target="_blank" rel="noopener">打开来源</a>'
                        % html.escape(fig["link"], quote=True))
        out.append(
            '<figure class="fig%s"><button class="zoom" data-target="%s" '
            'aria-label="放大查看">'
            '<img id="%s" src="%s" alt="%s" loading="lazy"></button>'
            '<figcaption>%s%s<span class="fig-meta">%s</span></figcaption></figure>'
            % (" wide" if fig.get("wide") else "", fid, fid, src,
               html.escape(fig.get("caption", ""), quote=True),
               badge(fig["type"]) + " " if fig.get("type") else "", cap,
               " · ".join(meta)))
    out.append("</div>")
    return "".join(out)


def render_originals(items, open_default=False):
    if not items:
        return ""
    rows = []
    for it in items:
        rows.append(
            "<tr><td>%s</td><td>%s<div class=\"where\">%s</div></td>"
            "<td class=\"en\">%s</td><td>%s</td></tr>"
            % (badge(it.get("type", "local")), inline(it.get("source", "")),
               inline(it.get("when", "")), inline(it.get("en", "")),
               inline(it.get("zh", ""))))
    return ('<details class="orig"%s><summary>原始内容对照（%d 条）</summary>'
            '<div class="table-wrap"><table><thead><tr><th>类型</th><th>出处</th>'
            '<th>原文</th><th>中文意思</th></tr></thead><tbody>%s</tbody></table>'
            "</div></details>" % (" open" if open_default else "", len(items),
                                  "".join(rows)))


CSS = """
:root{--bg:#f7f7f5;--card:#ffffff;--ink:#1d1d1f;--muted:#5f6368;--line:#e2e2de;
--accent:#0b5cad;--accent-soft:#e8f0fb;--ok:#1d7a46;--ok-soft:#e5f4ea;--warn:#9a5b00;
--warn-soft:#fdf1dd;--bad:#a12622;--bad-soft:#fbe7e6;--plain:#5b5f97;--plain-soft:#ecedf8;
--code:#f0f0ec}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141518;--card:#1d1f23;
--ink:#ececec;--muted:#a3a7ad;--line:#2e3137;--accent:#7fb2ee;--accent-soft:#1d2a3a;
--ok:#7fd3a0;--ok-soft:#18301f;--warn:#f0c070;--warn-soft:#352812;--bad:#f19a95;
--bad-soft:#3a1d1c;--plain:#b4b7ef;--plain-soft:#25263c;--code:#2a2c31}}
:root[data-theme="dark"]{--bg:#141518;--card:#1d1f23;--ink:#ececec;--muted:#a3a7ad;
--line:#2e3137;--accent:#7fb2ee;--accent-soft:#1d2a3a;--ok:#7fd3a0;--ok-soft:#18301f;
--warn:#f0c070;--warn-soft:#352812;--bad:#f19a95;--bad-soft:#3a1d1c;--plain:#b4b7ef;
--plain-soft:#25263c;--code:#2a2c31}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 -apple-system,
BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Segoe UI",sans-serif}
a{color:var(--accent)}
code{background:var(--code);padding:0 .3em;border-radius:4px;font-size:.92em;word-break:break-all}
.wrap{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
header.top{padding:8px 0 16px;border-bottom:1px solid var(--line);margin-bottom:20px}
header.top h1{font-size:1.65rem;line-height:1.3;margin:0 0 6px}
header.top .sub{color:var(--muted);margin:0}
.status{margin:14px 0 0;padding:10px 14px;border-left:4px solid var(--warn);background:var(--warn-soft);
border-radius:6px}
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card .k{color:var(--muted);font-size:.85rem;margin-bottom:2px}
.card .v{font-weight:600}
nav.toc{position:sticky;top:0;z-index:5;background:var(--bg);padding:8px 0;margin:0 0 12px;
border-bottom:1px solid var(--line);display:flex;gap:6px;overflow-x:auto;white-space:nowrap}
nav.toc a{display:inline-block;padding:4px 10px;border:1px solid var(--line);border-radius:999px;
text-decoration:none;color:var(--ink);background:var(--card);font-size:.88rem}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 18px 8px;
margin:0 0 22px;scroll-margin-top:56px}
section h2{margin:0 0 6px;font-size:1.3rem}
section .intro{color:var(--muted);margin:0 0 12px}
h3.sub{font-size:1rem;margin:18px 0 8px}
.table-wrap{width:100%;overflow-x:auto;margin:0 0 14px;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;min-width:560px;font-size:.92rem}
caption{text-align:left;padding:8px 10px;font-weight:600;color:var(--muted)}
th,td{padding:8px 10px;border-top:1px solid var(--line);text-align:left;vertical-align:top}
thead th{background:var(--accent-soft);border-top:none;white-space:nowrap}
tbody td:first-child{min-width:5em}
td.en{font-family:ui-serif,Georgia,"Times New Roman",serif;font-style:italic}
.where{color:var(--muted);font-size:.82rem}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.78rem;font-weight:600;
white-space:nowrap;vertical-align:1px}
.badge-official{background:var(--ok-soft);color:var(--ok)}
.badge-oral{background:var(--accent-soft);color:var(--accent)}
.badge-previous{background:var(--warn-soft);color:var(--warn)}
.badge-local{background:var(--plain-soft);color:var(--plain)}
.badge-user{background:var(--bad-soft);color:var(--bad)}
.figs{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;margin:6px 0 16px}
.fig{margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--bg)}
.fig.wide{grid-column:1/-1}
.fig button.zoom{display:block;width:100%;padding:0;border:0;background:none;cursor:zoom-in}
.fig img{display:block;width:100%;height:auto}
.fig figcaption{padding:8px 10px;font-size:.86rem}
.fig-meta{display:block;color:var(--muted);font-size:.8rem;margin-top:2px}
.notes{margin:0 0 14px;padding-left:1.2em}
.notes li{margin:4px 0}
details.orig{margin:4px 0 16px;border:1px dashed var(--line);border-radius:8px;padding:6px 10px}
details.orig summary{cursor:pointer;font-weight:600;color:var(--accent)}
details.orig .table-wrap{margin-top:8px}
footer{color:var(--muted);font-size:.85rem;margin-top:24px}
#lightbox{border:0;padding:0;background:transparent;max-width:96vw;max-height:96vh}
#lightbox::backdrop{background:rgba(0,0,0,.82)}
#lightbox img{max-width:96vw;max-height:92vh;display:block;border-radius:6px}
#lightbox .close{position:fixed;top:12px;right:16px;font-size:28px;color:#fff;background:none;border:0;
cursor:pointer}
.theme-toggle{float:right;border:1px solid var(--line);background:var(--card);color:var(--ink);
border-radius:999px;padding:4px 12px;cursor:pointer;font-size:.85rem}
@media (max-width:600px){header.top h1{font-size:1.3rem}section{padding:14px 12px 6px}
.figs{grid-template-columns:1fr}table{min-width:520px}}
@media print{nav.toc,.theme-toggle{display:none}details.orig{border:0}section{break-inside:avoid-page}}
"""

JS = """
(function(){
 var root=document.documentElement;
 try{var t=localStorage.getItem('exam-brief-theme');if(t)root.setAttribute('data-theme',t);}catch(e){}
 var tb=document.querySelector('.theme-toggle');
 if(tb)tb.addEventListener('click',function(){
  var dark=root.getAttribute('data-theme')==='dark'||(!root.getAttribute('data-theme')&&
   window.matchMedia('(prefers-color-scheme: dark)').matches);
  var next=dark?'light':'dark';root.setAttribute('data-theme',next);
  try{localStorage.setItem('exam-brief-theme',next);}catch(e){}
 });
 var dlg=document.getElementById('lightbox'),big=document.getElementById('lightbox-img');
 document.querySelectorAll('button.zoom').forEach(function(b){
  b.addEventListener('click',function(){
   var img=document.getElementById(b.getAttribute('data-target'));
   big.src=img.src;big.alt=img.alt;
   if(dlg.showModal)dlg.showModal();else window.open(img.src);
  });
 });
 if(dlg){dlg.addEventListener('click',function(){dlg.close();});}
 window.addEventListener('beforeprint',function(){
  document.querySelectorAll('details.orig').forEach(function(d){d.open=true;});
 });
})();
"""


def build(data, base_dir, max_width):
    counter = [0]
    parts = []
    title = data["title"]
    parts.append('<header class="top"><button class="theme-toggle" type="button">'
                 '切换深浅色</button><h1>%s</h1><p class="sub">%s</p>%s</header>'
                 % (inline(title), inline(data.get("subtitle", "")),
                    '<p class="status">%s</p>' % inline(data["status_note"])
                    if data.get("status_note") else ""))
    if data.get("summary"):
        parts.append('<div class="summary">%s</div>' % "".join(
            '<div class="card"><div class="k">%s</div><div class="v">%s</div></div>'
            % (inline(c["label"]), inline(c["value"])) for c in data["summary"]))
    sections = data["sections"]
    parts.append('<nav class="toc" aria-label="目录">%s</nav>' % "".join(
        '<a href="#%s">%s</a>' % (html.escape(s["id"], quote=True),
                                  inline(s.get("short", s["title"])))
        for s in sections))
    for s in sections:
        body = ['<section id="%s"><h2>%s</h2>' % (html.escape(s["id"], quote=True),
                                                    inline(s["title"]))]
        if s.get("intro"):
            body.append('<p class="intro">%s</p>' % inline(s["intro"]))
        for block in s.get("blocks", []):
            if block.get("heading"):
                body.append('<h3 class="sub">%s</h3>' % inline(block["heading"]))
            if block.get("table"):
                body.append(render_table(block["table"]))
            if block.get("figures"):
                body.append(render_figures(block["figures"], base_dir, max_width, counter))
            if block.get("notes"):
                body.append('<ul class="notes">%s</ul>' % "".join(
                    "<li>%s</li>" % inline(n) for n in block["notes"]))
            if block.get("originals"):
                body.append(render_originals(block["originals"],
                                             block.get("originals_open", False)))
        body.append("</section>")
        parts.append("".join(body))
    if data.get("footer"):
        parts.append("<footer>%s</footer>" % inline(data["footer"]))
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title><style>%s</style></head><body><div class=\"wrap\">%s</div>"
            "<dialog id=\"lightbox\"><button class=\"close\" aria-label=\"关闭\">×</button>"
            "<img id=\"lightbox-img\" alt=\"\"></dialog><script>%s</script></body></html>"
            % (html.escape(data.get("page_title", title)), CSS, "".join(parts), JS))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("data")
    ap.add_argument("output")
    ap.add_argument("--max-width", type=int, default=1400)
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as fh:
        data = json.load(fh)
    page = build(data, os.path.dirname(os.path.abspath(args.data)), args.max_width)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("wrote %s (%d bytes)" % (args.output, len(page.encode("utf-8"))))


if __name__ == "__main__":
    sys.exit(main())
