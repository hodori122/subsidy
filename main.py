"""전체 파이프라인: 지원금(매일) + 금리 비교(주 1회) + 청약 일정(주 1회 + 대단지)
  py main.py           평소 실행
  py main.py --reset   지원금 초안 기록 초기화 후 새로 생성
"""
import os, re, sys, glob, json, datetime as dt, requests, yaml
import collect, rank, draft, preview, images

CFG = yaml.safe_load(open("config.yaml", encoding="utf-8"))

def slug(s): return re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-")[:60]

def notify_telegram(msg):
    tok, cid = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if CFG.get("notify_telegram") and tok and cid:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      data={"chat_id": cid, "text": msg, "disable_web_page_preview": True}, timeout=15)

def reset(con):
    con.execute("UPDATE policy SET drafted=0"); con.commit()
    for f in glob.glob("drafts/*"): os.remove(f)
    print("초안 기록 초기화 완료")

def save_draft(d, p, today):
    """초안 저장 + 썸네일 + 알림용 항목 반환"""
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
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("초안:", base + ".html")
    site = preview.site_url()
    return {"title": d["title"], "tags": d["tags"], "short": p["title"][:20] + ("…" if len(p["title"]) > 20 else ""),
            "page_url": (site + "d/" + preview._slugfile(key) + ".html") if site else "",
            "image_path": ("docs/" + d["image"]) if d.get("image") else ""}

def main():
    con = collect.db()
    con.execute("CREATE TABLE IF NOT EXISTS extra(id TEXT PRIMARY KEY, created TEXT)")
    if "--reset" in sys.argv: reset(con)
    os.makedirs("drafts", exist_ok=True)
    today = dt.date.today().isoformat()
    items = []

    # 1) 지원금
    collect.run()
    for g in rank.pick(con, CFG["max_drafts_per_run"]):
        p, related = g[0], g[1:]
        if p["source"] == "gov24": p = collect.enrich_gov24(p)
        d = draft.build(p, related)
        items.append(save_draft(d, p, today))
        for x in g: con.execute("UPDATE policy SET drafted=1 WHERE id=?", (x["id"],))
    con.commit()

    # 2) 금리 비교 (주 1회)
    if CFG.get("rates_enabled") and os.environ.get("FSS_API_KEY"):
        try:
            import rates
            for d, p in rates.weekly_drafts():
                if con.execute("SELECT 1 FROM extra WHERE id=?", (p["id"],)).fetchone(): continue
                items.append(save_draft(d, p, today))
                con.execute("INSERT INTO extra VALUES(?,?)", (p["id"], today))
            con.commit()
        except Exception as e:
            print("금리 수집 실패:", e)

    # 3) 청약 일정 (주 1회 모음 + 대단지 개별)
    if CFG.get("apply_enabled"):
        try:
            import apply
            for d, p in apply.weekly_drafts(con):
                if con.execute("SELECT 1 FROM extra WHERE id=?", (p["id"],)).fetchone(): continue
                items.append(save_draft(d, p, today))
                con.execute("INSERT INTO extra VALUES(?,?)", (p["id"], today))
            con.commit()
        except Exception as e:
            print("청약 수집 실패:", e)

    preview.build()
    if not items:
        print("새 초안 없음"); return

    t = dt.date.today()
    head = f"📝 {t.month}월 {t.day}일 초안 {len(items)}건"
    notify_telegram(head + "\n" + "\n".join("• " + i["title"] for i in items))
    if CFG.get("notify_kakao") and os.environ.get("KAKAO_REST_KEY"):
        try:
            import kakao
            kakao.send(head + "\n" + "\n".join("• " + i["short"] for i in items), preview.site_url() or "https://www.tistory.com")
        except Exception as e:
            print("카톡 알림 실패:", e)
    if CFG.get("notify_email", True) and os.environ.get("MAIL_USER") and os.environ.get("MAIL_APP_PASSWORD"):
        try:
            import mailer
            mailer.send(head, items, preview.site_url())
        except Exception as e:
            print("메일 알림 실패:", e)

if __name__ == "__main__":
    main()
