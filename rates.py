"""금융감독원 '금융상품 한눈에' API → 예금·적금·주담대 금리 TOP 글 초안 (주 1회)
키: https://finlife.fss.or.kr 회원가입 → 오픈API → 인증키 → 환경변수 FSS_API_KEY"""
import os, html, datetime as dt, requests, yaml
CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))
FORCE = os.environ.get("FORCE_WEEKLY", "").lower() in ("1", "yes", "true")  # 요일 무시하고 즉시 생성
BASE = "https://finlife.fss.or.kr/finlifeapi/"
GROUPS = {"020000": "은행", "030300": "저축은행"}

def _fetch(kind, grp):
    key = os.environ["FSS_API_KEY"]
    out, page = [], 1
    while True:
        r = requests.get(f"{BASE}{kind}ProductsSearch.json", params={"auth": key, "topFinGrpNo": grp, "pageNo": page}, timeout=30)
        r.raise_for_status()
        res = r.json().get("result", {})
        base = {b["fin_prdt_cd"] + b["fin_co_no"]: b for b in res.get("baseList", [])}
        for o in res.get("optionList", []):
            b = base.get(o["fin_prdt_cd"] + o["fin_co_no"])
            if b: out.append({**b, **o})
        if page >= int(res.get("max_page_no", 1) or 1): break
        page += 1
    return out

def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def top_products(kind, term=12, n=10, grp="020000"):
    rows = []
    for x in _fetch(kind, grp):
        if str(x.get("save_trm")) != str(term): continue
        if kind == "saving" and x.get("rsrv_type_nm") and "자유" in x["rsrv_type_nm"] and CFG.get("rates_fixed_only", True): continue
        r1, r2 = _num(x.get("intr_rate")), _num(x.get("intr_rate2"))
        if r2 is None: continue
        rows.append({"bank": x["kor_co_nm"], "name": x["fin_prdt_nm"], "base": r1, "max": r2,
                     "join": x.get("join_way", ""), "cond": (x.get("spcl_cnd") or "").strip(),
                     "member": x.get("join_member", ""), "limit": x.get("max_limit")})
    # 같은 상품은 최고금리 하나만
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda r: (r["max"], r["base"] or 0), reverse=True):
        k = (r["bank"], r["name"])
        if k in seen: continue
        seen.add(k); uniq.append(r)
    return uniq[:n]

def _p(s): return html.escape((s or "").strip()).replace("\n", "<br>")

def deposit_or_saving_html(kind, rows, term, grp_name):
    label = "정기예금" if kind == "deposit" else "정기적금"
    today = dt.date.today()
    trs = "".join(f"<tr><td>{i+1}</td><td>{_p(r['bank'])}</td><td>{_p(r['name'])}</td><td>{r['base']:.2f}%</td><td><strong>{r['max']:.2f}%</strong></td><td>{_p(r['join'])}</td></tr>"
                  for i, r in enumerate(rows))
    top = rows[0]
    conds = "".join(f"<h3>{i+1}위 {_p(r['bank'])} {_p(r['name'])}</h3><p>기본 {r['base']:.2f}% → 우대 조건 충족 시 최고 <strong>{r['max']:.2f}%</strong>.</p>"
                    f"<p>{_p(r['cond'])[:400] or '우대 조건 정보 없음 (은행 확인)'}</p>" for i, r in enumerate(rows[:3]))
    return f"""
<p>{today.year}년 {today.month}월 {today.day}일 기준, {grp_name} {term}개월 {label} 금리를 금융감독원 공시 데이터로 정리했습니다. 오늘 기준 1위는 <strong>{_p(top['bank'])} {_p(top['name'])}</strong>으로 최고 {top['max']:.2f}%입니다.</p>
<h2>{label} 금리 TOP {len(rows)} ({term}개월, {grp_name})</h2>
<table><tr><th>순위</th><th>금융사</th><th>상품명</th><th>기본</th><th>최고</th><th>가입</th></tr>{trs}</table>
<p>"최고" 금리는 급여이체·카드실적·마케팅 동의 같은 우대 조건을 모두 채웠을 때 숫자예요. 조건 없이 받는 금리는 "기본" 칸을 보세요.</p>
<h2>상위 3개 우대 조건 뜯어보기</h2>
{conds}
<h2>고를 때 체크할 것</h2>
<p>1. 우대 조건 중 내가 실제로 채울 수 있는 게 몇 개인지 먼저 세어보세요. 기본금리가 높은 쪽이 결과적으로 유리한 경우가 많습니다.</p>
<p>2. 가입 한도가 낮은 특판은 목돈을 넣기 어렵습니다. 한도는 각 은행 페이지에서 확인하세요.</p>
<p>3. 저축은행도 예금자보호(1인당 금융사별 원금+이자 합산 보호한도)가 적용되니 한도 안에서 분산하면 안전합니다.</p>
<p><em>금리는 매주 바뀝니다. 가입 전 해당 금융사 홈페이지에서 최신 금리를 꼭 확인하세요. 출처: 금융감독원 금융상품통합비교공시</em></p>
"""

