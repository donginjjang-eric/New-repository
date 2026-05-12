# 이미지 업로드 → 상세페이지 5장 자동생성 토스 스타일 Streamlit 앱

import os

import streamlit as st

try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

from openai_client import (
    analyze_image,
    generate_detail_image,
    parse_analysis,
    save_good_example,
)
from prompts import STAGES

st.set_page_config(
    page_title="상세페이지 자동 생성",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="expanded",
)


def _check_password() -> bool:
    expected = None
    try:
        expected = st.secrets.get("APP_PASSWORD")
    except Exception:
        expected = os.getenv("APP_PASSWORD")
    if not expected:
        return True
    if st.session_state.get("auth_ok"):
        return True
    st.markdown("## 🔒 비밀번호를 입력해주세요")
    pw = st.text_input("비밀번호", type="password", label_visibility="collapsed")
    if pw:
        if pw == expected:
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.error("비밀번호가 틀려요.")
    return False


if not _check_password():
    st.stop()

st.markdown(
    """
<style>
    .main .block-container { padding-top: 2rem; max-width: 720px; }
    section[data-testid="stSidebar"] { background: #F7F8FA; }
    section[data-testid="stSidebar"] .block-container { padding-top: 2rem; }
    h1 { font-size: 2.2rem !important; font-weight: 800 !important; }
    h2 { font-size: 1.4rem !important; font-weight: 700 !important;
         margin-top: 2rem !important; }
    .stButton > button {
        width: 100%; min-height: 64px; font-size: 1.1rem; font-weight: 700;
        border-radius: 16px; border: none;
        background: linear-gradient(135deg, #0064FF 0%, #00C2FF 100%);
        color: white; transition: all 0.2s; margin-bottom: 8px;
    }
    .stButton > button:hover { transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,100,255,0.3); }
    .stButton > button:disabled {
        background: #E5E8EB; color: #8B95A1; cursor: not-allowed; }
    .stDownloadButton > button {
        background: white !important; color: #0064FF !important;
        border: 2px solid #0064FF !important; min-height: 48px;
    }
    .stTextInput input, .stTextArea textarea {
        font-size: 1.05rem !important; border-radius: 12px !important;
        border: 2px solid #E5E8EB !important; padding: 12px !important; }
    .stFileUploader {
        border-radius: 16px; padding: 20px;
        background: #F7F8FA; border: 2px dashed #D1D6DB; }
    .step-label { display: inline-block; padding: 6px 16px;
        background: #E8F3FF; color: #0064FF; border-radius: 999px;
        font-weight: 700; font-size: 1rem; margin-bottom: 12px; }
</style>
""",
    unsafe_allow_html=True,
)

if "results" not in st.session_state:
    st.session_state.results = []
if "product_info" not in st.session_state:
    st.session_state.product_info = {"name": "", "features": "", "target": "", "analysis": ""}
if "uploaded_bytes" not in st.session_state:
    st.session_state.uploaded_bytes = None


def generate_and_store(stage_num: int):
    stage = STAGES[stage_num]
    mime = st.session_state.get("uploaded_mime", "image/jpeg")
    result = generate_detail_image(
        stage_num,
        st.session_state.product_info,
        st.session_state.uploaded_bytes,
        mime,
    )
    st.session_state.results = [
        r for r in st.session_state.results if r["stage"] != stage_num
    ]
    st.session_state.results.append({
        "stage": stage_num,
        "image_bytes": result["image_bytes"],
        "stage_name": stage["name"],
        "used_prompt": result["prompt"],
        "review": result["review"],
        "retried": result["retried"],
        "liked": False,
    })


# ─────────── 메인 영역 (위에서부터) ───────────

st.title("🎨 상세페이지 자동 생성")
st.caption("이미지 한 장만 올리면 챗GPT가 상세페이지 5장을 만들어드려요.")

st.markdown("## 1️⃣ 상품 이미지 올리기")
uploaded = st.file_uploader(
    "이미지를 끌어놓거나 클릭해서 선택하세요",
    type=["png", "jpg", "jpeg", "webp"],
    label_visibility="collapsed",
)

if uploaded is not None:
    image_bytes = uploaded.read()
    st.session_state.uploaded_bytes = image_bytes
    st.session_state.uploaded_mime = uploaded.type

if st.session_state.uploaded_bytes is not None:
    st.image(st.session_state.uploaded_bytes,
             caption="업로드된 상품 이미지", use_container_width=True)

    if st.button("🔍 이미지에서 상품 정보 자동 추출",
                 key="analyze", use_container_width=True):
        with st.spinner("이미지를 분석 중이에요... (10~20초)"):
            try:
                mime = st.session_state.get("uploaded_mime", "image/jpeg")
                text = analyze_image(st.session_state.uploaded_bytes, mime)
                parsed = parse_analysis(text)
                st.session_state.product_info.update(parsed)
                st.success("자동 추출 완료! 아래 폼에서 수정하실 수 있어요.")
                st.rerun()
            except Exception as e:
                st.error(f"분석 실패: {e}")

st.markdown("## 2️⃣ 제품 정보 (선택사항)")
st.caption("비워두셔도 되지만, 적을수록 더 잘 만들어요.")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("상품명",
                         value=st.session_state.product_info.get("name", ""),
                         placeholder="예: 친환경 토마토")
with col2:
    target = st.text_input("타겟 고객",
                           value=st.session_state.product_info.get("target", ""),
                           placeholder="예: 건강 챙기는 30~40대 주부")

