# 진짜 자율 — gpt-image-2가 자기 판단대로 만들도록 최소한의 정보만 전달

STAGES = {
    1: {"name": "후킹 (메인 비주얼)", "emoji": "🎯", "label_en": "hero"},
    2: {"name": "공감/문제 제기", "emoji": "💭", "label_en": "empathy / pain point"},
    3: {"name": "제품 특징", "emoji": "✨", "label_en": "features"},
    4: {"name": "신뢰 요소", "emoji": "🏅", "label_en": "trust / social proof"},
    5: {"name": "구매 유도 (CTA)", "emoji": "🛒", "label_en": "call to action"},
}


def build_prompt(stage_num: int, product_info: dict) -> str:
    """모델에 줄 정보를 최소화. 디자인/카피 가이드는 모델 자율에 맡김."""
    s = STAGES[stage_num]
    name = (product_info.get("name") or "").strip()
    features = (product_info.get("features") or "").strip()
    target = (product_info.get("target") or "").strip()

    lines = [
        f"Page {stage_num} of 5 of a Korean ecommerce product detail page.",
        f"This page is the {s['label_en']} page.",
        "Use the attached image as the product.",
    ]
    if name:
        lines.append(f"Product: {name}")
    if features:
        lines.append(f"Features: {features}")
    if target:
        lines.append(f"Target customer: {target}")

    return "\n".join(lines)
