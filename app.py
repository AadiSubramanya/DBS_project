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
            if 'user_id' not in session or session.get('role') != role_name:
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
    except: pass

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        try:
            conn = get_connection(); c = conn.cursor()
            c.execute("SELECT user_id, role, full_name, password_hash FROM USERS WHERE username = :1", (u,))
            usr = c.fetchone()
            if usr and usr[3] == p:
                session.update({'user_id': usr[0], 'role': usr[1], 'full_name': usr[2]})
                log_audit(usr[0], "Logged in")
                flash(f"Welcome, {usr[2]}!")
                return redirect(url_for('dashboard'))
            flash("Invalid credentials")
        except Exception as e: flash(str(e))
    return render_template('auth.html', title="Login", is_register=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        r = request.form
        try:
            conn = get_connection(); c = conn.cursor()
            c.execute("INSERT INTO USERS(username, password_hash, full_name, role, email) VALUES (:1, :2, :3, :4, :5)",
                      (r['username'], r['password'], r['full_name'], r['role'], r['email']))
            conn.commit()
            flash("Registered successfully!")
            return redirect(url_for('login'))
        except Exception as e: flash(str(e))
    return render_template('auth.html', title="Register", is_register=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/login')
    role, uid = session['role'], session['user_id']
    data = {}
    try:
        conn = get_connection()
        c = conn.cursor()
        if role == 'Admin':
            # Fetch users to replicate the "old manage users" feel directly on the dash
            c.execute("SELECT user_id, username, full_name, role, email FROM USERS ORDER BY user_id")
            data['users'] = c.fetchall()
            
            # Fetch all tables for the Master Database Explorer
            tables = ['USERS', 'SUBJECTS', 'AUDIT_LOGS', 'QUESTIONS', 'TESTS', 'TEST_QUESTIONS', 'TEST_ATTEMPTS', 'STUDENT_ANSWERS']
            db_view = {}
            for t in tables:
                try:
                    c.execute(f"SELECT column_name FROM user_tab_columns WHERE table_name = '{t}' ORDER BY column_id")
                    cols = [col[0] for col in c.fetchall()]
                    c.execute(f"SELECT * FROM {t}")
                    db_view[t] = {'cols': cols, 'rows': c.fetchall()}
                except: db_view[t] = {'cols': [], 'rows': []}
            data['db_view'] = db_view
            
            # Legacy counts and logs
            for key, query in [('u_cnt', "SELECT COUNT(*) FROM USERS"), 
                               ('t_cnt', "SELECT COUNT(*) FROM TESTS"),
                               ('logs', "SELECT action, timestamp FROM AUDIT_LOGS ORDER BY timestamp DESC FETCH FIRST 50 ROWS ONLY"),
                               ('subjects', "SELECT name, description FROM SUBJECTS ORDER BY name")]:
                try:
                    c.execute(query)
                    data[key] = c.fetchone()[0] if 'COUNT' in query else c.fetchall()
                except Exception:
                    data[key] = 0 if 'COUNT' in query else []
        elif role == 'Instructor':
            c.execute("SELECT subject_id, name FROM SUBJECTS")
            data['subjects'] = c.fetchall()
            c.execute("SELECT test_id, title, duration_minutes FROM TESTS WHERE creator_id=:1", (uid,))
            data['tests'] = c.fetchall()
            c.execute("SELECT q.text, s.name FROM QUESTIONS q JOIN SUBJECTS s ON q.subject_id=s.subject_id WHERE instructor_id=:1", (uid,))
            data['questions'] = c.fetchall()
        else: # Student
            c.execute("SELECT test_id, title, duration_minutes FROM TESTS WHERE is_active=1 AND test_id NOT IN (SELECT test_id FROM TEST_ATTEMPTS WHERE student_id=:1)", (uid,))
            data['available'] = c.fetchall()
            c.execute("SELECT t.title, a.score, a.max_score FROM TEST_ATTEMPTS a JOIN TESTS t ON a.test_id=t.test_id WHERE a.student_id=:1", (uid,))
            data['completed'] = c.fetchall()
        conn.close()
    except Exception as e: flash(str(e))
    return render_template('dashboard.html', data=data)

@app.route('/admin/action', methods=['POST'])
@role_required('Admin')
def admin_action():
    action_type = request.form.get('action_type', 'add_subject')
    try:
        conn = get_connection()
        c = conn.cursor()
        if action_type == 'add_subject':
            c.execute("INSERT INTO SUBJECTS(name, description) VALUES (:1, :2)", (request.form['name'], request.form['desc']))
        elif action_type == 'delete_subject':
            c.execute("DELETE FROM SUBJECTS WHERE subject_id = :1", (request.form['subject_id'],))
        elif action_type == 'delete_user':
            c.execute("DELETE FROM USERS WHERE user_id = :1", (request.form['user_id'],))
        conn.commit()
    except Exception as e: flash(str(e))
    return redirect('/dashboard')

@app.route('/instructor/action', methods=['POST'])
@role_required('Instructor')
def inst_action():
    typ = request.form.get('type')
    try:
        conn = get_connection()
        c = conn.cursor()
        if typ == 'question':
            r = request.form
            c.execute("INSERT INTO QUESTIONS(subject_id, instructor_id, text, option_a, option_b, option_c, option_d, correct_option, difficulty, status) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,'Approved')",
                      (r['sub_id'], session['user_id'], r['text'], r['A'], r['B'], r['C'], r['D'], r['ans'], r['diff']))
        elif typ == 'test':
            c.execute("INSERT INTO TESTS(creator_id, title, duration_minutes) VALUES (:1,:2,:3)", (session['user_id'], request.form['title'], request.form['dur']))
        conn.commit()
    except Exception as e: flash(str(e))
    return redirect('/dashboard')

@app.route('/manage/<int:tid>', methods=['GET', 'POST'])
@role_required('Instructor')
def manage_test(tid):
    try:
        conn = get_connection()
        c = conn.cursor()
        if request.method == 'POST':
            c.execute("INSERT INTO TEST_QUESTIONS(test_id, question_id, points) VALUES (:1, :2, 1)", (tid, request.form['qid']))
            conn.commit()
        c.execute("SELECT title FROM TESTS WHERE test_id=:1", (tid,))
        title = c.fetchone()[0]
        c.execute("SELECT q.question_id, q.text FROM QUESTIONS q WHERE q.question_id NOT IN (SELECT question_id FROM TEST_QUESTIONS WHERE test_id=:1)", (tid,))
        avail = c.fetchall()
        c.execute("SELECT u.username, a.score, a.max_score FROM TEST_ATTEMPTS a JOIN USERS u ON a.student_id=u.user_id WHERE a.test_id=:1", (tid,))
        results = c.fetchall()
        conn.close()
        return render_template('manage.html', tid=tid, title=title, avail=avail, results=results)
    except Exception as e:
        flash(str(e))
        return redirect('/dashboard')

@app.route('/test/<int:tid>', methods=['GET', 'POST'])
@role_required('Student')
def test_view(tid):
    conn = get_connection()
    c = conn.cursor()
    if request.method == 'POST':
        try:
            c.execute("SELECT q.question_id, q.correct_option FROM QUESTIONS q JOIN TEST_QUESTIONS tq ON q.question_id=tq.question_id WHERE tq.test_id=:1", (tid,))
            ans_map = {row[0]: row[1].strip() for row in c.fetchall()}
            score, mx = 0, len(ans_map)
            
            c.execute("INSERT INTO TEST_ATTEMPTS(test_id, student_id, max_score) VALUES (:1,:2,:3)", (tid, session['user_id'], mx))
            c.execute("SELECT attempt_id FROM TEST_ATTEMPTS WHERE test_id=:1 AND student_id=:2 ORDER BY attempt_id DESC FETCH FIRST 1 ROWS ONLY", (tid, session['user_id']))
            aid = c.fetchone()[0]
            
            for qid, correct in ans_map.items():
                sel = request.form.get(f'q_{qid}')
                if sel == correct: score += 1
                if sel: c.execute("INSERT INTO STUDENT_ANSWERS(attempt_id, question_id, selected_option, is_correct) VALUES (:1,:2,:3,:4)", (aid, qid, sel, 1 if sel==correct else 0))
            
            c.execute("UPDATE TEST_ATTEMPTS SET score=:1 WHERE attempt_id=:2", (score, aid))
            conn.commit()
            log_audit(session['user_id'], f"Completed test {tid}")
            flash(f"Scored {score}/{mx}!")
            return redirect('/dashboard')
        except Exception as e: flash(str(e))

    try:
        c.execute("SELECT title, duration_minutes FROM TESTS WHERE test_id=:1", (tid,))
        tinfo = c.fetchone()
        c.execute("SELECT q.question_id, q.text, q.option_a, q.option_b, q.option_c, q.option_d FROM QUESTIONS q JOIN TEST_QUESTIONS tq ON q.question_id=tq.question_id WHERE tq.test_id=:1", (tid,))
        qs = c.fetchall()
        conn.close()
        return render_template('test.html', tid=tid, info=tinfo, qs=qs)
    except Exception as e:
        flash(str(e))
        return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True, port=5000)