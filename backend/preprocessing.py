import pandas as pd
import ast
import numpy as np

RECIPES_PATH = "data/RAW_recipes.csv"
MAX_ROWS = 8000


def list_to_text(text):
    if pd.isna(text):
        return ""
    try:
        v = ast.literal_eval(text)
        if isinstance(v, list):
            return " ".join([str(x) for x in v])
        return str(v)
    except:
        return str(text)


def parse_nutrition(nutrition_str):
    """
    Kolom nutrition di dataset formatnya list:
    [calories, total_fat_%dv, sugar_%dv, sodium_%dv, protein_%dv, sat_fat_%dv, carbs_%dv]
    Return dict dengan key yang readable.
    """
    try:
        vals = ast.literal_eval(str(nutrition_str))
        if isinstance(vals, list) and len(vals) >= 7:
            return {
                "calories":    float(vals[0]),
                "total_fat":   float(vals[1]),
                "sugar":       float(vals[2]),
                "sodium":      float(vals[3]),
                "protein":     float(vals[4]),
                "sat_fat":     float(vals[5]),
                "carbs":       float(vals[6]),
            }
    except:
        pass
    return {
        "calories": 0.0, "total_fat": 0.0, "sugar": 0.0,
        "sodium": 0.0, "protein": 0.0, "sat_fat": 0.0, "carbs": 0.0,
    }


def load_recipes():
    recipes = pd.read_csv(
        RECIPES_PATH,
        usecols=["id", "name", "tags", "description", "ingredients",
                 "nutrition", "minutes", "n_ingredients", "steps"]
    )

    # Expand ke 8000 baris, drop yang nama-nya kosong
    recipes = recipes.dropna(subset=["name"]).head(MAX_ROWS).copy()
    recipes = recipes.rename(columns={"id": "recipe_id"})
    recipes = recipes.reset_index(drop=True)

    # ── Text fields ──────────────────────────────────────────────────────────
    recipes["name_txt"] = recipes["name"].fillna("").astype(str)
    recipes["tags_txt"] = recipes["tags"].apply(list_to_text)
    recipes["ing_txt"]  = recipes["ingredients"].apply(list_to_text)
    recipes["desc_txt"] = recipes["description"].fillna("").astype(str)

    # text gabungan untuk TF-IDF dan SBERT embedding
    recipes["text"] = (
        recipes["name_txt"] + " " +
        recipes["tags_txt"] + " " +
        recipes["ing_txt"]  + " " +
        recipes["desc_txt"]
    ).str.lower().str.strip()

    # ── Nutrition ─────────────────────────────────────────────────────────────
    nutrition_parsed = recipes["nutrition"].apply(parse_nutrition)
    nutrition_df = pd.DataFrame(nutrition_parsed.tolist())
    recipes = pd.concat([recipes.reset_index(drop=True), nutrition_df], axis=1)

    # ── Helpers untuk explainer ───────────────────────────────────────────────
    # Flag "quick meal" jika <= 30 menit
    recipes["is_quick"] = recipes["minutes"].fillna(999) <= 30

    # Flag "high protein" jika protein %DV >= 20
    recipes["is_high_protein"] = recipes["protein"] >= 20

    # Flag "low calorie" jika < 300 kalori
    recipes["is_low_calorie"] = recipes["calories"] < 300

    return recipes