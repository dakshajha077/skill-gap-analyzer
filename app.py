from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os, json, io, uuid, time
import threading
from datetime import datetime, timedelta

from config import Config
from database.db import init_db, get_db
from utils.skill_analyzer import analyze_skills, get_job_roles
from utils.interview_analyzer import analyze_answer, clear_session
from utils.ai_chatbot import get_ai_response, get_user_chat_context
from utils.pdf_generator import generate_skill_report, generate_interview_report
from utils.github_analyzer import analyze_github_repo          # Feature 2
from utils.badge_system import update_streak, get_streak_info  # Feature 5
from utils.learning_planner import generate_30_day_plan, generate_interview_category_plan, INTERVIEW_CATEGORIES        # Feature 3
from utils.email_sender import EmailSender, EmailConfigError     # Email feature

app = Flask(__name__)
app.config.from_object(Config)

with app.app_context():
    init_db()

QUESTION_BANK = {
    "Technical": [
        "Explain Object-Oriented Programming and its four main principles.",
        "What is a linked list and how does it differ from an array?",
        "Explain the concept of recursion with an example.",
        "What is the difference between a stack and a queue?",
        "What is time complexity? Explain Big O notation.",
        "What is the difference between SQL and NoSQL databases?",
        "Explain what an API is and how REST APIs work.",
        "What is a binary search tree and how does searching work in it?",
        "What is the difference between HTTP and HTTPS?",
        "Explain what version control is and why Git is important.",
    ],
    "HR": [
        "Tell me about yourself and your background.",
        "What is your greatest strength and how has it helped you?",
        "What is your greatest weakness and how are you working on it?",
        "Where do you see yourself in five years?",
        "Why are you interested in this role and our company?",
        "Describe a situation where you worked under pressure.",
        "Tell me about a time you worked in a team and your contribution.",
        "How do you handle criticism or negative feedback?",
        "Describe a time you showed leadership or took initiative.",
        "Why should we hire you over other candidates?",
    ],
    "DSA": [
        "What is the difference between linear and non-linear data structures?",
        "Explain bubble sort and its time complexity.",
        "What is a hash table and how does it handle collisions?",
        "What is the difference between BFS and DFS graph traversal?",
        "Explain dynamic programming and when you would use it.",
        "What is a heap data structure and where is it used?",
        "Explain the merge sort algorithm and its complexity.",
        "What is a graph and what are its types?",
        "What is memoization and how does it optimize recursive solutions?",
        "Explain the two-pointer technique and give an example use case.",
    ],
    "Database": [
        "What is database normalization and why is it important?",
        "Explain the different types of SQL JOINs with examples.",
        "What is an index in a database and how does it improve performance?",
        "What is the difference between primary key and foreign key?",
        "Explain ACID properties in database transactions.",
        "What is a stored procedure and when would you use one?",
        "What is the difference between DELETE, TRUNCATE and DROP?",
        "Explain what a view is in SQL and its advantages.",
        "What is database sharding and why is it used?",
        "What is the difference between clustered and non-clustered indexes?",
    ],
    "Soft Skills": [
        "How do you manage your time when working on multiple projects?",
        "Describe a situation where you had a conflict with a teammate.",
        "How do you approach learning a new technology or skill?",
        "Tell me about a time you failed and what you learned from it.",
        "How do you communicate technical concepts to non-technical people?",
        "Describe your problem-solving process when you face a difficult challenge.",
        "How do you stay motivated during repetitive or boring tasks?",
        "Tell me about a time you had to adapt to a significant change.",
        "How do you give and receive constructive feedback?",
        "Describe a project you are most proud of and your role in it.",
    ],
}

CATEGORY_INFO = {
    "Technical":   {"icon": "bi-cpu-fill",      "color": "primary", "desc": "Core programming and CS fundamentals"},
    "HR":          {"icon": "bi-person-fill",    "color": "success", "desc": "Behavioural and personal questions"},
    "DSA":         {"icon": "bi-diagram-3-fill", "color": "warning", "desc": "Data structures and algorithms"},
    "Database":    {"icon": "bi-database-fill",  "color": "danger",  "desc": "SQL, NoSQL and database concepts"},
    "Soft Skills": {"icon": "bi-people-fill",    "color": "info",    "desc": "Communication and teamwork skills"},
}

JOBS_BY_CATEGORY = {
    "Technical": {
        "excellent": ["Software Developer", "Backend Developer", "Full Stack Developer", "DevOps Engineer", "Cloud Engineer"],
        "good":      ["Junior Software Developer", "Frontend Developer", "QA Automation Engineer", "Systems Analyst"],
        "average":   ["Junior Developer", "Technical Support Specialist", "QA Tester", "IT Support Engineer"],
        "weak":      ["Junior IT Intern", "Graduate Trainee (Tech)", "Technical Documentation Writer"],
    },
    "HR": {
        "excellent": ["HR Business Partner", "Talent Acquisition Specialist", "People Operations Manager", "HR Executive"],
        "good":      ["HR Generalist", "Recruitment Coordinator", "Employee Relations Officer", "HR Analyst"],
        "average":   ["HR Assistant", "Admin Coordinator", "Payroll Assistant", "HR Support Officer"],
        "weak":      ["HR Intern", "Admin Intern", "Recruitment Trainee"],
    },
    "DSA": {
        "excellent": ["Software Engineer", "Algorithm Engineer", "Backend Engineer", "Research Engineer", "Competitive Programmer"],
        "good":      ["Junior Software Engineer", "Systems Engineer", "Data Structures Tutor", "QA Engineer"],
        "average":   ["Junior QA Engineer", "Graduate Software Trainee", "Technical Support Analyst"],
        "weak":      ["Graduate Trainee (CS)", "CS Teaching Assistant", "Junior QA Tester"],
    },
    "Database": {
        "excellent": ["Database Administrator", "Data Engineer", "SQL Developer", "BI Developer", "Data Architect"],
        "good":      ["Junior DBA", "Data Analyst", "ETL Developer", "Reporting Analyst"],
        "average":   ["Junior Data Analyst", "Database Support Analyst", "Report Builder"],
        "weak":      ["Database Intern", "Junior Analyst", "Data Entry Specialist"],
    },
    "Soft Skills": {
        "excellent": ["Project Manager", "Business Analyst", "Team Lead", "Scrum Master", "Product Owner"],
        "good":      ["Project Coordinator", "Operations Analyst", "Client Relationship Executive", "Associate BA"],
        "average":   ["Project Support Officer", "Operations Assistant", "Junior Coordinator"],
        "weak":      ["Project Trainee", "Business Support Intern", "Operations Intern"],
    },
}

