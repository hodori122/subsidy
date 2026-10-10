"""전체 파이프라인: 수집 → 랭킹·묶기 → 초안 생성 → drafts/ 저장 → (선택) 텔레그램 알림
사용법:
  py main.py           평소 실행
  py main.py --reset   초안 기록을 초기화하고 drafts 폴더를 비운 뒤 새로 생성
"""
import os, re, sys, glob, json, datetime as dt, requests, yaml
import collect, rank, draft, preview, images

CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))

def slug(s): return re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-")[:60]

def notify(msg):
    tok, cid = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if CFG.get("notify_telegram") and tok and cid:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      data={"chat_id": cid, "text": msg, "disable_web_page_preview": True}, timeout=15)

def reset():
    con = collect.db()
    con.execute("UPDATE policy SET drafted=0"); con.commit()
    for f in glob.glob("drafts/*"): os.remove(f)
    print("초안 기록 초기화 완료")

def main():
    if "--reset" in sys.argv: reset()
    con = collect.run()
    groups = rank.pick(con, CFG["max_drafts_per_run"])
    if not groups:
        print("새 초안 없음"); preview.build(); return
    os.makedirs("drafts", exist_ok=True)
    today = dt.date.today().isoformat()
    lines = [f"📝 {today} 지원금 초안 {len(groups)}건"]
    short, mail_items = [], []
    for g in groups:
        p, related = g[0], g[1:]
        if p["source"] == "gov24": p = collect.enrich_gov24(p)
        d = draft.build(p, related)
        base = f"drafts/{today}_{slug(d['title'])}"
        key = os.path.basename(base)
        try:
            img = images.make(p, f"docs/img/{preview._slugfile(key)}.png")
            d["image"] = "img/" + os.path.basename(img)
        except Exception as e:
            print("이미지 생성 실패:", e)
        with open(base + ".html", "w", encoding="utf-8") as f:
            f.write(f"<!-- 제목: {d['title']} -->\n<!-- 태그: {', '.join(d['tags'])} -->\n<!-- 카테고리: {d['category']} -->\n<!-- 출처: {d['source_url']} -->\n{d['html']}")
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump({**d, "related_ids": [r["id"] for r in related]}, f, ensure_ascii=False, indent=2)
        for x in g:
            con.execute("UPDATE policy SET drafted=1 WHERE id=?", (x["id"],))
        extra = f" (+유사 {len(related)}건 묶음)" if related else ""
        lines.append(f"• {d['title']}{extra}")
        mail_items.append({"title": d["title"], "tags": d["tags"],
                           "page_url": (preview.site_url() + "d/" + preview._slugfile(key) + ".html") if preview.site_url() else "",
                           "image_path": ("docs/" + d["image"]) if d.get("image") else ""})
        short.append("• " + (p["title"][:20] + ("…" if len(p["title"]) > 20 else "")))
        print("초안:", base + ".html" + extra)
    con.commit()
    preview.build()
    notify("\n".join(lines))
    if CFG.get("notify_kakao") and os.environ.get("KAKAO_REST_KEY"):
        url = preview.site_url() or "https://www.tistory.com"
        text = f"📝 {dt.date.today().month}월 {dt.date.today().day}일 지원금 초안 {len(groups)}건\n" + "\n".join(short)
        try:
            import kakao
            kakao.send(text, url)
        except Exception as e:
            print("카톡 알림 실패:", e)
    if CFG.get("notify_email", True) and os.environ.get("MAIL_USER") and os.environ.get("MAIL_APP_PASSWORD"):
        try:
            import mailer
            mailer.send(f"📝 {dt.date.today().month}월 {dt.date.today().day}일 지원금 초안 {len(groups)}건",
                        mail_items, preview.site_url())
        except Exception as e:
            print("메일 알림 실패:", e)

if __name__ == "__main__":
    main()
