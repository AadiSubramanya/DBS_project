from flask import Flask, render_template, request, session, flash, redirect, url_for
from db_config import get_connection
import oracledb
from functools import wraps

app = Flask(__name__)
app.secret_key = "dev_secret"

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────
def read_db_val(val):
    """Safely extracts text from Oracle CLOB/BLOB types or returns the value."""
    if hasattr(val, "read"):
        try:
            return val.read()
        except Exception:
            return str(val)
    return val

# ─────────────────────────────────────────
# ROLE-BASED ACCESS DECORATOR
# ─────────────────────────────────────────
def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') != role_name:
                flash(f"Unauthorized. {role_name} access required.", 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ─────────────────────────────────────────
# LOGIN AUDIT (Triggers handle other events)
# ─────────────────────────────────────────
def log_audit(user_id, action):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO AUDIT_LOGS(user_id, action) VALUES (:1, :2)",
            (user_id, action)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ─────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT user_id, role, full_name, password_hash "
                "FROM USERS WHERE username = :1",
                (u,)
            )
            usr = c.fetchone()
            conn.close()

            if usr and usr[3] == p:
                session.update({
                    'user_id': usr[0],
                    'role': usr[1],
                    'full_name': usr[2]
                })
                log_audit(usr[0], "Logged in")
                return redirect(url_for('dashboard'))

            flash("Invalid username or password.", 'error')
        except Exception as e:
            flash(str(e), 'error')

    return render_template('auth.html', title="Login", is_register=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        r = request.form
        try:
            conn = get_connection()
            c = conn.cursor()

            # Stored procedure call
            c.callproc("sp_register_user", [
                r['username'],
                r['password'],
                r['full_name'],
                r['role'],
                r['email']
            ])

            conn.commit()
            conn.close()
            flash("Registered successfully! Please log in.", 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(str(e), 'error')

    return render_template('auth.html', title="Register", is_register=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session['role']
    uid = session['user_id']
    data = {}

    try:
        conn = get_connection()
        c = conn.cursor()

        # -------------------- ADMIN --------------------
        if role == 'Admin':
            c.execute(
                "SELECT user_id, username, full_name, role, email "
                "FROM USERS ORDER BY user_id"
            )
            data['users'] = c.fetchall()

            c.execute(
                "SELECT subject_id, name, description "
                "FROM SUBJECTS ORDER BY name"
            )
            data['subjects_list'] = c.fetchall()

            c.execute("SELECT COUNT(*) FROM USERS")
            data['u_cnt'] = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM TESTS")
            data['t_cnt'] = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM TEST_ATTEMPTS")
            data['total_attempts'] = c.fetchone()[0]

            c.execute("""
                SELECT AVG(
                    CASE WHEN max_score > 0
                    THEN (score / max_score) * 100
                    ELSE 0 END)
                FROM TEST_ATTEMPTS
            """)
            avg = c.fetchone()[0]
            data['avg_score'] = round(avg, 2) if avg else 0

            c.execute("SELECT COUNT(*) FROM TESTS WHERE is_active = 1")
            data['live_tests'] = c.fetchone()[0]

            # -------- Database Viewer (db_view) --------
            tables = [
                'USERS', 'SUBJECTS', 'QUESTIONS', 'TESTS',
                'TEST_QUESTIONS', 'TEST_ATTEMPTS',
                'STUDENT_ANSWERS', 'AUDIT_LOGS'
            ]
            db_view = {}

            for t in tables:
                try:
                    c.execute(
                        "SELECT column_name FROM user_tab_columns "
                        "WHERE table_name = :1 ORDER BY column_id",
                        (t,)
                    )
                    cols = [col[0] for col in c.fetchall()]

                    c.execute(f"SELECT * FROM {t}")
                    rows = c.fetchall()

                    processed_rows = []
                    for row in rows:
                        new_row = []
                        for val in row:
                            new_row.append(read_db_val(val))
                        processed_rows.append(new_row)

                    db_view[t] = {'cols': cols, 'rows': processed_rows}
                except Exception:
                    db_view[t] = {'cols': [], 'rows': []}

            data['db_view'] = db_view

        # -------------------- INSTRUCTOR --------------------
        elif role == 'Instructor':
            c.execute(
                "SELECT subject_id, name FROM SUBJECTS ORDER BY name"
            )
            data['subjects'] = c.fetchall()

            c.execute("""
                SELECT t.test_id, t.title, t.duration_minutes, s.name,
                       t.is_active,
                       CASE
                           WHEN t.is_active = 1 AND t.start_time IS NOT NULL THEN
                               GREATEST(
                                   0,
                                   FLOOR(
                                       (CAST(t.start_time AS DATE) +
                                       t.duration_minutes/1440 - SYSDATE) * 86400
                                   )
                               )
                           ELSE 0
                       END AS remaining_secs,
                       t.start_time
                FROM TESTS t
                LEFT JOIN SUBJECTS s ON t.subject_id = s.subject_id
                WHERE t.creator_id = :1
                ORDER BY t.test_id DESC
            """, (uid,))
            data['tests'] = c.fetchall()

        # -------------------- STUDENT --------------------
        else:
            c.execute("""
                SELECT t.test_id, t.title, t.duration_minutes, s.name
                FROM TESTS t
                LEFT JOIN SUBJECTS s ON t.subject_id = s.subject_id
                WHERE t.is_active = 1
                AND SYSTIMESTAMP <= t.start_time +
                    NUMTODSINTERVAL(t.duration_minutes, 'MINUTE')
                AND t.test_id NOT IN (
                    SELECT test_id
                    FROM TEST_ATTEMPTS
                    WHERE student_id = :1
                )
            """, (uid,))
            data['available'] = c.fetchall()

            c.execute("""
                SELECT t.title, a.score, a.max_score
                FROM TEST_ATTEMPTS a
                JOIN TESTS t ON a.test_id = t.test_id
                WHERE a.student_id = :1
            """, (uid,))
            data['completed'] = c.fetchall()

        conn.close()

    except Exception as e:
        flash(str(e), 'error')

    return render_template('dashboard.html', data=data)

# ─────────────────────────────────────────
# ADMIN ACTIONS
# ─────────────────────────────────────────
@app.route('/admin/action', methods=['POST'])
@role_required('Admin')
def admin_action():
    action_type = request.form.get('action_type', '')

    try:
        conn = get_connection()
        c = conn.cursor()

        if action_type == 'add_subject':
            name = request.form.get('name')
            desc = request.form.get('desc')
            c.execute(
                "INSERT INTO SUBJECTS(name, description) VALUES (:1, :2)",
                (name, desc)
            )
            flash(f"Subject '{name}' created.", 'success')

        elif action_type == 'delete_subject':
            c.execute(
                "DELETE FROM SUBJECTS WHERE subject_id = :1",
                (request.form['subject_id'],)
            )
            flash("Subject deleted.", 'success')

        elif action_type == 'delete_user':
            c.execute(
                "DELETE FROM USERS WHERE user_id = :1",
                (request.form['user_id'],)
            )
            flash("User deleted.", 'success')

        elif action_type == 'clear_log':
            c.execute("DELETE FROM AUDIT_LOGS")
            flash("Audit log cleared.", 'success')

        conn.commit()
        conn.close()

    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('dashboard'))

# ─────────────────────────────────────────
# INSTRUCTOR ACTIONS
# ─────────────────────────────────────────
@app.route('/instructor/action', methods=['POST'])
@role_required('Instructor')
def inst_action():
    typ = request.form.get('type')

    try:
        conn = get_connection()
        c = conn.cursor()

        if typ == 'test':
            sub_id = request.form.get('sub_id')
            title = request.form.get('title')
            dur = request.form.get('dur')

            new_tid = c.var(oracledb.NUMBER)
            c.callproc("sp_create_test", [
                session['user_id'],
                sub_id,
                title,
                int(dur),
                new_tid
            ])
            conn.commit()
            tid = int(new_tid.getvalue())
            conn.close()

            flash(f"Test '{title}' created! Now add questions below.", 'success')
            return redirect(url_for('manage_test', tid=tid))

        elif typ == 'delete_test':
            c.execute(
                "DELETE FROM TESTS WHERE test_id = :1 AND creator_id = :2",
                (request.form.get('test_id'), session['user_id'])
            )
            flash("Test deleted successfully.", 'success')

        conn.commit()
        conn.close()

    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('dashboard'))

@app.route('/instructor/toggle_test/<int:tid>')
@role_required('Instructor')
def toggle_test(tid):
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute(
            "SELECT is_active FROM TESTS "
            "WHERE test_id = :1 AND creator_id = :2",
            (tid, session['user_id'])
        )
        res = c.fetchone()

        if res:
            new_val = 0 if res[0] == 1 else 1
            if new_val == 1:
                c.execute(
                    "UPDATE TESTS SET is_active = 1, start_time = SYSTIMESTAMP "
                    "WHERE test_id = :1",
                    (tid,)
                )
                flash("Test is now LIVE.", 'success')
            else:
                c.execute(
                    "UPDATE TESTS SET is_active = 0 WHERE test_id = :1",
                    (tid,)
                )
                flash("Test closed.", 'success')

            conn.commit()

        conn.close()

    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('dashboard'))

