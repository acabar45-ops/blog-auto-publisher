# blog-auto-publisher

하우스맨 자동 블로그 발행 프로그램. 매일 오전 9시(월~금) Claude Sonnet 4.6으로 한국어 SEO 블로그 글을 생성해 WordPress에 자동 발행합니다.

## 📐 아키텍처

```
[Google Sheet 키워드 큐]
     ↓ (GitHub Actions cron, 월~금 09:00 KST)
[publish.py]
     ├─ 1. keyword_source.py  ─── 오늘 발행할 키워드 1개 fetch + "발행중" 락
     ├─ 2. claude_client.py   ─── Claude API로 1,500~2,000자 글 생성 (프롬프트 캐싱)
     ├─ 3. validator.py       ─── 길이·한국어·금지어 검증 (3회 재시도)
     ├─ 4. wp_client.py       ─── WordPress REST API로 발행 + Featured Image
     ├─ 5. vercel_deploy.py   ─── Vercel 재빌드 훅 호출 → 2분 내 사이트 반영
     └─ 6. notifier.py        ─── 솔라피로 사장님 카톡 알림 (성공/실패)
```

## 🛠 사전 준비

### 1. Anthropic API Key
1. https://console.anthropic.com/ 가입
2. Settings → API Keys → Create Key
3. `.env`에 `ANTHROPIC_API_KEY=sk-ant-...`

### 2. WordPress Application Password
1. WP 관리자 → 사용자 → 프로필 → 하단 "Application Passwords"
2. 이름 입력 → Add New → 24자리 비밀번호 한 번만 표시됨
3. `.env`에:
   ```
   WP_URL=https://cms.houseman.co.kr/wp-json/wp/v2
   WP_USER=houseman
   WP_APP_PW=xxxx xxxx xxxx xxxx xxxx xxxx
   ```

### 3. Google Sheet 키워드 DB
1. Google Cloud Console → IAM → 서비스 계정 생성 → JSON Key 다운로드
2. `credentials.json`로 저장 (`.gitignore`에 이미 포함됨)
3. Sheets API + Drive API 활성화
4. 시트 공유 → 서비스 계정 이메일(`xxx@xxx.iam.gserviceaccount.com`) **편집자 권한** 추가
5. 시트 포맷 (첫 행은 헤더):

| date | category | keyword | sub_keywords | status | url | created_at |
|---|---|---|---|---|---|---|
| 2026-06-16 | 건물주 실무 가이드 | 임대료 미납 대응 | 내용증명,법적 절차 | 대기 | | |
| 2026-06-17 | 단기임대 전문 | 강남 단기임대 수익률 | 2026,계산법 | 대기 | | |

6. `.env`에:
   ```
   GOOGLE_CREDENTIALS_PATH=credentials.json
   GOOGLE_SHEET_NAME=하우스맨 블로그큐
   GOOGLE_SHEET_WORKSHEET=keywords
   ```

### 4. Vercel Deploy Hook
1. Vercel 프로젝트 → Settings → Git → Deploy Hooks → 이름 "blog-publish" → URL 복사
2. `.env`에 `VERCEL_DEPLOY_HOOK=https://api.vercel.com/v1/integrations/deploy/prj_xxx/xxxx`

### 5. 솔라피 (알림톡 폴백 SMS)
1. 기존 하우스맨 SaaS에서 쓰는 키 재사용
2. `.env`에:
   ```
   SOLAPI_API_KEY=NCSxx...
   SOLAPI_API_SECRET=xxx
   SOLAPI_SENDER=02-XXXX-XXXX  # 발신번호
   NOTIFY_PHONE=010-XXXX-XXXX  # 사장님 휴대폰
   ```

## 🚀 로컬 테스트

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # 값 채우기
python publish.py       # 한 편 생성·발행
```

**드라이런** (WP 발행 없이 생성만 테스트):
```bash
python publish.py --dry-run
```

## ☁️ GitHub Actions 배포

1. GitHub repo 생성 후 코드 push
2. Repo Settings → Secrets and variables → Actions → 아래 키들 추가:
   - `ANTHROPIC_API_KEY`
   - `WP_URL`, `WP_USER`, `WP_APP_PW`
   - `GOOGLE_CREDENTIALS_JSON` (credentials.json 파일 내용 전체를 붙여넣기)
   - `GOOGLE_SHEET_NAME`, `GOOGLE_SHEET_WORKSHEET`
   - `VERCEL_DEPLOY_HOOK`
   - `SOLAPI_API_KEY`, `SOLAPI_API_SECRET`, `SOLAPI_SENDER`, `NOTIFY_PHONE`
3. `.github/workflows/daily-blog.yml`이 월~금 09:00 KST에 자동 실행

## 💰 비용

- Claude Sonnet 4.6: 편당 약 **$0.012 (≈ 16원)**
- 프롬프트 캐싱 적용 시: 편당 약 **$0.005 (≈ 7원)**
- 월 22편 기준: **약 150~350원**
- 이외: GitHub Actions 무료, Vercel 무료, WordPress 호스팅 별도

## 🛡 안전 장치

- **길이 검증**: 1,400자 미만 또는 2,200자 초과 시 재시도 (최대 3회)
- **한국어 비율**: 한글 85% 미만 시 재시도
- **금지어**: "절대적", "100% 확실", ChatGPT/OpenAI 명시 포함 시 draft 저장 + 사장님 알림
- **하우스맨 언급 확인**: 글에 "하우스맨" 단어 없으면 draft 저장
- **중복 발행 방지**: Google Sheet "발행중" 락 + 발행 완료 후 status 업데이트

## 📞 문의

- 하우스맨 박종호 대표 · 1544-4150
- 기술 문의: contact@houseman.co.kr
