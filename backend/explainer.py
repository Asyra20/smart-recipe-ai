import os
import json
import httpx
from anthropic import Anthropic

# Inisialisasi client Anthropic (pakai ANTHROPIC_API_KEY dari env)
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


# ── Rule-based explanation ────────────────────────────────────────────────────

def explain_rule_based(query_recipe: dict, recommended_recipe: dict, scores: dict) -> dict:
    """
    Generate penjelasan berbasis rule dari metadata resep.

    Args:
        query_recipe      : dict recipe yang dijadikan referensi
        recommended_recipe: dict recipe hasil rekomendasi
        scores            : dict {"sbert": float, "cbf": float, "cf": float, "hybrid": float}

    Return dict:
        {
          "reasons": ["similar ingredients", "breakfast category", ...],
          "confidence": "high" | "medium" | "low",
          "used_llm": False
        }
    """
    reasons = []

    # 1. Ingredient overlap
    q_ing  = set(_parse_list(query_recipe.get("ingredients", [])))
    r_ing  = set(_parse_list(recommended_recipe.get("ingredients", [])))
    shared = q_ing & r_ing

    if len(shared) >= 5:
        reasons.append(f"shares {len(shared)} ingredients (e.g. {', '.join(list(shared)[:3])})")
    elif len(shared) >= 2:
        reasons.append(f"similar ingredients: {', '.join(list(shared)[:3])}")

    # 2. Tag overlap
    q_tags = set(_parse_list(query_recipe.get("tags", [])))
    r_tags = set(_parse_list(recommended_recipe.get("tags", [])))
    shared_tags = q_tags & r_tags

    # Ambil tag yang informatif (bukan generic)
    SKIP_TAGS = {"easy", "course", "main-ingredient", "preparation", "occasion",
                 "cuisine", "dietary", "time-to-make", "technique"}
    useful_tags = [t for t in shared_tags if t not in SKIP_TAGS][:3]
    if useful_tags:
        reasons.append(f"{', '.join(useful_tags)} category")

    # 3. Nutritional profile
    q_cal  = query_recipe.get("calories", 0)
    r_cal  = recommended_recipe.get("calories", 0)
    if q_cal > 0 and r_cal > 0:
        cal_diff_pct = abs(q_cal - r_cal) / max(q_cal, r_cal)
        if cal_diff_pct < 0.2:
            reasons.append("similar calorie profile")

    if recommended_recipe.get("is_high_protein"):
        reasons.append("high protein")

    if recommended_recipe.get("is_low_calorie"):
        reasons.append("low calorie")

    # 4. Preparation time
    if recommended_recipe.get("is_quick"):
        reasons.append("quick to make (≤30 min)")

    q_min = query_recipe.get("minutes", 0)
    r_min = recommended_recipe.get("minutes", 0)
    if q_min and r_min and abs(q_min - r_min) <= 15 and not recommended_recipe.get("is_quick"):
        reasons.append("similar prep time")

    # 5. Score-based reasons
    if scores.get("cf", 0) > 0.3:
        reasons.append("popular among users who liked similar recipes")

    if scores.get("sbert", 0) > 0.7:
        reasons.append("semantically very similar")

    # Fallback kalau tidak ada reason sama sekali
    if not reasons:
        reasons.append("similar cooking style")

    # Confidence berdasarkan hybrid score
    hybrid = scores.get("hybrid", 0)
    if hybrid >= 0.65:
        confidence = "high"
    elif hybrid >= 0.40:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "reasons":    reasons,
        "confidence": confidence,
        "used_llm":   False,
    }


# ── LLM fallback ─────────────────────────────────────────────────────────────

def explain_with_llm(query_recipe: dict, recommended_recipe: dict, scores: dict) -> dict:
    """
    Fallback ke Claude claude-haiku-4-5-20251001 kalau rule-based kurang informatif.
    Hanya dipanggil kalau reasons dari rule-based < 2 atau confidence = "low".
    """
    prompt = f"""You are a culinary AI assistant. Explain briefly why recipe B is recommended based on recipe A.

Recipe A (reference): {query_recipe.get('name')}
- Tags: {_parse_list(query_recipe.get('tags', []))[:5]}
- Ingredients: {_parse_list(query_recipe.get('ingredients', []))[:8]}
- Calories: {query_recipe.get('calories', 'unknown')}

Recipe B (recommended): {recommended_recipe.get('name')}
- Tags: {_parse_list(recommended_recipe.get('tags', []))[:5]}
- Ingredients: {_parse_list(recommended_recipe.get('ingredients', []))[:8]}
- Calories: {recommended_recipe.get('calories', 'unknown')}

Similarity scores: semantic={scores.get('sbert', 0):.2f}, content={scores.get('cbf', 0):.2f}, collaborative={scores.get('cf', 0):.2f}

Respond ONLY with a JSON object, no markdown, no explanation outside JSON:
{{"reasons": ["reason 1", "reason 2", "reason 3"], "confidence": "high|medium|low"}}

Keep each reason under 8 words. Be specific, not generic."""

    try:
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        # Strip markdown kalau ada
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        parsed = json.loads(text)
        return {
            "reasons":    parsed.get("reasons", ["similar recipe"]),
            "confidence": parsed.get("confidence", "medium"),
            "used_llm":   True,
        }

    except Exception as e:
        print(f"[Explainer] LLM fallback error: {e}")
        return {
            "reasons":    ["similar cooking style and ingredients"],
            "confidence": "low",
            "used_llm":   False,
        }


# ── Public interface ──────────────────────────────────────────────────────────

def generate_explanation(
    query_recipe: dict,
    recommended_recipe: dict,
    scores: dict,
    force_llm: bool = False,
) -> dict:
    """
    Entry point utama. Coba rule-based dulu, fallback ke LLM kalau perlu.

    Return:
        {
          "reasons":    list[str],
          "confidence": "high" | "medium" | "low",
          "used_llm":   bool
        }
    """
    if force_llm:
        return explain_with_llm(query_recipe, recommended_recipe, scores)

    result = explain_rule_based(query_recipe, recommended_recipe, scores)

    # Fallback ke LLM kalau reasons terlalu sedikit atau confidence rendah
    should_use_llm = (
        len(result["reasons"]) < 2
        or result["confidence"] == "low"
    )

    if should_use_llm:
        return explain_with_llm(query_recipe, recommended_recipe, scores)

    return result


# ── Helper ────────────────────────────────────────────────────────────────────

def _parse_list(value) -> list:
    """Pastikan value jadi Python list."""
    if isinstance(value, list):
        return value
    import ast
    try:
        result = ast.literal_eval(str(value))
        return result if isinstance(result, list) else [str(result)]
    except:
        return [v.strip() for v in str(value).split(",") if v.strip()]