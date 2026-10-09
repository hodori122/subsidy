"""보조금24 / 온통청년 API에서 지원금·정책 수집 → SQLite 저장 → 신규/변경 건 반환"""
import os, time, sqlite3, json, hashlib, datetime as dt
import requests, yaml

CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))
DB = "policies.db"
GOV24_LIST   = "https://api.odcloud.kr/api/gov24/v3/serviceList"
GOV24_DETAIL = "https://api.odcloud.kr/api/gov24/v3/serviceDetail"
YOUTH_LIST   = "https://www.youthcenter.go.kr/go/ythip/getPlcy"

def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS policy(
        id TEXT PRIMARY KEY, source TEXT, title TEXT, summary TEXT, target TEXT,
        content TEXT, deadline TEXT, agency TEXT, url TEXT, how TEXT,
        hash TEXT, first_seen TEXT, last_seen TEXT, drafted INTEGER DEFAULT 0)""")
    return con

def _h(d): return hashlib.md5(json.dumps(d, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

# ---------- 보조금24 ----------
def _get(url, params, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == tries - 1: raise
            print(f"  재시도 {i+1}: {e}")
            time.sleep(3 * (i + 1))

def fetch_gov24():
    key = os.environ["DATA_GO_KR_KEY"]
    per = CFG.get("per_page", 100)
    out, total = [], None
    for page in range(1, CFG.get("max_pages", 200) + 1):
        j = _get(GOV24_LIST, {"serviceKey": key, "page": page, "perPage": per})
        total = total or j.get("totalCount")
        rows = j.get("data", [])
        if not rows: break
        for x in rows:
            out.append({
                "id": "gov24:" + str(x.get("서비스ID")),
                "source": "gov24",
                "title": (x.get("서비스명") or "").strip(),
                "summary": x.get("서비스목적요약") or x.get("서비스목적") or "",
                "target": x.get("지원대상") or "",
                "content": x.get("지원내용") or "",
                "deadline": x.get("신청기한") or "",
                "agency": x.get("소관기관명") or "",
                "url": x.get("상세조회URL") or "",
                "how": x.get("신청방법") or "",
            })
        if page % 10 == 0:
            print(f"  수집 중... {len(out)} / {total or '?'}")
        if total and len(out) >= total: break
        time.sleep(0.2)
    return out

def enrich_gov24(policy):
    """상세 API로 지원내용·구비서류 보강 (초안 대상만 호출해서 트래픽 절약)"""
    key = os.environ["DATA_GO_KR_KEY"]
    sid = policy["id"].split(":", 1)[1]
    try:
        r = requests.get(GOV24_DETAIL, params={"serviceKey": key, "cond[서비스ID::EQ]": sid, "perPage": 1}, timeout=30)
        d = (r.json().get("data") or [{}])[0]
        policy["content"] = d.get("지원내용") or policy["content"]
        policy["target"]  = d.get("지원대상") or policy["target"]
        policy["how"]     = d.get("신청방법") or policy["how"]
        policy["docs"]    = d.get("구비서류", "")
        policy["contact"] = d.get("문의처", "")
    except Exception as e:
        print("detail fail", sid, e)
    return policy

# ---------- 온통청년 ----------
def fetch_youth(max_pages=10):
    key = os.environ["YOUTH_API_KEY"]
    out = []
    for page in range(1, max_pages + 1):
        r = requests.get(YOUTH_LIST, params={"apiKeyNm": key, "pageNum": page, "pageSize": 100, "rtnType": "json"}, timeout=30)
        r.raise_for_status()
        rows = (r.json().get("result") or {}).get("youthPolicyList", [])
        if not rows: break
        for x in rows:
            out.append({
                "id": "youth:" + str(x.get("plcyNo")),
                "source": "youth",
                "title": x.get("plcyNm", "").strip(),
                "summary": x.get("plcyExplnCn", ""),
                "target": f"{x.get('sprtTrgtMinAge','')}~{x.get('sprtTrgtMaxAge','')}세 / {x.get('addAplyQlfcCndCn','')}",
                "content": x.get("plcySprtCn", ""),
                "deadline": x.get("aplyYmd", ""),
                "agency": x.get("sprvsnInstCdNm", ""),
                "url": x.get("aplyUrlAddr", ""),
                "how": x.get("plcyAplyMthdCn", ""),
            })
    return out

# ---------- 저장/변경감지 ----------
def upsert(con, items):
    now = dt.date.today().isoformat()
    new, changed = [], []
    for p in items:
        h = _h({k: p.get(k) for k in ("title","summary","target","content","deadline","how")})
        row = con.execute("SELECT hash, drafted FROM policy WHERE id=?", (p["id"],)).fetchone()
        if row is None:
            con.execute("INSERT INTO policy VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                (p["id"],p["source"],p["title"],p["summary"],p["target"],p["content"],
                 p["deadline"],p["agency"],p["url"],p["how"],h,now,now))
            new.append(p)
        else:
            if row[0] != h:
                con.execute("""UPDATE policy SET title=?,summary=?,target=?,content=?,deadline=?,agency=?,url=?,how=?,hash=?,last_seen=?,drafted=0 WHERE id=?""",
                    (p["title"],p["summary"],p["target"],p["content"],p["deadline"],p["agency"],p["url"],p["how"],h,now,p["id"]))
                changed.append(p)
            else:
                con.execute("UPDATE policy SET last_seen=? WHERE id=?", (now, p["id"]))
    con.commit()
    return new, changed

def run():
    con = db()
    items = []
    if CFG["sources"].get("gov24"): items += fetch_gov24()
    if CFG["sources"].get("youth"): items += fetch_youth()
    new, changed = upsert(con, items)
    print(f"수집 {len(items)}건 / 신규 {len(new)} / 변경 {len(changed)}")
    return con

if __name__ == "__main__":
    run()
