from flask import Flask, render_template, request, session, flash, redirect, url_for
from db_config import get_connection
import oracledb

app = Flask(__name__)
app.secret_key = "dev_secret"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # In a secure app, use password hashing here
            cursor.execute("SELECT user_id, role, full_name, password_hash FROM USERS WHERE username = :u", u=username)
            user_data = cursor.fetchone()
            
            if user_data and user_data[3] == password:
                session['user_id'] = user_data[0]
                session['role'] = user_data[1]
                session['full_name'] = user_data[2]
                flash(f"Welcome back, {user_data[2]}!")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid Username or Password")
        except oracledb.Error as e:
            flash(f"Database Error: {e}")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        role = request.form.get('role')
        
        if role not in ['Admin', 'Instructor', 'Student']:
            flash("Invalid role selected.")
            return redirect(url_for('register'))
            
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Simple plaintext insert because we bypassed werkzeug per guidelines
            cursor.execute("""
                INSERT INTO USERS (username, password_hash, full_name, role, email) 
                VALUES (:1, :2, :3, :4, :5)
            """, (username, password, full_name, role, email))
            
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
            
        except oracledb.IntegrityError:
            flash("Username or Email already exists!")
        except oracledb.Error as e:
            flash(f"Database Error: {e}")
            
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))
        
    return render_template('dashboard.html', role=session['role'])

@app.route('/admin/users')
def manage_users():
    if session.get('role') != 'Admin':
        flash("Unauthorized access! Admins only.")
        return redirect(url_for('dashboard'))
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Fetching all users
        cursor.execute("SELECT user_id, username, full_name, role, email FROM USERS ORDER BY user_id")
        users = cursor.fetchall()
        return render_template('manage_users.html', users=users)
    except oracledb.Error as e:
        flash(f"Database Error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/test')
def test():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('test.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)