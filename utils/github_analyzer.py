"""
Feature 2: GitHub Project Analyzer (REAL)

Replaces all previous mock/random logic with real GitHub REST API calls.
Uses repo metadata, languages, commit history (best-effort), README content,
and lightweight structure checks to compute a score and suggestions.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import requests

from config import Config

_GITHUB_API_BASE = "https://api.github.com"
_DEFAULT_TIMEOUT_S = 12


class GitHubAnalyzerError(RuntimeError):
    """User-facing analyzer error."""


@dataclass(frozen=True)
class ParsedRepo:
    owner: str
    repo: str


def _parse_repo_url(repo_url: str) -> ParsedRepo:
    """
    Extract owner/repo from GitHub URL.
    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/tree/branch
    """
    if not repo_url:
        raise GitHubAnalyzerError("Please provide a GitHub repository URL.")

    if not re.match(r"^https?://", repo_url, flags=re.IGNORECASE):
        raise GitHubAnalyzerError("Invalid GitHub URL. Use format: https://github.com/user/repo")

    parsed = urlparse(repo_url)
    host = (parsed.netloc or "").lower()
    if host not in {"github.com", "www.github.com"}:
        raise GitHubAnalyzerError("Invalid GitHub URL. Use format: https://github.com/user/repo")

    parts = [p for p in (parsed.path or "").strip("/").split("/") if p]
    if len(parts) < 2:
        raise GitHubAnalyzerError("Invalid GitHub URL. Use format: https://github.com/user/repo")

    owner, repo = parts[0], parts[1]
    repo = repo[:-4] if repo.endswith(".git") else repo

    if not owner or not repo:
        raise GitHubAnalyzerError("Invalid GitHub URL. Use format: https://github.com/user/repo")

    return ParsedRepo(owner=owner, repo=repo)


def _auth_headers() -> dict[str, str]:
    token = (getattr(Config, "GITHUB_TOKEN", None) or "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "skill-gap-analyzer/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_get(path: str, *, params: Optional[dict[str, Any]] = None) -> tuple[int, Any, dict[str, str]]:
    url = f"{_GITHUB_API_BASE}{path}"
    resp = requests.get(url, headers=_auth_headers(), params=params or {}, timeout=_DEFAULT_TIMEOUT_S)

    # Best-effort JSON decode
    payload: Any
    try:
        payload = resp.json() if resp.text else {}
    except ValueError:
        payload = {"message": resp.text[:200] if resp.text else "Non-JSON response from GitHub API"}

    headers = {k: v for k, v in resp.headers.items()}
    return resp.status_code, payload, headers


def _handle_api_error(status: int, payload: Any, headers: dict[str, str]) -> None:
    if 200 <= status < 300:
        return

    message = ""
    if isinstance(payload, dict):
        message = str(payload.get("message") or "")

    if status == 404:
        raise GitHubAnalyzerError("Repository not found (404). Check the URL or permissions.")

    if status in (401, 403):
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")
        if remaining == "0":
            extra = "GitHub rate limit exceeded."
            if reset and reset.isdigit():
                extra += f" Try again after the rate limit resets (unix: {reset})."
            raise GitHubAnalyzerError(extra)
        raise GitHubAnalyzerError(f"GitHub API access denied ({status}). {message or 'Forbidden.'}")

    if status == 409:
        # Often "Git Repository is empty."
        raise GitHubAnalyzerError(message or "Repository is empty.")

    raise GitHubAnalyzerError(f"GitHub API error ({status}). {message or 'Request failed.'}")


def _commit_count_from_link_header(link: str) -> int:
    """
    GitHub paginates results with Link headers.
    With `per_page=1`, the last page number ~= total commits for the branch.
    """
    m = re.search(r'<([^>]+)>;\s*rel=\"last\"', link or "")
    if not m:
        return 1
    last_url = m.group(1)
    parsed = urlparse(last_url)
    qs = parse_qs(parsed.query or "")
    page = (qs.get("page") or ["1"])[0]
    return int(page) if str(page).isdigit() else 1


# --- STEP 1: Replace mock data with real GitHub API calls --------------------
def fetch_github_data(repo_url: str) -> dict[str, Any]:
    parsed = _parse_repo_url(repo_url)

    status, repo_payload, headers = _github_get(f"/repos/{parsed.owner}/{parsed.repo}")
    _handle_api_error(status, repo_payload, headers)

    status, langs_payload, headers = _github_get(f"/repos/{parsed.owner}/{parsed.repo}/languages")
    _handle_api_error(status, langs_payload, headers)

    languages_sorted = []
    if isinstance(langs_payload, dict):
        languages_sorted = sorted(langs_payload.items(), key=lambda kv: kv[1], reverse=True)
    language_list = [name for name, _ in languages_sorted]

    default_branch = str((repo_payload or {}).get("default_branch") or "main")

    commits = 0
    commits_status, commits_payload, commits_headers = _github_get(
        f"/repos/{parsed.owner}/{parsed.repo}/commits",
        params={"per_page": 1, "sha": default_branch},
    )
    if commits_status == 409:
        commits = 0
    else:
        _handle_api_error(commits_status, commits_payload, commits_headers)
        link = commits_headers.get("Link", "")
        if link:
            commits = _commit_count_from_link_header(link)
        else:
            commits = len(commits_payload) if isinstance(commits_payload, list) else 0

    return {
        "stars": int((repo_payload or {}).get("stargazers_count") or 0),
        "forks": int((repo_payload or {}).get("forks_count") or 0),
        "open_issues": int((repo_payload or {}).get("open_issues_count") or 0),
        "languages": language_list,
        "commits": int(commits),
        "default_branch": default_branch,
        "repo_name": str((repo_payload or {}).get("name") or parsed.repo),
    }


# --- STEP 2: Fetch README content -------------------------------------------
def fetch_readme(repo_url: str) -> str:
    parsed = _parse_repo_url(repo_url)

    status, payload, headers = _github_get(f"/repos/{parsed.owner}/{parsed.repo}/readme")
    if status == 404:
        return ""
    _handle_api_error(status, payload, headers)

    if not isinstance(payload, dict):
        return ""

    content_b64 = payload.get("content") or ""
    if not content_b64:
        return ""

    try:
        decoded = base64.b64decode(content_b64, validate=False)
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return ""


# --- STEP 3: Repo structure analysis (lightweight) --------------------------
def analyze_repo_structure(repo_url: str) -> dict[str, bool]:
    parsed = _parse_repo_url(repo_url)

    status, repo_payload, headers = _github_get(f"/repos/{parsed.owner}/{parsed.repo}")
    _handle_api_error(status, repo_payload, headers)
    default_branch = str((repo_payload or {}).get("default_branch") or "main")

    def exists(path: str) -> bool:
        st, payload, hdrs = _github_get(
            f"/repos/{parsed.owner}/{parsed.repo}/contents/{path}",
            params={"ref": default_branch},
        )
        if st == 404:
            return False
        _handle_api_error(st, payload, hdrs)
        return True

    return {
        "has_tests": exists("tests"),
        "has_ci": exists(".github/workflows"),
        "has_dependencies": exists("requirements.txt") or exists("package.json"),
    }


# --- STEP 4: Replace scoring logic ------------------------------------------
def score_repository(data: dict[str, Any], structure: dict[str, bool], readme: str) -> float:
    stars = int(data.get("stars") or 0)
    commits = int(data.get("commits") or 0)
    languages = data.get("languages") or []
    readme_len = len(readme or "")

    # stars -> up to +2
    if stars >= 1000:
        stars_score = 2.0
    elif stars >= 200:
        stars_score = 1.5
    elif stars >= 50:
        stars_score = 1.0
    elif stars >= 10:
        stars_score = 0.5
    else:
        stars_score = 0.0

    # commits -> up to +2
    if commits >= 500:
        commits_score = 2.0
    elif commits >= 200:
        commits_score = 1.5
    elif commits >= 50:
        commits_score = 1.0
    elif commits >= 10:
        commits_score = 0.5
    else:
        commits_score = 0.0

    # README length -> +1
    if readme_len >= 1500:
        readme_score = 1.0
    elif readme_len >= 400:
        readme_score = 0.6
    elif readme_len >= 120:
        readme_score = 0.3
    else:
        readme_score = 0.0

    tests_score = 1.0 if structure.get("has_tests") else 0.0
    ci_score = 1.0 if structure.get("has_ci") else 0.0
    lang_score = 1.0 if isinstance(languages, list) and len(languages) >= 2 else 0.0

    return round(stars_score + commits_score + readme_score + tests_score + ci_score + lang_score, 2)  # max 8.0


def _readme_quality_10(readme: str) -> float:
    readme_len = len(readme or "")
    if readme_len >= 2500:
        return 10.0
    if readme_len >= 1200:
        return 8.0
    if readme_len >= 600:
        return 6.0
    if readme_len >= 200:
        return 4.0
    if readme_len >= 80:
        return 2.0
    return 0.0


# --- STEP 5: Skill extraction ------------------------------------------------
def extract_skills(data: dict[str, Any], readme: str) -> list[str]:
    skills: list[str] = []

    for lang in (data.get("languages") or []):
        if isinstance(lang, str) and lang not in skills:
            skills.append(lang)

    text = (readme or "").lower()
    keyword_map = {
        "react": "React",
        "next.js": "Next.js",
        "node": "Node.js",
        "express": "Express",
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "terraform": "Terraform",
        "github actions": "GitHub Actions",
        "aws": "AWS",
        "gcp": "GCP",
        "azure": "Azure",
        "graphql": "GraphQL",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "mongodb": "MongoDB",
        "redis": "Redis",
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow",
        "scikit-learn": "scikit-learn",
        "machine learning": "Machine Learning",
        "nlp": "NLP",
        "computer vision": "Computer Vision",
    }

    for key, label in keyword_map.items():
        if key in text and label not in skills:
            skills.append(label)

    return skills[:20]


# --- STEP 6: (Optional) NLP using sentence-transformers ----------------------
def _infer_domain(readme: str) -> Optional[str]:
    if not readme or len(readme) < 80:
        return None

    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except Exception:
        return _infer_domain_keywords(readme)

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        emb = model.encode([readme[:6000]], normalize_embeddings=True, show_progress_bar=False)[0]

        labels = {
            "Web Development": "This repository is about web development and building websites.",
            "Machine Learning": "This repository is about machine learning, models, and data science.",
            "DevOps": "This repository is about DevOps, CI/CD, infrastructure, and automation.",
            "Mobile Development": "This repository is about mobile app development.",
        }

        label_texts = list(labels.values())
        label_embs = model.encode(label_texts, normalize_embeddings=True, show_progress_bar=False)
        sims = (label_embs @ emb).tolist()
        best_idx = int(np.argmax(sims))
        best_label = list(labels.keys())[best_idx]
        best_sim = float(sims[best_idx])
        return best_label if best_sim >= 0.35 else _infer_domain_keywords(readme)
    except Exception:
        return _infer_domain_keywords(readme)


def _infer_domain_keywords(readme: str) -> Optional[str]:
    text = (readme or "").lower()
    if any(k in text for k in ("pytorch", "tensorflow", "scikit-learn", "machine learning", "dataset", "model")):
        return "Machine Learning"
    if any(k in text for k in ("docker", "kubernetes", "terraform", "github actions", "ci/cd")):
        return "DevOps"
    if any(k in text for k in ("react", "next.js", "express", "django", "flask", "frontend", "backend")):
        return "Web Development"
    return None


# --- STEP 7: Final analyzer function ----------------------------------------
def analyze_github_repo(repo_url: str) -> dict[str, Any]:
    try:
        parsed = _parse_repo_url(repo_url)
    except GitHubAnalyzerError as e:
        return {"error": str(e)}

    try:
        data = fetch_github_data(repo_url)
        readme = fetch_readme(repo_url)
        structure = analyze_repo_structure(repo_url)
        raw_score = score_repository(data, structure, readme)
        readme_score_10 = _readme_quality_10(readme)
        skills = extract_skills(data, readme)
        domain = _infer_domain(readme)
    except GitHubAnalyzerError as e:
        return {"error": str(e)}
    except requests.RequestException:
        return {"error": "Network error while contacting GitHub. Please try again."}
    except Exception:
        return {"error": "Unexpected error while analyzing the repository. Please try again."}

    # Map raw (0..8) to project_score (0..10) for existing UI expectations
    project_score = round(min(10.0, (raw_score / 8.0) * 10.0), 2) if raw_score >= 0 else 0.0

    strengths: list[str] = []
    improvements: list[str] = []

    if data["stars"] >= 50:
        strengths.append(f"Strong community interest ({data['stars']} stars).")
    elif data["stars"] >= 10:
        strengths.append(f"Growing community interest ({data['stars']} stars).")
    else:
        improvements.append("Increase visibility: add badges, screenshots, and share in dev communities.")

    if data["commits"] >= 50:
        strengths.append(f"Active development history ({data['commits']} commits).")
    else:
        improvements.append("Make more frequent, smaller commits with clear messages.")

    if structure.get("has_tests"):
        strengths.append("Includes tests — good engineering practice.")
    else:
        improvements.append("Add tests (unit/integration) to improve reliability.")

    if structure.get("has_ci"):
        strengths.append("CI/CD present — automated checks improve quality.")
    else:
        improvements.append("Add CI/CD with GitHub Actions for automated testing/linting.")

    if len(data.get("languages") or []) >= 2:
        strengths.append(f"Uses multiple technologies: {', '.join(data['languages'][:3])}.")

    if readme_score_10 >= 6:
        strengths.append("README is detailed and helpful for contributors.")
    else:
        improvements.append("Improve README (setup, usage, screenshots, contribution guidelines).")

    if structure.get("has_dependencies"):
        strengths.append("Dependency manifest detected (easier to set up).")
    else:
        improvements.append("Add a dependency manifest (e.g., requirements.txt or package.json).")

    if domain:
        strengths.append(f"Detected domain: {domain}.")

    strengths = strengths[:5] if strengths else ["Repository is accessible and analyzable."]
    improvements = improvements[:5] if improvements else ["Keep maintaining and iterating on this project."]

    summary = (
        f"{data['repo_name']} has {data['stars']} stars, {data['forks']} forks, "
        f"{data['open_issues']} open issues, and ~{data['commits']} commits."
    )
    if domain:
        summary += f" Likely domain: {domain}."

    return {
        # Spec-required (new)
        "score": raw_score,
        "skills": skills,
        "strengths": strengths,
        "improvements": improvements,
        "summary": summary,

        # Backwards-compatible fields used by existing UI/DB
        "repo_name": data["repo_name"],
        "repo_url": repo_url,
        "stars": data["stars"],
        "commits": data["commits"],
        "languages": data["languages"],
        "readme_score": round(readme_score_10, 1),
        "project_score": project_score,

        # Extra details
        "forks": data["forks"],
        "open_issues": data["open_issues"],
        "default_branch": data["default_branch"],
        "owner": parsed.owner,
    }
