"""
Feature 3: 30-Day Learning Planner
Generates a day-by-day structured learning plan for a given skill.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, DefaultDict, Iterable

# Skill-specific topic progressions with domain categories
SKILL_PLANS = {
    "python": [
        ("Variables & Data Types", "Write a simple calculator", "Fundamentals"),
        ("Control Flow", "Build a number guessing game", "Fundamentals"),
        ("Functions", "Create utility functions library", "Fundamentals"),
        ("Lists & Tuples", "Implement a to-do list app", "Data Structures"),
        ("Dictionaries & Sets", "Build a word frequency counter", "Data Structures"),
        ("File I/O", "CSV reader/writer script", "Core Libraries"),
        ("Error Handling", "Add try/except to existing projects", "Core Libraries"),
        ("OOP Basics", "Create a Bank Account class", "Object-Oriented"),
        ("OOP Inheritance", "Build a shape hierarchy", "Object-Oriented"),
        ("Modules & Packages", "Organize code into modules", "Organization"),
        ("List Comprehensions", "Refactor loops to comprehensions", "Advanced Syntax"),
        ("Lambda & Map/Filter", "Functional data transformation", "Advanced Syntax"),
        ("Decorators", "Build a timing decorator", "Advanced Syntax"),
        ("Generators", "Memory-efficient data pipelines", "Advanced Syntax"),
        ("Context Managers", "File handling best practices", "Advanced Features"),
        ("Regular Expressions", "Build a form validator", "Utilities"),
        ("datetime Module", "Build a countdown timer", "Utilities"),
        ("JSON Handling", "Parse an API response", "Data Handling"),
        ("requests Library", "Fetch and display weather data", "Web Integration"),
        ("Unit Testing", "Write tests for your calculator", "Testing"),
        ("Virtual Environments", "Set up a project environment", "Tools & Setup"),
        ("pip & Dependencies", "Build a requirements.txt workflow", "Tools & Setup"),
        ("SQLite with Python", "Build a contact database", "Databases"),
        ("Flask Basics", "Hello World web app", "Web Framework"),
        ("Flask Routes & Templates", "Multi-page personal website", "Web Framework"),
        ("Data Structures Review", "Implement stack, queue, linked list", "DSA Fundamentals"),
        ("Algorithms Practice", "Sorting algorithms from scratch", "Algorithms"),
        ("API Building", "Build a REST API with Flask", "Web Framework"),
        ("Async Programming", "asyncio and concurrent tasks", "Advanced Features"),
        ("Advanced Project", "Build & deploy a full Python app", "Projects"),
    ],
    "javascript": [
        ("Variables & Types", "Console.log experiments", "Fundamentals"),
        ("Functions", "Build a tip calculator", "Fundamentals"),
        ("Arrays", "Implement array manipulation helpers", "Data Structures"),
        ("Objects", "Create a user profile object", "Data Structures"),
        ("DOM Basics", "Change page content dynamically", "DOM & Browser"),
        ("Events", "Build an interactive button game", "DOM & Browser"),
        ("Conditionals & Loops", "FizzBuzz & number pyramid", "Control Flow"),
        ("Strings", "Build a string utilities library", "String Manipulation"),
        ("Array Methods", "filter/map/reduce exercises", "Functional Programming"),
        ("Spread & Destructuring", "Refactor code with ES6+", "ES6+ Features"),
        ("Template Literals", "Dynamic HTML generation", "ES6+ Features"),
        ("Arrow Functions", "Convert functions to arrow style", "ES6+ Features"),
        ("Promises", "Simulate async data fetch", "Asynchronous"),
        ("Async/Await", "Fetch real API data", "Asynchronous"),
        ("Fetch API", "Build a joke generator app", "APIs"),
        ("Local Storage", "Persist a to-do list", "Browser Storage"),
        ("ES6 Classes", "Build an OOP bank account", "Object-Oriented"),
        ("Modules", "Split code into ES modules", "Organization"),
        ("Error Handling", "Add try/catch to fetch calls", "Error Handling"),
        ("Regular Expressions", "Form validation with regex", "Validation"),
        ("JSON", "Parse and display JSON data", "Data Formats"),
        ("Map & Set", "Deduplicate data with Set", "Advanced Collections"),
        ("Closures", "Build a counter with closure", "Advanced Concepts"),
        ("Hoisting", "Understand hoisting behavior", "Advanced Concepts"),
        ("Node.js Basics", "Build a CLI tool", "Backend Fundamentals"),
        ("npm & Packages", "Use a third-party library", "Ecosystems"),
        ("Express Basics", "Simple REST API", "Backend Framework"),
        ("React Introduction", "Hello World in React", "Frontend Framework"),
        ("React Components", "Build a card component", "Frontend Framework"),
        ("Advanced Project", "Full-stack JS mini app", "Projects"),
    ],
    "dsa": [
        ("Big O Notation", "Analyze 5 code snippets", "Foundations"),
        ("Arrays", "Two Sum, Max Subarray", "Fundamentals"),
        ("Strings", "Reverse, Palindrome check", "Fundamentals"),
        ("Linked Lists", "Implement singly linked list", "Data Structures"),
        ("Stacks", "Valid parentheses problem", "Data Structures"),
        ("Queues", "BFS level order traversal", "Data Structures"),
        ("Hash Maps", "Two Sum with HashMap", "Data Structures"),
        ("Sets", "Find duplicates in array", "Data Structures"),
        ("Binary Search", "Search in rotated array", "Searching"),
        ("Two Pointers", "Container with most water", "Techniques"),
        ("Sliding Window", "Longest substring problems", "Techniques"),
        ("Recursion Basics", "Fibonacci, factorial", "Core Algorithms"),
        ("Merge Sort", "Implement from scratch", "Sorting"),
        ("Quick Sort", "Implement and analyze", "Sorting"),
        ("Trees Intro", "Implement binary tree", "Trees"),
        ("Tree Traversal", "Inorder, Preorder, Postorder", "Trees"),
        ("BST Operations", "Insert, Delete, Search", "Trees"),
        ("Graphs Intro", "Build adjacency list", "Graphs"),
        ("BFS", "Shortest path in grid", "Graph Traversal"),
        ("DFS", "Number of islands", "Graph Traversal"),
        ("Dynamic Programming Intro", "Climbing stairs", "Dynamic Programming"),
        ("DP Memoization", "House Robber problem", "Dynamic Programming"),
        ("DP Tabulation", "Coin change problem", "Dynamic Programming"),
        ("Heaps/Priority Queue", "Kth largest element", "Advanced Structures"),
        ("Tries", "Implement autocomplete", "Advanced Structures"),
        ("Backtracking", "N-Queens, Subsets", "Advanced Techniques"),
        ("Greedy Algorithms", "Activity selection problem", "Strategies"),
        ("Union Find", "Connected components", "Advanced Techniques"),
        ("Bit Manipulation", "Solve 5 bit manipulation problems", "Bit Operations"),
        ("Mock Interview", "Timed problem solving session", "Practice & Review"),
    ],
    "sql": [
        ("What is SQL?", "Install MySQL/PostgreSQL", "Fundamentals"),
        ("SELECT Basics", "Query a sample database", "Fundamentals"),
        ("WHERE Clause", "Filter records by conditions", "Querying"),
        ("ORDER BY & LIMIT", "Top N queries", "Querying"),
        ("INSERT & UPDATE", "Manage student records", "Data Manipulation"),
        ("DELETE & Transactions", "Safe data deletion", "Data Manipulation"),
        ("INNER JOIN", "Combine two related tables", "Joins"),
        ("LEFT & RIGHT JOIN", "Find unmatched records", "Joins"),
        ("GROUP BY", "Sales by category", "Aggregation"),
        ("HAVING Clause", "Filter aggregated results", "Aggregation"),
        ("Aggregate Functions", "COUNT, SUM, AVG, MAX, MIN", "Aggregation"),
        ("Subqueries", "Nested SELECT statements", "Advanced Querying"),
        ("CREATE TABLE", "Design an e-commerce schema", "Schema Design"),
        ("Normalization", "Convert 1NF → 3NF", "Database Design"),
        ("Primary & Foreign Keys", "Enforce referential integrity", "Constraints"),
        ("Indexes", "Add index and compare query speed", "Performance"),
        ("Views", "Create reusable query view", "Objects"),
        ("Stored Procedures", "Automate bulk operations", "Objects"),
        ("Triggers", "Auto-update timestamp on edit", "Objects"),
        ("Window Functions", "RANK, ROW_NUMBER", "Advanced Functions"),
        ("CTEs", "WITH clause for readability", "Advanced Functions"),
        ("CASE WHEN", "Conditional column output", "Functions"),
        ("String Functions", "Name formatting queries", "Functions"),
        ("Date Functions", "Reports by month/year", "Functions"),
        ("UNION & INTERSECT", "Combine result sets", "Set Operations"),
        ("Performance Tuning", "EXPLAIN query analysis", "Optimization"),
        ("Transactions & ACID", "ACID properties understanding", "Advanced Topics"),
        ("NoSQL Basics", "MongoDB intro and comparison", "NoSQL"),
        ("SQL in Python", "sqlite3 / psycopg2 project", "Integration"),
        ("Capstone Project", "Build a full relational database", "Projects"),
    ],
}

# Generic plan for unrecognized skills
def _generic_plan(skill: str) -> list:
    phases = [
        "Introduction & Overview", "Core Concepts Part 1", "Core Concepts Part 2",
        "Fundamentals Practice", "Intermediate Concepts", "Hands-on Exercise",
        "Advanced Concepts Part 1", "Advanced Concepts Part 2", "Project Planning",
        "Mini Project Build", "Review & Refactor", "Testing & Debugging",
        "Best Practices", "Real-world Applications", "Community & Resources",
    ]
    tasks = [
        "Watch GeeksforGeeks tutorials", "Read official documentation",
        "Follow guided examples", "Complete coding exercises",
        "Build a small demo", "Refactor previous code",
        "Solve practice problems", "Read case studies",
        "Plan a personal project", "Start building the project",
        "Write unit tests", "Peer code review",
        "Optimize performance", "Deploy/publish project",
        "Contribute to open source",
    ]
    plan = []
    for i in range(30):
        phase_idx = i % len(phases)
        task_idx = i % len(tasks)
        domain = phases[phase_idx]
        plan.append((
            f"{domain} — Day {i+1}",
            tasks[task_idx],
            domain
        ))
    return plan

def generate_30_day_plan(skill: str) -> list:
    """
    Returns a list of 30 dicts: {day, topic, task, domain, phase}
    Removed: resource URLs
    Added: domain (focus area/category for each day)
    """
    key = skill.lower().replace(" ", "")
    # Match known skills
    plan_data = None
    for k, v in SKILL_PLANS.items():
        if k in key or key in k:
            plan_data = v
            break

    if not plan_data:
        plan_data = _generic_plan(skill)

    result = []
    for i, (topic, task, domain) in enumerate(plan_data[:30], 1):
        result.append({
            "day":      i,
            "topic":    topic,
            "task":     task,
            "domain":   domain,
            "phase":    "Foundation" if i <= 10 else ("Core Skills" if i <= 20 else "Advanced & Project"),
        })
    return result


# ---------------------------------------------------------------------------
# Interview-category plans (Technical / HR / DSA / Database / Soft Skills)
# These are used when the "skill" dropdown selects an interview category.
# ---------------------------------------------------------------------------

INTERVIEW_CATEGORIES = {"Technical", "HR", "DSA", "Database", "Soft Skills"}


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


_CATEGORY_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "Technical": [
        ("object-oriented programming", "OOP Principles (4 pillars)"),
        ("linked list", "Linked Lists (ops & complexity)"),
        ("recursion", "Recursion (base case & stack)"),
        ("stack and a queue", "Stacks vs Queues"),
        ("time complexity", "Time Complexity & Big-O"),
        ("big o", "Time Complexity & Big-O"),
        ("sql and nosql", "SQL vs NoSQL (use cases)"),
        ("rest api", "REST APIs (verbs, statelessness)"),
        ("binary search tree", "Binary Search Trees (searching)"),
        ("http and https", "HTTP vs HTTPS (TLS basics)"),
        ("version control", "Version Control with Git"),
        ("git", "Version Control with Git"),
        ("api is", "APIs (basics & design)"),
    ],
    "HR": [
        ("tell me about yourself", "Self-Introduction (structured pitch)"),
        ("greatest strength", "Strengths (evidence & impact)"),
        ("greatest weakness", "Weakness (honest + improvement plan)"),
        ("five years", "Career Goals (5-year plan)"),
        ("interested in this role", "Motivation (why role/company)"),
        ("worked under pressure", "Handling Pressure (calm + prioritization)"),
        ("worked in a team", "Teamwork Example (collaboration)"),
        ("handle criticism", "Receiving Feedback (growth mindset)"),
        ("showed leadership", "Leadership/Initiative (ownership)"),
        ("why should we hire you", "Value Proposition (why hire me)"),
    ],
    "DSA": [
        ("linear and non-linear", "Linear vs Non-Linear DS"),
        ("bubble sort", "Bubble Sort + Complexity"),
        ("hash table", "Hash Tables + Collisions"),
        ("bfs and dfs", "Graph Traversal: BFS vs DFS"),
        ("dynamic programming", "Dynamic Programming (when/how)"),
        ("heap data structure", "Heaps & Priority Queues"),
        ("merge sort", "Merge Sort + Complexity"),
        ("what is a graph", "Graphs (types & representations)"),
        ("memoization", "Memoization (optimize recursion)"),
        ("two-pointer", "Two Pointers Technique"),
    ],
    "Database": [
        ("normalization", "Normalization (1NF→3NF)"),
        ("sql join", "SQL JOINs (types + use cases)"),
        ("index in a database", "Indexes (why & tradeoffs)"),
        ("primary key", "Primary vs Foreign Keys"),
        ("acid", "ACID Transactions"),
        ("stored procedure", "Stored Procedures (when/why)"),
        ("delete, truncate and drop", "DELETE vs TRUNCATE vs DROP"),
        ("what a view is", "Views (virtual tables)"),
        ("sharding", "Sharding (scaling data)"),
        ("clustered and non-clustered", "Clustered vs Non-Clustered Indexes"),
    ],
    "Soft Skills": [
        ("manage your time", "Time Management (prioritization)"),
        ("conflict with a teammate", "Conflict Resolution (calm + clarity)"),
        ("learning a new technology", "Learning Approach (plan + consistency)"),
        ("time you failed", "Handling Failure (learning & resilience)"),
        ("communicate technical concepts", "Explain Clearly to Non-Technical Audience"),
        ("problem-solving process", "Problem Solving (structured thinking)"),
        ("stay motivated", "Motivation & Discipline"),
        ("adapt to a significant change", "Adaptability (change management)"),
        ("constructive feedback", "Giving/Receiving Feedback (respectful)"),
        ("project you are most proud", "Project Storytelling (impact + ownership)"),
    ],
}


_CATEGORY_DEFAULT_TOPICS: dict[str, list[str]] = {
    k: [topic for _, topic in patterns] for k, patterns in _CATEGORY_PATTERNS.items()
}


def _infer_interview_topic(category: str, question: str) -> str:
    q = _norm(question)
    for needle, topic in _CATEGORY_PATTERNS.get(category, []):
        if needle in q:
            return topic
    # Fallback: try other patterns in the same category (best-effort)
    for needle, topic in _CATEGORY_PATTERNS.get(category, []):
        words = [w for w in needle.split() if len(w) >= 5]
        if words and any(w in q for w in words):
            return topic
    # Last resort: show a shortened question as "topic"
    short = " ".join((question or "").strip().split())
    return (short[:72] + "…") if len(short) > 72 else (short or "Interview Practice")


def _phase_for_day(day: int) -> str:
    if day <= 10:
        return "Foundation"
    if day <= 20:
        return "Core Skills"
    return "Advanced & Project"


def _domain_for(category: str, phase: str) -> str:
    if category in {"HR", "Soft Skills"}:
        return "Stories & Practice" if phase != "Advanced & Project" else "Mock Interviews"
    if category in {"DSA", "Database"}:
        return "Practice Problems" if phase != "Advanced & Project" else "Timed Practice"
    return "Concepts & Practice" if phase != "Advanced & Project" else "Mock Interviews"


def _task_for(category: str, phase: str, topic: str, weakness_labels: Iterable[str]) -> str:
    labels = {str(x) for x in weakness_labels if x}
    is_comm = "Communication Weakness" in labels
    is_conf = "Confidence Low" in labels
    is_conceptual = "Conceptual Weakness" in labels

    speak_suffix = " + explain it out loud in 2 minutes" if is_comm else ""
    confidence_suffix = " + repeat once on camera" if is_conf else ""

    if category in {"HR", "Soft Skills"}:
        tnorm = _norm(topic)
        if "self-introduction" in tnorm:
            base = "Write a 60–90s pitch (Present→Past→Future) + 1 achievement"
        elif "career goals" in tnorm:
            base = "Draft a 5-year answer (role + skills + milestones) + 1 backup plan"
        elif "motivation" in tnorm or "why role/company" in tnorm:
            base = "Prepare 3 reasons (role fit + company fit + growth) + 2 follow-ups"
        elif "value proposition" in tnorm or "why hire" in tnorm:
            base = "Create a 3-point pitch (skills + proof + impact) + 1 example"
        else:
            base = f"Draft a structured example answer for: {topic} (use STAR if it's scenario-based)"

        if phase == "Foundation":
            return f"{base}{confidence_suffix}"
        if phase == "Core Skills":
            return f"Practice 2 follow-ups for: {topic}{speak_suffix}{confidence_suffix}"
        return f"Mock interview: {topic} (2 mins) + 1 follow-up{confidence_suffix}"

    # Technical / DSA / Database
    if phase == "Foundation":
        practice = "dry-run 2 examples" if is_conceptual else "write 5 key bullets + 1 example"
        return f"Revise {topic} ({practice}){speak_suffix}"
    if phase == "Core Skills":
        if category == "DSA":
            return f"Solve 2 problems on {topic} + write time/space analysis{speak_suffix}"
        if category == "Database":
            return f"Write 10 queries for {topic} + explain results{speak_suffix}"
        return f"Answer 3 interview questions on {topic}{speak_suffix}"
    # Advanced
    if category == "DSA":
        return f"Timed set: 1 medium on {topic} + review mistakes{speak_suffix}"
    if category == "Database":
        return f"Mini-case: design + queries for {topic}{speak_suffix}"
    return f"Mock: explain {topic} + 1 quick follow-up{speak_suffix}"


def generate_interview_category_plan(category: str, answers: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """
    Generates a 30-day plan for interview categories.

    If `answers` are provided, the plan is personalized: topics that were weak in the
    session are prioritized and repeated more often.
    """
    category = (category or "").strip()
    if category not in INTERVIEW_CATEGORIES:
        return generate_30_day_plan(category)

    base_topics = list(_CATEGORY_DEFAULT_TOPICS.get(category, []))
    if not base_topics:
        return generate_30_day_plan(category)

    topic_stats: DefaultDict[str, dict[str, Any]] = defaultdict(lambda: {"weak": 0, "strong": 0, "labels": set()})

    if answers:
        for row in answers:
            question = str(row.get("question") or "")
            result_category = str(row.get("result_category") or "")
            topic = _infer_interview_topic(category, question)
            topic_stats[topic]["labels"].add(result_category)
            if result_category == "Good Answer":
                topic_stats[topic]["strong"] += 1
            else:
                topic_stats[topic]["weak"] += 1

    # Ensure base topics exist even if not seen in answers
    for t in base_topics:
        _ = topic_stats[t]

    def _base_index(t: str) -> int:
        try:
            return base_topics.index(t)
        except ValueError:
            return 999

    ordered_topics = sorted(
        topic_stats.keys(),
        key=lambda t: (-topic_stats[t]["weak"], -topic_stats[t]["strong"], _base_index(t)),
    )

    weighted_pool: list[str] = []
    for t in ordered_topics:
        weak = int(topic_stats[t]["weak"])
        weight = 3 if weak > 0 else 1
        weighted_pool.extend([t] * weight)
    if not weighted_pool:
        weighted_pool = base_topics[:]

    plan: list[dict[str, Any]] = []
    for day in range(1, 31):
        phase = _phase_for_day(day)
        topic = weighted_pool[(day - 1) % len(weighted_pool)]
        labels = topic_stats[topic]["labels"]
        plan.append({
            "day": day,
            "topic": topic,
            "task": _task_for(category, phase, topic, labels),
            "domain": _domain_for(category, phase),
            "phase": phase,
        })
    return plan