# ─────────────────────────────────────────
# MANAGE TEST
# ─────────────────────────────────────────
@app.route('/manage/<int:tid>', methods=['GET', 'POST'])
@role_required('Instructor')
def manage_test(tid):
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute(
            "SELECT title, subject_id FROM TESTS "
            "WHERE test_id = :1 AND creator_id = :2",
            (tid, session['user_id'])
        )
        row = c.fetchone()
        if not row:
            flash("Test not found or access denied.", 'error')
            return redirect('/dashboard')

        title, sid = row

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'create_and_add':
                r = request.form
                c.callproc("sp_create_question_and_add", [
                    sid,
                    session['user_id'],
                    r['text'],
                    r['a'],
                    r['b'],
                    r['c'],
                    r['d'],
                    r['ans'],
                    tid
                ])
                conn.commit()
                flash("Question added to test.", 'success')

            elif action == 'add':
                c.execute(
                    "INSERT INTO TEST_QUESTIONS(test_id, question_id, points) "
                    "VALUES (:1, :2, 1)",
                    (tid, request.form['qid'])
                )
                conn.commit()
                flash("Question added.", 'success')

            elif action == 'remove':
                c.execute(
                    "DELETE FROM TEST_QUESTIONS "
                    "WHERE test_id = :1 AND question_id = :2",
                    (tid, request.form['qid'])
                )
                conn.commit()
                flash("Question removed from test.", 'success')

            return redirect(url_for('manage_test', tid=tid))

        # Current questions
        c.execute("""
            SELECT q.question_id, q.text,
                   q.option_a, q.option_b, q.option_c, q.option_d,
                   q.correct_option
            FROM QUESTIONS q
            JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
            WHERE tq.test_id = :1
        """, (tid,))
        current_qs = [
            [row[0], read_db_val(row[1]), row[2], row[3], row[4], row[5], row[6]]
            for row in c.fetchall()
        ]

        # Available questions
        c.execute("""
            SELECT q.question_id, q.text
            FROM QUESTIONS q
            WHERE q.subject_id = :1
            AND q.question_id NOT IN (
                SELECT question_id FROM TEST_QUESTIONS WHERE test_id = :2
            )
        """, (sid, tid))
        avail = [
            [row[0], read_db_val(row[1])]
            for row in c.fetchall()
        ]

        conn.close()
        return render_template(
            'manage.html',
            tid=tid,
            title=title,
            current_qs=current_qs,
            avail=avail
        )

    except Exception as e:
        flash(str(e), 'error')
        return redirect('/dashboard')

