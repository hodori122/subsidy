"""선정된 정책 → 블로그 초안(HTML + 메타) 생성. 템플릿 기본, Claude API로 선택적 리라이트"""
import os, re, json, html, datetime as dt, yaml
CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))

def _p(s): return html.escape((s or "").strip()).replace("\n", "<br>")

def _short(s, n=70):
    s = re.sub(r"\s+", " ", (s or "").replace("○", "").replace("ㅇ", " ")).strip(" -·")
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "… (아래 참고)"

def template_html(p: dict) -> str:
    year = dt.date.today().year
    import intro
    return intro.intro_html(p) + f"""
<p>{_p(p['summary'])}</p>

<h2>{_p(p['title'])} 한눈에 보기</h2>
<table>
<tr><th>항목</th><th>내용</th></tr>
<tr><td>지원 내용</td><td>{_p(amount_label(p['content']) or _short(p['content']))}</td></tr>
<tr><td>지원 대상</td><td>{_p(_short(p['target']))}</td></tr>
<tr><td>신청 기한</td><td>{_p(_short(p['deadline'], 40) or '상시 / 공고 확인')}</td></tr>
<tr><td>소관 기관</td><td>{_p(p['agency'])}</td></tr>
</table>

<h2>지원 대상</h2>
<p>{_p(p['target'])}</p>

<h2>지원 내용</h2>
<p>{_p(p['content'])}</p>

<h2>신청 방법</h2>
<p>{_p(p['how'] or '소관 기관 또는 정부24(보조금24)에서 신청할 수 있습니다.')}</p>
{('<h3>구비 서류</h3><p>' + _p(p.get('docs')) + '</p>') if p.get('docs') else ''}

<h2>자주 묻는 질문</h2>
<h3>중복 수급이 가능한가요?</h3>
<p>유사 지원과 중복 여부는 공고마다 다릅니다. 신청 전 소관 기관에 확인하세요.</p>
<h3>신청 후 언제 지급되나요?</h3>
<p>심사 기간은 기관별로 다르며, 보통 신청 후 2~8주 정도 걸립니다.</p>

<h2>신청하러 가기</h2>
<p>{('<a href="' + html.escape(p['url']) + '" target="_blank" rel="noopener">▶ 공식 신청·상세 페이지 바로가기</a>') if p.get('url') else '정부24에서 서비스명으로 검색하세요.'}</p>
{('<p>문의: ' + _p(p.get('contact')) + '</p>') if p.get('contact') else ''}
{__import__('intro').closing_html(p)}
<p><em>본 글은 {year}년 {dt.date.today().month}월 기준 공공데이터를 바탕으로 작성되었으며, 최신 내용은 공식 페이지에서 확인하세요.</em></p>
"""

def claude_rewrite(p: dict, base_html: str) -> str:
    """구조·사실은 유지하고 문장만 읽기 쉽게. 수치·대상 조건은 절대 창작하지 않도록 지시"""
    import anthropic
    client = anthropic.Anthropic()
    prompt = f"""다음은 정부 지원금 안내 블로그 초안 HTML입니다. 아래 규칙을 지켜 다시 써주세요.

규칙:
1. 제공된 사실(금액, 대상, 기한, 기관, URL)은 절대 바꾸거나 추가로 지어내지 마세요. 정보가 없으면 "공고 확인 필요"라고 쓰세요.
2. h2/h3 구조와 표는 유지하되, 문장을 검색자가 읽기 쉽게 자연스러운 한국어로 다듬으세요.
3. 첫 문단은 핵심 혜택과 누가 받을 수 있는지 2~3문장으로 요약하세요.
4. 광고성 과장 표현("무조건", "100%") 금지.
5. 출력은 HTML만, 설명이나 코드펜스 없이.

정책 원본 데이터:
{json.dumps({k: p.get(k) for k in ('title','summary','target','content','deadline','agency','how','docs')}, ensure_ascii=False)}

초안 HTML:
{base_html}"""
    r = client.messages.create(model=CFG["claude_model"], max_tokens=3000,
                               messages=[{"role": "user", "content": prompt}])
    out = "".join(b.text for b in r.content if b.type == "text")
    return re.sub(r"^```html|```$", "", out.strip(), flags=re.M).strip()

