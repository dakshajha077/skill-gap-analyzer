"""
Feature 5: Daily Login + Badge System
Tracks login streak and assigns badge based on total session performance score.
"""
from datetime import date

# Badge thresholds: (min_score, badge_label, icon, color)
BADGE_LEVELS = [
    (10.0, "Expert",    "bi-star-fill",      "#f59e0b"),
    ( 8.0, "Master",    "bi-trophy-fill",    "#8B5CF6"),
    ( 5.0, "Skilled",   "bi-award-fill",     "#10b981"),
    ( 3.0, "Learner",   "bi-book-fill",      "#3b82f6"),
    ( 0.0, "Beginner",  "bi-mortarboard-fill","#64748b"),
]

NEXT_BADGE = {
    "Beginner": ("Learner",  3.0),
    "Learner":  ("Skilled",  5.0),
    "Skilled":  ("Master",   8.0),
    "Master":   ("Expert",  10.0),
    "Expert":   (None,       None),
}

def get_badge(total_score: float) -> dict:
    """Return badge info dict for a given total score."""
    for threshold, label, icon, color in BADGE_LEVELS:
        if total_score >= threshold:
            return {"label": label, "icon": icon, "color": color}
    return {"label": "Beginner", "icon": "bi-mortarboard-fill", "color": "#64748b"}

def get_next_badge_info(current_badge: str, total_score: float) -> dict:
    """Return info about the next badge to achieve."""
    next_name, next_threshold = NEXT_BADGE.get(current_badge, (None, None))
    if next_name is None:
        return {"next": None, "needed": 0, "progress": 100}
    needed = max(0, next_threshold - total_score)
    # Progress percentage toward next badge
    prev_threshold = 0
    for t, l, _, _ in reversed(BADGE_LEVELS):
        if l == current_badge:
            prev_threshold = t
            break
    span = next_threshold - prev_threshold
    progress = int(min(100, ((total_score - prev_threshold) / span) * 100)) if span > 0 else 100
    return {"next": next_name, "needed": round(needed, 1), "progress": max(0, progress)}

def update_streak(db, user_id: int, new_session_avg: float = 0) -> dict:
    """
    Called on login. Updates streak, recalculates badge.
    Returns streak info dict.
    """
    today = str(date.today())
    row = db.execute('SELECT * FROM user_streaks WHERE user_id=?', (user_id,)).fetchone()

    if row is None:
        # First login
        total_score = new_session_avg
        badge_info = get_badge(total_score)
        db.execute(
            'INSERT INTO user_streaks (user_id, login_streak, last_login_date, total_score, badge) VALUES (?,?,?,?,?)',
            (user_id, 1, today, total_score, badge_info['label'])
        )
        streak = 1
    else:
        last_date = row['last_login_date']
        streak = row['login_streak']
        total_score = row['total_score'] + new_session_avg

        if last_date == today:
            # Already logged in today — just update score
            streak = streak
        else:
            from datetime import date as dclass, timedelta
            last = dclass.fromisoformat(last_date)
            diff = (date.today() - last).days
            streak = (streak + 1) if diff == 1 else 1  # reset if gap > 1 day

        badge_info = get_badge(total_score)
        db.execute(
            '''UPDATE user_streaks SET login_streak=?, last_login_date=?, total_score=?, badge=?
               WHERE user_id=?''',
            (streak, today, total_score, badge_info['label'], user_id)
        )

    db.commit()
    badge = get_badge(total_score)
    next_info = get_next_badge_info(badge['label'], total_score)
    return {
        "streak": streak,
        "total_score": round(total_score, 1),
        "badge": badge,
        "next_badge": next_info,
    }

def get_streak_info(db, user_id: int) -> dict:
    """Read current streak info without modifying it."""
    row = db.execute('SELECT * FROM user_streaks WHERE user_id=?', (user_id,)).fetchone()
    if not row:
        badge = get_badge(0)
        return {"streak": 0, "total_score": 0, "badge": badge, "next_badge": get_next_badge_info("Beginner", 0)}
    badge = get_badge(row['total_score'])
    next_info = get_next_badge_info(badge['label'], row['total_score'])
    return {
        "streak": row['login_streak'],
        "total_score": round(row['total_score'], 1),
        "badge": badge,
        "next_badge": next_info,
    }