# ─────────────────────────────────────────
# TEST ANALYTICS
# ─────────────────────────────────────────
@app.route('/instructor/analytics/<int:tid>')
@role_required('Instructor')
def test_analytics(tid):
    try:
        conn = get_connection()
        c = conn.cursor()

        # Check access and get test details
        c.execute("""
            SELECT title, is_active
            FROM TESTS
            WHERE test_id = :1 AND creator_id = :2
        """, (tid, session['user_id']))
        test_row = c.fetchone()

        if not test_row:
            flash("Test not found or access denied.", 'error')
            return redirect(url_for('dashboard'))

        title, is_active = test_row

        # Get total attempts
        c.execute("SELECT COUNT(*) FROM TEST_ATTEMPTS WHERE test_id = :1", (tid,))
        total_attempts = c.fetchone()[0]

        stats = {
            'total': total_attempts,
            'avg_pct': 0,
            'max_pct': 0,
            'min_pct': 0,
            'pass_count': 0,
            'pass_rate': 0,
            'dist': [0, 0, 0, 0] # 0-25, 26-50, 51-75, 76-100
        }
        
        q_stats = []
        student_results = []

        if total_attempts > 0:
            # Overall Stats
            c.execute("""
                SELECT 
                    AVG(CASE WHEN max_score > 0 THEN (score / max_score) * 100 ELSE 0 END),
                    MAX(CASE WHEN max_score > 0 THEN (score / max_score) * 100 ELSE 0 END),
                    MIN(CASE WHEN max_score > 0 THEN (score / max_score) * 100 ELSE 0 END),
                    SUM(CASE WHEN (CASE WHEN max_score > 0 THEN (score / max_score) * 100 ELSE 0 END) >= 50 THEN 1 ELSE 0 END)
                FROM TEST_ATTEMPTS
                WHERE test_id = :1
            """, (tid,))
            
            # handle case where all entries might be null 
            avg, mx, mn, pass_count = c.fetchone()
            
            stats['avg_pct'] = round(avg, 1) if avg else 0
            stats['max_pct'] = round(mx, 1) if mx else 0
            stats['min_pct'] = round(mn, 1) if mn else 0
            stats['pass_count'] = int(pass_count) if pass_count else 0
            stats['pass_rate'] = round((stats['pass_count'] / total_attempts) * 100, 1) if total_attempts > 0 else 0

            # Score Distribution
            c.execute("""
                SELECT 
                    CASE WHEN max_score > 0 THEN (score / max_score) * 100 ELSE 0 END as pct
                FROM TEST_ATTEMPTS
                WHERE test_id = :1
            """, (tid,))
            
            for row in c.fetchall():
                pct = row[0]
                if pct <= 25:
                    stats['dist'][0] += 1
                elif pct <= 50:
                    stats['dist'][1] += 1
                elif pct <= 75:
                    stats['dist'][2] += 1
                else:
                    stats['dist'][3] += 1

            # Question Breakdown
            c.execute("""
                SELECT 
                    q.question_id, 
                    q.text, 
                    q.option_a, q.option_b, q.option_c, q.option_d, q.correct_option,
                    (SELECT COUNT(*) FROM STUDENT_ANSWERS sa 
                     JOIN TEST_ATTEMPTS ta ON sa.attempt_id = ta.attempt_id 
                     WHERE sa.question_id = q.question_id AND ta.test_id = :1) as attempts,
                    (SELECT COUNT(*) FROM STUDENT_ANSWERS sa 
                     JOIN TEST_ATTEMPTS ta ON sa.attempt_id = ta.attempt_id 
                     WHERE sa.question_id = q.question_id AND ta.test_id = :2 AND sa.is_correct = 1) as correct_qty
                FROM QUESTIONS q
                JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
                WHERE tq.test_id = :3
            """, (tid, tid, tid))
            
            idx = 1
            for row in c.fetchall():
                qid, text, oa, ob, oc, od, correct, qs_attempts, qs_correct = row
                
                text_str = read_db_val(text)
                
                accuracy = round((qs_correct / qs_attempts) * 100, 1) if qs_attempts > 0 else 0
                
                q_stats.append({
                    'num': idx,
                    'text': text_str,
                    'opt_a': oa,
                    'opt_b': ob,
                    'opt_c': oc,
                    'opt_d': od,
                    'correct': correct,
                    'attempts': qs_attempts,
                    'correct_count': qs_correct,
                    'accuracy': accuracy
                })
                idx += 1
                
            # Sort by accuracy (lowest first to show hardest)
            q_stats.sort(key=lambda x: x['accuracy'])

            # Individual Results
            c.execute("""
                SELECT 
                    u.full_name, 
                    u.username,
                    ta.score, 
                    ta.max_score,
                    CASE WHEN ta.max_score > 0 THEN ROUND((ta.score / ta.max_score) * 100, 1) ELSE 0 END
                FROM TEST_ATTEMPTS ta
                JOIN USERS u ON ta.student_id = u.user_id
                WHERE ta.test_id = :1
                ORDER BY ta.score DESC
            """, (tid,))
            student_results = c.fetchall()

        conn.close()
        
        return render_template(
            'test_analytics.html',
            title=title,
            is_active=is_active,
            stats=stats,
            q_stats=q_stats,
            student_results=student_results
        )

    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('dashboard'))

