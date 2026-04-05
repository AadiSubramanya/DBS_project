from flask import Flask, render_template, request, session, flash, redirect, url_for
from db_config import get_connection
import oracledb
from functools import wraps

app = Flask(__name__)
app.secret_key = "dev_secret"

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') != role_name:
                flash(f"Unauthorized. {role_name} access required.")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_audit(user_id, action):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO AUDIT_LOGS(user_id, action) VALUES (:1, :2)", (user_id, action))
        conn.commit()
        conn.close()
    except:
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
        u, p = request.form.get('username'), request.form.get('password')
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT user_id, role, full_name, password_hash FROM USERS WHERE username = :1", (u,))
            usr = c.fetchone()
            conn.close()
            if usr and usr[3] == p:
                session.update({'user_id': usr[0], 'role': usr[1], 'full_name': usr[2]})
                log_audit(usr[0], "Logged in")
                return redirect(url_for('dashboard'))
            flash("Invalid username or password.")
        except Exception as e:
            flash(str(e))
    return render_template('auth.html', title="Login", is_register=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        r = request.form
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "INSERT INTO USERS(username, password_hash, full_name, role, email) VALUES (:1, :2, :3, :4, :5)",
                (r['username'], r['password'], r['full_name'], r['role'], r['email'])
            )
            conn.commit()
            conn.close()
            flash("Registered successfully! Please log in.")
            return redirect(url_for('login'))
        except Exception as e:
            flash(str(e))
    return render_template('auth.html', title="Register", is_register=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────
# DATABASE MIGRATION TOOL
# ─────────────────────────────────────────

@app.route('/fix_database')
def fix_database():
    """Adds missing columns to existing tables without losing data."""
    msgs = []
    try:
        conn = get_connection()
        c = conn.cursor()
        # Add subject_id to TESTS if missing
        try:
            c.execute("ALTER TABLE TESTS ADD subject_id NUMBER REFERENCES SUBJECTS(subject_id) ON DELETE SET NULL")
            conn.commit()
            msgs.append("Added subject_id to TESTS.")
        except oracledb.DatabaseError as e:
            if "00957" in str(e) or "already used" in str(e):
                msgs.append("subject_id already exists in TESTS.")
            else:
                msgs.append(f"TESTS alter error: {e}")
        # Add is_active to TESTS if missing
        try:
            c.execute("ALTER TABLE TESTS ADD is_active NUMBER DEFAULT 0 NOT NULL")
            conn.commit()
            msgs.append("Added is_active to TESTS.")
        except oracledb.DatabaseError as e:
            if "00957" in str(e) or "already used" in str(e):
                msgs.append("is_active already exists in TESTS.")
            else:
                msgs.append(f"is_active alter error: {e}")
        conn.close()
    except Exception as e:
        msgs.append(f"Connection error: {e}")
    flash(" | ".join(msgs))
    return redirect(url_for('dashboard'))

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role, uid = session['role'], session['user_id']
    data = {}
    try:
        conn = get_connection()
        c = conn.cursor()

        if role == 'Admin':
            c.execute("SELECT user_id, username, full_name, role, email FROM USERS ORDER BY user_id")
            data['users'] = c.fetchall()

            try:
                c.execute("SELECT subject_id, name, description FROM SUBJECTS ORDER BY name")
                data['subjects_list'] = c.fetchall()
            except:
                data['subjects_list'] = []

            try:
                c.execute("SELECT COUNT(*) FROM USERS")
                data['u_cnt'] = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM TESTS")
                data['t_cnt'] = c.fetchone()[0]
            except:
                data['u_cnt'] = 0
                data['t_cnt'] = 0

            tables = ['USERS', 'SUBJECTS', 'QUESTIONS', 'TESTS', 'TEST_QUESTIONS', 'TEST_ATTEMPTS', 'STUDENT_ANSWERS', 'AUDIT_LOGS']
            db_view = {}
            for t in tables:
                try:
                    c.execute(f"SELECT column_name FROM user_tab_columns WHERE table_name = '{t}' ORDER BY column_id")
                    cols = [col[0] for col in c.fetchall()]
                    c.execute(f"SELECT * FROM {t}")
                    rows = c.fetchall()

                    processed_rows = []
                    for row in rows:
                        new_row = []
                        for val in row:
                            if hasattr(val, "read"):   # this is a LOB (CLOB/BLOB)
                                try:
                                    new_row.append(val.read())
                                except:
                                    new_row.append(str(val))
                            else:
                                new_row.append(val)
                        processed_rows.append(new_row)

                    db_view[t] = {'cols': cols, 'rows': processed_rows}
                except:
                    db_view[t] = {'cols': [], 'rows': []}
            data['db_view'] = db_view

        elif role == 'Instructor':
            try:
                c.execute("SELECT subject_id, name FROM SUBJECTS ORDER BY name")
                data['subjects'] = c.fetchall()
            except:
                data['subjects'] = []

            try:
                c.execute("""
                    SELECT t.test_id, t.title, t.duration_minutes, s.name, t.is_active
                    FROM TESTS t
                    LEFT JOIN SUBJECTS s ON t.subject_id = s.subject_id
                    WHERE t.creator_id = :1
                    ORDER BY t.test_id DESC
                """, (uid,))
                data['tests'] = c.fetchall()
            except:
                data['tests'] = []

        else:  # Student
            try:
                c.execute("""
                    SELECT t.test_id, t.title, t.duration_minutes, s.name
                    FROM TESTS t
                    LEFT JOIN SUBJECTS s ON t.subject_id = s.subject_id
                    WHERE t.is_active = 1
                    AND t.test_id NOT IN (
                        SELECT test_id FROM TEST_ATTEMPTS WHERE student_id = :1
                    )
                """, (uid,))
                data['available'] = c.fetchall()
            except:
                data['available'] = []

            try:
                c.execute("""
                    SELECT t.title, a.score, a.max_score
                    FROM TEST_ATTEMPTS a
                    JOIN TESTS t ON a.test_id = t.test_id
                    WHERE a.student_id = :1
                """, (uid,))
                data['completed'] = c.fetchall()
            except:
                data['completed'] = []

        conn.close()
    except Exception as e:
        flash(str(e))
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
            name = request.form.get('name', '').strip()
            desc = request.form.get('desc', '').strip()
            if not name:
                flash("Subject name is required.")
                return redirect('/dashboard')
            c.execute("INSERT INTO SUBJECTS(name, description) VALUES (:1, :2)", (name, desc))
            flash(f"Subject '{name}' created.")
        elif action_type == 'delete_subject':
            c.execute("DELETE FROM SUBJECTS WHERE subject_id = :1", (request.form['subject_id'],))
            flash("Subject deleted.")
        elif action_type == 'delete_user':
            c.execute("DELETE FROM USERS WHERE user_id = :1", (request.form['user_id'],))
            flash("User deleted.")
        conn.commit()
        conn.close()
    except Exception as e:
        flash(str(e))
    return redirect('/dashboard')

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
            title  = request.form.get('title', '').strip()
            dur    = request.form.get('dur')
            if not sub_id or not title or not dur:
                flash("All fields required to create a test.")
                return redirect('/dashboard')
            c.execute(
                "INSERT INTO TESTS(creator_id, subject_id, title, duration_minutes, is_active) VALUES (:1,:2,:3,:4,0)",
                (session['user_id'], sub_id, title, dur)
            )
            c.execute("SELECT MAX(test_id) FROM TESTS WHERE creator_id = :1", (session['user_id'],))
            new_tid = c.fetchone()[0]
            conn.commit()
            conn.close()
            flash(f"Test '{title}' created! Now add questions below.")
            return redirect(url_for('manage_test', tid=new_tid))
        conn.commit()
        conn.close()
    except Exception as e:
        flash(str(e))
    return redirect('/dashboard')

@app.route('/instructor/toggle_test/<int:tid>')
@role_required('Instructor')
def toggle_test(tid):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT is_active FROM TESTS WHERE test_id = :1 AND creator_id = :2", (tid, session['user_id']))
        res = c.fetchone()
        if res is None:
            flash("Test not found.")
        else:
            new_val = 0 if res[0] == 1 else 1
            c.execute("UPDATE TESTS SET is_active = :1 WHERE test_id = :2", (new_val, tid))
            conn.commit()
            flash("Test is now LIVE." if new_val == 1 else "Test closed.")
        conn.close()
    except Exception as e:
        flash(str(e))
    return redirect('/dashboard')

# ─────────────────────────────────────────
# MANAGE TEST (Instructor)
# ─────────────────────────────────────────

@app.route('/manage/<int:tid>', methods=['GET', 'POST'])
@role_required('Instructor')
def manage_test(tid):
    try:
        conn = get_connection()
        c = conn.cursor()

        # Fetch test info
        c.execute("SELECT title, subject_id FROM TESTS WHERE test_id = :1 AND creator_id = :2", (tid, session['user_id']))
        row = c.fetchone()
        if row is None:
            flash("Test not found or access denied.")
            return redirect('/dashboard')
        title, sid = row[0], row[1]

        if request.method == 'POST':
            action = request.form.get('action', '')

            if action == 'create_and_add':
                # Author a brand-new question and immediately link it
                r = request.form
                c.execute(
                    "INSERT INTO QUESTIONS(subject_id, instructor_id, text, option_a, option_b, option_c, option_d, correct_option, status) "
                    "VALUES (:1,:2,:3,:4,:5,:6,:7,:8,'Approved')",
                    (sid, session['user_id'], r['text'], r['a'], r['b'], r['c'], r['d'], r['ans'].strip().upper())
                )
                c.execute("SELECT MAX(question_id) FROM QUESTIONS WHERE instructor_id = :1", (session['user_id'],))
                qid = c.fetchone()[0]
                c.execute("INSERT INTO TEST_QUESTIONS(test_id, question_id, points) VALUES (:1, :2, 1)", (tid, qid))
                conn.commit()
                flash("Question added to test.")

            elif action == 'add':
                # Add an existing bank question
                c.execute("INSERT INTO TEST_QUESTIONS(test_id, question_id, points) VALUES (:1, :2, 1)", (tid, request.form['qid']))
                conn.commit()
                flash("Question added.")

            elif action == 'remove':
                # Remove a question from the test (does NOT delete from bank)
                c.execute("DELETE FROM TEST_QUESTIONS WHERE test_id = :1 AND question_id = :2", (tid, request.form['qid']))
                conn.commit()
                flash("Question removed from test.")

            return redirect(url_for('manage_test', tid=tid))

        # Load page data
        # Questions already in this test
        c.execute("""
            SELECT q.question_id, q.text, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_option
            FROM QUESTIONS q
            JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
            WHERE tq.test_id = :1
        """, (tid,))
        current_qs = c.fetchall()

        # Questions in bank (same subject) but NOT yet in this test
        c.execute("""
            SELECT q.question_id, q.text
            FROM QUESTIONS q
            WHERE q.subject_id = :1
            AND q.question_id NOT IN (SELECT question_id FROM TEST_QUESTIONS WHERE test_id = :2)
        """, (sid, tid))
        avail = c.fetchall()

        # Student results analytics
        c.execute("""
            SELECT u.username, a.score, a.max_score, a.start_time
            FROM TEST_ATTEMPTS a
            JOIN USERS u ON a.student_id = u.user_id
            WHERE a.test_id = :1
            ORDER BY a.start_time DESC
        """, (tid,))
        results = c.fetchall()

        conn.close()
        return render_template('manage.html', tid=tid, title=title, current_qs=current_qs, avail=avail, results=results)

    except Exception as e:
        flash(str(e))
        return redirect('/dashboard')

# ─────────────────────────────────────────
# STUDENT TEST TAKING
# ─────────────────────────────────────────

@app.route('/test/<int:tid>', methods=['GET', 'POST'])
@role_required('Student')
def test_view(tid):
    try:
        conn = get_connection()
        c = conn.cursor()

        # Verify test is live
        c.execute("SELECT title, duration_minutes, subject_id FROM TESTS WHERE test_id = :1 AND is_active = 1", (tid,))
        test_row = c.fetchone()
        if test_row is None:
            flash("Test not found or not active.")
            conn.close()
            return redirect('/dashboard')

        test_title, duration, test_sid = test_row

        # Get subject name
        subject_name = 'General'
        try:
            c.execute("SELECT name FROM SUBJECTS WHERE subject_id = :1", (test_sid,))
            srow = c.fetchone()
            if srow:
                subject_name = srow[0]
        except:
            pass

        if request.method == 'POST':
            # Fetch all questions + correct answers for this test
            c.execute("""
                SELECT q.question_id, q.correct_option
                FROM QUESTIONS q
                JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
                WHERE tq.test_id = :1
            """, (tid,))
            ans_map = {row[0]: row[1].strip().upper() for row in c.fetchall()}
            max_score = len(ans_map)

            # Insert the attempt row first
            c.execute(
                "INSERT INTO TEST_ATTEMPTS(test_id, student_id, score, max_score) VALUES (:1, :2, 0, :3)",
                (tid, session['user_id'], max_score)
            )
            conn.commit()

            # Fetch the attempt_id we just created
            c.execute(
                "SELECT MAX(attempt_id) FROM TEST_ATTEMPTS WHERE test_id = :1 AND student_id = :2",
                (tid, session['user_id'])
            )
            aid = c.fetchone()[0]

            # Score and save answers
            score = 0
            for qid, correct in ans_map.items():
                selected = request.form.get(f'q_{qid}', '').strip().upper()
                is_correct = 1 if selected == correct else 0
                if selected:
                    score += is_correct
                    c.execute(
                        "INSERT INTO STUDENT_ANSWERS(attempt_id, question_id, selected_option, is_correct) VALUES (:1,:2,:3,:4)",
                        (aid, qid, selected, is_correct)
                    )

            # Update the final score
            c.execute("UPDATE TEST_ATTEMPTS SET score = :1 WHERE attempt_id = :2", (score, aid))
            conn.commit()
            conn.close()
            log_audit(session['user_id'], f"Completed test {tid}, scored {score}/{max_score}")
            flash(f"Test submitted! You scored {score} out of {max_score}.")
            return redirect(url_for('dashboard'))

        # GET: show the test questions
        c.execute("""
            SELECT q.question_id, q.text, q.option_a, q.option_b, q.option_c, q.option_d
            FROM QUESTIONS q
            JOIN TEST_QUESTIONS tq ON q.question_id = tq.question_id
            WHERE tq.test_id = :1
        """, (tid,))
        qs = c.fetchall()
        conn.close()

        info = (test_title, duration, subject_name)
        return render_template('test.html', tid=tid, info=info, qs=qs)

    except Exception as e:
        flash(str(e))
        return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True, port=5000)