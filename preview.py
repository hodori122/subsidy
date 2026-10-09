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
        body = f"""<div class="wrap">
<a href="../index.html">← 목록</a>
<h1>{html.escape(d['title'])}</h1>
<div class="card"><div class="label">제목</div><div class="row"><div class="v" id="ttl">{html.escape(d['title'])}</div><button onclick="copyText('ttl','제목 복사됨')">복사</button></div></div>
<div class="card"><div class="label">태그</div><div class="row"><div class="v" id="tags">{html.escape(tags)}</div><button onclick="copyText('tags','태그 복사됨')">복사</button></div>
<div class="label" style="margin-top:8px">카테고리: {html.escape(d.get('category',''))}</div></div>
<div class="card"><label class="mark"><input type="checkbox" id="done"> 티스토리에 올림</label>
{('<div style="margin-top:6px"><a href="' + html.escape(d['source_url']) + '" target="_blank" rel="noopener">공식 페이지에서 금액·기한 확인하기</a></div>') if d.get('source_url') else ''}</div>
<div class="card body" id="body">{d['html']}</div>
<pre id="src" hidden>{html.escape(d['html'])}</pre>
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
