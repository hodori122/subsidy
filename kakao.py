"""카카오톡 '나에게 보내기' 알림
- 로컬: kakao_token.json 에 리프레시 토큰 저장
- GitHub Actions: Secrets 의 KAKAO_REFRESH_TOKEN 사용, 토큰이 갱신되면 GH_PAT 로 Secret 자동 업데이트
"""
import os, json, base64, requests

TOKEN_FILE = "kakao_token.json"
AUTH_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

def _client():
    d = {"client_id": os.environ["KAKAO_REST_KEY"]}
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        d["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    return d

def _load_refresh():
    if os.environ.get("KAKAO_REFRESH_TOKEN"):
        return os.environ["KAKAO_REFRESH_TOKEN"].strip()
    if os.path.exists(TOKEN_FILE):
        return json.load(open(TOKEN_FILE, encoding="utf-8"))["refresh_token"]
    return None

def _update_github_secret(name, value):
    from nacl import encoding, public
    repo, pat = os.environ["GITHUB_REPOSITORY"], os.environ["GH_PAT"]
    h = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
    k = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key", headers=h, timeout=15).json()
    box = public.SealedBox(public.PublicKey(k["key"].encode(), encoding.Base64Encoder()))
    enc = base64.b64encode(box.encrypt(value.encode())).decode()
    r = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/{name}", headers=h,
                     json={"encrypted_value": enc, "key_id": k["key_id"]}, timeout=15)
    r.raise_for_status()

def _save_refresh(token):
    if os.environ.get("GITHUB_ACTIONS"):
        if os.environ.get("GH_PAT"):
            _update_github_secret("KAKAO_REFRESH_TOKEN", token)
            print("카카오 리프레시 토큰을 GitHub Secret 에 갱신했습니다")
        else:
            print("⚠ GH_PAT 가 없어 새 리프레시 토큰을 저장하지 못했습니다 (약 2개월 후 만료)")
    else:
        json.dump({"refresh_token": token}, open(TOKEN_FILE, "w", encoding="utf-8"))

def exchange_code(code, redirect_uri):
    r = requests.post(AUTH_URL, data={**_client(), "grant_type": "authorization_code",
                                      "redirect_uri": redirect_uri, "code": code}, timeout=15)
    j = r.json()
    if "refresh_token" not in j:
        raise RuntimeError(f"토큰 발급 실패: {j}")
    return j

def access_token():
    rt = _load_refresh()
    if not rt:
        raise RuntimeError("카카오 토큰이 없습니다. 먼저 'py kakao_login.py' 를 실행하세요.")
    j = requests.post(AUTH_URL, data={**_client(), "grant_type": "refresh_token", "refresh_token": rt},
                      timeout=15).json()
    if "access_token" not in j:
        raise RuntimeError(f"토큰 갱신 실패 (다시 kakao_login.py 실행 필요): {j}")
    if j.get("refresh_token"):          # 만료 1개월 전부터 새 토큰이 내려옴 → 저장하면 사실상 무기한
        _save_refresh(j["refresh_token"])
    return j["access_token"]

def send(text, url, button="초안 보기"):
    tpl = {"object_type": "text", "text": text[:200],
           "link": {"web_url": url, "mobile_web_url": url}, "button_title": button}
    r = requests.post(SEND_URL, headers={"Authorization": f"Bearer {access_token()}"},
                      data={"template_object": json.dumps(tpl, ensure_ascii=False)}, timeout=15)
    j = r.json()
    if j.get("result_code") != 0:
        raise RuntimeError(f"카톡 전송 실패: {j}")
    print("카톡 알림 전송 완료")
