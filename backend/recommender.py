import ast
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from preprocessing import load_recipes
from faiss_index import build_faiss_index, search_faiss
from collaborative import build_cf_model, get_cf_scores
from explainer import generate_explanation

# ── Bobot hybrid ──────────────────────────────────────────────────────────────
W_SBERT = 0.40
W_CBF   = 0.35
W_CF    = 0.25

# ── Load data ─────────────────────────────────────────────────────────────────
print("[Recommender] Loading recipes...")
recipes = load_recipes()
recipe_ids = recipes["recipe_id"].tolist()
texts      = recipes["text"].tolist()

# ── CBF: TF-IDF ───────────────────────────────────────────────────────────────
print("[Recommender] Building TF-IDF matrix...")
vectorizer = TfidfVectorizer(max_features=50000, stop_words="english")
X_tfidf    = normalize(vectorizer.fit_transform(texts))

# ── SBERT + FAISS ─────────────────────────────────────────────────────────────
print("[Recommender] Building FAISS index (or loading from cache)...")
embeddings, faiss_index, sbert_model = build_faiss_index(texts)

# ── Collaborative Filtering ───────────────────────────────────────────────────
print("[Recommender] Building CF model (or loading from cache)...")
cf_matrix, recipe_id_to_cf_idx = build_cf_model(recipe_ids)

print(f"[Recommender] Ready — {len(recipes)} recipes loaded")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_list_field(value) -> list:
    if isinstance(value, list):
        return value
    try:
        result = ast.literal_eval(str(value))
        return result if isinstance(result, list) else [str(result)]
    except:
        return [v.strip() for v in str(value).split(",") if v.strip()]


def _row_to_dict(row) -> dict:
    """Konversi DataFrame row ke dict yang siap di-return ke frontend."""
    return {
        "recipe_id":       int(row["recipe_id"]),
        "name":            str(row["name"]),
        "description":     str(row["description"]) if not isinstance(row["description"], float) else "",
        "tags":            _parse_list_field(row["tags"]),
        "ingredients":     _parse_list_field(row["ingredients"]),
        "steps":           _parse_list_field(row["steps"]) if "steps" in row and not isinstance(row.get("steps"), float) else [],
        # Nutrition
        "calories":        round(float(row.get("calories", 0)), 1),
        "protein":         round(float(row.get("protein", 0)), 1),
        # Flags
        "is_quick":        bool(row.get("is_quick", False)),
        "is_high_protein": bool(row.get("is_high_protein", False)),
        "is_low_calorie":  bool(row.get("is_low_calorie", False)),
        "minutes":         int(row.get("minutes", 0)) if not isinstance(row.get("minutes"), float) else 0,
    }


def _build_result(row, scores: dict, query_row=None, with_explanation: bool = True) -> dict:
    """Gabungkan recipe data + scores + explanation."""
    result = _row_to_dict(row)
    result["scores"] = {
        "sbert":  round(float(scores.get("sbert", 0)), 4),
        "cbf":    round(float(scores.get("cbf", 0)), 4),
        "cf":     round(float(scores.get("cf", 0)), 4),
        "hybrid": round(float(scores.get("hybrid", 0)), 4),
    }
    # Alias untuk backward compat dengan frontend lama
    result["score"] = result["scores"]["hybrid"]

    if with_explanation and query_row is not None:
        result["explanation"] = generate_explanation(
            query_recipe=_row_to_dict(query_row),
            recommended_recipe=_row_to_dict(row),
            scores=scores,
        )
    else:
        result["explanation"] = None

    return result


def _get_cbf_scores(idx: int) -> np.ndarray:
    """TF-IDF cosine similarity dari recipe[idx] ke semua recipe."""
    scores = (X_tfidf @ X_tfidf[idx].T).toarray().ravel()
    return scores.astype(np.float32)


def _get_sbert_scores(idx: int) -> np.ndarray:
    """Cosine similarity dari recipe[idx] embedding ke semua recipe (via dot product)."""
    query_vec = embeddings[idx].reshape(1, -1)
    scores    = (embeddings @ query_vec.T).ravel()
    return scores.astype(np.float32)


