"""
utils/skill_analyzer.py
=======================

TF-IDF + cosine-similarity based skill gap analysis.

This module keeps the Flask app's public API stable:
  - `get_job_roles()`
  - `analyze_skills(user_skills_text, job_role, job_description="")`

For resume-vs-job-description comparisons, use:
  - `analyze_skill_gap(resume_text, job_text)`
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from skill_analyzer import analyze_skill_gap, preprocess_text


JOB_SKILLS = {
    "Software Developer": [
        "Python",
        "Java",
        "Data Structures",
        "Algorithms",
        "Object Oriented Programming",
        "Git",
        "REST API",
        "SQL",
        "Unit Testing",
        "Problem Solving",
        "Linux",
        "Agile",
        "Design Patterns",
        "Debugging",
        "Code Review",
    ],
    "Web Developer": [
        "HTML",
        "CSS",
        "JavaScript",
        "React",
        "Node.js",
        "REST API",
        "Git",
        "SQL",
        "Responsive Design",
        "TypeScript",
        "Bootstrap",
        "JSON",
        "Webpack",
        "Testing",
        "Version Control",
    ],
    "Data Analyst": [
        "Python",
        "SQL",
        "Excel",
        "Data Visualization",
        "Statistics",
        "Pandas",
        "NumPy",
        "Tableau",
        "Power BI",
        "Machine Learning",
        "Data Cleaning",
        "Report Writing",
        "Problem Solving",
        "Critical Thinking",
        "Communication",
    ],
    "Machine Learning Engineer": [
        "Python",
        "Machine Learning",
        "Deep Learning",
        "TensorFlow",
        "PyTorch",
        "Scikit-learn",
        "Natural Language Processing",
        "Data Structures",
        "Statistics",
        "SQL",
        "Git",
        "Docker",
        "Mathematics",
        "Research Skills",
        "Model Deployment",
    ],
    "Backend Developer": [
        "Python",
        "Node.js",
        "REST API",
        "SQL",
        "NoSQL",
        "Docker",
        "Git",
        "Linux",
        "Microservices",
        "Authentication",
        "Caching",
        "Message Queues",
        "Testing",
        "Security",
        "System Design",
    ],
    "Full Stack Developer": [
        "HTML",
        "CSS",
        "JavaScript",
        "React",
        "Node.js",
        "Python",
        "SQL",
        "Git",
        "REST API",
        "Docker",
        "TypeScript",
        "MongoDB",
        "Testing",
        "Agile",
        "System Design",
    ],
    "DevOps Engineer": [
        "Linux",
        "Docker",
        "Kubernetes",
        "CI/CD",
        "Git",
        "Python",
        "Bash Scripting",
        "AWS",
        "Monitoring",
        "Networking",
        "Terraform",
        "Ansible",
        "Security",
        "Problem Solving",
        "System Administration",
    ],
    "Database Administrator": [
        "SQL",
        "MySQL",
        "PostgreSQL",
        "Database Design",
        "Normalization",
        "Performance Tuning",
        "Backup and Recovery",
        "Indexing",
        "Stored Procedures",
        "NoSQL",
        "Data Security",
        "Linux",
        "Monitoring",
        "Replication",
        "Troubleshooting",
    ],
    "HR Executive": [
        "Communication",
        "Recruitment",
        "Employee Relations",
        "HR Policies",
        "Interviewing",
        "Conflict Resolution",
        "Microsoft Office",
        "People Management",
        "Training and Development",
        "Performance Management",
        "Payroll",
        "Labor Laws",
        "Onboarding",
        "Leadership",
        "Problem Solving",
    ],
    "Business Analyst": [
        "Business Analysis",
        "SQL",
        "Excel",
        "Requirements Gathering",
        "Stakeholder Management",
        "Process Modeling",
        "Communication",
        "Problem Solving",
        "Data Analysis",
        "Documentation",
        "Agile",
        "JIRA",
        "Presentation Skills",
        "Critical Thinking",
        "Wireframing",
    ],
    "Project Manager": [
        "Project Planning",
        "Risk Management",
        "Agile",
        "Scrum",
        "Leadership",
        "Communication",
        "Budgeting",
        "Stakeholder Management",
        "MS Project",
        "Problem Solving",
        "Team Management",
        "Reporting",
        "JIRA",
        "Critical Thinking",
        "Negotiation",
    ],
    "Cybersecurity Analyst": [
        "Network Security",
        "Penetration Testing",
        "Linux",
        "Firewalls",
        "SIEM",
        "Python",
        "Vulnerability Assessment",
        "Incident Response",
        "Cryptography",
        "Ethical Hacking",
        "Risk Assessment",
        "Compliance",
        "Cloud Security",
        "IDS/IPS",
        "Log Analysis",
    ],
    "Cloud Engineer": [
        "AWS",
        "Azure",
        "Google Cloud",
        "Docker",
        "Kubernetes",
        "Terraform",
        "CI/CD",
        "Linux",
        "Python",
        "Networking",
        "Security",
        "Monitoring",
        "Serverless",
        "Storage",
        "System Design",
    ],
    "Mobile Developer": [
        "Android",
        "iOS",
        "React Native",
        "Flutter",
        "Java",
        "Swift",
        "Kotlin",
        "REST API",
        "Git",
        "UI/UX Design",
        "SQLite",
        "Firebase",
        "Testing",
        "App Store Publishing",
        "Problem Solving",
    ],
    "UI/UX Designer": [
        "Figma",
        "Adobe XD",
        "User Research",
        "Wireframing",
        "Prototyping",
        "UI Design",
        "UX Design",
        "CSS",
        "HTML",
        "Interaction Design",
        "Typography",
        "Color Theory",
        "Usability Testing",
        "Communication",
        "Adobe Photoshop",
    ],
}

MATCH_THRESHOLD = 0.30
MODERATE_THR = 0.50
STRONG_THR = 0.75


def get_job_roles() -> List[str]:
    return sorted(JOB_SKILLS.keys())


def _dedupe_preserve_order(items: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _parse_skills_text(text: str) -> List[str]:
    if not text:
        return []
    # Common separators: commas, newlines, pipes, bullets, semicolons.
    parts = re.split(r"[,\n;|]+", text)
    return _dedupe_preserve_order([p.strip() for p in parts if p and p.strip()])


def _fit_phrase_vectorizer(texts: Sequence[str]) -> TfidfVectorizer:
    extra_stopwords = {
        "looking",
        "seeking",
        "required",
        "requirements",
        "responsibilities",
        "role",
        "candidate",
        "skills",
        "skill",
        "experience",
        "preferred",
        "plus",
        "including",
        "must",
    }
    stopwords = sorted(set(ENGLISH_STOP_WORDS).union(extra_stopwords))
    vectorizer = TfidfVectorizer(stop_words=stopwords, ngram_range=(1, 2))
    vectorizer.fit(texts)
    return vectorizer


def _strength(sim: float) -> str:
    if sim >= STRONG_THR:
        return "strong"
    if sim >= MODERATE_THR:
        return "moderate"
    return "weak"


def analyze_skills(user_skills_text: str, job_role: str, job_description: str = "") -> Dict:
    """
    Skill-gap analysis for a given job role (used by the Flask UI).

    This compares user-provided skill phrases against the role's required skills using:
      - TF-IDF vectors over skill phrases
      - cosine similarity

    Returns a dict containing:
      - overall_score (0..100)
      - matched_skills / missing_skills / extra_skills
      - counts + recommendations
    """
    user_skills = _parse_skills_text(user_skills_text)
    if not user_skills:
        return {"error": "No skills provided. Please enter your skills."}

    required_skills = JOB_SKILLS.get(job_role)
    if not required_skills:
        return {"error": "Could not determine required skills for this role."}

    # Use the optional JD to slightly expand vocabulary, without changing the required set.
    extra_vocab_text = preprocess_text(job_description) if job_description else ""

    user_clean = [preprocess_text(s) for s in user_skills]
    req_clean = [preprocess_text(s) for s in required_skills]
    corpus = [t for t in (user_clean + req_clean + ([extra_vocab_text] if extra_vocab_text else [])) if t.strip()]
    if not corpus:
        return {"error": "Insufficient text after preprocessing."}

    try:
        vectorizer = _fit_phrase_vectorizer(corpus)
    except ValueError:
        return {"error": "Could not build TF-IDF vocabulary from provided skills."}

    user_vecs = vectorizer.transform(user_clean)
    req_vecs = vectorizer.transform(req_clean)
    sim_matrix = cosine_similarity(user_vecs, req_vecs)  # (n_user, n_required)

    matched_skills: List[Dict] = []
    missing_skills: List[Dict] = []
    extra_skills: List[Dict] = []
    user_details: List[Dict] = []

    # For each required skill, pick the best matching user skill.
    best_req_sim: List[float] = []
    req_matched: List[bool] = []
    for j in range(len(required_skills)):
        col = sim_matrix[:, j]
        best_idx = int(col.argmax()) if col.size else 0
        best_sim = float(col[best_idx]) if col.size else 0.0
        best_req_sim.append(best_sim)
        req_matched.append(best_sim >= MATCH_THRESHOLD)

        if best_sim >= MATCH_THRESHOLD:
            user_skill = user_skills[best_idx]
            matched_skills.append(
                {
                    "user_skill": user_skill,
                    "matched_to": required_skills[j],
                    "similarity": round(best_sim * 100, 1),
                    "strength": _strength(best_sim),
                }
            )
        else:
            missing_skills.append(
                {
                    "skill": required_skills[j],
                    "gap": round((1 - best_sim) * 100, 1),
                    "closest": round(best_sim * 100, 1),
                }
            )

    # For each user skill, record its best required match to identify extras.
    user_matched: List[bool] = []
    for i in range(len(user_skills)):
        row = sim_matrix[i]
        best_idx = int(row.argmax()) if row.size else 0
        best_sim = float(row[best_idx]) if row.size else 0.0
        best_req = required_skills[best_idx] if required_skills else ""
        is_match = best_sim >= MATCH_THRESHOLD
        user_matched.append(is_match)
        strength = _strength(best_sim) if is_match else "weak"
        user_details.append(
            {
                "skill": user_skills[i],
                "best_match": best_req,
                "similarity": round(best_sim * 100, 1),
                "strength": strength,
            }
        )
        if best_sim < MATCH_THRESHOLD:
            extra_skills.append(
                {
                    "user_skill": user_skills[i],
                    "similarity": round(best_sim * 100, 1),
                    "strength": "weak",
                }
            )

    # Overall score: F1-like balance of coverage (recall) and relevance (precision).
    precision = (sum(user_matched) / len(user_matched)) if user_matched else 0.0
    recall = (sum(req_matched) / len(req_matched)) if req_matched else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    overall_score = round(f1 * 100.0, 1)

    if overall_score >= 80:
        profile_label, profile_color = "Excellent Match", "success"
    elif overall_score >= 60:
        profile_label, profile_color = "Good Match", "primary"
    elif overall_score >= 40:
        profile_label, profile_color = "Partial Match", "warning"
    else:
        profile_label, profile_color = "Skill Gap Detected", "danger"

    strong_count = sum(1 for m in matched_skills if m["strength"] == "strong")
    moderate_count = sum(1 for m in matched_skills if m["strength"] == "moderate")

    top_missing = sorted(missing_skills, key=lambda x: x["gap"], reverse=True)[:5]
    recommendations = [f"Learn {m['skill']} — it is a core requirement for {job_role} roles." for m in top_missing]

    return {
        "job_role": job_role,
        "overall_score": overall_score,
        "profile_label": profile_label,
        "profile_color": profile_color,
        "user_skills": user_skills,
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "extra_skills": extra_skills,
        "strong_skills": [d for d in user_details if d["strength"] == "strong"],
        "moderate_skills": [d for d in user_details if d["strength"] == "moderate"],
        "weak_skills": [d for d in user_details if d["strength"] == "weak"],
        "skill_details": user_details,
        "strong_count": strong_count,
        "moderate_count": moderate_count,
        "missing_count": len(missing_skills),
        "total_required": len(required_skills),
        "recommendations": recommendations,
        "skills_source": "static",
        "extracted_from_jd": [],
    }
