"""글마다 대표 이미지(썸네일 카드) 자동 생성 → docs/img/*.png
티스토리 목록 썸네일·SNS 공유 이미지로 쓰기 좋은 1200x675 크기"""
import os, re, urllib.request
from PIL import Image, ImageDraw, ImageFont
import yaml, intro, draft

CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))
W, H = 1200, 675
THEMES = {  # 주제별 색: (배경, 진한색, 포인트)
    "출산·육아": ("#fdf0f3", "#9d2f4f", "#f4a7b9"),
    "주거":      ("#ecf6f4", "#0f5e57", "#7fcfc4"),
    "청년":      ("#eef3fc", "#1d4e9e", "#9dbcf0"),
    "소상공인":  ("#fdf4ea", "#9a4a12", "#f3bf86"),
    "어르신":    ("#f3f0fa", "#4b3a8c", "#c2b5ea"),
    "생활지원":  ("#eff6ef", "#2c6b2f", "#a8d5a3"),
}
FONT_DIR = "fonts"
FONT_URLS = {
    "bold": "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-ExtraBold.ttf",
    "reg":  "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf",
}
LOCAL = {
    "bold": [CFG.get("font_bold", ""), "C:/Windows/Fonts/malgunbd.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", "/System/Library/Fonts/AppleSDGothicNeo.ttc"],
    "reg":  [CFG.get("font_regular", ""), "C:/Windows/Fonts/malgun.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/System/Library/Fonts/AppleSDGothicNeo.ttc"],
}

def _font_path(kind):
    for p in LOCAL[kind]:
        if p and os.path.exists(p): return p
    os.makedirs(FONT_DIR, exist_ok=True)
    dst = os.path.join(FONT_DIR, os.path.basename(FONT_URLS[kind]))
    if not os.path.exists(dst):
        urllib.request.urlretrieve(FONT_URLS[kind], dst)
    return dst

def _font(kind, size):
    p = _font_path(kind)
    return ImageFont.truetype(p, size, index=0)

def _wrap(d, text, font, maxw, max_lines):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=font) <= maxw:
            cur = test; continue
        if cur: lines.append(cur)
        cur = w
        while d.textlength(cur, font=font) > maxw:          # 띄어쓰기 없는 긴 단어 강제 줄바꿈
            i = len(cur)
            while i > 1 and d.textlength(cur[:i], font=font) > maxw: i -= 1
            lines.append(cur[:i]); cur = cur[i:]
    if cur: lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while d.textlength(lines[-1] + "…", font=font) > maxw: lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines

def make(p, out_path):
    topic, _ = intro.topic_of(p)
    bg, ink, pt = THEMES.get(topic, THEMES["생활지원"])
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)

    # 배경 장식: 오른쪽 아래 큰 원 두 개
    d.ellipse([W - 360, H - 330, W + 160, H + 190], fill=pt)
    d.ellipse([W - 190, H - 470, W + 30, H - 250], outline=pt, width=14)

    pad = 80
    tag_f = _font("reg", 30)
    tag = f"{topic} 지원"
    tw = d.textlength(tag, font=tag_f)
    d.rounded_rectangle([pad, pad, pad + tw + 44, pad + 58], radius=29, fill=ink)
    d.text((pad + 22, pad + 12), tag, font=tag_f, fill=bg)

    title = re.sub(r"\s+", " ", p["title"]).strip()
    size = 74 if len(title) <= 18 else 64 if len(title) <= 30 else 56
    tf = _font("bold", size)
    lines = _wrap(d, title, tf, W - pad * 2 - 120, 3)
    y = pad + 110
    for ln in lines:
        d.text((pad, y), ln, font=tf, fill=ink)
        y += int(size * 1.28)

    lab = draft.amount_label(p.get("content"))
    sub_f = _font("reg", 38)
    sub = f"{lab} · 대상·신청방법 총정리" if lab else "지원 대상 · 금액 · 신청방법 총정리"
    d.text((pad, y + 16), sub, font=sub_f, fill=ink)

    foot_f = _font("reg", 28)
    nick = CFG.get("blog_nickname", "지원금 알리미")
    d.line([pad, H - pad - 30, pad + 60, H - pad - 30], fill=ink, width=4)
    d.text((pad, H - pad - 12), nick, font=foot_f, fill=ink)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    im.save(out_path, "PNG", optimize=True)
    return out_path
