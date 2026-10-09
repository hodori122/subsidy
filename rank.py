"""돈 되는 순 점수 + 비슷한 주제 자동 묶기(중복 방지)"""
import re, datetime as dt, yaml
from difflib import SequenceMatcher
CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))
COLS = ["id","source","title","summary","target","content","deadline","agency","url","how"]

REGIONS = ("서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","충청",
           "전북","전남","전라","경북","경남","경상","제주")
LEAD = re.compile(r"^(\S*(부|청|처|위원회|공단|공사|재단|진흥원|시|군|구|도|특별자치도|광역시))\s+")
STOP = ["지원사업","지원금","지원","사업","서비스","안내","신청"]

def norm(title: str) -> str:
    t = re.sub(r"\(.*?\)|\[.*?\]|「|」|『|』", " ", title or "")
    for _ in range(3):                     # "경상남도 창원시 ..." 처럼 여러 단계 접두어 제거
        t2 = LEAD.sub("", t.strip())
        if t2 == t.strip(): break
        t = t2
    for r in REGIONS:
        if t.startswith(r): t = t[len(r):]
    t = re.sub(r"[^가-힣A-Za-z0-9]", "", t)
    for w in STOP: t = t.replace(w, "")
    return t

def similar(a: str, b: str) -> bool:
    if not a or not b: return False
    if len(a) >= 4 and len(b) >= 4 and (a in b or b in a): return True
    return SequenceMatcher(None, a, b).ratio() >= CFG.get("similarity", 0.7)

def is_regional(p: dict) -> bool:
    ag = p.get("agency") or ""
    return ag.startswith(REGIONS) or bool(re.search(r"(시|군|구|도)$", ag))

def _expired(deadline: str) -> bool:
    if not deadline: return False
    m = re.findall(r"(20\d{2})[.\-/년 ]*(\d{1,2})[.\-/월 ]*(\d{1,2})", deadline)
    if not m: return False
    y, mo, d = map(int, m[-1])
    try: return dt.date(y, mo, d) < dt.date.today()
    except ValueError: return False

def score(p: dict) -> int:
    text = f"{p['title']} {p['summary']} {p['content']}"
    s = 0
    for kw in CFG["hot_keywords"]:
        if kw["word"] in text: s += kw["score"]
    if re.search(r"\d\s*(만|억)?\s*원", text): s += 3
    if "상시" in (p["deadline"] or "") or not p["deadline"]: s += 1
    if any(x in text for x in CFG["exclude_keywords"]): s -= 10
    if len(p["content"] or "") < 40: s -= 3
    if not is_regional(p): s += 2              # 전국 단위가 검색량 큼
    return s

def pick(con, limit):
    """반환: [[대표정책, 유사1, 유사2, ...], ...]"""
    rows = con.execute(f"SELECT {','.join(COLS)} FROM policy WHERE drafted=0").fetchall()
    cands = [dict(zip(COLS, r)) for r in rows]
    if CFG["skip_expired"]:
        cands = [c for c in cands if not _expired(c["deadline"])]
    for c in cands:
        c["_n"] = norm(c["title"]); c["_s"] = score(c)
    cands.sort(key=lambda c: c["_s"], reverse=True)

    done = [norm(t) for (t,) in con.execute("SELECT title FROM policy WHERE drafted=1")]
    groups = []
    max_rel = CFG.get("max_related", 8)
    for c in cands:
        if any(similar(c["_n"], d) for d in done):
            continue                                  # 이미 쓴 주제 → 건너뜀
        for g in groups:
            if similar(c["_n"], g[0]["_n"]):
                if len(g) < max_rel + 1: g.append(c)
                break
        else:
            if len(groups) < limit: groups.append([c])
    # 대표 글은 전국 단위 > 점수 순
    for g in groups:
        g.sort(key=lambda p: (is_regional(p), -p["_s"]))
    return groups