features = st.text_area(
    "핵심 특징",
    value=st.session_state.product_info.get("features", ""),
    placeholder="예: 무농약 인증, 당도 10브릭스, 새벽 수확 당일 배송",
    height=80,
)

st.session_state.product_info["name"] = name
st.session_state.product_info["features"] = features
st.session_state.product_info["target"] = target

# ─────────── 결과 영역 (사이드바 코드보다 먼저 실행되도록 위에 배치) ───────────

st.markdown("## 📦 생성된 상세페이지")

if not st.session_state.results:
    if st.session_state.uploaded_bytes is None:
        st.info("👆 먼저 위에서 상품 이미지를 올려주세요.")
    else:
        st.info("👈 왼쪽 사이드바에서 1번 버튼을 눌러 시작하세요.")
else:
    sorted_results = sorted(st.session_state.results, key=lambda r: r["stage"])
    for r in sorted_results:
        review = r.get("review") or {}
        score = review.get("score", 0)
        if score >= 85:
            badge_color, badge_text = "#0AB36D", f"🟢 검수 {score}점 · 잘 나옴"
        elif score >= 70:
            badge_color, badge_text = "#F59E0B", f"🟡 검수 {score}점 · 보통"
        else:
            badge_color, badge_text = "#EF4444", f"🔴 검수 {score}점 · 다시 만드세요"
        retried_mark = " · ✨ 재시도 후 개선" if r.get("retried") else ""

        st.markdown(
            f"<div class='step-label'>{r['stage']}번 · {r['stage_name']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='display:inline-block;padding:6px 14px;"
            f"background:{badge_color}1A;color:{badge_color};"
            f"border-radius:999px;font-weight:700;font-size:0.95rem;"
            f"margin-bottom:12px;'>{badge_text}{retried_mark}</div>",
            unsafe_allow_html=True,
        )
        st.image(r["image_bytes"], use_container_width=True)

        col_dl, col_redo, col_like = st.columns(3)
        with col_dl:
            st.download_button(
                label=f"💾 다운로드",
                data=r["image_bytes"],
                file_name=f"detail_{r['stage']:02d}_{r['stage_name'].split('(')[0].strip()}.png",
                mime="image/png",
                key=f"dl_{r['stage']}",
                use_container_width=True,
            )
        with col_redo:
            if st.button(f"🔄 다시 만들기", key=f"redo_{r['stage']}",
                         use_container_width=True):
                with st.spinner(f"{r['stage']}번 다시 만드는 중... (50~90초)"):
                    try:
                        generate_and_store(r["stage"])
                        st.rerun()
                    except Exception as e:
                        st.error(f"{r['stage']}번 재생성 실패: {e}")
        with col_like:
            like_label = "❤️ 학습됨" if r.get("liked") else "👍 좋아요 (학습)"
            if st.button(like_label, key=f"like_{r['stage']}",
                         disabled=r.get("liked", False),
                         use_container_width=True):
                try:
                    save_good_example(
                        r["stage"],
                        r.get("used_prompt", ""),
                        st.session_state.product_info.get("name", ""),
                    )
                    r["liked"] = True
                    st.toast("학습 풀에 저장됐어요. 다음 호출에 참고됩니다.", icon="🧠")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

        if review.get("issues") or review.get("suggestions"):
            with st.expander("🔍 검수 결과 자세히 보기"):
                if review.get("issues"):
                    st.markdown("**부족한 점**")
                    for it in review["issues"]:
                        st.markdown(f"- {it}")
                if review.get("suggestions"):
                    st.markdown("**개선 제안**")
                    for it in review["suggestions"]:
                        st.markdown(f"- {it}")

        if r.get("used_prompt"):
            with st.expander("🧠 GPT가 만든 디자인 프롬프트 보기"):
                st.text(r["used_prompt"])
        st.markdown("---")

    if st.button("🗑️ 모두 지우고 처음부터", use_container_width=True):
        st.session_state.results = []
        st.rerun()

# ─────────── 사이드바 (가장 마지막 - 결과 영역이 먼저 그려진 후 실행됨) ───────────
# 이 위치에 둬야 사이드바 버튼 클릭 시 spinner 도는 동안에도
# 이미 생성된 결과 카드가 메인 화면에 그대로 남아있음.

with st.sidebar:
    st.markdown("### 🎨 단계별 생성")
    st.caption("순서대로 눌러보세요.\n디자인 → 생성 → 검수 3단계로 진행됩니다.\n한 단계당 약 50~90초 (재시도 시 더 걸림).")
    st.markdown("")

    can_generate = st.session_state.uploaded_bytes is not None

    for i in range(1, 6):
        stage = STAGES[i]
        already_done = any(r["stage"] == i for r in st.session_state.results)
        check = " ✅" if already_done else ""
        label = f"{stage['emoji']} {i}번 · {stage['name'].split('(')[0].strip()}{check}"
        if st.button(label, key=f"side_gen_{i}",
                     disabled=not can_generate,
                     use_container_width=True):
            with st.spinner(f"{i}번 ({stage['name']}) 작업 중...\n"
                            f"1/3: 디자인 프롬프트 → 2/3: 이미지 생성 → "
                            f"3/3: 검수 (총 50~90초, 재시도 시 더 걸림)"):
                try:
                    generate_and_store(i)
                    st.rerun()
                except Exception as e:
                    st.error(f"{i}번 생성 실패: {e}")

    if not can_generate:
        st.caption("👈 메인 화면에서 이미지를 먼저 올려주세요.")
