# 상세페이지 자동 생성기

이미지 1장만 올리면 스마트스토어용 상세페이지 5장을 챗GPT(GPT-4o + gpt-image-2)가 만들어주는 토스 스타일 미니멀 앱.

## 5단계 흐름
1. 🎯 **후킹** — 시선 사로잡는 메인 비주얼
2. 💭 **공감** — 고객 문제 제기
3. ✨ **특징** — 핵심 셀링포인트
4. 🏅 **신뢰** — 인증/후기/데이터
5. 🛒 **구매유도** — 한정 혜택 + CTA

## 내부 파이프라인
```
디자이너 GPT-4o (이미지 분석 + 디테일 영문 프롬프트 작성, Few-shot 학습)
   ↓
gpt-image-2 (이미지 생성)
   ↓
검수자 GPT-4o (0~100 점수 + 부족한 점 + 개선 제안)
   ↓ 70점 미만이면 자동 재시도 1회
👍 좋아요 누르면 learning_pool.json에 저장 → 다음 호출 시 참고
```

## 로컬 실행

```powershell
# 처음 한 번만
pip install -r requirements.txt

# .env에 API 키 입력
notepad .env

# 서버 띄우기
streamlit run app.py
```

브라우저가 자동으로 열림 (`http://localhost:8501` 또는 `:8502`).

## Streamlit Cloud 배포 (본인만 비밀번호로 접근)

1. **GitHub에 푸시** (auto_detail_page 폴더 → 새 레포)
2. https://share.streamlit.io 접속 → GitHub 로그인
3. "New app" → 레포 선택 → Main file path: `app.py`
4. "Advanced settings" → "Secrets" 탭에서 다음 입력:
   ```toml
   OPENAI_API_KEY = "sk-..."
   APP_PASSWORD = "원하는비밀번호"
   ```
5. Deploy 클릭 → 약 1~2분 후 `https://*.streamlit.app` URL 발급
6. 본인만 접근 가능: 페이지 들어가면 비밀번호 입력란이 먼저 나옴

## 비용
- 1장 풀세트(디자인 분석 + 생성 + 검수): 약 70~100원
- 재시도 발생 시 1.5배

## 파일 구성
- `app.py` — Streamlit UI (비밀번호 게이트 포함)
- `prompts.py` — 5단계 + 디자이너/검수자 시스템 프롬프트
- `openai_client.py` — OpenAI 호출 + Few-shot 학습 + 자동 재시도
- `learning_pool.json` — 👍 받은 좋은 예시 누적 (자동 생성)
- `.env` — 로컬 API 키 (깃 제외)
- `.streamlit/secrets.toml` — 클라우드 시크릿 (깃 제외)