def _get_jobs_for_category(category, avg_score, good_count):
    jobs = JOBS_BY_CATEGORY.get(category, JOBS_BY_CATEGORY["Technical"])
    if avg_score >= 75 and good_count >= 7:
        return jobs["excellent"], "Senior / Core Roles"
    elif avg_score >= 60 and good_count >= 5:
        return jobs["good"], "Mid-Level Roles"
    elif avg_score >= 45:
        return jobs["average"], "Entry Level Roles"
    else:
        return jobs["weak"], "Trainee / Intern Roles"


# ── MULTI-DEVICE LOGIN SUPPORT ────────────────────────────────────────────────
def get_device_name():
    """Extract device name from user-agent"""
    ua = request.headers.get('User-Agent', 'Unknown Device')
    if 'Mobile' in ua or 'Android' in ua or 'iPhone' in ua:
        return 'Mobile Device'
    elif 'iPad' in ua or 'Tablet' in ua:
        return 'Tablet'
    elif 'Windows' in ua:
        return 'Windows PC'
    elif 'Mac' in ua or 'Macintosh' in ua:
        return 'Mac'
    elif 'Linux' in ua:
        return 'Linux PC'
    else:
        return 'Web Browser'

def create_device_session(user_id, device_name=None):
    """Create a new device session token"""
    token = str(uuid.uuid4())
    if device_name is None:
        device_name = get_device_name()
    
    db = get_db()
    try:
        db.execute(
            '''INSERT INTO device_sessions (user_id, device_name, session_token, ip_address)
               VALUES (?, ?, ?, ?)''',
            (user_id, device_name, token, request.remote_addr)
        )
        db.commit()
    finally:
        db.close()
    
    return token

def validate_device_session(token):
    """Validate device session token and return user_id"""
    db = get_db()
    try:
        result = db.execute(
            '''SELECT user_id, is_active FROM device_sessions 
               WHERE session_token = ? AND is_active = 1''',
            (token,)
        ).fetchone()
        if result:
            # Update last activity
            db.execute('''UPDATE device_sessions SET last_activity = CURRENT_TIMESTAMP 
                         WHERE session_token = ?''', (token,))
            db.commit()
            return result['user_id']
        return None
    finally:
        db.close()

def deactivate_device_session(token):
    """Deactivate a device session"""
    db = get_db()
    try:
        db.execute('UPDATE device_sessions SET is_active = 0 WHERE session_token = ?', (token,))
        db.commit()
    finally:
        db.close()

def get_active_devices(user_id):
    """Get all active devices for a user"""
    db = get_db()
    try:
        devices = db.execute(
            '''SELECT id, device_name, device_type, created_at, last_activity, ip_address 
               FROM device_sessions 
               WHERE user_id = ? AND is_active = 1
               ORDER BY last_activity DESC''',
            (user_id,)
        ).fetchall()
        return devices
    finally:
        db.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def home():
    return render_template('index.html', categories=CATEGORY_INFO)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        pwd   = request.form.get('password', '')
        if not name or not email or not pwd:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        db = get_db()
        if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            flash('Email already registered.', 'warning')
            db.close()
            return render_template('register.html')
        db.execute('INSERT INTO users (name,email,password) VALUES (?,?,?)',
                   (name, email, generate_password_hash(pwd)))
        db.commit()
        db.close()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pwd   = request.form.get('password', '')
        db    = get_db()
        user  = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if user and check_password_hash(user['password'], pwd):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            
            # Feature: Create device session for multi-device support
            device_token = create_device_session(user['id'])
            session['device_token'] = device_token
            
            # Feature 5: update login streak on successful login
            update_streak(db, user['id'])
            db.close()
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(url_for('dashboard'))
        db.close()
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    # Deactivate device session on logout
    device_token = session.get('device_token')
    if device_token:
        deactivate_device_session(device_token)
    session.clear()
    return redirect(url_for('home'))


@app.route('/devices')
@login_required
def devices():
    """Manage active devices for multi-device login"""
    active_devices = get_active_devices(session['user_id'])
    return render_template('devices.html', devices=active_devices)


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    int_sessions = db.execute(
        '''
        SELECT s.*
        FROM interview_sessions s
        WHERE s.user_id = ?
          AND s.completed = 1
          AND (SELECT COUNT(*) FROM answers a WHERE a.session_id = s.id) >= 10
        ORDER BY s.created_at DESC
        LIMIT 10
        ''',
        (session['user_id'],)).fetchall()
    skill_analyses = db.execute(
        'SELECT * FROM skill_analyses WHERE user_id=? ORDER BY created_at DESC LIMIT 5',
        (session['user_id'],)).fetchall()
    all_answers = db.execute(
        'SELECT * FROM answers WHERE user_id=? ORDER BY created_at DESC',
        (session['user_id'],)).fetchall()

    # Feature 5: fetch streak/badge info for dashboard
    streak_info = get_streak_info(db, session['user_id'])

    # Feature 2: fetch user's repo scores for leaderboard context
    my_repos = db.execute(
        'SELECT * FROM github_repos WHERE user_id=? ORDER BY project_score DESC LIMIT 3',
        (session['user_id'],)).fetchall()

    recent_session_metrics = []
    if int_sessions:
        session_ids = [s['id'] for s in int_sessions]
        placeholders = ','.join('?' for _ in session_ids)
        session_answer_rows = db.execute(
            f'''SELECT session_id, result_category, COUNT(*) as count
                FROM answers
                WHERE session_id IN ({placeholders})
                GROUP BY session_id, result_category''',
            session_ids
        ).fetchall()

        session_counts_map = {}
        for row in session_answer_rows:
            session_counts_map.setdefault(row['session_id'], {})[row['result_category']] = row['count']

        for sess in int_sessions:
            counts = session_counts_map.get(sess['id'], {})
            total_questions = sum(counts.values())
            good_answers = counts.get('Good Answer', 0)
            recent_session_metrics.append({
                'id': sess['id'],
                'category': sess['category'],
                'avg_score': float(sess['avg_score'] or 0),
                'good_answers': good_answers,
                'needs_work': max(total_questions - good_answers, 0),
                'total_questions': total_questions,
                'created_at': sess['created_at'],
            })

    db.close()

    total_sessions = len(int_sessions)
    avg_score = round(sum(s['avg_score'] for s in int_sessions) / total_sessions, 1) if total_sessions else 0
    cat_counts = {}
    for a in all_answers:
        cat_counts[a['result_category']] = cat_counts.get(a['result_category'], 0) + 1

    return render_template('dashboard.html',
        int_sessions=int_sessions, skill_analyses=skill_analyses,
        total_sessions=total_sessions, avg_score=avg_score,
        cat_counts=cat_counts, categories=CATEGORY_INFO,
        all_answers=all_answers, streak_info=streak_info,
        my_repos=my_repos, recent_session_metrics=recent_session_metrics)


