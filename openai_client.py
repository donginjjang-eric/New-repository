# gpt-image-2 단독 호출 — GPT-4o 없이, 텍스트+이미지를 모델에 자율적으로 맡김

import base64
import io
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image as PILImage

from prompts import build_prompt

LEARNING_POOL_PATH = Path(__file__).parent / "learning_pool.json"


def _resolve_key(override: str = "") -> str:
    if override and not override.startswith("sk-여기에"):
        return override.strip()
    load_dotenv(override=True)
    return os.getenv("OPENAI_API_KEY", "").strip()


def _client(api_key: str = "") -> OpenAI:
    key = _resolve_key(api_key)
    if not key or key.startswith("sk-여기에"):
        raise RuntimeError(
            "OpenAI API 키가 설정되지 않았어요. "
            "platform.openai.com → API keys 에서 발급받아 .env에 입력하거나 "
            "Streamlit Cloud Secrets에 등록해주세요."
        )
    return OpenAI(api_key=key)


# ─────────── learning_pool (참고용 누적) ───────────

def save_good_example(stage_num: int, prompt: str, product_type: str = "") -> None:
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


# ─────────── gpt-image-2 단독 호출 ───────────

def generate_detail_image(stage_num: int, product_info: dict,
                          source_image_bytes: bytes,
                          mime_type: str = "image/jpeg") -> dict:
    """gpt-image-2에 이미지 + 짧은 텍스트만 전달하고 모델 자율에 맡김.
    GPT-4o thinking·검수·합성 등 통제 단계 없음.
    """
    prompt = build_prompt(stage_num, product_info)

    img = PILImage.open(io.BytesIO(source_image_bytes))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG")
    png_buf.seek(0)
    png_buf.name = "source.png"

    resp = _client().images.edit(
        model="gpt-image-2",
        image=png_buf,
        prompt=prompt,
        size="1024x1536",
        quality="high",
        n=1,
    )
    image_bytes = base64.b64decode(resp.data[0].b64_json)
    return {"image_bytes": image_bytes, "prompt": prompt}
