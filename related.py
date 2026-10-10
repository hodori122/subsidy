"""내 블로그 RSS에서 비슷한 글을 찾아 '함께 보면 좋은 글' 링크 생성 (내부 링크)"""
import re, html, requests, yaml
import xml.etree.ElementTree as ET
CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))
_cache = None

def _posts():
    global _cache
    if _cache is not None: return _cache
    _cache = []
    url = (CFG.get("blog_url") or "").rstrip("/")
    if not url: return _cache
    try:
        r = requests.get(url + "/rss", timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        for it in root.iter("item"):
            t = (it.findtext("title") or "").strip()
            l = (it.findtext("link") or "").strip()
            if not t or not l or "보호되어" in t: continue
            cats = " ".join(c.text or "" for c in it.findall("category"))
            desc = re.sub(r"<[^>]+>", " ", it.findtext("description") or "")[:300]
            _cache.append({"title": t, "link": l, "text": f"{t} {cats} {desc}"})
    except Exception as e:
        print("RSS 읽기 실패:", e)
    return _cache

STOP = set("지원 신청 방법 대상 총정리 년 월 일 기준 안내 정보 최대 비교 금리 일정 사업 서비스".split())
def _tokens(s):
    s = re.sub(r"[^가-힣A-Za-z0-9 ]", " ", s)
    toks = set()
    for w in s.split():
        w = re.sub(r"(은|는|이|가|을|를|의|에|로|과|와)$", "", w)
        if len(w) >= 2 and w not in STOP: toks.add(w)
    # 2글자 조각도 추가 (띄어쓰기 다른 경우 대비)
    joined = re.sub(r"\s", "", s)
    toks |= {joined[i:i+2] for i in range(len(joined) - 1) if re.match(r"[가-힣]{2}", joined[i:i+2])}
    return toks

def find(d, p, n=3):
    q = _tokens(f"{d['title']} {p.get('summary','')} {p.get('title','')}")
    scored = []
    for post in _posts():
        if post["title"] == d["title"]: continue
        t = _tokens(post["text"])
        if not t: continue
        score = len(q & t) / (len(q) ** 0.5 * len(t) ** 0.5)
        if score >= CFG.get("related_min_score", 0.12): scored.append((score, post))
    scored.sort(key=lambda x: -x[0])
    return [p_ for _, p_ in scored[:n]]

def html_block(posts):
    if not posts: return ""
    lis = "".join(f'<li><a href="{html.escape(x["link"])}">{html.escape(x["title"])}</a></li>' for x in posts)
    return f"<h2>함께 보면 좋은 글</h2>\n<ul>{lis}</ul>\n"

def attach(d, p):
    """초안 HTML의 마무리 문단 앞에 관련 글 삽입"""
    block = html_block(find(d, p))
    if not block: return d
    h = d["html"]
    m = re.search(r"<p><em>본 글은|<p><em>금리는|<p><em>일정은|<p><em>분양가", h)
    d["html"] = (h[:m.start()] + block + h[m.start():]) if m else h + block
    d["related_posts"] = len(find(d, p))
    return d
