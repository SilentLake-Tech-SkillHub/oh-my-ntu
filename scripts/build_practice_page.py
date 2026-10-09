#!/usr/bin/env python3
"""Build one offline, gated-answer practice page from a JSON question bank.

The bank is a JSON object:
  {"course": "<课程代码>", "paper_id": "Week01-A", "version": "20260926-v1",
   "title": "...", "banner": "本地练习，非官方 Quiz/Final",
   "questions": [{"prompt": "...", "options": ["..."], "answer": [0],
                  "en": "...", "zh": "...", "source": "file · PDF p. N", "topic": "..."}]}
Declare requirements (allow_code, minimum_visual_questions), kind and requires_figure.
Use --review for fingerprint-bound semantic review or --draft for an unaccepted preview.
`answer` holds zero-based option indices; more than one index makes a multi-select item.
Fill-in items use {"type": "fill", "prompt": "...", "accept": ["normal distribution", "gaussian"], ...}
instead of options/answer; matching ignores case, punctuation and extra spaces.
Optional: "points" (positive number, default 1), "answer_basis" (post-submission label),
"prompt_image" and "prompt_image_caption" (visible before submission).
Optional per question: "image" (path relative to the bank file) and "image_caption"; the image is
embedded and shown only in the post-submission feedback, as answer evidence.
Course data lives in the bank file, never in this script.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from audit_practice_bank import RENDERER_VERSION, audit, materialize, validate

STYLE = '''<style>*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#1c2a3a;font:16px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:970px;margin:auto;padding:30px 18px 100px}.hero,.card,.result{background:#fff;border:1px solid #d9e1eb;border-radius:14px;padding:24px;margin-bottom:18px}h1{margin:4px 0;font-size:32px}h2{font-size:20px}.meta{color:#536476}.option{display:flex;gap:12px;align-items:flex-start;border:1px solid #cfdae7;border-radius:9px;padding:13px;margin:9px 0;cursor:pointer}.option:hover{border-color:#5487ba}.option:focus-within{outline:2px solid #477ab1}input{margin-top:5px}button{border:0;border-radius:8px;padding:13px 20px;font-size:16px;cursor:pointer}.primary{background:#1d5c9a;color:white}.primary:disabled{background:#aab4bf;cursor:not-allowed}.secondary{background:#e7edf4;color:#20354c}.bar{position:sticky;bottom:0;background:#fff;border-top:1px solid #d9e1eb;padding:12px;display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}.right{display:flex;gap:8px}.result{border-left:5px solid #2877ac}.wrong{border-left-color:#b04747}.correct{border-left-color:#3b8d61}.history{margin-top:20px}.history li{margin:5px 0}.fill{width:100%;padding:10px;border:1px solid #cfdae7;border-radius:8px;font-size:16px}.evidence img{max-width:100%;height:auto;border:1px solid #d9e1eb;border-radius:8px}.evidence figcaption{color:#536476;font-size:14px}code{background:#edf1f6;padding:1px 4px;border-radius:3px}a{color:#185d9e}@media(max-width:600px){main{padding:12px 10px 110px}.hero,.card,.result{padding:17px}.bar{align-items:stretch}.bar>*{width:100%}.right button{flex:1}}</style>'''

JS = r'''<script>
const QUESTIONS=__QUESTIONS__;
const COURSE=__COURSE__;
const PAPER=__PAPER__;
const VERSION=__VERSION__;
const CONTENT_METADATA=__CONTENT_METADATA__;
const KEY=`ntu-practice:${COURSE}:${PAPER}:${VERSION}:${CONTENT_METADATA.content_sha256}`;
const HIST=`ntu-practice-history:${COURSE}:${PAPER}`;
const TOTAL=QUESTIONS.reduce((n,q)=>n+(q.points??1),0);
const letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ';
let answers=Array.from({length:QUESTIONS.length},()=>[]);
let submitted=false;
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function rich(s){return esc(s).replace(/`([^`]+)`/g,'<code>$1</code>');}
function load(){try{const x=JSON.parse(localStorage.getItem(KEY));if(x&&Array.isArray(x.answers)&&x.answers.length===QUESTIONS.length){answers=x.answers.map(a=>Array.isArray(a)?a:[]);submitted=!!x.submitted;}}catch(e){}}
function save(){localStorage.setItem(KEY,JSON.stringify({version:VERSION,answers,submitted,updated:new Date().toISOString()}));}
function label(a){return a.length?a.map(i=>letters[i]).join(', '):'—';}
function norm(s){return String(s||'').toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g,' ').trim();}
function questionImage(q){return q.prompt_image?`<figure class="evidence"><img src="${esc(q.prompt_image)}" alt="${esc(q.prompt_image_caption||'Question figure')}"><figcaption>${esc(q.prompt_image_caption||'')}</figcaption></figure>`:'';}
function isFill(q){return q.type==='fill';}
function score(q,a){if(isFill(q))return q.accept.map(norm).includes(norm(a[0]))?1:0;const right=q.answer;const wrong=a.filter(i=>!right.includes(i));if(wrong.length)return 0;return a.filter(i=>right.includes(i)).length/right.length;}
function render(){
 document.getElementById('questions').innerHTML=QUESTIONS.map((q,i)=>isFill(q)?`<article class="card" id="q${i+1}"><h2>Question ${i+1} <span class="meta">· Fill in the blank</span></h2><p>${rich(q.prompt)}</p>${questionImage(q)}<input class="fill" type="text" name="q${i}" aria-label="Question ${i+1} answer" value="${esc(answers[i][0]||'')}" ${submitted?'disabled':''}><div class="feedback" id="f${i}"></div></article>`:`<article class="card" id="q${i+1}"><h2>Question ${i+1} <span class="meta">· ${q.answer.length>1?'Select all that apply':'Select one'}</span></h2><p>${rich(q.prompt)}</p>${questionImage(q)}${q.options.map((op,j)=>`<label class="option"><input aria-label="Question ${i+1} option ${letters[j]}" type="${q.answer.length>1?'checkbox':'radio'}" name="q${i}" value="${j}" ${answers[i].includes(j)?'checked':''} ${submitted?'disabled':''}><span><strong>${letters[j]}.</strong> ${rich(op)}</span></label>`).join('')}<div class="feedback" id="f${i}"></div></article>`).join('');
 document.querySelectorAll('#questions input.fill').forEach(el=>el.addEventListener('input',event=>{const i=Number(event.target.name.slice(1));const v=event.target.value;answers[i]=v.trim()?[v]:[];save();update();}));
 document.querySelectorAll('#questions input:not(.fill)').forEach(el=>el.addEventListener('change',event=>{const i=Number(event.target.name.slice(1)),j=Number(event.target.value);if(event.target.type==='radio')answers[i]=[j];else answers[i]=event.target.checked?[...answers[i],j].sort() : answers[i].filter(v=>v!==j);save();update();}));
 if(submitted)showFeedback();update();renderHistory();
}
function update(){let done=answers.filter(a=>a.length).length;document.getElementById('progress').textContent=`${done} / ${QUESTIONS.length} answered`+(submitted?' · submitted':'');document.getElementById('submit').disabled=!CONTENT_METADATA.content_reviewed||submitted||done!==QUESTIONS.length;}
function showFeedback(){let sum=0;QUESTIONS.forEach((q,i)=>{const a=answers[i],points=score(q,a);sum+=points*(q.points??1);const card=document.getElementById(`q${i+1}`);card.classList.add(points===1?'correct':'wrong');const lines=isFill(q)?`Your answer: ${esc(a[0]||'—')}<br>Accepted answers: ${q.accept.map(esc).join(' / ')}`:(()=>{const miss=q.answer.filter(v=>!a.includes(v));const extra=a.filter(v=>!q.answer.includes(v));return `Your answer: ${label(a)}<br>Correct answer: ${label(q.answer)}<br>Missed: ${label(miss)} · Incorrectly selected: ${label(extra)}`;})();const ev=q.image?`<figure class="evidence"><img src="${q.image}" alt="evidence for question ${i+1}" loading="lazy"><figcaption>${esc(q.image_caption||'')}</figcaption></figure>`:'';document.getElementById(`f${i}`).innerHTML=`<div class="result"><strong>${points===1?'Correct':'Review'} · ${(points*(q.points??1)).toFixed(2)} / ${q.points??1}</strong><p>${lines}</p>${q.answer_basis?`<p><strong>Answer basis / 答案依据:</strong> ${esc(q.answer_basis)}</p>`:''}<p><strong>Explanation (EN):</strong> ${esc(q.en)}</p><p><strong>解析（中文）：</strong> ${esc(q.zh)}</p><p><strong>Knowledge:</strong> ${esc(q.topic)}</p><p><strong>Lecture source:</strong> ${esc(q.source)}</p>${ev}</div>`;});document.getElementById('summary').innerHTML=`<div class="result"><strong>Score: ${sum.toFixed(2)} / ${TOTAL}</strong><p>${Math.round(100*sum/TOTAL)}% · All answers and sources are now visible below.</p></div>`;return sum;}
function renderHistory(){let hist=[];try{hist=JSON.parse(localStorage.getItem(HIST))||[]}catch(e){}document.getElementById('history').innerHTML=hist.length?'<h2>Submission history</h2><ol>'+hist.slice().reverse().map(h=>`<li>${esc(h.time)} · ${esc(h.score)} / ${esc(h.maxPoints??TOTAL)} · ${esc(h.version)} · wrong: ${esc(h.wrong.join(', ')||'none')}</li>`).join('')+'</ol>':'<h2>Submission history</h2><p>No submissions yet.</p>';}
document.getElementById('submit').addEventListener('click',()=>{if(!CONTENT_METADATA.content_reviewed||submitted||answers.some(a=>!a.length))return;submitted=true;const sum=showFeedback();let hist=[];try{hist=JSON.parse(localStorage.getItem(HIST))||[]}catch(e){}hist.push({time:new Date().toLocaleString(),score:sum.toFixed(2),maxPoints:TOTAL,version:VERSION,contentSha256:CONTENT_METADATA.content_sha256,answers:answers.map(a=>[...a]),optionOrder:QUESTIONS.map(q=>(q.options||[]).map((_,j)=>letters[j])),wrong:QUESTIONS.map((q,i)=>score(q,answers[i])===1?null:i+1).filter(Boolean)});localStorage.setItem(HIST,JSON.stringify(hist));save();render();document.getElementById('summary').scrollIntoView({behavior:'smooth'});});
document.getElementById('reset').addEventListener('click',()=>{if(!confirm('Reset the current attempt? Your submission history will remain.'))return;answers=Array.from({length:QUESTIONS.length},()=>[]);submitted=false;save();document.getElementById('summary').innerHTML='';render();window.scrollTo({top:0,behavior:'smooth'});});
load();render();
</script>'''


def embed_images(questions: list[dict], base: Path) -> list[dict]:
    return materialize({"questions": questions}, base)["questions"]


def render(bank: dict, base: Path = Path("."), review: dict | None = None,
           draft: bool = False) -> str:
    validate(bank)
    bank = materialize(bank, base)
    result = audit(bank, review)
    if result["automatic_errors"] or (not draft and result["status"] != "passed"):
        raise ValueError("Content acceptance failed: " + "; ".join(result["errors"]))
    questions = bank["questions"]
    metadata = {"renderer_version": RENDERER_VERSION,
                "content_sha256": result["content_sha256"],
                "content_reviewed": result["status"] == "passed" and not draft,
                "bank_fields": {k: bank.get(k) for k in ("title", "banner", "requirements")}}
    notice = ("" if metadata["content_reviewed"] else
              '<p role="status" class="result">Draft preview · 内容审核未完成，提交关闭；不能作为已验收成品交付。</p>')
    total = sum(q.get("points", 1) for q in questions)
    distribution = ", ".join(f'Q{i}: {q.get("points", 1):g}' for i, q in enumerate(questions, 1))
    title = html.escape(bank["title"])
    banner = html.escape(bank.get("banner", "本地练习，非官方 Quiz/Final"))
    qjson = json.dumps(questions, ensure_ascii=False).replace("<", "\\u003c")
    script = (JS.replace("__QUESTIONS__", qjson)
                .replace("__COURSE__", json.dumps(bank["course"]).replace("<", "\\u003c"))
                .replace("__PAPER__", json.dumps(bank["paper_id"]).replace("<", "\\u003c"))
                .replace("__VERSION__", json.dumps(bank["version"]).replace("<", "\\u003c"))
                .replace("__CONTENT_METADATA__", json.dumps(metadata, ensure_ascii=False).replace("<", "\\u003c")))
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title}</title>{STYLE}'
        f'<main><header class="hero"><div class="meta">{html.escape(bank["course"])} · {html.escape(bank["version"])} · {banner}</div>'
        f'<h1>{title}</h1>{notice}<p>{len(questions)} questions · {total:g} points total ({distribution}). Complete every question before submission. '
        'Answers and bilingual explanations appear only after submission.</p>'
        '<p class="meta">Progress and submission history are saved in this browser. For multi-select questions, an incomplete '
        'but otherwise correct selection receives proportional credit; any incorrect selection scores zero. '
        'Fill-in answers are matched against accepted variants, ignoring case and punctuation.</p></header>'
        '<div id="summary" aria-live="polite"></div><div id="questions"></div><section id="history" class="history"></section></main>'
        '<footer class="bar"><span id="progress" aria-live="polite"></span><div class="right">'
        '<button id="reset" class="secondary">Reset attempt</button><button id="submit" class="primary" disabled>Submit all</button>'
        f'</div></footer>{script}</html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bank", type=Path, help="JSON question bank")
    parser.add_argument("output", type=Path, help="HTML file to write")
    parser.add_argument("--review", type=Path, help="Fingerprint-bound semantic review JSON")
    parser.add_argument("--draft", action="store_true", help="Unaccepted preview with submission disabled")
    args = parser.parse_args()
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
    args.output.write_text(render(bank, args.bank.resolve().parent, review, args.draft), encoding="utf-8")
    print(args.output, len(bank["questions"]), "questions; browser acceptance pending")


if __name__ == "__main__":
    main()
