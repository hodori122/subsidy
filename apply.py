"""한국부동산원 청약홈 분양정보 API → 주간 청약 일정 모음글 + 대단지 개별글
data.go.kr 에서 '한국부동산원_청약홈 분양정보 조회 서비스' 활용신청 (DATA_GO_KR_KEY 공용)"""
import os, html, datetime as dt, requests, yaml
CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))
BASE = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/"

def _get(path, params):
    key = os.environ["DATA_GO_KR_KEY"]
    r = requests.get(BASE + path, params={"serviceKey": key, "perPage": 500, **params}, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def _d(s):
    try: return dt.date.fromisoformat(s[:10].replace(".", "-"))
    except Exception: return None

def upcoming(days=14):
    """접수 시작일이 오늘~N일 안인 분양"""
    today = dt.date.today()
    rows = []
    for x in _get("getAPTLttotPblancDetail", {"page": 1}):
        s = _d(x.get("RCEPT_BGNDE") or "")
        if not s or not (today - dt.timedelta(days=2) <= s <= today + dt.timedelta(days=days)): continue
        rows.append({
            "no": x.get("HOUSE_MANAGE_NO"), "name": x.get("HOUSE_NM", ""), "region": x.get("SUBSCRPT_AREA_CODE_NM", ""),
            "addr": x.get("HSSPLY_ADRES", ""), "units": x.get("TOT_SUPLY_HSHLDCO") or 0,
            "sp_start": x.get("SPSPLY_RCEPT_BGNDE") or "", "start": x.get("RCEPT_BGNDE", ""), "end": x.get("RCEPT_ENDDE", ""),
            "r1": x.get("GNRL_RNK1_CRSPAREA_RCPTDE") or "", "winner": x.get("PRZWNER_PRESNATN_DE", ""),
            "move": x.get("MVN_PREARNGE_YM", ""), "builder": x.get("CNSTRCT_ENTRPS_NM", ""),
            "tel": x.get("MDHS_TELNO", ""), "url": x.get("PBLANC_URL") or x.get("HMPG_ADRS") or "", "rent": x.get("RENT_SECD_NM", ""),
        })
    rows.sort(key=lambda r: (r["start"], -int(r["units"] or 0)))
    return rows

def types_of(no):
    try:
        return _get("getAPTLttotPblancMdl", {"page": 1, "cond[HOUSE_MANAGE_NO::EQ]": no})
    except Exception:
        return []

def _p(s): return html.escape(str(s or "")).replace("\n", "<br>")

def roundup_html(rows):
    today = dt.date.today()
    by = {}
    for r in rows: by.setdefault(r["region"] or "기타", []).append(r)
    secs = ""
    for reg, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        trs = "".join(f"<tr><td>{_p(r['name'])}</td><td>{_p(r['units'])}</td><td>{_p(r['sp_start'] or '-')}</td><td>{_p(r['start'])}</td><td>{_p(r['winner'])}</td>"
                      f"<td>{('<a href=\"' + html.escape(r['url']) + '\" target=\"_blank\" rel=\"noopener\">공고</a>') if r['url'] else '-'}</td></tr>" for r in rs)
        secs += f"<h2>{_p(reg)} ({len(rs)}곳)</h2><table><tr><th>단지</th><th>세대</th><th>특별공급</th><th>1순위</th><th>당첨발표</th><th>공고</th></tr>{trs}</table>"
    big = sorted(rows, key=lambda r: -int(r["units"] or 0))[:3]
    bigs = "".join(f"<h3>{_p(r['name'])} · {_p(r['units'])}세대</h3><p>{_p(r['addr'])}<br>시공: {_p(r['builder'] or '공고 확인')} · 입주예정: {_p(r['move'] or '공고 확인')} · 문의 {_p(r['tel'])}</p>" for r in big)
    return f"""
<p>{today.month}월 {today.day}일 기준, 앞으로 2주 안에 청약 접수가 시작되는 아파트 {len(rows)}곳을 청약홈 공고 데이터로 정리했습니다. 지역별로 나눴으니 내 지역부터 확인하세요.</p>
{secs}
<h2>이번 주 규모 큰 단지</h2>
{bigs}
<h2>청약 전 체크리스트</h2>
<p>1. 청약통장 가입 기간과 납입 횟수가 해당 지역 1순위 조건에 맞는지 청약홈에서 먼저 확인하세요.</p>
<p>2. 특별공급(신혼·생애최초·다자녀)은 일반공급보다 경쟁률이 낮은 경우가 많습니다. 소득 기준이 있으니 공고문의 특공 요건을 보세요.</p>
<p>3. 분양가와 중도금 대출 조건은 모집공고문 뒤쪽에 있습니다. 당첨 후 자금 계획이 안 서면 계약 포기 시 재당첨 제한이 걸릴 수 있어요.</p>
<p><em>일정은 사업 주체 사정으로 바뀔 수 있습니다. 접수 전 청약홈(applyhome.co.kr)에서 최종 공고를 확인하세요. 출처: 한국부동산원 청약홈</em></p>
"""

def single_html(r, types):
    trs = "".join(f"<tr><td>{_p(t.get('HOUSE_TY',''))}</td><td>{_p(t.get('SUPLY_HSHLDCO',''))}</td><td>{_p(t.get('LTTOT_TOP_AMOUNT',''))}만원</td></tr>" for t in types) if types else ""
    tbl = f"<h2>주택형별 공급 세대수·분양가</h2><table><tr><th>주택형</th><th>세대</th><th>분양 최고가</th></tr>{trs}</table>" if trs else ""
    return f"""
<p><strong>{_p(r['name'])}</strong> 청약 일정과 조건을 모집공고 데이터 기준으로 정리했습니다. 총 {_p(r['units'])}세대 규모이고, 일반공급 1순위 접수는 {_p(r['r1'] or r['start'])}입니다.</p>
<h2>{_p(r['name'])} 기본 정보</h2>
<table><tr><th>항목</th><th>내용</th></tr>
<tr><td>위치</td><td>{_p(r['addr'])}</td></tr><tr><td>공급 세대</td><td>{_p(r['units'])}세대</td></tr>
<tr><td>시공사</td><td>{_p(r['builder'] or '공고 확인')}</td></tr><tr><td>입주 예정</td><td>{_p(r['move'] or '공고 확인')}</td></tr>
<tr><td>문의</td><td>{_p(r['tel'])}</td></tr></table>
<h2>청약 일정</h2>
<table><tr><th>구분</th><th>일정</th></tr>
<tr><td>특별공급</td><td>{_p(r['sp_start'] or '-')}</td></tr><tr><td>1순위</td><td>{_p(r['r1'] or r['start'])}</td></tr>
<tr><td>접수 마감</td><td>{_p(r['end'])}</td></tr><tr><td>당첨자 발표</td><td>{_p(r['winner'])}</td></tr></table>
{tbl}
<h2>이런 분이 노려볼 만해요</h2>
<p>세대수가 많은 단지는 특별공급 물량도 많아서 신혼부부·생애최초 자격이 되면 일반공급보다 유리합니다. 소득 기준이 있으니 공고문의 특별공급 요건을 먼저 보세요.</p>
<h2>모집공고 확인</h2>
<p>{('<a href="' + html.escape(r['url']) + '" target="_blank" rel="noopener">▶ 청약홈 모집공고 바로가기</a>') if r['url'] else '청약홈(applyhome.co.kr)에서 단지명으로 검색하세요.'}</p>
<p><em>분양가·일정은 변경될 수 있으니 최종 공고문을 꼭 확인하세요. 출처: 한국부동산원 청약홈</em></p>
"""

def weekly_drafts(con):
    """주 1회 모음글 + 대단지 개별글(최초 1회). 반환: [(draft, pseudo_policy)]"""
    today = dt.date.today()
    out = []
    rows = upcoming(CFG.get("apply_days", 14))
    if not rows: return out
    week = f"{today.year}-W{today.isocalendar()[1]}"
    y, m, d = today.year, today.month, today.day
    if today.weekday() == CFG.get("apply_weekday", 1):
        p = {"id": f"apply:roundup:{week}", "title": "이번 주 아파트 청약 일정", "summary": "2주 내 접수 시작 단지 모음", "content": f"{len(rows)}곳", "subtitle": f"{m}월 {d}일 기준 · 2주 내 접수 {len(rows)}곳",
             "target": "", "agency": "한국부동산원", "url": "https://www.applyhome.co.kr", "how": "", "deadline": ""}
        out.append(({"id": p["id"], "title": f"{m}월 {d}일 기준 전국 아파트 청약 일정 총정리 ({len(rows)}곳, 지역별)",
                     "tags": ["아파트청약일정", f"{y}년청약", "청약홈", "분양일정", "특별공급"], "category": "청약·분양",
                     "html": roundup_html(rows), "source_url": p["url"]}, p))
    min_units = CFG.get("apply_single_min_units", 800)
    for r in rows:
        if int(r["units"] or 0) < min_units: continue
        pid = f"apply:{r['no']}"
        if con.execute("SELECT 1 FROM extra WHERE id=?", (pid,)).fetchone(): continue
        p = {"id": pid, "title": f"{r['name']} 청약", "summary": f"{r['region']} {r['units']}세대 분양", "content": f"{r['units']}세대", "subtitle": f"{r['region']} · {r['units']}세대 · 1순위 {r['r1'] or r['start']}",
             "target": "", "agency": "한국부동산원", "url": r["url"], "how": "", "deadline": r["end"]}
        out.append(({"id": pid, "title": f"{r['name']} 청약 일정·분양가·특별공급 조건 총정리 ({r['units']}세대)",
                     "tags": [f"{r['name']}청약", f"{r['region']}분양", "청약일정", "분양가", "특별공급"], "category": "청약·분양",
                     "html": single_html(r, types_of(r["no"])), "source_url": r["url"]}, p))
    return out