@app.route('/skill-analysis')
@login_required
def skill_analysis():
    job_roles = get_job_roles()
    return render_template('skill_analysis.html', job_roles=job_roles)


@app.route('/analyze-skills', methods=['POST'])
@login_required
def analyze_skills_route():
    data        = request.get_json()
    user_skills = data.get('skills', '').strip()
    job_role    = data.get('job_role', '').strip()

    if not user_skills:
        return jsonify({'error': 'Please enter your skills.'}), 400
    if not job_role:
        return jsonify({'error': 'Please select a job role.'}), 400

    result = analyze_skills(user_skills, job_role)
    if 'error' in result:
        return jsonify({'error': result['error']}), 400

    db = get_db()
    db.execute(
        '''INSERT INTO skill_analyses
           (user_id, job_role, user_skills, required_skills, matched_skills,
            missing_skills, extra_skills, overall_score)
           VALUES (?,?,?,?,?,?,?,?)''',
        (session['user_id'], job_role,
         ', '.join(result['user_skills']),
         ', '.join(result['required_skills']),
         json.dumps(result['matched_skills']),
         json.dumps(result['missing_skills']),
         json.dumps(result['extra_skills']),
         result['overall_score']))
    analysis_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    db.commit()
    db.close()

    result['analysis_id'] = analysis_id
    return jsonify(result)


@app.route('/skill-report/<int:analysis_id>')
@login_required
def download_skill_report(analysis_id):
    db = get_db()
    row = db.execute('SELECT * FROM skill_analyses WHERE id=? AND user_id=?',
                     (analysis_id, session['user_id'])).fetchone()
    db.close()
    if not row:
        flash('Report not found.', 'danger')
        return redirect(url_for('skill_analysis'))

    analysis = {
        "job_role":        row['job_role'],
        "overall_score":   row['overall_score'],
        "profile_label":   "Excellent Match" if row['overall_score'] >= 80 else
                           "Good Match"      if row['overall_score'] >= 60 else
                           "Partial Match"   if row['overall_score'] >= 40 else
                           "Skill Gap Detected",
        "matched_skills":  json.loads(row['matched_skills']),
        "missing_skills":  json.loads(row['missing_skills']),
        "extra_skills":    json.loads(row['extra_skills']),
        "strong_count":    sum(1 for m in json.loads(row['matched_skills']) if m.get('strength') == 'strong'),
        "moderate_count":  sum(1 for m in json.loads(row['matched_skills']) if m.get('strength') == 'moderate'),
        "missing_count":   len(json.loads(row['missing_skills'])),
        "recommendations": [f"Learn {m['skill']} — core requirement for {row['job_role']}."
                            for m in json.loads(row['missing_skills'])[:5]],
    }

    pdf_bytes = generate_skill_report(analysis, session['user_name'])
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"SkillGap_Report_{row['job_role'].replace(' ', '_')}.pdf"
    )


@app.route('/select-category')
@login_required
def select_category():
    return render_template('select_category.html', categories=CATEGORY_INFO)


@app.route('/api/check-incomplete-session/<category>')
@login_required
def check_incomplete_session(category):
    """Check if user has an incomplete interview session for this category"""
    if category not in QUESTION_BANK:
        return jsonify({'has_incomplete': False}), 400
    
    db = get_db()
    try:
        result = db.execute(
            '''SELECT id, created_at FROM interview_sessions 
               WHERE user_id = ? AND category = ? AND completed = 0
               ORDER BY created_at DESC LIMIT 1''',
            (session['user_id'], category)
        ).fetchone()
        
        if result:
            return jsonify({
                'has_incomplete': True,
                'session_id': result['id'],
                'created_at': result['created_at']
            })
        return jsonify({'has_incomplete': False})
    finally:
        db.close()


@app.route('/continue-interview/<session_id>')
@login_required
def continue_interview(session_id):
    """Continue an incomplete interview session"""
    db = get_db()
    try:
        interview = db.execute(
            '''SELECT id, category, user_id FROM interview_sessions 
               WHERE id = ? AND user_id = ? AND completed = 0''',
            (session_id, session['user_id'])
        ).fetchone()
        
        if not interview:
            return redirect(url_for('select_category'))
        
        # Count completed answers to find current question index
        completed_answers = db.execute(
            'SELECT COUNT(*) as count FROM answers WHERE session_id = ?',
            (session_id,)
        ).fetchone()
        
        q_idx = completed_answers['count']
        session['interview_session_id'] = interview['id']
        session['interview_category'] = interview['category']
        session['current_q_index'] = q_idx
        session.modified = True
        
        return redirect(url_for('interview'))
    finally:
        db.close()


