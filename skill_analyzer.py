"""
skill_analyzer.py
================

Production-oriented, TF-IDF + cosine similarity based skill gap analysis.

Given:
  - resume text
  - job description text

Returns:
  {
    "matched_skills": [...],
    "missing_skills": [...],
    "similarity_score": float
  }

Design goals:
  - Clear separation of concerns (preprocess, vectorize, similarity, skill extraction, evaluation)
  - Robust handling of empty/noisy inputs
  - Debug-friendly structure and upgrade path for future embedding-based backends
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple, TypedDict

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer

logger = logging.getLogger(__name__)

class SkillGapResult(TypedDict):
    """Return type for `analyze_skill_gap`."""

    matched_skills: List[str]
    missing_skills: List[str]
    similarity_score: float


def _safe_str(value: object) -> str:
    """Coerce unknown input into a safe string; returns empty string on invalid values."""
    return value if isinstance(value, str) else ""


def preprocess_text(text: str | None) -> str:
    """
    Normalize free-form text for vectorization and keyword extraction.

    Rules:
      - lowercase
      - remove punctuation and numbers
      - normalize whitespace
      - safe on empty/invalid input

    Notes:
      - Stopword removal is handled by the TF-IDF vectorizer (`stop_words="english"`).
      - This keeps Unicode letters (e.g., accented characters) and removes non-letters.
    """
    raw = _safe_str(text)
    if not raw or not raw.strip():
        return ""

    lowered = raw.lower()
    # Keep letters and whitespace; convert everything else (digits/punct/symbols) to spaces.
    cleaned_chars = [(ch if (ch.isalpha() or ch.isspace()) else " ") for ch in lowered]
    cleaned = "".join(cleaned_chars)
    normalized = re.sub(r"\s+", " ", cleaned).strip()
    return normalized


@dataclass(frozen=True)
class TfidfConfig:
    """
    Configuration for the TF-IDF vectorizer.

    Defaults are chosen to be:
      - accurate enough for short documents
      - efficient (bounded vocabulary)
      - easy to tune later
    """

    ngram_range: Tuple[int, int] = (1, 2)  # unigrams + bigrams
    max_features: int = 8000
    stop_words: str | Sequence[str] = "english"
    max_df: float = 0.85
    min_df: int = 2
    sublinear_tf: bool = True

    def build(self, *, corpus_size: int) -> TfidfVectorizer:
        """
        Build a vectorizer instance adjusted for small corpora.

        For very small corpora (e.g., resume + job description), `min_df=2` can
        prune nearly everything; we automatically relax it to 1 in that case.
        Likewise, `max_df<1.0` can remove the *shared* terms in tiny corpora
        (df=1.0 for overlapping terms when corpus_size=2), so we disable it.
        """
        effective_min_df: int = 1 if corpus_size < 3 else self.min_df
        effective_max_df: float = 1.0 if corpus_size < 5 else self.max_df
        return TfidfVectorizer(
            ngram_range=self.ngram_range,
            stop_words=self.stop_words,
            max_features=self.max_features,
            min_df=effective_min_df,
            max_df=effective_max_df,
            sublinear_tf=self.sublinear_tf,
        )


def train_vectorizer(corpus: Sequence[str], *, config: TfidfConfig | None = None) -> TfidfVectorizer:
    """
    Fit and return a TF-IDF vectorizer over the provided (preprocessed) corpus.

    Args:
        corpus: Preprocessed documents (strings).
        config: Optional vectorizer configuration.

    Raises:
        ValueError: If the corpus has no usable tokens after preprocessing / filtering.
    """
    resolved_config = config or TfidfConfig()
    usable = [t for t in corpus if isinstance(t, str) and t.strip()]
    if not usable:
        raise ValueError("Empty corpus after preprocessing.")

    vectorizer = resolved_config.build(corpus_size=len(usable))
    vectorizer.fit(usable)
    return vectorizer


def compute_similarity(vectorizer: TfidfVectorizer, resume: str, job_desc: str) -> float:
    """
    Compute cosine similarity between two preprocessed texts using a fitted TF-IDF vectorizer.

    Returns:
        Similarity score in [0, 1] (TF-IDF is non-negative).
    """
    if not resume.strip() or not job_desc.strip():
        return 0.0

    vectors = vectorizer.transform([resume, job_desc])
    score = float(cosine_similarity(vectors[0], vectors[1])[0][0])
    # Numerical safety: keep score bounded.
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


@dataclass(frozen=True)
class SkillExtractionConfig:
    """
    Configuration for TF-IDF based keyword/skill extraction.

    Filtering behavior:
      - Terms are ranked by TF-IDF score for the given document.
      - A term is kept only if it passes both:
          (a) score threshold (`min_score`)
          (b) percentile threshold (`min_percentile`) relative to this document's term scores
      - Noisy terms are removed (short tokens, generic boilerplate).

    Threshold guidance:
      - `min_percentile=0.8` keeps roughly the top 20% highest-scoring terms for that document.
      - Increasing `min_percentile` makes the output shorter and more selective.
    """

    top_n: int = 20
    min_score: float = 0.0
    min_percentile: float = 0.80
    min_token_length: int = 3
    generic_terms: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                # Generic / non-skill boilerplate commonly found in resumes and job descriptions.
                "looking",
                "seek",
                "seeking",
                "candidate",
                "candidates",
                "position",
                "role",
                "developer",
                "developers",
                "engineer",
                "engineers",
                "experience",
                "knowledge",
                "working",
                "work",
                "ability",
                "skills",
                "skill",
                "required",
                "requirements",
                "responsibilities",
                "preferred",
                "strong",
                "plus",
                "including",
                "must",
                "team",
                "using",
                "used",
                "use",
                "good",
                "excellent",
                "develop",
                "developing",
                "development",
                "manage",
                "management",
                "project",
                "projects",
                "design",
                "implement",
                "implementation",
                "years",
                "year",
            }
        )
    )
    phrase_headwords: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                # Common "skill phrase" heads that tend to form meaningful bigrams.
                "learning",
                "analysis",
                "analytics",
                "engineering",
                "science",
                "development",
                "testing",
                "security",
                "visualization",
                "management",
                "deployment",
                "cloud",
                "database",
                "networking",
                "administration",
                "scripting",
                "automation",
                "architecture",
            }
        )
    )
    phrase_allowlist: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                # Common technical phrases that don't end with a headword.
                "rest api",
                "ci cd",
                "power bi",
                "data structures",
                "object oriented programming",
                "node js",
                "react native",
                "scikit learn",
                "machine learning",
                "deep learning",
                "natural language processing",
            }
        )
    )
    drop_unigrams_covered_by_phrases: bool = True


def _percentile_threshold(values: Sequence[float], *, percentile: float) -> float:
    """Compute a percentile threshold without requiring extra dependencies."""
    if not values:
        return 0.0
    if percentile <= 0.0:
        return min(values)
    if percentile >= 1.0:
        return max(values)

    ordered = sorted(values)
    # Linear index (no interpolation): good enough for keyword filtering.
    idx = int(round((len(ordered) - 1) * percentile))
    return float(ordered[idx])


def extract_top_keywords(
    vectorizer: TfidfVectorizer,
    text: str,
    *,
    config: SkillExtractionConfig | None = None,
) -> List[str]:
    """
    Extract high-quality keywords/phrases (treated as "skills") using TF-IDF importance.

    Args:
        vectorizer: Fitted TF-IDF vectorizer.
        text: Preprocessed text.
        config: Extraction configuration (thresholding and noise filtering).

    Returns:
        List of unique terms sorted by decreasing TF-IDF importance.
    """
    resolved = config or SkillExtractionConfig()
    if not text or not text.strip() or resolved.top_n <= 0:
        return []

    vector = vectorizer.transform([text])
    if getattr(vector, "nnz", 0) == 0:
        return []

    feature_names = vectorizer.get_feature_names_out()
    coo = vector.tocoo()
    scored_terms: List[Tuple[str, float]] = [(str(feature_names[i]), float(s)) for i, s in zip(coo.col, coo.data)]
    if not scored_terms:
        return []

    scores = [s for _, s in scored_terms]
    # For short texts, percentile thresholds become overly aggressive and can hide
    # obvious skills (e.g., shared terms). In that case, rely on `top_n` + noise filtering.
    if len(scores) <= (resolved.top_n * 2):
        percentile_floor = 0.0
    else:
        percentile_floor = _percentile_threshold(scores, percentile=resolved.min_percentile)
    score_floor = max(float(resolved.min_score), float(percentile_floor))

    stop_words: frozenset[str]
    resolved_stop_words = getattr(vectorizer, "stop_words_", None)
    if resolved_stop_words is not None:
        stop_words = frozenset(str(w) for w in resolved_stop_words)
    else:
        raw_stop_words = getattr(vectorizer, "stop_words", None)
        if raw_stop_words is None:
            stop_words = frozenset()
        elif raw_stop_words == "english":
            stop_words = frozenset(str(w) for w in ENGLISH_STOP_WORDS)
        else:
            stop_words = frozenset(str(w) for w in raw_stop_words)

    def is_noisy_token(token: str) -> bool:
        return (
            len(token) < resolved.min_token_length
            or token in resolved.generic_terms
            or token in stop_words
        )

    # Prefer evaluating phrases before unigrams so that component unigrams can be dropped
    # when `drop_unigrams_covered_by_phrases=True`.
    phrases: List[Tuple[str, float]] = []
    unigrams: List[Tuple[str, float]] = []
    for term, score in scored_terms:
        (phrases if len(term.split()) > 1 else unigrams).append((term, score))
    phrases.sort(key=lambda x: x[1], reverse=True)
    unigrams.sort(key=lambda x: x[1], reverse=True)

    selected_with_scores: List[Tuple[str, float]] = []
    seen: set[str] = set()
    covered_unigrams: set[str] = set()

    for term, score in (phrases + unigrams):
        if len(selected_with_scores) >= resolved.top_n:
            break
        if score < score_floor:
            # Since terms are sorted by score descending, we can stop early.
            # (applies independently to phrases and unigrams due to concatenation order)
            continue

        normalized = term.strip()
        if not normalized or normalized in seen:
            continue

        parts = normalized.split()
        if any(is_noisy_token(p) for p in parts):
            continue
        if len(parts) > 1 and (parts[-1] not in resolved.phrase_headwords) and (normalized not in resolved.phrase_allowlist):
            continue

        if resolved.drop_unigrams_covered_by_phrases and len(parts) == 1 and parts[0] in covered_unigrams:
            continue

        selected_with_scores.append((normalized, score))
        seen.add(normalized)
        if len(parts) > 1:
            covered_unigrams.update(parts)

    # Return terms sorted by importance (highest TF-IDF first), with phrases as a tie-breaker.
    selected_with_scores.sort(key=lambda x: (x[1], len(x[0].split())), reverse=True)
    return [t for t, _ in selected_with_scores]


def extract_skills(vectorizer: TfidfVectorizer, text: str, top_n: int = 10) -> List[str]:
    """
    Backwards-compatible alias for keyword extraction.

    Prefer `extract_top_keywords(..., config=SkillExtractionConfig(...))` for more control.
    """
    return extract_top_keywords(vectorizer, text, config=SkillExtractionConfig(top_n=top_n))


class SkillGapAnalyzer:
    """
    End-to-end analyzer that orchestrates preprocessing, vectorization, similarity, and skill extraction.

    This is intentionally modular so the feature extractor can be replaced later
    (e.g., embeddings) without changing the public API.
    """

    def __init__(
        self,
        *,
        tfidf_config: TfidfConfig | None = None,
        skill_config: SkillExtractionConfig | None = None,
    ) -> None:
        self._tfidf_config = tfidf_config or TfidfConfig()
        self._skill_config = skill_config or SkillExtractionConfig()

    def analyze(self, resume_text: str | None, job_description: str | None) -> SkillGapResult:
        """
        Analyze resume vs job description and return matched/missing skills and similarity.
        """
        resume_clean = preprocess_text(resume_text)
        job_clean = preprocess_text(job_description)

        if not resume_clean and not job_clean:
            return {"matched_skills": [], "missing_skills": [], "similarity_score": 0.0}

        corpus = [t for t in (resume_clean, job_clean) if t.strip()]
        if not corpus:
            return {"matched_skills": [], "missing_skills": [], "similarity_score": 0.0}

        try:
            vectorizer = train_vectorizer(corpus, config=self._tfidf_config)
        except ValueError:
            logger.debug("TF-IDF training failed (empty vocabulary).")
            return {"matched_skills": [], "missing_skills": [], "similarity_score": 0.0}

        similarity = compute_similarity(vectorizer, resume_clean, job_clean)

        resume_skills = extract_top_keywords(vectorizer, resume_clean, config=self._skill_config)
        job_skills = extract_top_keywords(vectorizer, job_clean, config=self._skill_config)

        resume_set = set(resume_skills)
        matched = [s for s in job_skills if s in resume_set]
        missing = [s for s in job_skills if s not in resume_set]

        logger.debug(
            "Skill gap analysis: similarity=%.4f resume_skills=%d job_skills=%d matched=%d missing=%d",
            similarity,
            len(resume_skills),
            len(job_skills),
            len(matched),
            len(missing),
        )

        return {
            "matched_skills": matched,
            "missing_skills": missing,
            "similarity_score": float(similarity),
        }


def analyze_skill_gap(
    resume: str | None,
    job_desc: str | None,
    *,
    top_n: int = 20,
    tfidf_config: TfidfConfig | None = None,
    min_score: float = 0.0,
    min_percentile: float = 0.80,
) -> SkillGapResult:
    """
    Convenience wrapper for one-off analyses.

    Args:
        resume: Raw resume text.
        job_desc: Raw job description.
        top_n: Maximum number of extracted skills to consider per document.
        tfidf_config: Optional TF-IDF configuration (vectorizer parameters).
        min_score: Absolute TF-IDF floor for skill extraction.
        min_percentile: Relative floor (e.g., 0.8 keeps top 20% scores).
    """
    analyzer = SkillGapAnalyzer(
        tfidf_config=tfidf_config,
        skill_config=SkillExtractionConfig(
            top_n=top_n,
            min_score=min_score,
            min_percentile=min_percentile,
        ),
    )
    return analyzer.analyze(resume, job_desc)


def evaluate(
    true_labels: Sequence[Sequence[str]],
    predicted: Sequence[Sequence[str]],
    *,
    average: str = "micro",
) -> Dict[str, float]:
    """
    Evaluate multilabel skill predictions with precision/recall/F1.

    Args:
        true_labels: list of true skill sets, e.g. [["python","sql"], ["ml"]]
        predicted: list of predicted skill sets (same shape)
        average: sklearn averaging strategy ("micro", "macro", "weighted", etc.)
    """
    if len(true_labels) != len(predicted):
        raise ValueError("true_labels and predicted must have the same number of samples.")

    mlb = MultiLabelBinarizer()
    # Fit on the union of labels so evaluation is stable even if predictions contain
    # labels absent from the ground truth (common during iteration).
    mlb.fit(list(true_labels) + list(predicted))
    y_true = mlb.transform(true_labels)
    y_pred = mlb.transform(predicted)

    if y_true.size == 0:
        return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}

    return {
        "precision": float(precision_score(y_true, y_pred, average=average, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average=average, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, average=average, zero_division=0)),
    }


def multilabel_precision(
    true_labels: Sequence[Sequence[str]],
    predicted: Sequence[Sequence[str]],
    *,
    average: str = "micro",
) -> float:
    """Multilabel precision for skill extraction/prediction."""
    return float(evaluate(true_labels, predicted, average=average)["precision"])


def multilabel_recall(
    true_labels: Sequence[Sequence[str]],
    predicted: Sequence[Sequence[str]],
    *,
    average: str = "micro",
) -> float:
    """Multilabel recall for skill extraction/prediction."""
    return float(evaluate(true_labels, predicted, average=average)["recall"])


def multilabel_f1(
    true_labels: Sequence[Sequence[str]],
    predicted: Sequence[Sequence[str]],
    *,
    average: str = "micro",
) -> float:
    """Multilabel F1 score for skill extraction/prediction."""
    return float(evaluate(true_labels, predicted, average=average)["f1_score"])
