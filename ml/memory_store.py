"""
ml/memory_store.py
==================
HYBRID AI LAYER — Memory Database + Embedding Similarity Search + Feedback Loop

HOW IT WORKS:
  1. Stores (text, label, embedding) triples in a JSON file (memory.json).
  2. Before every model prediction:
       - Embed the input text
       - Cosine-search stored embeddings
       - If best similarity > SIMILARITY_THRESHOLD → return stored label directly
       - Else → hand off to the original model (fallback)
  3. After a prediction, the caller may submit a correction:
       - Stores (text, corrected_label) in memory → used from the next call onward
  4. Embeddings are computed incrementally (no full retraining).

INTEGRATION:
  Import and use `hybrid_predict()` from interview_analyzer.py.
  Call `add_to_memory(text, label)` to store user corrections.

THREAD SAFETY:
  A simple file lock (via a module-level Lock) prevents race conditions
  under Flask's development server. For production use, swap the JSON
  store for SQLite or Redis.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Optional

import numpy as np

# ── Config ─────────────────────────────────────────────────────────────────
MEMORY_FILE        = os.path.join(os.path.dirname(__file__), "memory.json")
SIMILARITY_THRESHOLD = 0.82   # cosine ≥ 0.82 → trust memory over model
LOW_CONF_THRESHOLD   = 0.60   # model confidence below this → prefer memory if any hit ≥ 0.70

_lock = threading.Lock()

# ── Lazy ST model (shared with interview_analyzer to avoid double-loading) ──
_st_model = None

def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _st_model


def _embed(text: str) -> np.ndarray:
    """Return a unit-norm 1-D embedding for a single text string."""
    model = _get_st_model()
    emb = model.encode([text], normalize_embeddings=True, show_progress_bar=False)
    return emb[0]  # shape (dim,)


# ── Memory I/O ──────────────────────────────────────────────────────────────

def _load_memory() -> list[dict]:
    """Load memory records from JSON. Each record: {text, label, embedding}."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
        return records
    except (json.JSONDecodeError, OSError):
        return []


def _save_memory(records: list[dict]) -> None:
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)


# ── Public API ───────────────────────────────────────────────────────────────

def add_to_memory(text: str, label: str) -> None:
    """
    Store a (text, label) pair with its embedding.
    Called after user feedback: 'the correct label was X'.

    Deduplicates: if an identical text already exists, updates its label
    instead of appending a duplicate.
    """
    with _lock:
        records = _load_memory()
        emb = _embed(text).tolist()  # JSON-serialisable

        # Check for near-duplicate (cosine ≥ 0.98 = almost identical text)
        for rec in records:
            stored_emb = np.array(rec["embedding"])
            sim = float(np.dot(np.array(emb), stored_emb))
            if sim >= 0.98:
                rec["label"] = label      # update label in-place
                rec["embedding"] = emb    # refresh embedding
                _save_memory(records)
                return

        # New entry
        records.append({"text": text, "label": label, "embedding": emb})
        _save_memory(records)


def similarity_search(
    text: str,
    top_k: int = 1
) -> list[tuple[str, float]]:
    """
    Return the top_k (label, cosine_similarity) pairs from memory
    for the given input text.  Returns [] if memory is empty.
    """
    with _lock:
        records = _load_memory()

    if not records:
        return []

    query_emb = _embed(text)
    stored_embs = np.array([r["embedding"] for r in records])  # (N, dim)
    labels      = [r["label"] for r in records]

    sims = stored_embs @ query_emb  # cosine since all are unit-norm

    # Get top_k
    top_indices = np.argsort(sims)[::-1][:top_k]
    return [(labels[i], float(sims[i])) for i in top_indices]


def hybrid_predict(
    text: str,
    model_label: str,
    model_confidence: float,
) -> tuple[str, float, str]:
    """
    Core hybrid decision function.

    Parameters
    ----------
    text             : The raw answer / input text.
    model_label      : Label predicted by the underlying classifier.
    model_confidence : Probability the classifier assigned to model_label.

    Returns
    -------
    (final_label, final_confidence, source)
    source is one of: "memory" | "model"

    Decision logic
    ──────────────
    1. Search memory for the nearest neighbour.
    2a. If best_sim ≥ SIMILARITY_THRESHOLD → trust memory (high-confidence recall).
    2b. If best_sim ≥ 0.70 AND model_confidence < LOW_CONF_THRESHOLD
         → prefer memory (model is uncertain, memory has a decent match).
    2c. Otherwise → use the model prediction as-is.
    """
    hits = similarity_search(text, top_k=1)

    if hits:
        mem_label, mem_sim = hits[0]

        # Case 2a: strong memory match
        if mem_sim >= SIMILARITY_THRESHOLD:
            return mem_label, mem_sim, "memory"

        # Case 2b: model is shaky, memory has a reasonable match
        if mem_sim >= 0.70 and model_confidence < LOW_CONF_THRESHOLD:
            return mem_label, mem_sim, "memory"

    # Case 2c: fall back to the model
    return model_label, model_confidence, "model"


def memory_stats() -> dict:
    """Return basic statistics about the memory store (for diagnostics)."""
    with _lock:
        records = _load_memory()
    label_counts: dict[str, int] = {}
    for r in records:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
    return {"total_records": len(records), "label_distribution": label_counts}
