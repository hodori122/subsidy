"""drafts/*.json → docs/ 에 모바일 미리보기·복사 페이지 생성 (GitHub Pages 로 공개)"""
import os, glob, json, html, re

DOCS = "docs"

CSS = """
:root{--bg:#f5f7f6;--card:#fff;--ink:#1b2421;--muted:#66726d;--line:#e1e7e4;--accent:#0f766e;--on:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#101614;--card:#18201d;--ink:#e8eeeb;--muted:#93a19b;--line:#27322e;--accent:#2dd4bf;--on:#06201c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;word-break:keep-all;
padding:env(safe-area-inset-top) 0 calc(90px + env(safe-area-inset-bottom))}
a{color:var(--accent)}.wrap{max-width:720px;margin:0 auto;padding:16px}
h1{font-size:20px;line-height:1.4;margin:6px 0 12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:12px 0}
.label{font-size:13px;color:var(--muted);margin-bottom:4px}
.row{display:flex;gap:8px;align-items:flex-start}.row .v{flex:1;min-width:0;overflow-wrap:anywhere}
button{font:inherit;font-size:14px;font-weight:600;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:8px 12px;white-space:nowrap}
.bar{position:fixed;left:0;right:0;bottom:0;display:flex;gap:8px;padding:10px 12px calc(10px + env(safe-area-inset-bottom));background:var(--card);border-top:1px solid var(--line)}
.bar button{flex:1;padding:12px}.bar .main{background:var(--accent);color:var(--on);border-color:var(--accent)}
.body table{border-collapse:collapse;width:100%;font-size:14px;display:block;overflow-x:auto}
.body th,.body td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}
.body h2{font-size:19px;border-bottom:2px solid var(--accent);padding-bottom:4px;margin-top:28px}
.body h3{font-size:17px}
.toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:20px;font-size:14px;opacity:0;transition:opacity .2s;pointer-events:none}
.toast.on{opacity:1}
.list a{display:block;text-decoration:none;color:var(--ink)}.list .t{font-weight:600;line-height:1.45}
.list .d{font-size:13px;color:var(--muted)}.done{opacity:.45}.chk{color:var(--accent);font-weight:700}
label.mark{display:flex;gap:8px;align-items:center;font-weight:600}
"""

import yaml as _yaml
_CFG = _yaml.safe_load(open("config.yaml", encoding="utf-8"))

PROMPT = """아래는 정부 지원금·금리·청약 안내 블로그 초안이야. 이걸 사람이 직접 쓴 것처럼 자연스럽게 다듬고, 운영자의 생각이 담긴 문단을 추가해줘.

[운영자 설정]
""" + (_CFG.get("author_profile") or "지원금·금리·청약 정보를 직접 찾아보고 정리하는 블로그 운영자. 말투는 존댓말, 친근하지만 가볍지 않게.") + """

[지켜야 할 것]
1. 금액, 대상 조건, 기한, 기관명, 링크는 절대 바꾸거나 새로 지어내지 마. 원문에 없는 정보가 필요하면 "공고 확인 필요"라고 써.
2. h2, h3, 표, 링크 같은 HTML 구조는 그대로 유지해. 출력은 HTML만, 설명이나 코드 표시 없이.
3. 공고문 말투를 옆집 아는 사람이 설명해 주듯 풀어 써. 조건을 뭉뚱그리지 말고 숫자는 정확히 남겨.
4. 서두 두 문단은 통째로 새로 써. 이 지원이 왜 쓸만한지, 어떤 사람한테 특히 좋은지로 시작해.
5. 운영자 생각 문단을 2곳 추가해. 위치는 본문 중간(지원 내용이나 표 다음)과 신청 방법 다음. 각 2~4문장. 내용은 이런 것들로:
   - 조건을 보고 느낀 점 (예: "소득 기준이 생각보다 넉넉해서 맞벌이도 해볼 만합니다")
   - 신청할 때 헷갈릴 만한 부분과 그 이유
   - 비슷한 지원과 비교했을 때의 장단점
   - 어떤 사람은 서두르고 어떤 사람은 안 해도 되는지
   단, "제가 신청해 봤더니", "제 주변 사람이 받았는데" 같은 직접 경험담은 쓰지 마. 정보를 읽고 판단한 의견만 써.
6. "무조건", "100%", "꼭 받으세요" 같은 과장은 쓰지 마.
7. 이모지는 한두 개 이하. 글 전체 길이는 원문의 1.2배 이내.

[초안]
"""

JS = """
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('on');setTimeout(()=>t.classList.remove('on'),1600)}
function fallbackCopy(text){const ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove()}
async function copyText(id,msg){const v=document.getElementById(id).textContent;try{await navigator.clipboard.writeText(v)}catch(e){fallbackCopy(v)}toast(msg)}
async function copyRich(){const el=document.getElementById('body');
 try{await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([el.innerHTML],{type:'text/html'}),'text/plain':new Blob([el.innerText],{type:'text/plain'})})]);toast('본문 복사됨 (서식 포함)')}
 catch(e){const r=document.createRange();r.selectNodeContents(el);const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');s.removeAllRanges();toast('본문 복사됨')}}
"""

