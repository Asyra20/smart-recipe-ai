from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from recommender import (
    recommend_by_recipe,
    semantic_search,
    get_recipe_by_id,
)
from explainer import generate_explanation, _parse_list

app = FastAPI(title="Smart Recipe AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Smart Recipe AI v2 — Hybrid Recommender Running"}


# ── Search ────────────────────────────────────────────────────────────────────

@app.get("/search")
def search(q: str = Query(..., min_length=1)):
    """
    Semantic search menggunakan SBERT + FAISS.
    Cepat — explanation di-skip, bisa di-enable dengan ?explain=true
    """
    results = semantic_search(q)
    return {
        "query":   q,
        "results": results,
    }


# ── Recommend ─────────────────────────────────────────────────────────────────

@app.get("/recommend/{recipe_id}")
def recommend(
    recipe_id: int,
    explain: bool = Query(default=True),
    top_k: int   = Query(default=10, ge=1, le=50),
):
    """
    Hybrid recommendation: SBERT (40%) + CBF (35%) + CF (25%).
    ?explain=false untuk skip AI explanation (lebih cepat).
    ?top_k=N untuk ubah jumlah hasil (default 10, max 50).
    """
    results = recommend_by_recipe(recipe_id, top_k=top_k, with_explanation=explain)

    if not results:
        raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")

    return {"recipe_id": recipe_id, "recommendations": results}


# ── Single recipe ─────────────────────────────────────────────────────────────

@app.get("/recipe/{recipe_id}")
def get_recipe(recipe_id: int):
    """Ambil detail satu recipe berdasarkan ID."""
    recipe = get_recipe_by_id(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe {recipe_id} not found")
    return recipe


# ── Explain (standalone) ──────────────────────────────────────────────────────

@app.post("/explain")
def explain(body: dict):
    """
    Generate explanation untuk pasangan recipe.
    Body: { "query_id": int, "recommended_id": int, "force_llm": bool (optional) }
    """
    query_id       = body.get("query_id")
    recommended_id = body.get("recommended_id")
    force_llm      = body.get("force_llm", False)

    if not query_id or not recommended_id:
        raise HTTPException(status_code=400, detail="query_id dan recommended_id wajib diisi")

    query_recipe       = get_recipe_by_id(query_id)
    recommended_recipe = get_recipe_by_id(recommended_id)

    if not query_recipe:
        raise HTTPException(status_code=404, detail=f"Recipe {query_id} not found")
    if not recommended_recipe:
        raise HTTPException(status_code=404, detail=f"Recipe {recommended_id} not found")

    # Hitung scores on-the-fly untuk standalone explain
    from recommender import _get_sbert_scores, _get_cbf_scores, cf_matrix, recipe_id_to_cf_idx, recipes
    from collaborative import get_cf_scores

    idx_list = recipes.index[recipes["recipe_id"] == query_id].tolist()
    if not idx_list:
        raise HTTPException(status_code=404, detail=f"Recipe {query_id} not in index")

    idx          = idx_list[0]
    rec_idx_list = recipes.index[recipes["recipe_id"] == recommended_id].tolist()
    if not rec_idx_list:
        raise HTTPException(status_code=404, detail=f"Recipe {recommended_id} not in index")
    rec_idx = rec_idx_list[0]

    sbert_scores             = _get_sbert_scores(idx)
    cbf_scores               = _get_cbf_scores(idx)
    cf_scores, cf_valid      = get_cf_scores(cf_matrix, recipe_id_to_cf_idx.get(query_id, idx))
    w = W_SBERT + W_CBF + (W_CF if cf_valid else 0)

    scores = {
        "sbert":  float(sbert_scores[rec_idx]),
        "cbf":    float(cbf_scores[rec_idx]),
        "cf":     float(cf_scores[rec_idx]) if cf_valid else 0.0,
        "hybrid": float(
            (0.40 * sbert_scores[rec_idx] + 0.35 * cbf_scores[rec_idx]
             + (0.25 * cf_scores[rec_idx] if cf_valid else 0.0))
        ),
    }

    explanation = generate_explanation(
        query_recipe=query_recipe,
        recommended_recipe=recommended_recipe,
        scores=scores,
        force_llm=force_llm,
    )

    return {
        "query_id":       query_id,
        "recommended_id": recommended_id,
        "explanation":    explanation,
        "scores":         scores,
    }


# Konstanta bobot (dipakai endpoint /explain)
W_SBERT = 0.40
W_CBF   = 0.35
W_CF    = 0.25