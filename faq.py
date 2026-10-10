"""정책 원문에서 실제로 궁금해할 만한 질문만 뽑아 FAQ 생성. 원문에 근거 없는 답은 만들지 않음"""
import re, html

def _sent(text, kw, n=110):
    """kw 가 들어간 문장 하나를 원문에서 추출"""
    text = re.sub(r"\s+", " ", text or "")
    for s in re.split(r"(?<=[.다요음함])\s|(?<=\))\s(?=[-○ㅇ•·])|\s[-○ㅇ•·]\s", text):
        if kw in s:
            s = s.strip(" -○ㅇ•·")
            return s if len(s) <= n else s[:n] + "…"
    return None

def build(p, related=None):
    content, target, how = p.get("content") or "", p.get("target") or "", p.get("how") or ""
    deadline, agency, docs = p.get("deadline") or "", p.get("agency") or "", p.get("docs") or ""
    allt = f"{target} {content}"
    qs = []

    s = _sent(allt, "소득")
    if s: qs.append(("소득 기준이 있나요?", f"네, 있습니다. 공고에는 \"{s}\"로 안내되어 있어요. 본인 소득이 기준 안에 드는지 먼저 확인하세요."))

    m = re.search(r"(만\s*)?(\d{2})\s*세?\s*(?:~|부터|이상|-|∼)\s*(만\s*)?(\d{2})\s*세", allt)
    if m: qs.append(("나이 조건은 어떻게 되나요?", f"{m.group(2)}세부터 {m.group(4)}세까지가 대상입니다. 신청일 기준으로 보는 경우가 많으니 생일이 가까우면 서두르세요."))
    elif "청년" in allt and "세" in allt:
        s = _sent(allt, "세")
        if s: qs.append(("나이 조건은 어떻게 되나요?", f"공고 기준은 \"{s}\"입니다."))

    if re.search(r"(시|군|구|도)$", agency) or any(r in agency for r in ("서울", "경기", "부산", "인천", "대구", "광주", "대전", "울산", "세종", "강원", "충", "전", "경", "제주")):
        qs.append(("다른 지역에 살아도 신청할 수 있나요?", f"이 지원은 {html.escape(agency)}에서 운영하는 것이라 기본적으로 해당 지역 거주자(주민등록 기준)가 대상입니다. 다른 지역은 거주지 지자체의 유사 지원을 확인하세요." + (" 아래 '지역별·유사 지원' 표도 참고하세요." if related else "")))

    s = _sent(allt, "중복")
    if s: qs.append(("다른 지원과 중복해서 받을 수 있나요?", f"공고에 \"{s}\"라고 되어 있습니다. 비슷한 지원을 이미 받고 있다면 신청 전에 확인하세요."))

    if any(k in how for k in ("온라인", "인터넷", "누리집", "홈페이지", "앱", "정부24", "복지로")):
        s = _sent(how, "온라인") or _sent(how, "누리집") or _sent(how, "정부24") or _sent(how, "복지로") or how[:100]
        qs.append(("온라인으로도 신청되나요?", f"네. {html.escape(s)}"))
    elif "방문" in how:
        qs.append(("꼭 방문해야 하나요?", f"공고상 신청 방법은 \"{html.escape(how[:100])}\"입니다. 온라인 신청 안내가 없으니 방문 전 전화로 확인하면 헛걸음을 줄일 수 있어요."))

    if deadline and not any(k in deadline for k in ("상시", "연중", "수시")):
        qs.append(("언제까지 신청해야 하나요?", f"신청 기한은 \"{html.escape(deadline[:80])}\"입니다. 예산이 소진되면 조기 마감되는 경우가 많으니 되도록 빨리 신청하세요."))
    elif any(k in deadline for k in ("상시", "연중", "수시")) and "소진" in f"{deadline} {content}":
        qs.append(("연중 신청이면 천천히 해도 되나요?", "연중 접수지만 예산이 소진되면 조기 마감된다고 안내되어 있습니다. 해당되면 미루지 않는 게 좋아요."))

    if docs:
        qs.append(("준비할 서류는 무엇인가요?", f"공고에 안내된 구비서류는 \"{html.escape(docs[:140])}\"입니다. 기관마다 추가 서류를 요구할 수 있으니 신청 전 한 번 더 확인하세요."))

    qs = qs[:3]
    if len(qs) < 2:
        return ""
    body = "".join(f"<h3>{html.escape(q)}</h3>\n<p>{a}</p>\n" for q, a in qs)
    return body
