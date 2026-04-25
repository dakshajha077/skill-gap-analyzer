"""
utils/interview_analyzer.py
============================
Interview answer analyzer using sentence-transformers (all-MiniLM-L6-v2).

Old TF-IDF / joblib classifier pipeline has been removed.
The model is loaded lazily on first use and reused thereafter.
"""

import numpy as np
import os
import re
import sys

# ── Hybrid AI layer (memory + similarity search + feedback loop) ─────────────
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from ml.memory_store import hybrid_predict, add_to_memory
    _HYBRID_ENABLED = True
except ImportError:
    _HYBRID_ENABLED = False
    def hybrid_predict(text, model_label, model_confidence):
        return model_label, model_confidence, "model"
    def add_to_memory(text, label):
        pass
# ─────────────────────────────────────────────────────────────────────────────

_st_model   = None
_session_emb = {}


def _get_bert():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _st_model


DISPLAY = {
    "Technical":   {
        "Good Answer": "Good Answer", "Technical Weakness": "Technical Weakness",
        "Communication Weakness": "Communication Weakness", "Confidence Low": "Confidence Low",
    },
    "HR":          {
        "Good Answer": "Good Answer", "Technical Weakness": "Weak Response",
        "Communication Weakness": "Communication Weakness", "Confidence Low": "Confidence Low",
    },
    "DSA":         {
        "Good Answer": "Good Answer", "Technical Weakness": "Conceptual Weakness",
        "Communication Weakness": "Communication Weakness", "Confidence Low": "Confidence Low",
    },
    "Database":    {
        "Good Answer": "Good Answer", "Technical Weakness": "Technical Weakness",
        "Communication Weakness": "Communication Weakness", "Confidence Low": "Confidence Low",
    },
    "Soft Skills": {
        "Good Answer": "Good Answer", "Technical Weakness": "Weak Response",
        "Communication Weakness": "Communication Weakness", "Confidence Low": "Confidence Low",
    },
}

SCORE_RANGES = {
    "Good Answer":            (65, 93),
    "Technical Weakness":     (15, 48),
    "Weak Response":          (15, 45),
    "Conceptual Weakness":    (15, 48),
    "Communication Weakness": (18, 45),
    "Confidence Low":         (5,  30),
}

FEEDBACK = {
    "Good Answer":            "Well done! Your answer demonstrates clear understanding and addresses the question effectively.",
    "Technical Weakness":     "Your answer lacks technical accuracy. Review the core concepts and practice explaining them step by step.",
    "Weak Response":          "Your response does not adequately address the question. Provide specific examples from your experience.",
    "Conceptual Weakness":    "Key concepts are missing or incorrect. Study the topic and practice with concrete implementations.",
    "Communication Weakness": "Your answer is unclear or poorly structured. Use the STAR method for behavioral questions.",
    "Confidence Low":         "Your response shows hesitation. Regular mock practice will build your confidence and composure.",
}

SUGGESTIONS = {
    "Good Answer":            ["Keep practising to maintain this standard", "Prepare real project examples to support answers", "Try more advanced follow-up questions"],
    "Technical Weakness":     ["Revise core concepts from scratch", "Implement a small project using this concept", "Practice explaining out loud without notes"],
    "Weak Response":          ["Prepare 2-3 specific examples from your experience", "Use STAR: Situation Task Action Result", "Research the role and company beforehand"],
    "Conceptual Weakness":    ["Study through visual diagrams", "Implement the concept from scratch", "Trace through examples by hand"],
    "Communication Weakness": ["Record yourself and review for clarity", "Practice STAR for every behavioral answer", "Focus on one clear point per answer"],
    "Confidence Low":         ["Do 10 mock questions daily for two weeks", "Practice in front of a mirror or with a friend", "Remember: interviewers want you to succeed"],
}

CONF_SIGNALS = [
    "i dont know", "i don't know", "no idea", "not sure", "i cant", "i can't",
    "very nervous", "anxious", "scared", "my mind went blank", "i freeze",
    "i forget", "i forgot", "please give me", "i am sorry i cannot",
    "i am afraid", "i have no idea", "i don't remember", "i dont remember",
]
COMM_SIGNALS = [" um ", " uh ", " er ", "you know", "sort of", "kind of",
                "i guess", "hard to explain", "cannot explain", "struggling to"]
FILLER_RE = re.compile(r'\b(um|uh|er|hmm)\b')


def _hash_answer(text):
    words = set(re.sub(r'[^a-z\s]', '', text.lower()).split())
    return frozenset(words)


