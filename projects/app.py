from flask import Flask, request, render_template
import mysql.connector
import bcrypt

app = Flask(__name__)

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",  # no password
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
                return "<h1>Login Successful</h1>"
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
            cursor.execute("INSERT INTO Student (id, name, mail, group_id, cred_count, curr_sem) VALUES (%s,%s,%s,Null,0,0)",
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

if __name__ == "__main__":

    app.run(debug=True)
