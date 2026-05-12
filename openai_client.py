# OpenAI API 호출 래퍼 — 디자인 → 생성 → 검수 → 자동 재시도 + Few-shot 학습

import base64
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image as PILImage

from prompts import (
    DESIGNER_SYSTEM_PROMPT,
    REVIEWER_SYSTEM_PROMPT,
    STAGES,
    VISION_ANALYSIS_PROMPT,
    build_prompt,
)

CANVAS_W, CANVAS_H = 1024, 1536
PRODUCT_BOX_W, PRODUCT_BOX_H = 720, 720
PRODUCT_TOP = 480

LEARNING_POOL_PATH = Path(__file__).parent / "learning_pool.json"
PASS_SCORE = 70
MAX_RETRY = 1


def _resolve_key(override: str = "") -> str:
    if override and not override.startswith("sk-여기에"):
        return override.strip()
    load_dotenv(override=True)
    return os.getenv("OPENAI_API_KEY", "").strip()


def _client(api_key: str = "") -> OpenAI:
    key = _resolve_key(api_key)
    if not key or key.startswith("sk-여기에"):
        raise RuntimeError(
            "왼쪽 사이드바에 OpenAI API 키를 입력해주세요. "
            "platform.openai.com → API keys 에서 발급받을 수 있습니다."
        )
    return OpenAI(api_key=key)


# ─────────── learning_pool (Few-shot 예시 저장소) ───────────

def load_good_examples(stage_num: int, limit: int = 3) -> list[dict]:
    """같은 stage의 ★ 받은 예시 최근 N개 반환."""
    if not LEARNING_POOL_PATH.exists():
        return []
    try:
        data = json.loads(LEARNING_POOL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    examples = [e for e in data.get("good_examples", [])
                if e.get("stage") == stage_num]
    return examples[-limit:]


def save_good_example(stage_num: int, prompt: str, product_type: str = "") -> None:
    """사용자가 👍 누른 결과의 프롬프트를 풀에 저장."""
    data = {"good_examples": []}
    if LEARNING_POOL_PATH.exists():
        try:
            data = json.loads(LEARNING_POOL_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data.setdefault("good_examples", []).append({
        "stage": stage_num,
        "prompt": prompt,
        "product_type": product_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    data["good_examples"] = data["good_examples"][-50:]
    LEARNING_POOL_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─────────── 1단계: 디자인 프롬프트 생성 (Few-shot 주입) ───────────

def design_detailed_prompt(stage_num: int, product_info: dict,
                           source_image_bytes: bytes,
                           mime_type: str = "image/jpeg",
                           extra_feedback: str = "") -> str:
    """GPT-4o가 이미지와 단계 의도를 보고 detailed 영문 프롬프트 작성.
    learning_pool의 ★ 예시들을 few-shot으로 주입.
    extra_feedback이 있으면 검수 재시도용 개선 지시 추가.
    """
    base_intent = build_prompt(stage_num, product_info)
    b64 = base64.b64encode(source_image_bytes).decode("utf-8")

    messages = [{"role": "system", "content": DESIGNER_SYSTEM_PROMPT}]

    examples = load_good_examples(stage_num, limit=3)
    if examples:
        ex_text = "\n\n───\n\n".join(
            f"[Previous high-rated prompt for stage {e['stage']}]\n{e['prompt']}"
            for e in examples
        )
        messages.append({
            "role": "user",
            "content": (
                "Here are previous prompts the user rated highly. "
                "Match their tone, structure, and copy style.\n\n" + ex_text
            ),
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I'll match this style closely.",
        })

    user_text = base_intent
    if extra_feedback:
        user_text += (
            f"\n\n[CRITICAL — Previous attempt scored low. Fix these issues:]\n"
            f"{extra_feedback}"
        )

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": user_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
            },
        ],
    })

    resp = _client().chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )
    return (resp.choices[0].message.content or "").strip()


# ─────────── 2단계: 이미지 생성 (캔버스 + edit API + 자동 합성 폴백) ───────────

