# 지원금 초안 자동화 v3 (카톡 알림 + 모바일 미리보기)

매일 아침 7시: 지원금 수집 → 초안 5개 → 모바일 미리보기 페이지 생성 → 카톡 "나와의 채팅"으로 알림
카톡의 [초안 보기] → 초안 선택 → [제목 복사] [본문 복사] → 티스토리 앱에 붙여넣기

## A. 카카오 설정 (PC에서 1회)
1. https://developers.kakao.com 로그인 → 내 애플리케이션 → 애플리케이션 추가 (이름 아무거나)
2. 앱 키 → **REST API 키** 복사
3. 카카오 로그인 → 활성화 ON → Redirect URI 에 `http://localhost:8080/callback` 등록
4. 카카오 로그인 → 동의항목 → **카카오톡 메시지 전송** → 선택 동의로 설정
5. 플랫폼 → Web → 사이트 도메인에 `https://아이디.github.io` 등록 (카톡 버튼 링크용)
6. auto 폴더에서:
   ```
   set KAKAO_REST_KEY=REST API 키
   py kakao_login.py
   ```
   브라우저 로그인·동의 → 카톡 "나와의 채팅"에 테스트 메시지가 오면 성공. 화면에 나온 리프레시 토큰을 복사해 둡니다.

## B. GitHub 설정 (1회)
1. github.com 가입 → New repository → 이름 `subsidy` → **Public** (무료 Pages 조건. 키는 Secrets 에 따로 저장되어 공개되지 않음)
2. Add file → Upload files → auto 폴더 안 파일 전부 업로드 (`kakao_token.json` 은 올리지 마세요). `.github` 폴더가 안 올라가면 Add file → Create new file 에서 `.github/workflows/daily.yml` 이름으로 내용을 붙여넣기
3. Settings → Pages → Source: Deploy from a branch → `main` / `/docs` → Save
4. Settings → Secrets and variables → Actions → New repository secret:
   - `DATA_GO_KR_KEY` 공공데이터 인증키
   - `KAKAO_REST_KEY` 카카오 REST API 키
   - `KAKAO_REFRESH_TOKEN` A-6 에서 받은 토큰
   - `GH_PAT` 아래 C 에서 만든 토큰 (카톡 토큰 자동 갱신용)
5. Actions 탭 → 지원금 초안 자동 생성 → Run workflow 로 바로 테스트

## C. GH_PAT 만들기
GitHub 프로필 → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate
- Repository access: Only select → `subsidy`
- Permissions → Repository → **Secrets: Read and write**
- 생성된 토큰을 B-4 의 `GH_PAT` 로 등록

## 휴대폰에서 올리기
- 미리보기 페이지 하단 [본문 복사] → 티스토리 앱 글쓰기에 붙여넣기 (소제목·표 서식 유지)
- 앱에서 서식이 깨지면: 크롬으로 tistory.com → "데스크톱 사이트" 켜기 → HTML 모드 → [HTML 복사] 붙여넣기
- 올린 뒤 "티스토리에 올림" 체크 → 목록에서 흐리게 표시

## 로컬(PC)에서 돌릴 때
`py main.py` → docs/index.html 을 더블클릭하면 같은 미리보기 화면. 카톡 알림도 kakao_token.json 으로 동작