def _is_copy_pasted(answer, session_id):
    h = _hash_answer(answer)
    if session_id not in _session_emb:
        return False
    for prev in _session_emb[session_id]:
        if len(h) > 0 and len(h & prev) / max(len(h | prev), 1) > 0.88:
            return True
    return False


def _register(answer, session_id):
    h = _hash_answer(answer)
    _session_emb.setdefault(str(session_id), []).append(h)


def clear_session(session_id):
    _session_emb.pop(str(session_id), None)


def _signals(answer):
    al   = answer.lower()
    conf = sum(1 for s in CONF_SIGNALS if s in al)
    comm = sum(1 for s in COMM_SIGNALS if s in al)
    fill = len(FILLER_RE.findall(al))
    return conf, comm, fill


def analyze_answer(question, answer, interview_category="Technical", session_id=None):
    display_map = DISPLAY.get(interview_category, DISPLAY["Technical"])
    wc          = len(answer.strip().split())

    if session_id and _is_copy_pasted(answer, str(session_id)):
        _register(answer, str(session_id))
        disp = display_map.get("Technical Weakness", "Technical Weakness")
        return {
            "category": disp, "score": 0,
            "feedback": "This answer is identical or very similar to a previous answer. Each question requires a unique, relevant response.",
            "improvement_suggestions": [
                "Read each question carefully",
                "Each answer must address the specific question asked",
                "Do not repeat previous responses",
            ],
            "job_recommendations": [],
            "confidence_scores": {"Copy-paste detected": "Similarity > 88%"},
            "word_count": wc, "evaluated_by": "Originality Checker",
            "confidence_level": "Flagged", "confidence_color": "danger",
            "confidence_note": "Answer too similar to a previous answer. Score set to 0.",
        }

    if session_id:
        _register(answer, str(session_id))

    conf, comm, fill = _signals(answer)

    # ── Rule-based classification using signal detection ──────────────────────
    # (No TF-IDF classifier or joblib — pure semantic + rule-based pipeline)
    if wc < 4:
        base_cat, model_prob = "Technical Weakness", 0.8
    elif conf >= 2 or (conf >= 1 and wc < 15):
        base_cat, model_prob = "Confidence Low", 0.75
    elif comm >= 2 or fill >= 3:
        base_cat, model_prob = "Communication Weakness", 0.65
    else:
        # Use semantic model to score answer quality
        model   = _get_bert()
        q_emb   = model.encode([question], normalize_embeddings=True)
        a_emb   = model.encode([answer],   normalize_embeddings=True)
        sim     = float((q_emb @ a_emb.T)[0][0])

        # Map similarity to category + confidence
        if sim >= 0.45:
            base_cat, model_prob = "Good Answer",        min(0.95, 0.60 + sim * 0.5)
        elif sim >= 0.25:
            base_cat, model_prob = "Technical Weakness", 0.60
        else:
            base_cat, model_prob = "Technical Weakness", 0.75
    # ─────────────────────────────────────────────────────────────────────────

    # ── Hybrid AI layer (memory + self-learned corrections) ──────────────────
    base_cat, model_prob, predict_source = hybrid_predict(answer, base_cat, model_prob)
    # ─────────────────────────────────────────────────────────────────────────

    disp_cat = display_map.get(base_cat, base_cat)
    lo, hi   = SCORE_RANGES.get(disp_cat, (15, 50))
    score    = round(min(93, max(5, lo + (hi - lo) * model_prob)))

    if model_prob >= 0.80:
        conf_level, conf_color = "High Confidence",   "success"
        conf_note = f"Model is {model_prob:.0%} confident in this classification."
    elif model_prob >= 0.60:
        conf_level, conf_color = "Medium Confidence", "primary"
        conf_note = f"Model confidence: {model_prob:.0%}."
    else:
        conf_level, conf_color = "Low Confidence",    "warning"
        conf_note = f"Model confidence: {model_prob:.0%}. Answer may be ambiguous."

    return {
        "category": disp_cat, "score": score,
        "feedback": FEEDBACK.get(disp_cat, ""),
        "improvement_suggestions": SUGGESTIONS.get(disp_cat, []),
        "job_recommendations": [],
        "confidence_scores": {"Model Confidence": f"{model_prob:.0%}"},
        "word_count": wc,
        "evaluated_by": "Memory (Self-learned)" if predict_source == "memory" else "AI Semantic Analysis",
        "confidence_level": conf_level,
        "confidence_color": conf_color,
        "confidence_note": conf_note,
        "predict_source": predict_source,
    }