def _prepare_canvas(source_bytes: bytes) -> tuple[bytes, tuple[int, int, int, int]]:
    """원본 상품을 흰 캔버스 가운데에 배치. (PNG bytes, 상품 위치 box) 반환.
    box는 (left, top, right, bottom) 좌표 — 후처리 합성 시 동일 위치에 다시 사용.
    """
    canvas = PILImage.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 255))
    src = PILImage.open(io.BytesIO(source_bytes))
    if src.mode != "RGBA":
        src = src.convert("RGBA")

    src_ratio = src.width / src.height
    if src_ratio > 1:
        new_w = PRODUCT_BOX_W
        new_h = int(new_w / src_ratio)
    else:
        new_h = PRODUCT_BOX_H
        new_w = int(new_h * src_ratio)
    src = src.resize((new_w, new_h), PILImage.LANCZOS)

    left = (CANVAS_W - new_w) // 2
    top = PRODUCT_TOP + (PRODUCT_BOX_H - new_h) // 2
    canvas.paste(src, (left, top), src)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    buf.name = "canvas.png"
    return buf.getvalue(), (left, top, left + new_w, top + new_h)


def _generate_image(prompt: str, source_bytes: bytes) -> tuple[bytes, tuple]:
    """edit API + 캔버스로 outpainting. (결과 bytes, 상품 box) 반환."""
    canvas_bytes, product_box = _prepare_canvas(source_bytes)
    canvas_buf = io.BytesIO(canvas_bytes)
    canvas_buf.name = "canvas.png"

    resp = _client().images.edit(
        model="gpt-image-2",
        image=canvas_buf,
        prompt=prompt,
        size="1024x1536",
        quality="high",
        n=1,
    )
    return base64.b64decode(resp.data[0].b64_json), product_box


def composite_original(result_bytes: bytes, source_bytes: bytes,
                       product_box: tuple) -> bytes:
    """A 폴백: 결과 이미지의 상품 영역에 원본을 정확히 덮어씌움 (100% 보존)."""
    result = PILImage.open(io.BytesIO(result_bytes)).convert("RGBA")
    src = PILImage.open(io.BytesIO(source_bytes))
    if src.mode != "RGBA":
        src = src.convert("RGBA")

    left, top, right, bottom = product_box
    box_w, box_h = right - left, bottom - top
    src_ratio = src.width / src.height
    if src_ratio > 1:
        new_w = box_w
        new_h = int(new_w / src_ratio)
    else:
        new_h = box_h
        new_w = int(new_h * src_ratio)
    src = src.resize((new_w, new_h), PILImage.LANCZOS)

    place_left = left + (box_w - new_w) // 2
    place_top = top + (box_h - new_h) // 2
    result.paste(src, (place_left, place_top), src)

    buf = io.BytesIO()
    result.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


# ─────────── 3단계: 검수 ───────────

def review_image(image_bytes: bytes, stage_num: int,
                 product_info: dict,
                 source_image_bytes: bytes = None,
                 source_mime: str = "image/jpeg") -> dict:
    """GPT-4o vision이 결과 이미지를 평가. 원본도 함께 비교."""
    b64_result = base64.b64encode(image_bytes).decode("utf-8")
    stage = STAGES[stage_num]
    context = (
        f"Stage {stage_num}: {stage['name']}\n"
        f"Required: {stage['must']}\n"
        f"Forbidden: {stage['forbid']}\n"
        f"Product: {product_info.get('name', '')} / "
        f"{product_info.get('features', '')} / "
        f"target: {product_info.get('target', '')}"
    )

    content = [
        {"type": "text", "text": context},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_result}"},
        },
    ]
    if source_image_bytes is not None:
        b64_src = base64.b64encode(source_image_bytes).decode("utf-8")
        content.append({
            "type": "text",
            "text": "Above is the generated image. Below is Image A (original product) for comparison."
        })
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{source_mime};base64,{b64_src}"},
        })

    resp = _client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_tokens=600,
        temperature=0.3,
    )
    return _parse_review(resp.choices[0].message.content or "")


