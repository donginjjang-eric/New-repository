# auto_detail_page — 체크리스트

## 목표
이미지 1장 업로드 → 스마트스토어 상세페이지 5장(후킹→공감→특징→신뢰→구매유도) 자동 생성.
50대도 쓸 수 있는 토스 스타일 미니멀 UI.

## 작업 항목

### A. 환경 세팅
- [ ] Python(파이썬) 설치 확인 (3.10 이상)
- [ ] `requirements.txt` 작성 — streamlit, openai, python-dotenv, Pillow
- [ ] 의존성 설치 (`pip install -r requirements.txt`)
- [ ] `.env.example` 작성 (API 키 양식)
- [ ] `.env` 파일에 사용자 OpenAI API 키 넣기
- [ ] `.gitignore`에 `.env`, `__pycache__` 추가

### B. 프롬프트 모듈 (`prompts.py`)
- [ ] 5단계 프롬프트 템플릿 작성
  - [ ] 1번: 후킹 (메인 이미지 + 강력한 헤드라인)
  - [ ] 2번: 공감/문제 제기
  - [ ] 3번: 제품 특징 (셀링포인트 3개)
  - [ ] 4번: 신뢰 요소 (인증/후기/데이터)
  - [ ] 5번: 구매 유도 (CTA)
- [ ] 폼 입력(상품명/특징/타겟)을 프롬프트에 끼워넣는 함수

### C. OpenAI 호출 모듈 (`openai_client.py`)
- [ ] GPT-4o Vision으로 업로드 이미지 분석 → 제품 설명 추출
- [ ] gpt-image-1로 상세페이지 이미지 생성
- [ ] 에러 처리 (API 키 오류, 잔액 부족, 타임아웃)

### D. Streamlit UI (`app.py`)
- [ ] 이미지 업로드 박스 (드래그앤드롭)
- [ ] 폼 — 상품명, 핵심 특징, 타겟 고객
- [ ] 1~5번 큰 버튼 (가로 배치, 큰 글씨)
- [ ] 각 번호 클릭 시 아래에 결과 이미지가 순차적으로 쌓이는 구조
- [ ] 다운로드 버튼 (각 이미지마다)
- [ ] 로딩 상태 표시 ("이미지 생성 중...")

### E. 검증
- [ ] `streamlit run app.py` 로 서버 띄우기
- [ ] 토마토 샘플 이미지(`실습용 기본 자료/토마토-1.jpg`)로 1번 후킹 생성
- [ ] 1~5번 모두 순차 생성 정상 동작 확인
- [ ] 다운로드 동작 확인

### F. 마무리
- [x] README.md 작성 (실행 방법, 비용 안내)
- [ ] 첫 커밋 (git init부터)

### G. 검수 에이전트 + Few-shot 학습 (2026-05-12 신규)
- [ ] prompts.py에 REVIEWER_SYSTEM_PROMPT 추가
  - 점수(0~100) + 부족한 항목 + 개선 제안 출력
- [ ] learning_pool.json 파일 구조 정의 (good_examples 배열)
- [ ] openai_client.py에 헬퍼 함수 추가
  - load_good_examples(stage_num, limit=3)
  - save_good_example(stage_num, prompt, product_type)
- [ ] openai_client.py에 review_image() 함수
  - GPT-4o vision으로 결과 이미지 평가
  - 점수 + 피드백 반환
- [ ] generate_detail_image()에 검수 + 재시도 로직 통합
  - 1차 생성 → 검수 → 점수 70 미만이면 피드백 합쳐서 1회 재시도
- [ ] design_detailed_prompt()에 few-shot 예시 주입
  - 같은 stage의 좋은 예시 최근 3개를 system 메시지에 추가
- [ ] app.py에 👍 좋아요 버튼 + 검수 점수 표시
  - 좋아요 클릭 시 learning_pool에 저장
  - 점수에 따라 결과 카드 위에 뱃지 (🟢 잘 나옴 / 🟡 보통 / ✨ 재시도 후 개선)