@app.route('/start-interview/<category>')
@login_required
def start_interview(category):
    if category not in QUESTION_BANK:
        return redirect(url_for('select_category'))
    
    db = get_db()
    
    # Mark any incomplete sessions for this category as abandoned
    db.execute(
        '''UPDATE interview_sessions SET completed = 1 
           WHERE user_id = ? AND category = ? AND completed = 0''',
        (session['user_id'], category)
    )
    db.commit()
    
    # Create new session
    cur = db.execute('INSERT INTO interview_sessions (user_id, category) VALUES (?,?)',
                     (session['user_id'], category))
    db.commit()
    sid = cur.lastrowid
    db.close()
    
    session['interview_session_id'] = sid
    session['interview_category']   = category
    session['current_q_index']      = 0
    return redirect(url_for('interview'))


@app.route('/interview')
@login_required
def interview():
    if 'interview_session_id' not in session:
        return redirect(url_for('select_category'))
    cat   = session.get('interview_category')
    q_idx = session.get('current_q_index', 0)
    qs    = QUESTION_BANK[cat]
    if q_idx >= len(qs):
        return redirect(url_for('results'))
    return render_template('interview.html',
        question=qs[q_idx], q_index=q_idx, total=len(qs),
        category=cat, progress=int(q_idx / len(qs) * 100),
        category_info=CATEGORY_INFO[cat])


@app.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    data = request.get_json(silent=True) or {}
    answer = (data.get('answer') or '').strip()

    cat = session.get('interview_category')
    sid = session.get('interview_session_id')
    if not cat or not sid or cat not in QUESTION_BANK:
        return jsonify({'error': 'Interview session not found. Please start a new interview.'}), 400

    if not answer or len(answer.split()) < 2:
        return jsonify({'error': 'Please provide a more detailed answer.'}), 400

    # Canonicalise q_idx from DB to prevent duplicate inserts on client retry.
    # This happens when the server saved the answer, but the client couldn't parse the response.
    session_q_idx = int(session.get('current_q_index', 0) or 0)
    db = get_db()
    try:
        completed_answers = db.execute(
            'SELECT COUNT(*) as count FROM answers WHERE session_id = ? AND user_id = ?',
            (sid, session['user_id'])
        ).fetchone()
        db_q_idx = int(completed_answers['count']) if completed_answers else 0

        # If the DB says we're already past this question, treat as an idempotent retry:
        # move the client forward without inserting a mismatched answer.
        if db_q_idx > session_q_idx:
            session['current_q_index'] = db_q_idx
            session.modified = True
            is_last = db_q_idx >= len(QUESTION_BANK[cat])
            if is_last:
                clear_session(str(sid))
            return jsonify({'is_last': is_last, 'already_submitted': True})

        # If session claims we're ahead of the DB, something is out of sync (back/forward, stale cookie, etc.).
        if db_q_idx < session_q_idx:
            session['current_q_index'] = db_q_idx
            session.modified = True
            return jsonify({'error': 'Session out of sync. Please refresh and try again.'}), 409

        if session_q_idx >= len(QUESTION_BANK[cat]):
            clear_session(str(sid))
            return jsonify({'is_last': True, 'already_submitted': True})

        question = QUESTION_BANK[cat][session_q_idx]

        try:
            result = analyze_answer(question, answer, cat, session_id=str(sid))
        except Exception:
            app.logger.exception("analyze_answer failed")
            return jsonify({'error': 'Server error while analysing your answer. Please try again.'}), 500

        fb = result['feedback']
        if result.get('improvement_suggestions'):
            fb += '||SUGG||' + '||S||'.join(result['improvement_suggestions'])
        if result.get('confidence_note'):
            fb += (f"||CNOTE||{result['confidence_note']}"
                   f"||CLVL||{result.get('confidence_level', '')}"
                   f"||CCLR||{result.get('confidence_color', 'secondary')}"
                   f"||EVBY||{result.get('evaluated_by', '')}")

        db.execute(
            '''INSERT INTO answers (session_id,user_id,question,answer,result_category,score,feedback)
               VALUES (?,?,?,?,?,?,?)''',
            (sid, session['user_id'], question, answer,
             result['category'], result['score'], fb))
        db.commit()

        session['current_q_index'] = session_q_idx + 1
        session.modified = True

        is_last = (session_q_idx + 1) >= len(QUESTION_BANK[cat])
        if is_last:
            clear_session(str(sid))
        return jsonify({**result, 'is_last': is_last})
    finally:
        db.close()


@app.route('/api/warmup', methods=['POST'])
@login_required
def warmup():
    """
    Warm up ML models in the background so the first submit doesn't time out
    on hosts with strict request time limits.
    """
    def _do_warmup():
        try:
            analyze_answer("Warmup question", "Warmup answer to load models.", "Technical", session_id=None)
        except Exception:
            app.logger.exception("Warmup failed")

    threading.Thread(target=_do_warmup, daemon=True).start()
    return jsonify({'started': True})