# ─────────────────────────────────────────
# STUDENT TEST TAKING
# ─────────────────────────────────────────
@app.route('/test/<int:tid>', methods=['GET', 'POST'])
@role_required('Student')
def test_view(tid):
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            SELECT t.title, t.duration_minutes, t.subject_id,
                   GREATEST(
                       1,
                       FLOOR(
                           (CAST(t.start_time AS DATE) +
                           t.duration_minutes/1440 - SYSDATE) * 86400
                       )
                   ) AS remaining_secs
            FROM TESTS t
            WHERE t.test_id = :1
            AND t.is_active = 1
            AND SYSDATE <=
                CAST(t.start_time AS DATE) + t.duration_minutes/1440
        """, (tid,))
        test_row = c.fetchone()

        if not test_row:
            flash("Test not found or expired.", 'error')
            return redirect('/dashboard')

        test_title, duration, test_sid, remaining_secs = test_row

        c.execute(
            "SELECT name FROM SUBJECTS WHERE subject_id = :1",
            (test_sid,)
        )
        subject_name = c.fetchone()[0]

        if request.method == 'POST':
            c.execute("""
                SELECT q.question_id, q.correct_option
                FROM QUESTIONS q
                JOIN TEST_QUESTIONS tq
                ON q.question_id = tq.question_id
                WHERE tq.test_id = :1
            """, (tid,))
            ans_map = {row[0]: row[1].strip().upper() for row in c.fetchall()}
            max_score = len(ans_map)

            attempt_id_var = c.var(oracledb.NUMBER)
            c.callproc("sp_create_test_attempt", [
                tid,
                session['user_id'],
                max_score,
                attempt_id_var
            ])
            conn.commit()
            aid = int(attempt_id_var.getvalue())

            score = 0
            for qid, correct in ans_map.items():
                selected = request.form.get(f'q_{qid}', '').strip().upper()
                is_correct = 1 if selected == correct else 0
                if selected:
                    score += is_correct
                    c.execute("""
                        INSERT INTO STUDENT_ANSWERS
                        (attempt_id, question_id, selected_option, is_correct)
                        VALUES (:1, :2, :3, :4)
                    """, (aid, qid, selected, is_correct))

            c.callproc("sp_update_test_score", [aid, score])
            conn.commit()
            conn.close()

            flash(f"Test submitted! You scored {score} out of {max_score}.", 'success')
            return redirect(url_for('dashboard'))

        c.execute("""
            SELECT q.question_id, q.text,
                   q.option_a, q.option_b, q.option_c, q.option_d
            FROM QUESTIONS q
            JOIN TEST_QUESTIONS tq
            ON q.question_id = tq.question_id
            WHERE tq.test_id = :1
        """, (tid,))
        qs = [
            [row[0], read_db_val(row[1]), row[2], row[3], row[4], row[5]]
            for row in c.fetchall()
        ]

        conn.close()
        info = (test_title, duration, subject_name, int(remaining_secs))
        return render_template('test.html', tid=tid, info=info, qs=qs)

    except Exception as e:
        flash(str(e), 'error')
        return redirect('/dashboard')

# ─────────────────────────────────────────
# APP ENTRY POINT
# ─────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)