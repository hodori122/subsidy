"""최초 1회 실행: 카카오 로그인 → 리프레시 토큰 발급 → 테스트 메시지 전송
사용법: set KAKAO_REST_KEY=REST API 키   →   py kakao_login.py
"""
import os, sys, webbrowser, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import kakao

REDIRECT = "http://localhost:8080/callback"
code_box = {}

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code_box["code"] = (q.get("code") or [None])[0]
        code_box["error"] = (q.get("error_description") or q.get("error") or [None])[0]
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
        msg = "로그인 완료! 이 창을 닫고 명령 프롬프트로 돌아가세요." if code_box["code"] else f"실패: {code_box['error']}"
        self.wfile.write(f"<h2 style='font-family:sans-serif'>{msg}</h2>".encode())
    def log_message(self, *a): pass

def main():
    if not os.environ.get("KAKAO_REST_KEY"):
        os.environ["KAKAO_REST_KEY"] = input("카카오 REST API 키를 붙여넣고 엔터: ").strip()
    url = ("https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": os.environ["KAKAO_REST_KEY"], "redirect_uri": REDIRECT,
        "response_type": "code", "scope": "talk_message"}))
    print("브라우저에서 카카오 로그인 후 '동의하고 계속하기'를 눌러주세요...")
    webbrowser.open(url)
    srv = HTTPServer(("localhost", 8080), H)
    while "code" not in code_box:
        srv.handle_request()
    if not code_box["code"]:
        sys.exit(f"로그인 실패: {code_box['error']}")
    tok = kakao.exchange_code(code_box["code"], REDIRECT)
    kakao._save_refresh(tok["refresh_token"])
    print("\n✅ 토큰 발급 완료 (kakao_token.json 저장)")
    print("\n▼ GitHub Secrets 의 KAKAO_REFRESH_TOKEN 에 아래 값을 등록하세요 ▼")
    print(tok["refresh_token"])
    try:
        kakao.send("✅ 지원금 초안 알림 연결 완료!\n내일 아침부터 이 방으로 초안 알림이 옵니다.",
                   "https://www.tistory.com", "티스토리 열기")
        print("\n카톡 '나와의 채팅'을 확인하세요.")
    except Exception as e:
        print("\n테스트 메시지 실패:", e)

if __name__ == "__main__":
    main()
