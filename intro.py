"""친근한 서두·마무리 문단 생성. 글마다 문장 조합이 달라지도록 정책 ID로 고정 선택
(같은 문장이 모든 글에 반복되면 검색엔진이 중복 문서로 보기 때문)"""
import hashlib, html, yaml
CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))

TOPICS = [  # (판별 키워드, 주제명, 공감 문장들)
    (("출산", "임신", "산모", "신생아", "육아", "아동", "보육"), "출산·육아", [
        "아이를 기다리거나 막 품에 안은 가정이라면 하나라도 더 챙기고 싶으시죠.",
        "육아는 마음도 바쁘고 지출도 정말 빠르게 늘어나더라고요.",
        "출산 전후로 챙길 서류도 많고 정신없으실 텐데, 받을 수 있는 건 꼭 받으셔야죠.",
    ]),
    (("전세", "월세", "주거", "주택", "임대", "보증금"), "주거", [
        "집 문제만큼 마음 졸이는 일도 없는 것 같아요.",
        "전월세 계약을 앞두고 있으면 한 푼이 아쉽잖아요.",
        "요즘 주거비 부담, 다들 체감하고 계실 거예요.",
    ]),
    (("청년",), "청년", [
        "사회 초년생 시기엔 고정비 하나 줄이는 게 정말 크죠.",
        "청년 대상 지원은 조건만 맞으면 생각보다 혜택이 쏠쏠해요.",
        "나이 기준이 있는 지원이라 해당될 때 꼭 챙기셔야 해요.",
    ]),
    (("소상공인", "자영업", "창업", "사업자"), "소상공인", [
        "가게 운영하시면서 이런 정보까지 찾아보시기 쉽지 않으시죠.",
        "매출은 그대로인데 비용만 오르는 요즘, 지원금 하나도 소중합니다.",
        "사장님들이 몰라서 못 받는 지원이 의외로 많더라고요.",
    ]),
    (("노인", "어르신", "65세", "기초연금", "장기요양"), "어르신", [
        "부모님께 해당되는 지원이 있는지 한 번씩 확인해 드리면 좋아요.",
        "어르신 지원은 신청하지 않으면 자동으로 나오지 않는 경우가 많아요.",
    ]),
]
DEFAULT_EMPATHY = [
    "알고 보면 받을 수 있는 지원인데 몰라서 놓치는 경우가 정말 많아요.",
    "정부 지원은 신청해야 받을 수 있는 게 대부분이라, 미리 알아두는 게 중요해요.",
    "조건이 복잡해 보여도 하나씩 보면 생각보다 간단해요.",
]
GREETINGS = [
    "안녕하세요, {nick}입니다 😊",
    "안녕하세요! 생활 속 지원금 챙겨드리는 {nick}이에요.",
    "반갑습니다, {nick}입니다.",
    "안녕하세요 여러분, {nick}예요 🙌",
]
TOPIC_LINES = [
    "오늘은 <strong>{t}</strong> 내용을 정리해 봤어요.",
    "오늘 가져온 정보는 <strong>{t}</strong>입니다.",
    "이번 글에서는 <strong>{t}</strong>에 대해 알려드릴게요.",
]
PROMISES = [
    "누가 받을 수 있는지, 얼마를 받는지, 어떻게 신청하는지 순서대로 정리했으니 끝까지 확인해 보세요!",
    "대상부터 신청 방법까지 한 번에 보실 수 있게 정리했어요. 해당되시는지 같이 확인해 봐요.",
    "읽고 나면 바로 신청할 수 있도록 핵심만 골라 담았어요.",
]
CLOSINGS = [
    "오늘 정보가 도움이 되셨다면 주변에 필요한 분께도 공유해 주세요. 궁금한 점은 댓글로 남겨주시면 아는 만큼 답해 드릴게요 😊",
    "놓치기 쉬운 지원이라 필요한 분들께 꼭 닿았으면 좋겠어요. 더 궁금한 건 댓글로 편하게 물어봐 주세요!",
    "신청 기한이 있는 지원은 미루지 말고 꼭 챙기세요. 다음에도 유용한 지원금 소식으로 찾아올게요 🙌",
]

def _pick(seq, key, salt):
    h = int(hashlib.md5(f"{key}:{salt}".encode()).hexdigest(), 16)
    return seq[h % len(seq)]

def topic_of(p):
    text = f"{p.get('title','')} {p.get('summary','')} {p.get('target','')}"
    for kws, name, lines in TOPICS:
        if any(k in text for k in kws):
            return name, lines
    return "생활지원", DEFAULT_EMPATHY

def intro_html(p):
    nick = html.escape(CFG.get("blog_nickname", "지원금 알리미"))
    _, lines = topic_of(p)
    k = p["id"]
    t = html.escape(p["title"])
    return (f"<p>{_pick(GREETINGS, k, 'g').format(nick=nick)}</p>\n"
            f"<p>{_pick(lines, k, 'e')} {_pick(TOPIC_LINES, k, 't').format(t=t)} "
            f"{_pick(DEFAULT_EMPATHY, k, 'd') if lines is not DEFAULT_EMPATHY else ''}</p>\n"
            f"<p>{_pick(PROMISES, k, 'p')}</p>\n")

def closing_html(p):
    return f"<p>{_pick(CLOSINGS, p['id'], 'c')}</p>\n"
