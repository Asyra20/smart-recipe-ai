import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ── Path cache ───────────────────────────────────────────────────────────────
CACHE_DIR        = "cache"
EMBEDDINGS_PATH  = os.path.join(CACHE_DIR, "embeddings.npy")
FAISS_INDEX_PATH = os.path.join(CACHE_DIR, "recipes.index")

MODEL_NAME = "all-MiniLM-L6-v2"


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def build_faiss_index(texts: list[str], force_rebuild: bool = False):
    """
    Build atau load FAISS index dari list of texts.

    Flow:
    1. Kalau cache ada dan force_rebuild=False → load langsung (cepat)
    2. Kalau tidak ada atau force_rebuild=True → encode semua teks,
       simpan .npy + .index, lalu return

    Return:
        embeddings  : np.ndarray shape (N, D), float32
        index       : faiss.IndexFlatIP  (inner product = cosine setelah normalize)
        model       : SentenceTransformer (disimpan untuk encode query nanti)
    """
    _ensure_cache_dir()

    model = SentenceTransformer(MODEL_NAME)

    # ── Load dari cache ───────────────────────────────────────────────────────
    if (not force_rebuild
            and os.path.exists(EMBEDDINGS_PATH)
            and os.path.exists(FAISS_INDEX_PATH)):

        print("[FAISS] Loading embeddings from cache...")
        embeddings = np.load(EMBEDDINGS_PATH)
        index = faiss.read_index(FAISS_INDEX_PATH)
        print(f"[FAISS] Loaded {embeddings.shape[0]} embeddings, dim={embeddings.shape[1]}")
        return embeddings, index, model

    # ── Build baru ────────────────────────────────────────────────────────────
    print(f"[FAISS] Encoding {len(texts)} recipes (first time, akan di-cache)...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=64,
        normalize_embeddings=True,   # L2 normalize → inner product = cosine similarity
        convert_to_numpy=True,
    ).astype(np.float32)

    # IndexFlatIP: brute-force inner product, exact, cocok untuk ~8000 item
    # Kalau mau scale ke 100k+, ganti ke IndexIVFFlat
    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Simpan cache
    np.save(EMBEDDINGS_PATH, embeddings)
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"[FAISS] Index built & cached ({embeddings.shape[0]} vectors, dim={dim})")

    return embeddings, index, model


def search_faiss(index, query_embedding: np.ndarray, top_k: int = 50):
    """
    Cari top_k nearest neighbors dari query_embedding.

    Args:
        index           : faiss.Index yang sudah di-build
        query_embedding : np.ndarray shape (D,) atau (1, D), float32, sudah L2-normalized
        top_k           : jumlah hasil

    Return:
        scores  : np.ndarray shape (top_k,)  — cosine similarity [0..1]
        indices : np.ndarray shape (top_k,)  — index di recipes DataFrame
    """
    qvec = np.array(query_embedding, dtype=np.float32).reshape(1, -1)

    # Normalize query juga (jaga-jaga kalau belum)
    faiss.normalize_L2(qvec)

    scores, indices = index.search(qvec, top_k)
    return scores[0], indices[0]