@app.route('/results')
@login_required
def results():
    sid = session.get('interview_session_id')
    if not sid:
        return redirect(url_for('select_category'))

    db = get_db()
    answers = db.execute('SELECT * FROM answers WHERE session_id=? ORDER BY id ASC', (sid,)).fetchall()
    if not answers:
        db.close()
        return redirect(url_for('select_category'))

    scores    = [a['score'] for a in answers]
    avg_score = round(sum(scores) / len(scores), 1)
    cat_counts = {}
    for a in answers:
        cat_counts[a['result_category']] = cat_counts.get(a['result_category'], 0) + 1

    db.execute('UPDATE interview_sessions SET avg_score=?,completed=1 WHERE id=?', (avg_score, sid))

    # Feature 5: update badge with session score contribution
    update_streak(db, session['user_id'], new_session_avg=avg_score / 10)
    db.commit()
    db.close()

    interview_category = session.get('interview_category')
    good = cat_counts.get('Good Answer', 0)
    tw   = sum(v for k, v in cat_counts.items() if any(x in k for x in ['Weakness', 'Weak', 'Conceptual']))

    strong_pts, weak_pts = [], []
    if good >= 7: strong_pts.append("Excellent overall — 7+ correct answers")
    if good >= 5: strong_pts.append("Strong conceptual understanding")
    if cat_counts.get('Communication Weakness', 0) == 0: strong_pts.append("Clear and well-structured communication")
    if cat_counts.get('Confidence Low', 0) == 0: strong_pts.append("Confident and composed delivery")
    if not strong_pts: strong_pts.append("Attempted all questions consistently")

    if tw >= 4: weak_pts.append(f"Gaps in {tw} answers — review these topics")
    if cat_counts.get('Communication Weakness', 0) >= 2: weak_pts.append("Communication clarity needs improvement")
    if cat_counts.get('Confidence Low', 0) >= 2: weak_pts.append("Build confidence through regular mock practice")
    if avg_score < 50: weak_pts.append("Overall preparation needs significant improvement")
    if not weak_pts: weak_pts.append("Minor areas to polish — keep practising!")

    job_list, job_label = _get_jobs_for_category(interview_category, avg_score, good)
    perf_label = ("Excellent 🌟" if avg_score >= 80 else
                  "Good 👍"      if avg_score >= 65 else
                  "Average 📈"   if avg_score >= 50 else
                  "Needs Work 💪")

    # Prepare session context for chatbot (Feature 1)
    session_context = {
        "category": interview_category,
        "avg_score": avg_score,
        "performance_label": perf_label,
        "strong_points": strong_pts,
        "weak_points": weak_pts,
        "job_recommendations": job_list,
        "cat_counts": dict(cat_counts),
        "total_questions": len(answers),
    }

    return render_template('results.html',
        answers=answers, avg_score=avg_score, cat_counts=cat_counts,
        total=len(answers), strong_points=strong_pts, weak_points=weak_pts,
        job_recommendations=job_list, job_label=job_label,
        performance_label=perf_label, interview_category=interview_category,
        session_context=json.dumps(session_context), session_id=sid)


@app.route('/session/<int:session_id>')
@login_required
def session_detail(session_id):
    db = get_db()
    sess = db.execute('SELECT * FROM interview_sessions WHERE id=? AND user_id=?',
                      (session_id, session['user_id'])).fetchone()
    if not sess:
        db.close()
        flash('Session not found.', 'danger')
        return redirect(url_for('dashboard'))
    answers = db.execute(
        'SELECT * FROM answers WHERE session_id=? ORDER BY id ASC', (session_id,)
    ).fetchall()
    db.close()

    scores    = [a['score'] for a in answers]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    cat_counts = {}
    for a in answers:
        cat_counts[a['result_category']] = cat_counts.get(a['result_category'], 0) + 1

    good_answers = [a for a in answers if a['result_category'] == 'Good Answer']
    needs_work   = [a for a in answers if a['result_category'] != 'Good Answer']
    good_count   = cat_counts.get('Good Answer', 0)
    tw           = sum(v for k, v in cat_counts.items() if any(x in k for x in ['Weakness', 'Weak', 'Conceptual']))
    conf_low     = cat_counts.get('Confidence Low', 0)
    total        = len(answers)

    strong_points, weak_points = [], []
    if good_count >= 7: strong_points.append("Excellent performance — 7+ correct answers")
    if good_count >= 5: strong_points.append("Strong overall conceptual understanding")
    if cat_counts.get('Communication Weakness', 0) == 0: strong_points.append("Clear and well-structured communication")
    if cat_counts.get('Confidence Low', 0) == 0: strong_points.append("Confident delivery throughout")
    if not strong_points: strong_points.append("Attempted all questions consistently")

    if tw >= 3: weak_points.append(f"Technical gaps in {tw} answers — revise core concepts")
    if cat_counts.get('Communication Weakness', 0) >= 2: weak_points.append("Communication needs improvement — practice STAR method")
    if conf_low >= 2: weak_points.append(f"Confidence low in {conf_low} answers — mock practice needed")
    if not weak_points: weak_points.append("Minor areas to polish — keep practising!")

    job_list, job_label = _get_jobs_for_category(sess['category'], avg_score, good_count)
    performance_label   = ("Excellent 🌟" if avg_score >= 80 else
                           "Good 👍"      if avg_score >= 65 else
                           "Average 📈"   if avg_score >= 50 else
                           "Needs Work 💪")
    category_info = CATEGORY_INFO.get(sess['category'], {"icon": "bi-circle", "color": "secondary", "desc": ""})

    session_context = {
        "category": sess['category'],
        "avg_score": avg_score,
        "performance_label": performance_label,
        "strong_points": strong_points,
        "weak_points": weak_points,
        "job_recommendations": job_list,
        "cat_counts": dict(cat_counts),
        "total_questions": total,
    }

    return render_template('session_detail.html',
        sess=sess, answers=answers, avg_score=avg_score,
        cat_counts=cat_counts, good_answers=good_answers,
        needs_work=needs_work, strong_points=strong_points,
        weak_points=weak_points, job_recommendations=job_list,
        job_label=job_label, performance_label=performance_label,
        category_info=category_info, total=total,
        session_context=json.dumps(session_context))