_UNIT = {"천만": 10**7, "백만": 10**6, "십만": 10**5, "만": 10**4, "천": 10**3, None: 1}
_AMT = re.compile(r"(?:(\d[\d,]*(?:\.\d+)?)\s*억\s*)?(?:(\d[\d,]*(?:\.\d+)?)\s*(천만|백만|십만|만|천)?\s*)?원")
_THRESH_BEFORE = ("소득", "자산", "재산", "매출", "연봉", "보증금", "전세금", "주택가격", "가격", "시가", "급여")
_THRESH_AFTER = ("이하", "이상", "미만", "초과")

def max_amount(text: str):
    """지원내용에서 '받는 금액'만 골라 최대값 반환 (소득·자산 기준 금액은 제외)"""
    text = text or ""
    found, capped = [], []
    for m in _AMT.finditer(text):
        eok, num, unit = m.group(1), m.group(2), m.group(3)
        if not eok and not num: continue
        v = 0
        if eok: v += float(eok.replace(",", "")) * 10**8
        if num: v += float(num.replace(",", "")) * _UNIT[unit]
        if v < 10000 or v > 5 * 10**9: continue          # 1만원 미만·50억 초과는 노이즈
        before, after = text[max(0, m.start()-12):m.start()], text[m.end():m.end()+6]
        if any(w in before for w in _THRESH_BEFORE) or any(w in after for w in _THRESH_AFTER):
            continue
        found.append(v)
        if "최대" in text[max(0, m.start()-6):m.start()] or "한도" in after:
            capped.append(v)
    pool = capped or found
    return max(pool) if pool else None

def fmt_won(v: float) -> str:
    if v >= 10**8:
        e = v / 10**8
        rest = int((v % 10**8) / 10**4)
        return f"{int(e)}억 {rest:,}만원" if rest and e >= 1 else f"{e:g}억원"
    if v >= 10**4: return f"{int(v / 10**4):,}만원"
    return f"{int(v):,}원"

def amount_label(text):
    """'최대'가 명시된 경우에만 '최대'를 붙여 과장 방지"""
    v = max_amount(text)
    if not v: return None
    return ("최대 " if "최대" in (text or "") or "한도" in (text or "") else "") + fmt_won(v)

def make_title(p: dict, related=None) -> str:
    y = dt.date.today().year
    t = p["title"]
    lab = amount_label(p.get("content"))    # 제목 금액은 대표(전국) 기준만: 지역 금액 섞으면 과장됨
    tail = " (지역별 추가 지원 포함)" if related else ""
    if lab:
        return f"{y}년 {t} 신청방법·대상 총정리 ({lab}){tail}"
    return f"{y}년 {t} 신청방법·지원대상·기한 총정리{tail}"

def related_html(related) -> str:
    if not related: return ""
    rows = []
    for r in related:
        c = (r.get("content") or "").strip().replace("\n", " ")
        c = c[:90] + ("…" if len(c) > 90 else "")
        link = f'<a href="{html.escape(r["url"])}" target="_blank" rel="noopener">바로가기</a>' if r.get("url") else "-"
        rows.append(f"<tr><td>{_p(r['agency'])}</td><td>{_p(r['title'])}</td><td>{_p(c)}</td><td>{link}</td></tr>")
    return ("<h2>지역별·유사 지원 함께 보기</h2>"
            "<p>같은 목적의 지원을 지자체·기관에서도 운영합니다. 거주지 기준으로 중복 신청 가능 여부를 확인하세요.</p>"
            "<table><tr><th>기관</th><th>지원명</th><th>주요 내용</th><th>신청</th></tr>"
            + "".join(rows) + "</table>")

def make_tags(p: dict) -> list:
    base = {p["agency"], "정부지원금", "보조금24", str(dt.date.today().year) + "년지원금"}
    for kw in CFG["hot_keywords"]:
        if kw["word"] in (p["title"] + p["summary"]): base.add(kw["word"] + "지원금")
    return [t for t in base if t][:10]

def build(p: dict, related=None) -> dict:
    body = template_html(p)
    rel = related_html(related)
    if rel:
        body = body.replace("<h2>자주 묻는 질문</h2>", rel + "\n<h2>자주 묻는 질문</h2>")
    if CFG.get("use_claude_rewrite") and os.environ.get("ANTHROPIC_API_KEY"):
        try: body = claude_rewrite(p, body)
        except Exception as e: print("rewrite skip:", e)
    return {"id": p["id"], "title": make_title(p, related), "tags": make_tags(p),
            "category": "정부지원금", "html": body, "source_url": p.get("url", "")}