def _parse_review(text: str) -> dict:
    result = {
        "score": 0, "pass": False, "product_changed": False,
        "issues": [], "suggestions": [], "raw": text,
    }
    m = re.search(r"SCORE:\s*(\d+)", text)
    if m:
        result["score"] = int(m.group(1))
    m = re.search(r"PASS:\s*(YES|NO)", text, re.IGNORECASE)
    if m:
        result["pass"] = m.group(1).upper() == "YES"
    m = re.search(r"PRODUCT_PRESERVED:\s*(YES|NO)", text, re.IGNORECASE)
    if m:
        result["product_changed"] = m.group(1).upper() == "NO"
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("ISSUES"):
            section = "issues"
            continue
        if line.startswith("SUGGESTIONS"):
            section = "suggestions"
            continue
        if line.startswith("-") and section:
            result[section].append(line.lstrip("- ").strip())
    return result


# ─────────── 통합: 생성 + 검수 + 자동 재시도 ───────────

def analyze_image(image_bytes: bytes, mime_type: str = "image/jpeg",
                  api_key: str = "") -> str:
    """업로드된 상품 이미지를 GPT-4o Vision으로 분석해 텍스트 정보 반환."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    resp = _client(api_key).chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_ANALYSIS_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=500,
    )
    return resp.choices[0].message.content or ""


OUTPAINT_PREFIX = (
    "The product (Image A) is already placed in the center of a 1024x1536 "
    "vertical canvas with white empty space around it (top, sides, bottom). "
    "Your task is to fill ONLY the surrounding white areas with the Korean "
    "ecommerce detail page design described below. CRITICAL: Do NOT redraw, "
    "modify, recolor, or alter the centered product image — keep it exactly "
    "as is. Only add design elements (background, copy, badges, decorative "
    "motifs) in the white margins.\n\n"
    "=== DESIGN INSTRUCTIONS ===\n"
)


def generate_detail_image(stage_num: int, product_info: dict,
                          source_image_bytes: bytes,
                          mime_type: str = "image/jpeg") -> dict:
    """전체 파이프라인: 캔버스 준비 → edit outpainting → 검수 → 변형 시 자동 합성 폴백.
    반환: {image_bytes, prompt, review, retried, composited}
    """
    detailed = design_detailed_prompt(stage_num, product_info,
                                      source_image_bytes, mime_type)
    full_prompt = OUTPAINT_PREFIX + detailed
    image_bytes, product_box = _generate_image(full_prompt, source_image_bytes)
    review = review_image(image_bytes, stage_num, product_info,
                          source_image_bytes, mime_type)
    retried = False

    if not review["pass"] and MAX_RETRY > 0:
        feedback = "\n".join(
            ["Issues:"] + [f"- {i}" for i in review["issues"]]
            + ["Fixes needed:"] + [f"- {s}" for s in review["suggestions"]]
        )
        detailed = design_detailed_prompt(
            stage_num, product_info, source_image_bytes, mime_type,
            extra_feedback=feedback,
        )
        full_prompt = OUTPAINT_PREFIX + detailed
        image_bytes, product_box = _generate_image(full_prompt, source_image_bytes)
        review = review_image(image_bytes, stage_num, product_info,
                              source_image_bytes, mime_type)
        retried = True

    composited = False
    if review.get("product_changed", False):
        image_bytes = composite_original(image_bytes, source_image_bytes, product_box)
        composited = True

    return {
        "image_bytes": image_bytes,
        "prompt": detailed,
        "review": review,
        "retried": retried,
        "composited": composited,
    }


def parse_analysis(text: str) -> dict:
    """analyze_image 결과 텍스트를 {name, features, target} 딕셔너리로 파싱."""
    result = {"name": "", "features": "", "target": ""}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("상품명:"):
            result["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("특징:"):
            result["features"] = line.split(":", 1)[1].strip()
        elif line.startswith("타겟:"):
            result["target"] = line.split(":", 1)[1].strip()
    return result