@app.route('/api/sessions/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_interview_session(session_id: int):
    db = get_db()
    try:
        existing = db.execute(
            'SELECT id FROM interview_sessions WHERE id = ? AND user_id = ?',
            (session_id, session['user_id'])
        ).fetchone()
        if not existing:
            return jsonify({'success': False, 'error': 'Session not found.'}), 404

        # Delete dependent rows first for FK safety.
        db.execute('DELETE FROM answers WHERE session_id = ? AND user_id = ?', (session_id, session['user_id']))
        db.execute('DELETE FROM interview_sessions WHERE id = ? AND user_id = ?', (session_id, session['user_id']))
        db.commit()
    finally:
        db.close()

    if session.get('interview_session_id') == session_id:
        session.pop('interview_session_id', None)

    return jsonify({'success': True, 'message': f'Session #{session_id} deleted.'})


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    msg  = data.get('message', '').strip()
    rat  = int(data.get('rating', 0))
    if not msg or rat < 1 or rat > 5:
        return jsonify({'error': 'Please provide a message and rating.'}), 400
    db = get_db()
    db.execute('INSERT INTO feedback (name,email,rating,category,message) VALUES (?,?,?,?,?)',
               (data.get('name', ''), data.get('email', ''), rat, data.get('category', 'General'), msg))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/send-session-report-email', methods=['POST'])
@login_required
def send_session_report_email():
    """Send a specific interview session report with profile details and PDF attachment."""
    try:
        data = request.get_json(silent=True) or {}
        sid = data.get('session_id') or session.get('interview_session_id')
        recipient_email = (data.get('recipient_email') or '').strip().lower()

        if not sid:
            return jsonify({'error': 'No interview session found.'}), 400

        db = get_db()
        try:
            user = db.execute(
                'SELECT name, email, phone, location, created_at FROM users WHERE id=?',
                (session['user_id'],)
            ).fetchone()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            interview_session = db.execute(
                'SELECT * FROM interview_sessions WHERE id=? AND user_id=?',
                (sid, session['user_id'])
            ).fetchone()
            if not interview_session:
                return jsonify({'error': 'Session not found'}), 404

            answers = db.execute(
                'SELECT * FROM answers WHERE session_id=? ORDER BY id ASC',
                (sid,)
            ).fetchall()
            if not answers:
                return jsonify({'error': 'No interview results found'}), 404
        finally:
            db.close()

        scores = [a['score'] for a in answers]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        cat_counts = {}
        for a in answers:
            cat_counts[a['result_category']] = cat_counts.get(a['result_category'], 0) + 1

        interview_category = interview_session['category']
        good = cat_counts.get('Good Answer', 0)
        needs_work = len(answers) - good
        tw = sum(v for k, v in cat_counts.items() if any(x in k for x in ['Weakness', 'Weak', 'Conceptual']))

        strong_pts, weak_pts = [], []
        if good >= 7:
            strong_pts.append("Excellent overall — 7+ correct answers")
        if good >= 5:
            strong_pts.append("Strong conceptual understanding")
        if cat_counts.get('Communication Weakness', 0) == 0:
            strong_pts.append("Clear and well-structured communication")
        if cat_counts.get('Confidence Low', 0) == 0:
            strong_pts.append("Confident and composed delivery")
        if not strong_pts:
            strong_pts.append("Attempted all questions consistently")

        if tw >= 4:
            weak_pts.append(f"Gaps in {tw} answers — review these topics")
        if cat_counts.get('Communication Weakness', 0) >= 2:
            weak_pts.append("Communication clarity needs improvement")
        if cat_counts.get('Confidence Low', 0) >= 2:
            weak_pts.append("Build confidence through regular mock practice")
        if avg_score < 50:
            weak_pts.append("Overall preparation needs significant improvement")
        if not weak_pts:
            weak_pts.append("Minor areas to polish — keep practising!")

        job_list, job_label = _get_jobs_for_category(interview_category, avg_score, good)
        perf_label = ("Excellent 🌟" if avg_score >= 80 else
                      "Good 👍"      if avg_score >= 65 else
                      "Average 📈"   if avg_score >= 50 else
                      "Needs Work 💪")

        profile_details = {
            'name': user['name'],
            'email': user['email'],
            'phone': user['phone'] or '',
            'location': user['location'] or '',
            'member_since': user['created_at'][:10] if user['created_at'] else 'Not available',
        }

        email_data = {
            'session_id': int(sid),
            'avg_score': avg_score,
            'category': interview_category,
            'performance_label': perf_label,
            'strong_points': strong_pts,
            'weak_points': weak_pts,
            'job_recommendations': job_list,
            'job_label': job_label,
            'good_answers': good,
            'needs_work': needs_work,
            'total_questions': len(answers),
            'profile_details': profile_details,
            'report_filename': f"Interview_Session_{sid}_{interview_category.replace(' ', '_')}.pdf",
            'category_breakdown': [
                {'label': label, 'count': count}
                for label, count in cat_counts.items()
            ],
            'answer_highlights': [
                {
                    'question': answer['question'],
                    'result_category': answer['result_category'],
                    'score': answer['score'],
                }
                for answer in answers
            ],
        }

        report_pdf = generate_interview_report(email_data, profile_details)
        config_email = (Config.GMAIL_EMAIL or '').strip()
        config_password = (Config.GMAIL_PASSWORD or '').strip()
        sender_email = None if EmailSender._looks_like_placeholder(config_email) else config_email
        sender_password = None if EmailSender._looks_like_placeholder(config_password) else config_password

        try:
            email_sender = EmailSender(
                smtp_server=Config.MAIL_SERVER,
                smtp_port=Config.MAIL_PORT,
                sender_email=sender_email,
                sender_password=sender_password,
            )
        except EmailConfigError as e:
            return jsonify({'error': str(e)}), 500

        target_email = recipient_email or user['email']
        success = email_sender.send_interview_report(
            recipient_email=target_email,
            user_name=user['name'],
            interview_data=email_data,
            report_pdf=report_pdf
        )

        if success:
            return jsonify({
                'success': True,
                'message': f'Report sent successfully to {target_email}!'
            })

        error_message = 'Failed to send email. Please check your mail configuration and try again later.'
        details = (email_sender.last_error or '').lower()
        if any(token in details for token in ['authentication failed', 'username and password not accepted', 'smtpauthenticationerror', '535']):
            error_message = 'SMTP authentication failed. If you use Gmail, set GMAIL_EMAIL and a Gmail App Password in GMAIL_PASSWORD.'

        payload = {'error': error_message}
        if Config.DEBUG and email_sender.last_error:
            payload['details'] = email_sender.last_error
        return jsonify(payload), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── FEEDBACK LEARNING LOOP ────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────


# ── MULTI-DEVICE MANAGEMENT API ─────────────────────────────────────────────
@app.route('/api/devices', methods=['GET'])
@login_required
def list_devices():
    """Get all active devices for the current user"""
    devices = get_active_devices(session['user_id'])
    devices_list = []
    for device in devices:
        devices_list.append({
            'id': device['id'],
            'name': device['device_name'],
            'type': device['device_type'],
            'ip': device['ip_address'],
            'lastActivity': device['last_activity'],
            'loginDate': device['created_at'],
            'isCurrent': session.get('device_token') is not None  # Could be improved with token comparison
        })
    return jsonify({'devices': devices_list, 'count': len(devices_list)})


@app.route('/api/devices/<int:device_id>/revoke', methods=['POST'])
@login_required
def revoke_device(device_id):
    """Revoke access on a specific device"""
    db = get_db()
    try:
        # Verify the device belongs to this user
        device = db.execute(
            '''SELECT session_token FROM device_sessions 
               WHERE id = ? AND user_id = ?''',
            (device_id, session['user_id'])
        ).fetchone()
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Deactivate the device
        db.execute('UPDATE device_sessions SET is_active = 0 WHERE id = ?', (device_id,))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Device access revoked'})
    finally:
        db.close()


@app.route('/profile')
@login_required
def profile():
    """User profile page with device management"""
    devices = get_active_devices(session['user_id'])
    db = get_db()
    try:
        user = db.execute(
            'SELECT name, email, phone, location, avatar_path, created_at FROM users WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
    finally:
        db.close()

    return render_template(
        'settings.html',
        devices=devices,
        user_name=user['name'] if user else session.get('user_name', 'User'),
        user_email=user['email'] if user else '',
        user_phone=user['phone'] if user else '',
        user_location=user['location'] if user else '',
        user_avatar_url=url_for('static', filename=user['avatar_path']) if user and user['avatar_path'] else '',
        user_created_at=user['created_at'] if user else ''
    )


@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update editable profile details for the current user."""
    data = request.get_json(silent=True) or request.form
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    location = data.get('location', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Name is required.'}), 400
    if not email:
        return jsonify({'success': False, 'error': 'Email is required.'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'success': False, 'error': 'Please enter a valid email address.'}), 400
    if phone and len(phone) < 7:
        return jsonify({'success': False, 'error': 'Please enter a valid contact number.'}), 400

    db = get_db()
    try:
        existing_user = db.execute(
            'SELECT id FROM users WHERE email = ? AND id != ?',
            (email, session['user_id'])
        ).fetchone()
        if existing_user:
            return jsonify({'success': False, 'error': 'That email is already in use.'}), 400

        db.execute(
            '''UPDATE users
               SET name = ?, email = ?, phone = ?, location = ?
               WHERE id = ?''',
            (name, email, phone, location, session['user_id'])
        )
        db.commit()
    finally:
        db.close()

    session['user_name'] = name
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully.',
        'profile': {
            'name': name,
            'email': email,
            'phone': phone,
            'location': location
        }
    })


@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify({'success': False, 'error': 'File too large. Max size is 2MB.'}), 413


_ALLOWED_AVATAR_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}


def _is_allowed_avatar(filename: str) -> bool:
    ext = os.path.splitext(filename or '')[1].lower()
    return ext in _ALLOWED_AVATAR_EXTENSIONS


def _safe_remove_static_file(static_relative_path: str) -> None:
    if not static_relative_path:
        return

    rel_norm = static_relative_path.replace('\\', '/').lstrip('/')
    base_dir = os.path.abspath(os.path.join(app.static_folder, 'uploads', 'avatars'))
    abs_path = os.path.abspath(os.path.join(app.static_folder, rel_norm))

    if abs_path.startswith(base_dir) and os.path.isfile(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            pass


@app.route('/profile/avatar', methods=['POST'])
@login_required
def upload_profile_avatar():
    file = request.files.get('avatar')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'Please choose an image file to upload.'}), 400

    original_name = secure_filename(file.filename)
    if not _is_allowed_avatar(original_name):
        return jsonify({'success': False, 'error': 'Unsupported file type. Use PNG, JPG, or WEBP.'}), 400

    user_id = session['user_id']
    ext = os.path.splitext(original_name)[1].lower()
    upload_dir = os.path.join(app.static_folder, 'uploads', 'avatars', str(user_id))
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"avatar_{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(upload_dir, filename)
    file.save(abs_path)

    avatar_path = os.path.join('uploads', 'avatars', str(user_id), filename).replace('\\', '/')

    db = get_db()
    try:
        existing = db.execute('SELECT avatar_path FROM users WHERE id = ?', (user_id,)).fetchone()
        if existing and existing['avatar_path']:
            _safe_remove_static_file(existing['avatar_path'])

        db.execute('UPDATE users SET avatar_path = ? WHERE id = ?', (avatar_path, user_id))
        db.commit()
    finally:
        db.close()

    return jsonify({
        'success': True,
        'message': 'Profile photo updated successfully.',
        'avatar_url': url_for('static', filename=avatar_path),
    })


@app.route('/profile/avatar/delete', methods=['POST'])
@login_required
def delete_profile_avatar():
    user_id = session['user_id']
    db = get_db()
    try:
        existing = db.execute('SELECT avatar_path FROM users WHERE id = ?', (user_id,)).fetchone()
        if existing and existing['avatar_path']:
            _safe_remove_static_file(existing['avatar_path'])
        db.execute('UPDATE users SET avatar_path = ? WHERE id = ?', ('', user_id))
        db.commit()
    finally:
        db.close()

    return jsonify({'success': True, 'message': 'Profile photo removed.'})
# ─────────────────────────────────────────────────────────────────────────────


@app.route('/transcribe', methods=['POST'])
@login_required
def transcribe():
    from utils.speech_handler import transcribe_audio_base64
    data  = request.get_json()
    audio = data.get('audio', '')
    if not audio:
        return jsonify({'error': 'No audio.'}), 400
    try:
        return jsonify({'text': transcribe_audio_base64(audio)})
    except ValueError as e:
        return jsonify({'error': str(e)}), 422
    except ConnectionError as e:
        return jsonify({'error': str(e)}), 503


# ── FEATURE 1: AI CHATBOT API ─────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """
    AI-Powered Chatbot Endpoint
    
    Accepts:
    - message: User's question
    - mode: 'session' (post-interview) or 'dashboard' (general)
    - history: Optional conversation history
    - context: Optional pre-computed context
    
    Returns:
    - reply: AI-generated response
    """
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    mode = data.get('mode', 'session')
    history = data.get('history', [])
    context = data.get('context', {})
    user_id = session.get('user_id')
    
    # Validate input
    if not message:
        return jsonify({'error': 'Empty message.'}), 400
    
    if not user_id:
        return jsonify({'error': 'User not authenticated.'}), 401
    
    try:
        # Get AI response with context
        reply = get_ai_response(
            message=message,
            user_id=user_id,
            context=context if context else None,
            history=history,
            mode=mode
        )
        
        return jsonify({'reply': reply})
    
    except Exception as e:
        print(f"Chatbot error: {e}")
        return jsonify({'error': 'Failed to generate response. Please try again.'}), 500


@app.route('/api/chat-context/<int:user_id>')
@login_required
def get_chat_context_endpoint(user_id):
    """
    Endpoint to get user's context for chatbot initialization
    
    Returns:
    - User stats (score, sessions, skills, etc.)
    """
    if session.get('user_id') != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        context = get_user_chat_context(user_id)
        return jsonify(context)
    except Exception as e:
        print(f"Context retrieval error: {e}")
        return jsonify({'error': 'Failed to retrieve context'}), 500


# ── FEATURE 2: GITHUB ANALYZER + LEADERBOARD ─────────────────────────────────
@app.route('/github-analyzer')
@login_required
def github_analyzer():
    db = get_db()
    my_repos = db.execute(
        'SELECT id, user_id, username, repo_url, repo_name, stars, commits, languages, readme_score, project_score, strengths, improvements, created_at FROM github_repos WHERE user_id=? ORDER BY project_score DESC',
        (session['user_id'],)
    ).fetchall()
    # Convert Row objects to dicts and parse JSON fields
    my_repos = [dict(repo) for repo in my_repos]
    for repo in my_repos:
        repo['languages'] = json.loads(repo['languages'] or '[]')
        repo['strengths'] = json.loads(repo['strengths'] or '[]')
        repo['improvements'] = json.loads(repo['improvements'] or '[]')
    db.close()
    return render_template('github_analyzer.html', my_repos=my_repos)


@app.route('/api/analyze-github', methods=['POST'])
@login_required
def api_analyze_github():
    """Analyze a GitHub repo URL and save result."""
    data = request.get_json(silent=True) or {}
    repo_url = data.get('repo_url', '').strip()
    if not repo_url:
        return jsonify({'error': 'Please provide a GitHub repository URL.'}), 400

    result = analyze_github_repo(repo_url)
    if 'error' in result:
        return jsonify(result), 400

    # Save to DB
    db = get_db()
    db.execute(
        '''INSERT INTO github_repos
           (user_id, username, repo_url, repo_name, stars, commits, languages,
            readme_score, project_score, strengths, improvements)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (session['user_id'], session['user_name'], repo_url,
         result['repo_name'], result['stars'], result['commits'],
         json.dumps(result['languages']), result['readme_score'],
         result['project_score'], json.dumps(result['strengths']),
         json.dumps(result['improvements']))
    )
    db.commit()
    db.close()

    result['user_name'] = session['user_name']
    return jsonify(result)


@app.route('/api/leaderboard')
@login_required
def api_leaderboard():
    """Return top 10 leaderboard entries."""
    db = get_db()
    rows = db.execute(
        '''SELECT gr.username, gr.repo_name, gr.repo_url, gr.project_score,
                  gr.languages, u.name as user_name, gr.created_at
           FROM github_repos gr
           JOIN users u ON u.id = gr.user_id
           ORDER BY gr.project_score DESC LIMIT 10'''
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ── FEATURE 3: 30-DAY LEARNING PLANNER ───────────────────────────────────────
@app.route('/api/learning-plan', methods=['POST'])
@login_required
def api_learning_plan():
    """Generate a 30-day learning plan for a given skill."""
    data  = request.get_json(silent=True) or {}
    skill = data.get('skill', '').strip()
    session_id = data.get('session_id')
    if not skill:
        return jsonify({'error': 'Please provide a skill name.'}), 400

    # If the selected "skill" is one of our interview categories, generate a topic-specific plan.
    if skill in INTERVIEW_CATEGORIES:
        answers = None
        if session_id is not None:
            try:
                session_id_int = int(session_id)
            except (TypeError, ValueError):
                session_id_int = None

            if session_id_int is not None:
                db = get_db()
                try:
                    sess = db.execute(
                        'SELECT id, category FROM interview_sessions WHERE id=? AND user_id=?',
                        (session_id_int, session['user_id'])
                    ).fetchone()
                    # Only use session answers if the session matches the selected category
                    if sess and sess['category'] == skill:
                        rows = db.execute(
                            'SELECT question, result_category, score FROM answers WHERE session_id=? AND user_id=? ORDER BY id ASC',
                            (session_id_int, session['user_id'])
                        ).fetchall()
                        answers = [dict(r) for r in rows]
                finally:
                    db.close()

        plan = generate_interview_category_plan(skill, answers=answers)
        return jsonify({'skill': skill, 'plan': plan})

    plan = generate_30_day_plan(skill)
    return jsonify({'skill': skill, 'plan': plan})


# ── FEATURE 5: BADGE INFO API ─────────────────────────────────────────────────
@app.route('/api/badge-info')
@login_required
def api_badge_info():
    """Return current streak and badge info for the logged-in user."""
    db = get_db()
    info = get_streak_info(db, session['user_id'])
    db.close()
    return jsonify(info)


if __name__ == '__main__':
    app.run(debug=Config.DEBUG)
