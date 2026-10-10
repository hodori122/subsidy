"""초안 알림 메일 (Gmail/네이버 SMTP + 앱 비밀번호)
환경변수: MAIL_USER(보내는 주소), MAIL_APP_PASSWORD(앱 비밀번호), MAIL_TO(받는 주소, 없으면 MAIL_USER)"""
import os, html, smtplib, ssl, mimetypes
from email.message import EmailMessage
from email.utils import make_msgid
import yaml

CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))

def _smtp_host(user):
    if CFG.get("mail_smtp"): return CFG["mail_smtp"]
    return "smtp.naver.com" if user.endswith("@naver.com") else "smtp.gmail.com"

def build(subject, items, index_url=""):
    """items: [{"title","tags","page_url","image_path","agency"}]"""
    user = os.environ["MAIL_USER"]
    msg = EmailMessage()
    msg["Subject"], msg["From"] = subject, user
    msg["To"] = os.environ.get("MAIL_TO") or user

    plain = [subject, ""] + [f"- {i['title']}\n  {i.get('page_url','')}" for i in items]
    msg.set_content("\n".join(plain))

    cards, imgs = [], []
    for i in items:
        img_tag = ""
        if i.get("image_path") and os.path.exists(i["image_path"]):
            cid = make_msgid()
            imgs.append((cid, i["image_path"]))
            img_tag = f'<img src="cid:{cid[1:-1]}" alt="" style="width:100%;max-width:560px;border-radius:8px;display:block;margin-bottom:10px">'
        btn = (f'<a href="{html.escape(i["page_url"])}" style="display:inline-block;background:#0f766e;color:#fff;'
               f'text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600">초안 열기 · 복사하기</a>') if i.get("page_url") else ""
        cards.append(f"""<div style="border:1px solid #e1e7e4;border-radius:12px;padding:16px;margin:0 0 16px;background:#fff">
{img_tag}<div style="font-size:17px;font-weight:700;line-height:1.45;margin-bottom:6px">{html.escape(i['title'])}</div>
<div style="font-size:13px;color:#66726d;margin-bottom:12px">태그: {html.escape(', '.join(i.get('tags', [])))}</div>{btn}</div>""")
    all_btn = (f'<p style="text-align:center;margin:20px 0"><a href="{html.escape(index_url)}" style="color:#0f766e;font-weight:600">전체 초안함 보기 →</a></p>'
               if index_url else "")
    body = f"""<div style="background:#f5f7f6;padding:20px 12px;font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;color:#1b2421">
<div style="max-width:600px;margin:0 auto"><h2 style="font-size:20px;margin:0 0 16px">{html.escape(subject)}</h2>
{''.join(cards)}{all_btn}
<p style="font-size:12px;color:#93a19b;text-align:center">이미지는 길게 눌러 저장한 뒤 티스토리 본문 첫 이미지로 넣으면 썸네일이 됩니다.</p></div></div>"""
    msg.add_alternative(body, subtype="html")
    html_part = msg.get_payload()[-1]
    for cid, path in imgs:
        ctype = mimetypes.guess_type(path)[0] or "image/png"
        maintype, subtype = ctype.split("/")
        with open(path, "rb") as f:
            html_part.add_related(f.read(), maintype=maintype, subtype=subtype, cid=cid,
                                  filename=os.path.basename(path))
    return msg

def send(subject, items, index_url=""):
    user, pw = os.environ["MAIL_USER"], os.environ["MAIL_APP_PASSWORD"].replace(" ", "")
    msg = build(subject, items, index_url)
    with smtplib.SMTP_SSL(_smtp_host(user), 465, context=ssl.create_default_context(), timeout=30) as s:
        s.login(user, pw)
        s.send_message(msg)
    print("메일 알림 전송 완료 →", msg["To"])