def _fuse_scores(sbert: np.ndarray, cbf: np.ndarray, cf: np.ndarray,
                 cf_valid: bool) -> np.ndarray:
    """
    Gabungkan 3 skor jadi 1 hybrid score.
    Kalau CF tidak valid (zero vector), redistribusikan bobotnya ke SBERT dan CBF.
    """
    if cf_valid:
        hybrid = W_SBERT * sbert + W_CBF * cbf + W_CF * cf
    else:
        # Redistribusi bobot CF
        w_s = W_SBERT / (W_SBERT + W_CBF)
        w_c = W_CBF   / (W_SBERT + W_CBF)
        hybrid = w_s * sbert + w_c * cbf
    return hybrid


# ── Public API ────────────────────────────────────────────────────────────────

def recommend_by_recipe(recipe_id: int, top_k: int = 10, with_explanation: bool = True):
    """
    Hybrid recommendation berdasarkan recipe_id.
    Dipakai di endpoint GET /recommend/{recipe_id}
    """
    idx_list = recipes.index[recipes["recipe_id"] == recipe_id].tolist()
    if not idx_list:
        return []

    idx       = idx_list[0]
    query_row = recipes.iloc[idx]

    # Ambil skor dari ketiga engine
    sbert_scores = _get_sbert_scores(idx)
    cbf_scores   = _get_cbf_scores(idx)
    cf_idx       = recipe_id_to_cf_idx.get(recipe_id, idx)
    cf_scores, cf_valid = get_cf_scores(cf_matrix, cf_idx)

    hybrid_scores = _fuse_scores(sbert_scores, cbf_scores, cf_scores, cf_valid)
    hybrid_scores[idx] = -1  # exclude self

    # Ambil top_k
    top_idx = np.argpartition(hybrid_scores, -top_k)[-top_k:]
    top_idx = top_idx[np.argsort(hybrid_scores[top_idx])[::-1]]

    results = []
    for i in top_idx:
        scores = {
            "sbert":  float(sbert_scores[i]),
            "cbf":    float(cbf_scores[i]),
            "cf":     float(cf_scores[i]) if cf_valid else 0.0,
            "hybrid": float(hybrid_scores[i]),
        }
        results.append(_build_result(
            recipes.iloc[i], scores, query_row, with_explanation
        ))

    return results


def semantic_search(query: str, top_k: int = 10, with_explanation: bool = False):
    """
    Semantic search via SBERT + FAISS.
    Dipakai di endpoint GET /search?q=...

    Explanation di-skip by default untuk search (lebih cepat),
    bisa di-enable kalau dibutuhkan.
    """
    query_embedding = sbert_model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # FAISS search ambil candidate lebih banyak (50), lalu re-rank dengan hybrid
    faiss_scores, faiss_indices = search_faiss(faiss_index, query_embedding, top_k=min(50, len(recipes)))

    # Untuk search, tidak ada query recipe jadi CF tidak dipakai
    # Hybrid = SBERT score saja (sudah paling relevan untuk free-text search)
    results = []
    for rank, (score, idx) in enumerate(zip(faiss_scores, faiss_indices)):
        if idx < 0:  # FAISS bisa return -1 kalau kurang hasil
            continue
        row = recipes.iloc[idx]
        scores = {
            "sbert":  float(score),
            "cbf":    0.0,
            "cf":     0.0,
            "hybrid": float(score),
        }
        result = _build_result(row, scores, query_row=None, with_explanation=False)
        results.append(result)

        if len(results) >= top_k:
            break

    return results


def get_recipe_by_id(recipe_id: int) -> dict | None:
    """Ambil satu recipe lengkap berdasarkan ID."""
    idx_list = recipes.index[recipes["recipe_id"] == recipe_id].tolist()
    if not idx_list:
        return None
    row = recipes.iloc[idx_list[0]]
    return _row_to_dict(row)