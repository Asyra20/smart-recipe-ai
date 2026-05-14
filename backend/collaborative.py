import os
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from sklearn.preprocessing import normalize

INTERACTIONS_PATH = "data/RAW_interactions.csv"
CACHE_DIR         = "cache"
CF_VECTORS_PATH   = os.path.join(CACHE_DIR, "cf_vectors.npy")
CF_IDS_PATH       = os.path.join(CACHE_DIR, "cf_recipe_ids.npy")

# Jumlah latent factors SVD
N_FACTORS = 50


def build_cf_model(recipe_ids_in_dataset: list[int], force_rebuild: bool = False):
    """
    Build Collaborative Filtering model dari RAW_interactions.csv.

    Hasilnya adalah recipe latent vectors (dari SVD) yang bisa dipakai
    untuk menghitung similarity antar resep berdasarkan pola user rating.

    Return:
        cf_matrix : np.ndarray shape (N_recipes_in_dataset, N_FACTORS)
                    Row i → latent vector untuk recipe_ids_in_dataset[i]
                    Recipe yang tidak ada di interactions → zero vector
        recipe_id_to_cf_idx : dict {recipe_id: row_index di cf_matrix}
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # ── Load cache ────────────────────────────────────────────────────────────
    if (not force_rebuild
            and os.path.exists(CF_VECTORS_PATH)
            and os.path.exists(CF_IDS_PATH)):

        print("[CF] Loading CF vectors from cache...")
        cf_vectors      = np.load(CF_VECTORS_PATH)
        cached_ids      = np.load(CF_IDS_PATH).tolist()
        id_to_idx       = {rid: i for i, rid in enumerate(cached_ids)}

        # Align ke dataset saat ini
        cf_matrix, recipe_id_to_cf_idx = _align_to_dataset(
            cf_vectors, cached_ids, id_to_idx, recipe_ids_in_dataset
        )
        print(f"[CF] Loaded {len(cached_ids)} CF vectors from cache")
        return cf_matrix, recipe_id_to_cf_idx

    # ── Build dari scratch ────────────────────────────────────────────────────
    print("[CF] Building CF model from interactions...")

    interactions = pd.read_csv(
        INTERACTIONS_PATH,
        usecols=["user_id", "recipe_id", "rating"]
    )

    # Hanya pakai recipe yang ada di dataset kita (8000 baris)
    recipe_id_set = set(recipe_ids_in_dataset)
    interactions  = interactions[interactions["recipe_id"].isin(recipe_id_set)]

    print(f"[CF] {len(interactions)} interactions untuk {interactions['recipe_id'].nunique()} recipes")

    if len(interactions) == 0:
        print("[CF] Warning: tidak ada interactions, CF akan skip")
        n = len(recipe_ids_in_dataset)
        cf_matrix = np.zeros((n, N_FACTORS), dtype=np.float32)
        recipe_id_to_cf_idx = {rid: i for i, rid in enumerate(recipe_ids_in_dataset)}
        return cf_matrix, recipe_id_to_cf_idx

    # Encode user_id dan recipe_id jadi integer index
    user_enc   = {u: i for i, u in enumerate(interactions["user_id"].unique())}
    recipe_enc = {r: i for i, r in enumerate(interactions["recipe_id"].unique())}

    rows   = interactions["user_id"].map(user_enc).values
    cols   = interactions["recipe_id"].map(recipe_enc).values
    data   = interactions["rating"].astype(float).values

    n_users   = len(user_enc)
    n_recipes = len(recipe_enc)

    # User-item matrix (sparse)
    ui_matrix = csr_matrix((data, (rows, cols)), shape=(n_users, n_recipes))

    # SVD — k=N_FACTORS latent dimensions
    # svds return U (n_users × k), S (k,), Vt (k × n_recipes)
    k = min(N_FACTORS, min(n_users, n_recipes) - 1)
    _, S, Vt = svds(ui_matrix.astype(np.float32), k=k)

    # Recipe latent vectors = Vt.T @ diag(S) → shape (n_recipes, k)
    recipe_latent = (Vt.T * S).astype(np.float32)      # (n_recipes, k)
    recipe_latent = normalize(recipe_latent, norm="l2") # normalize untuk cosine sim

    # Mapping recipe_id → latent vector
    recipe_id_list = list(recipe_enc.keys())            # recipe_id aktual

    # Simpan cache
    np.save(CF_VECTORS_PATH, recipe_latent)
    np.save(CF_IDS_PATH, np.array(recipe_id_list))
    print(f"[CF] SVD selesai: {n_recipes} recipe vectors, {k} latent factors")

    id_to_idx = {rid: i for i, rid in enumerate(recipe_id_list)}

    cf_matrix, recipe_id_to_cf_idx = _align_to_dataset(
        recipe_latent, recipe_id_list, id_to_idx, recipe_ids_in_dataset
    )
    return cf_matrix, recipe_id_to_cf_idx


def _align_to_dataset(cf_vectors, cf_ids, id_to_idx, recipe_ids_in_dataset):
    """
    Align CF vectors ke urutan recipe_ids_in_dataset.
    Recipe yang tidak ada di CF (belum pernah di-rate) → zero vector.
    """
    n       = len(recipe_ids_in_dataset)
    k       = cf_vectors.shape[1]
    aligned = np.zeros((n, k), dtype=np.float32)

    for i, rid in enumerate(recipe_ids_in_dataset):
        if rid in id_to_idx:
            aligned[i] = cf_vectors[id_to_idx[rid]]

    recipe_id_to_cf_idx = {rid: i for i, rid in enumerate(recipe_ids_in_dataset)}
    return aligned, recipe_id_to_cf_idx


def get_cf_scores(cf_matrix: np.ndarray, query_idx: int, top_k: int = 50):
    """
    Hitung cosine similarity dari recipe[query_idx] ke semua recipe lain.

    Return:
        scores  : np.ndarray shape (N,) — similarity scores
        valid   : bool — False kalau recipe tidak punya CF vector (all zeros)
    """
    query_vec = cf_matrix[query_idx]

    # Kalau zero vector (tidak ada di interactions), CF tidak reliable
    if np.linalg.norm(query_vec) < 1e-6:
        return np.zeros(len(cf_matrix), dtype=np.float32), False

    # Dot product dengan semua vectors (sudah L2-normalized → = cosine sim)
    scores          = cf_matrix @ query_vec
    scores[query_idx] = -1  # exclude self
    return scores.astype(np.float32), True