def _page(title, body, extra_js=""):
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>{body}<div class="toast" id="toast"></div>
<script>{JS}{extra_js}</script></body></html>"""

def _load():
    items = []
    for f in sorted(glob.glob("drafts/*.json"), reverse=True):
        d = json.load(open(f, encoding="utf-8"))
        d["_key"] = os.path.splitext(os.path.basename(f))[0]
        d["_date"] = d["_key"][:10]
        items.append(d)
    return items

def _slugfile(key):
    import hashlib
    return key[:10] + "-" + hashlib.md5(key.encode()).hexdigest()[:8]

def build():
    items = _load()
    os.makedirs(f"{DOCS}/d", exist_ok=True)
    open(f"{DOCS}/.nojekyll", "w").close()
    open(f"{DOCS}/robots.txt", "w").write("User-agent: *\nDisallow: /\n")

    rows = []
    for d in items:
        fn = _slugfile(d["_key"]) + ".html"
        tags = ", ".join(d.get("tags", []))
        img_card = ""
        if d.get("image"):
            src = "../" + d["image"]
            img_card = (f'<div class="card"><div class="label">대표 이미지 · 티스토리 본문 첫 이미지로 넣으면 썸네일이 됩니다</div>'
                        f'<img src="{src}" alt="" style="width:100%;border-radius:8px;display:block">'
                        f'<div class="row" style="margin-top:8px"><a href="{src}" download style="flex:1"><button style="width:100%">이미지 저장</button></a></div>'
                        f'<div class="label" style="margin-top:6px">아이폰은 이미지를 길게 눌러 "사진에 저장"</div></div>')
        body = f"""<div class="wrap">
<a href="../index.html">← 목록</a>
<h1>{html.escape(d['title'])}</h1>
<div class="card"><div class="label">제목</div><div class="row"><div class="v" id="ttl">{html.escape(d['title'])}</div><button onclick="copyText('ttl','제목 복사됨')">복사</button></div></div>
<div class="card"><div class="label">태그</div><div class="row"><div class="v" id="tags">{html.escape(tags)}</div><button onclick="copyText('tags','태그 복사됨')">복사</button></div>
<div class="label" style="margin-top:8px">카테고리: {html.escape(d.get('category',''))}</div></div>
<div class="card"><label class="mark"><input type="checkbox" id="done"> 티스토리에 올림</label>
{('<div style="margin-top:6px"><a href="' + html.escape(d['source_url']) + '" target="_blank" rel="noopener">공식 페이지에서 금액·기한 확인하기</a></div>') if d.get('source_url') else ''}</div>
{img_card}
<div class="card body" id="body">{d['html']}</div>
<pre id="src" hidden>{html.escape(d['html'])}</pre>
<pre id="ai" hidden>{html.escape(PROMPT + d['html'])}</pre>
<div class="card"><div class="label">AI로 문장 다듬기</div>
<div class="row"><button style="flex:1" onclick="copyText('ai','프롬프트+초안 복사됨 · AI 앱에 붙여넣기')">AI 다듬기용 복사</button><a href="https://claude.ai/new" target="_blank" rel="noopener" style="flex:1"><button style="width:100%">Claude 열기</button></a></div>
<div class="label" style="margin-top:6px">복사 → Claude(또는 다른 AI)에 붙여넣기 → 결과를 읽고 의견 문단이 본인 생각과 다르면 그 부분만 고치기 → 티스토리 HTML 모드에 붙여넣기</div></div>
</div>
<div class="bar"><button onclick="copyText('src','HTML 복사됨 (PC HTML모드용)')">HTML 복사</button><button class="main" onclick="copyRich()">본문 복사</button></div>"""
        js = f"""const K='done:{d['_key']}',c=document.getElementById('done');try{{c.checked=localStorage.getItem(K)==='1'}}catch(e){{}}
c.addEventListener('change',()=>{{try{{localStorage.setItem(K,c.checked?'1':'0')}}catch(e){{}}}});"""
        open(f"{DOCS}/d/{fn}", "w", encoding="utf-8").write(_page(d["title"], body, js))
        rows.append(f'<li class="card" data-k="{html.escape(d["_key"])}"><a href="d/{fn}"><div class="t">{html.escape(d["title"])}</div>'
                    f'<div class="d">{d["_date"]} <span class="chk"></span></div></a></li>')

    idx = f"""<div class="wrap"><h1>지원금 초안함</h1>
<p class="d" style="color:var(--muted);font-size:14px">초안 {len(items)}개 · 올린 글은 흐리게 표시됩니다</p>
<ul class="list" style="list-style:none;padding:0">{''.join(rows) or '<li class="card">아직 초안이 없습니다. 다음 실행 후 다시 확인하세요.</li>'}</ul></div>"""
    js = """document.querySelectorAll('[data-k]').forEach(li=>{try{if(localStorage.getItem('done:'+li.dataset.k)==='1'){li.classList.add('done');li.querySelector('.chk').textContent='✓ 올림'}}catch(e){}});"""
    open(f"{DOCS}/index.html", "w", encoding="utf-8").write(_page("지원금 초안함", idx, js))
    print(f"미리보기 페이지 {len(items)}개 생성 → {DOCS}/index.html")

def site_url():
    import yaml
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    if cfg.get("site_url"): return cfg["site_url"].rstrip("/") + "/"
    repo = os.environ.get("GITHUB_REPOSITORY")          # owner/repo
    if repo:
        owner, name = repo.split("/")
        return f"https://{owner.lower()}.github.io/{name}/"
    return ""

if __name__ == "__main__":
    build()