def mortgage_html(rows):
    today = dt.date.today()
    trs = "".join(f"<tr><td>{i+1}</td><td>{_p(r['bank'])}</td><td>{_p(r['name'])}</td><td>{r['min']:.2f}%</td><td>{r['max']:.2f}%</td><td>{_p(r['type'])}</td></tr>" for i, r in enumerate(rows))
    return f"""
<p>{today.year}년 {today.month}월 {today.day}일 기준 은행 주택담보대출 금리를 낮은 순으로 정리했습니다. 실제 적용 금리는 신용도·LTV·우대 조건에 따라 달라지니 "최저" 칸은 참고용으로 보세요.</p>
<h2>주택담보대출 금리 낮은 순 TOP {len(rows)}</h2>
<table><tr><th>순위</th><th>은행</th><th>상품명</th><th>최저</th><th>최고</th><th>금리유형</th></tr>{trs}</table>
<h2>비교할 때 주의할 점</h2>
<p>1. 최저 금리는 최고 신용등급에 우대 조건을 다 채웠을 때 숫자입니다. 본인 조건으로 받으면 보통 그보다 0.3~1%p 높게 나옵니다.</p>
<p>2. 변동금리는 6개월·12개월마다 바뀝니다. 고정·혼합형과 총이자를 비교하려면 은행 상담 시 "총 상환액"으로 물어보세요.</p>
<p>3. 중도상환수수료, 부대비용(인지세·근저당 설정비)도 같이 보셔야 합니다.</p>
<p><em>출처: 금융감독원 금융상품통합비교공시. 금리는 수시로 바뀌니 신청 전 은행에서 확인하세요.</em></p>
"""

def top_mortgage(n=10):
    rows = []
    for x in _fetch("mortgageLoan", "020000"):
        lo, hi = _num(x.get("lend_rate_min")), _num(x.get("lend_rate_max"))
        if lo is None: continue
        rows.append({"bank": x["kor_co_nm"], "name": x["fin_prdt_nm"], "min": lo, "max": hi or lo,
                     "type": f"{x.get('mrtg_type_nm','')}/{x.get('lend_rate_type_nm','')}/{x.get('rpay_type_nm','')}"})
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda r: r["min"]):
        if (r["bank"], r["name"]) in seen: continue
        seen.add((r["bank"], r["name"])); uniq.append(r)
    return uniq[:n]

def weekly_drafts():
    """월요일(또는 config의 rates_weekday)에만 생성. 반환: [(draft_dict, pseudo_policy)]"""
    today = dt.date.today()
    if not FORCE and today.weekday() != CFG.get("rates_weekday", 0): return []
    y, m, d = today.year, today.month, today.day
    week = f"{y}-W{today.isocalendar()[1]}"
    out = []
    jobs = [("deposit", 12, "020000", "은행"), ("saving", 12, "020000", "은행"), ("deposit", 12, "030300", "저축은행")]
    for kind, term, grp, gname in jobs:
        rows = top_products(kind, term, 10, grp)
        if len(rows) < 5: continue
        label = "정기예금" if kind == "deposit" else "정기적금"
        title = f"{m}월 {d}일 {gname} {label} 금리 TOP10 ({term}개월) 최고 {rows[0]['max']:.2f}%"
        p = {"id": f"rates:{kind}:{grp}:{week}", "title": f"{gname} {label} 금리 비교", "summary": f"{gname} {label} 금리 순위",
             "content": f"최고 {rows[0]['max']:.2f}%", "subtitle": f"{m}월 {d}일 기준 · {term}개월 · 최고 {rows[0]['max']:.2f}%", "target": "", "agency": "금융감독원", "url": "https://finlife.fss.or.kr", "how": "", "deadline": ""}
        out.append(({"id": p["id"], "title": title, "tags": [f"{label}금리", f"{gname}{label}", "금리비교", f"{y}년{label}", "고금리"],
                     "category": "금리 비교", "html": deposit_or_saving_html(kind, rows, term, gname), "source_url": p["url"]}, p))
    rows = top_mortgage(10)
    if len(rows) >= 5:
        p = {"id": f"rates:mortgage:{week}", "title": "은행 주택담보대출 금리 비교", "summary": "주담대 금리 순위", "content": f"최저 {rows[0]['min']:.2f}%", "subtitle": f"{m}월 {d}일 기준 · 최저 {rows[0]['min']:.2f}%",
             "target": "", "agency": "금융감독원", "url": "https://finlife.fss.or.kr", "how": "", "deadline": ""}
        out.append(({"id": p["id"], "title": f"{m}월 {d}일 주택담보대출 금리 낮은 은행 TOP10 (최저 {rows[0]['min']:.2f}%)",
                     "tags": ["주택담보대출금리", "주담대비교", "대출금리", f"{y}년대출", "은행별금리"],
                     "category": "금리 비교", "html": mortgage_html(rows), "source_url": p["url"]}, p))
    return out
