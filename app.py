# 이미지 업로드 → 상세페이지 5장 자동생성 토스 스타일 Streamlit 앱

import os

import streamlit as st

try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

try:
    import streamlit_shadcn_ui as ui
    HAS_SHADCN = True
except Exception:
    HAS_SHADCN = False

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
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800;900&display=swap');
    html, body, [class*="css"], button, input, textarea {
        font-family: 'Pretendard', -apple-system, sans-serif !important;
    }

    /* 전체 배경 - shadcn 느낌의 미세한 회색 */
    .stApp { background: #FAFAFA; }
    .main .block-container { padding-top: 1.5rem; max-width: 760px; }

    /* 사이드바 — 메인과 명확히 구분 */
    section[data-testid="stSidebar"] {
        background: #0F172A !important;
        border-right: none;
        box-shadow: 4px 0 24px rgba(0,0,0,0.08);
    }
    section[data-testid="stSidebar"] .block-container { padding-top: 2rem; }
    section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: white !important; }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] small,
    section[data-testid="stSidebar"] p {
        color: #CBD5E1 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: #1E293B !important;
        color: #F1F5F9 !important;
        border: 1px solid #334155 !important;
        box-shadow: none !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #334155 !important;
        border-color: #475569 !important;
        transform: none;
    }
    section[data-testid="stSidebar"] .stButton > button:disabled {
        background: #1E293B !important;
        color: #64748B !important;
        opacity: 0.5;
    }

    /* 헤드 폰트 */
    h1 { font-size: 1.9rem !important; font-weight: 800 !important;
         letter-spacing: -0.03em; color: #0F172A; }
    h2 { font-size: 1.3rem !important; font-weight: 700 !important;
         margin-top: 2rem !important; letter-spacing: -0.02em; color: #0F172A; }

    /* shadcn-스타일 카드 영역 (헤더 박스) */
    .shadcn-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .shadcn-card h1 { margin-top: 0 !important; margin-bottom: 8px !important; }
    .shadcn-card .desc {
        color: #64748B; font-size: 0.95rem;
        margin-bottom: 16px;
    }
    .metric-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .metric-pill {
        background: #F1F5F9; padding: 6px 12px;
        border-radius: 8px; font-size: 0.82rem;
        font-weight: 600; color: #475569;
        border: 1px solid #E2E8F0;
    }
    .metric-pill.accent { background: #0F172A; color: white; border: none; }

    /* 진행 트래커 — 가독성 강화 */
    .progress-tracker {
        display: flex; align-items: flex-start; justify-content: space-between;
        background: white; padding: 18px 16px; border-radius: 12px;
        margin-bottom: 20px; border: 1px solid #E2E8F0;
    }
    .progress-step {
        display: flex; flex-direction: column; align-items: center; gap: 8px;
        flex-shrink: 0;
    }
    .progress-dot {
        width: 36px; height: 36px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.9rem; font-weight: 800; transition: all 0.3s;
        border: 2px solid;
    }
    .progress-dot.done {
        background: #0F172A; color: white; border-color: #0F172A;
    }
    .progress-dot.todo {
        background: white; color: #475569; border-color: #94A3B8;
    }
    .progress-line { flex: 1; height: 2px; background: #CBD5E1;
        margin-top: 17px; min-width: 8px; align-self: flex-start; }
    .progress-line.done { background: #0F172A; }
    .progress-label {
        font-size: 0.78rem; font-weight: 700;
        white-space: nowrap; line-height: 1.2;
    }
    .progress-label.done { color: #0F172A; }
    .progress-label.todo { color: #334155; }

    /* 버튼 — shadcn 미니멀 */
    .stButton > button {
        width: 100%; min-height: 48px; font-size: 0.95rem; font-weight: 600;
        border-radius: 10px; border: 1px solid #E2E8F0;
        background: white; color: #0F172A;
        transition: all 0.15s; margin-bottom: 6px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        letter-spacing: -0.01em;
    }
    .stButton > button:hover {
        background: #F8FAFC; border-color: #CBD5E1;
        transform: translateY(-1px);
    }
    .stButton > button:disabled {
        background: #F8FAFC; color: #94A3B8;
        border-color: #E2E8F0; cursor: not-allowed; transform: none;
    }
    .stDownloadButton > button {
        background: #0F172A !important; color: white !important;
        border: none !important; min-height: 44px;
    }
    .stDownloadButton > button:hover {
        background: #1E293B !important;
    }

    /* 입력 폼 */
    .stTextInput input, .stTextArea textarea {
        font-size: 0.95rem !important; border-radius: 8px !important;
        border: 1px solid #E2E8F0 !important; padding: 10px 12px !important;
        background: white !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #0F172A !important;
        box-shadow: 0 0 0 3px rgba(15,23,42,0.08) !important;
    }
    .stFileUploader {
        border-radius: 12px; padding: 20px;
        background: white;
        border: 2px dashed #CBD5E1;
    }

    /* 결과 카드 */
    .step-label {
        display: inline-block; padding: 6px 12px;
        background: #0F172A; color: white;
        border-radius: 8px;
        font-weight: 700; font-size: 0.85rem; margin-bottom: 12px;
        letter-spacing: -0.01em;
    }
    div[data-testid="stImage"] img {
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }

    /* 뷰 토글 */
    .stRadio > div { flex-direction: row !important; gap: 4px !important; }
    .stRadio label {
        background: white; padding: 6px 14px; border-radius: 8px;
        border: 1px solid #E2E8F0; cursor: pointer;
        font-weight: 600 !important; font-size: 0.9rem;
    }
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
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "single"
if "total_generated" not in st.session_state:
    st.session_state.total_generated = 0


SHORT_LABELS = {1: "후킹", 2: "공감", 3: "특징", 4: "신뢰", 5: "구매유도"}


def _render_progress_tracker() -> str:
    """1-2-3-4-5 도트 진행 시각화 HTML."""
    done_stages = {r["stage"] for r in st.session_state.results}
    parts = ["<div class='progress-tracker'>"]
    for i in range(1, 6):
        is_done = i in done_stages
        dot_class = "done" if is_done else "todo"
        check = "✓" if is_done else str(i)
        parts.append(
            f"<div class='progress-step'>"
            f"<div class='progress-dot {dot_class}'>{check}</div>"
            f"<div class='progress-label {dot_class}'>{SHORT_LABELS[i]}</div>"
            f"</div>"
        )
        if i < 5:
            line_class = "done" if is_done and (i + 1) in done_stages else ""
            parts.append(f"<div class='progress-line {line_class}'></div>")
    parts.append("</div>")
    return "".join(parts)


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

done_count = len(st.session_state.results)
liked_count = sum(1 for r in st.session_state.results if r.get("liked"))

st.markdown(
    f"""
<div class='shadcn-card'>
    <h1>상세페이지 자동 생성</h1>
    <div class='desc'>이미지 한 장으로 챗GPT가 상세페이지 5장을 만들어드립니다.</div>
    <div class='metric-row'>
        <div class='metric-pill accent'>진행 {done_count}/5</div>
        <div class='metric-pill'>❤️ 학습 {liked_count}장</div>
        <div class='metric-pill'>🤖 GPT-image-2</div>
        <div class='metric-pill'>🔍 검수 자동</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(_render_progress_tracker(), unsafe_allow_html=True)

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
    view = st.radio(
        "보기 방식",
        options=["📜 단일 큰 카드", "🖼️ 5장 그리드"],
        index=0 if st.session_state.view_mode == "single" else 1,
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.view_mode = "single" if "단일" in view else "gallery"

    sorted_results = sorted(st.session_state.results, key=lambda r: r["stage"])

    if st.session_state.view_mode == "gallery":
        cols = st.columns(5)
        for idx, r in enumerate(sorted_results):
            with cols[idx % 5]:
                st.image(r["image_bytes"], use_container_width=True)
                review = r.get("review") or {}
                score = review.get("score", 0)
                emoji = "🟢" if score >= 85 else ("🟡" if score >= 70 else "🔴")
                st.markdown(
                    f"<div style='text-align:center;font-size:0.78rem;"
                    f"font-weight:700;color:#4E5968;margin-top:4px;'>"
                    f"{r['stage']}번 {emoji} {score}점</div>",
                    unsafe_allow_html=True,
                )
        if len(sorted_results) < 5:
            empty_slots = 5 - len(sorted_results)
            st.caption(f"※ {empty_slots}장 더 만들면 풀세트 완성")
        st.markdown("---")
        if st.button("🗑️ 모두 지우고 처음부터",
                     key="clear_gallery", use_container_width=True):
            st.session_state.results = []
            st.rerun()
    else:
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

        if st.button("🗑️ 모두 지우고 처음부터",
                     key="clear_single", use_container_width=True):
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
