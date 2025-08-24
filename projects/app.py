from flask import Flask, request, render_template, session, redirect, url_for
import mysql.connector
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # random key for sessions

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",  
        database="cse_370_project"
    )

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("login.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    role = request.form.get("role")  
    user_id = request.form.get("id")
    password = request.form.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if role == "student":
            cursor.execute("SELECT pass FROM StudentPass WHERE stu_id = %s", (user_id,))
        elif role == "faculty":
            cursor.execute("SELECT pass FROM FacultyPass WHERE fac_id = %s", (user_id,))
        elif role == "admin":
            cursor.execute("SELECT pass FROM Admin WHERE id = %s", (user_id,))
        else:
            return "Invalid role selected"

        row = cursor.fetchone()
        if row:
            hashed_pass = row["pass"].encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), hashed_pass):
                session['user_id'] = user_id
                session['role'] = role
                return redirect(url_for('dashboard'))
        return "<h1>Wrong ID or Password</h1>"

    finally:
        cursor.close()
        conn.close()

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["POST"])
def signup():
    role = request.form.get("role")
    user_id = request.form.get("id")
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        if role == "student":
            cursor.execute("INSERT INTO Student (id, name, mail, group_id, cred_count, curr_sem) VALUES (%s,%s,%s,NULL,0,0)",
                           (user_id, name, email))
            cursor.execute("INSERT INTO StudentPass (stu_id, pass) VALUES (%s, %s)", (user_id, hashed))

        elif role == "faculty":
            cursor.execute("INSERT INTO Faculty (id, name, mail, slot_available, status) VALUES (%s,%s,%s,1,1)",
                           (user_id, name, email))
            cursor.execute("INSERT INTO FacultyPass (fac_id, pass) VALUES (%s, %s)", (user_id, hashed))

        elif role == "admin":
            cursor.execute("INSERT INTO Admin (id, pass, name, mail) VALUES (%s,%s,%s,%s)",
                           (user_id, hashed, name, email))
        else:
            return "Invalid role selected"

        conn.commit()
        return "<h1>Signup Successful</h1>"

    except mysql.connector.Error as err:
        return f"<h1>Error: {err}</h1>"

    finally:
        cursor.close()
        conn.close()

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login_page'))
    role = session['role']
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    # Placeholder for student/faculty dashboards (expand as needed)
    return f"<h1>Welcome, {role.capitalize()} {session['user_id']}</h1><a href='/logout'>Logout</a>"

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login_page'))

    search_id = request.form.get("search_id", "") if request.method == "POST" else ""
    users = []  # combined list of students and faculty

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # fetch students
        if search_id:
            cursor.execute("SELECT id, name, mail, 'student' as role FROM Student WHERE id LIKE %s", (f"{search_id}",))
        else:
            cursor.execute("SELECT id, name, mail, 'student' as role FROM Student")
        students = cursor.fetchall()
        users.extend(students)

        # fetch faculty
        if search_id:
            cursor.execute("SELECT id, name, mail, 'faculty' as role FROM Faculty WHERE id LIKE %s", (f"{search_id}",))
        else:
            cursor.execute("SELECT id, name, mail, 'faculty' as role FROM Faculty")
        faculty = cursor.fetchall()
        users.extend(faculty)

    finally:
        cursor.close()
        conn.close()

    return render_template("admin_dashboard.html", users=users, search_id=search_id)

# ---------------- EDIT PASSWORD ----------------
@app.route("/edit_password/<user_role>/<user_id>", methods=["GET", "POST"])
def edit_password(user_role, user_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login_page'))

    if request.method == "POST":
        new_password = request.form.get("new_password")
        if new_password:
            hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                if user_role == "student":
                    cursor.execute("UPDATE StudentPass SET pass = %s WHERE stu_id = %s", (hashed, user_id))
                elif user_role == "faculty":
                    cursor.execute("UPDATE FacultyPass SET pass = %s WHERE fac_id = %s", (hashed, user_id))
                conn.commit()
                return redirect(url_for('admin_dashboard'))
            except mysql.connector.Error as err:
                return f"<h1>Error: {err}</h1>"
            finally:
                cursor.close()
                conn.close()

    return render_template("edit_password.html", user_role=user_role, user_id=user_id)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)

