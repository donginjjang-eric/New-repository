# 상세페이지 5단계 — gpt-image-2가 직접 받는 프롬프트 (GPT-4o 없이)

STAGES = {
    1: {
        "name": "후킹 (메인 비주얼)",
        "emoji": "🎯",
        "intent": "Hero page — eye-catching main visual with strong Korean hook copy. NO purchase CTA, NO 'Buy Now' buttons.",
    },
    2: {
        "name": "공감/문제 제기",
        "emoji": "💭",
        "intent": "Empathy page — point out customer pain points with relatable scenarios. NO purchase CTA.",
    },
    3: {
        "name": "제품 특징",
        "emoji": "✨",
        "intent": "Features page — 3 key selling points with icons or cards, infographic feel. NO purchase CTA.",
    },
    4: {
        "name": "신뢰 요소",
        "emoji": "🏅",
        "intent": "Trust page — reviews, ratings, certifications, social proof, sales numbers. NO purchase CTA.",
    },
    5: {
        "name": "구매 유도 (CTA)",
        "emoji": "🛒",
        "intent": "CTA page — limited offer badge, large 'Buy Now' Korean button, guarantee messages (refund, free shipping).",
    },
}


def build_prompt(stage_num: int, product_info: dict) -> str:
    """gpt-image-2에 직접 보낼 짧은 영문 프롬프트.
    GPT-4o의 thinking 단계 없이 gpt-image-2가 자율적으로 해석.
    """
    s = STAGES[stage_num]
    name = (product_info.get("name") or "").strip()
    features = (product_info.get("features") or "").strip()
    target = (product_info.get("target") or "").strip()

    lines = [
        f"Create page {stage_num} of 5 for a Korean ecommerce product detail page. "
        "Use the attached image as the hero product — keep its design, logo, and color faithful.",
        "",
        f"Page intent: {s['intent']}",
    ]

    if name or features or target:
        lines.append("")
        lines.append("Product info:")
        if name:
            lines.append(f"- Name: {name}")
        if features:
            lines.append(f"- Features: {features}")
        if target:
            lines.append(f"- Target customer: {target}")

    lines.extend([
        "",
        "Design style: modern minimal Korean D2C aesthetic (similar to 마뗑킴, 매그매그, 오아이오아이). "
        "Ivory / beige / cream / soft taupe tones preferred. Ample whitespace, precise grid alignment. "
        "AVOID: pink floral patterns, glitter, rainbow gradients, garish old Korean homeshopping look.",
        "",
        "Typography: small English serif label on top, large bold Korean sans-serif headline, "
        "thin Korean subcopy, rounded pill chips with short keywords, optional decorative motif.",
        "",
        "Korean copy must be modern and natural — avoid clichés like '우아함의 정수', '빛나는 당신', "
        "'프리미엄 퀄리티', '단 하나의 선택'.",
        "",
        f"Format: vertical 1024x1536. Produce only page {stage_num}, not a collage of multiple pages.",
    ])

    return "\n".join(lines)
