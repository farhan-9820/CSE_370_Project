from flask import Flask, request, render_template, session, redirect, url_for
import mysql.connector
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random key for sessions

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
    elif role == 'student':
        return redirect(url_for('student_dashboard'))
    elif role == 'faculty':
        return redirect(url_for('faculty_dashboard'))
    return f"<h1>Welcome, {role.capitalize()} {session['user_id']}</h1><a href='/logout'>Logout</a>"

# ---------------- STUDENT DASHBOARD / PROFILE ----------------
@app.route("/student_dashboard", methods=["GET", "POST"])
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch profile data
        cursor.execute("SELECT id, name, mail, curr_sem, group_id FROM Student WHERE id = %s", (user_id,))
        profile = cursor.fetchone()

        # Fetch interests
        cursor.execute("SELECT interest FROM StudentInterests WHERE stu_id = %s", (user_id,))
        interests = [row['interest'] for row in cursor.fetchall()]

        # Fetch links
        cursor.execute("SELECT link FROM StudentLinks WHERE stu_id = %s", (user_id,))
        links = [row['link'] for row in cursor.fetchall()]

        if request.method == "POST":
            if 'add_interest' in request.form:
                interest = request.form.get("interest")
                if interest:
                    cursor.execute("INSERT INTO StudentInterests (stu_id, interest) VALUES (%s, %s)", (user_id, interest))
                    conn.commit()
            elif 'add_link' in request.form:
                link = request.form.get("link")
                if link:
                    cursor.execute("INSERT INTO StudentLinks (stu_id, link) VALUES (%s, %s)", (user_id, link))
                    conn.commit()
            return redirect(url_for('student_dashboard'))

    finally:
        cursor.close()
        conn.close()

    return render_template("student_profile.html", profile=profile, interests=interests, links=links, is_own=True)

# ---------------- EDIT STUDENT PROFILE ----------------
@app.route("/edit_student_profile", methods=["GET", "POST"])
def edit_student_profile():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch current data
        cursor.execute("SELECT id, name, mail, curr_sem FROM Student WHERE id = %s", (user_id,))
        profile = cursor.fetchone()

        cursor.execute("SELECT interest FROM StudentInterests WHERE stu_id = %s", (user_id,))
        interests = [row['interest'] for row in cursor.fetchall()]

        cursor.execute("SELECT link FROM StudentLinks WHERE stu_id = %s", (user_id,))
        links = [row['link'] for row in cursor.fetchall()]

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            curr_sem = request.form.get("curr_sem")

            # Update basic profile
            cursor.execute("UPDATE Student SET name = %s, mail = %s, curr_sem = %s WHERE id = %s",
                          (name, email, curr_sem, user_id))

            # Delete selected interests
            delete_interests = request.form.getlist("delete_interests")
            for interest in delete_interests:
                cursor.execute("DELETE FROM StudentInterests WHERE stu_id = %s AND interest = %s", (user_id, interest))

            # Update interests (if any)
            update_interests = request.form.getlist("update_interests")
            original_interests = request.form.getlist("original_interests")
            for orig, new in zip(original_interests, update_interests):
                if orig != new:
                    cursor.execute("UPDATE StudentInterests SET interest = %s WHERE stu_id = %s AND interest = %s", (new, user_id, orig))

            # Add new interest
            new_interest = request.form.get("new_interest")
            if new_interest:
                cursor.execute("INSERT INTO StudentInterests (stu_id, interest) VALUES (%s, %s)", (user_id, new_interest))

            # Delete selected links
            delete_links = request.form.getlist("delete_links")
            for link in delete_links:
                cursor.execute("DELETE FROM StudentLinks WHERE stu_id = %s AND link = %s", (user_id, link))

            # Update links (if any)
            update_links = request.form.getlist("update_links")
            original_links = request.form.getlist("original_links")
            for orig, new in zip(original_links, update_links):
                if orig != new:
                    cursor.execute("UPDATE StudentLinks SET link = %s WHERE stu_id = %s AND link = %s", (new, user_id, orig))

            # Add new link
            new_link = request.form.get("new_link")
            if new_link:
                cursor.execute("INSERT INTO StudentLinks (stu_id, link) VALUES (%s, %s)", (user_id, new_link))

            conn.commit()
            return redirect(url_for('student_dashboard'))

    finally:
        cursor.close()
        conn.close()

    return render_template("edit_student_profile.html", profile=profile, interests=interests, links=links)

# ---------------- VIEW OTHER STUDENT PROFILE ----------------
@app.route("/view_student_profile/<student_id>", methods=["GET"])
def view_student_profile(student_id):
    if 'role' not in session or session['role'] not in ['student', 'faculty']:
        return redirect(url_for('login_page'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch profile data
        cursor.execute("SELECT id, name, mail, curr_sem FROM Student WHERE id = %s", (student_id,))
        profile = cursor.fetchone()

        if not profile:
            return "<h1>Student not found</h1>"

        # Fetch interests
        cursor.execute("SELECT interest FROM StudentInterests WHERE stu_id = %s", (student_id,))
        interests = [row['interest'] for row in cursor.fetchall()]

        # Fetch links
        cursor.execute("SELECT link FROM StudentLinks WHERE stu_id = %s", (student_id,))
        links = [row['link'] for row in cursor.fetchall()]

    finally:
        cursor.close()
        conn.close()

    return render_template("student_profile.html", profile=profile, interests=interests, links=links, is_own=False)

# ---------------- SEARCH STUDENTS ----------------
@app.route("/search_students", methods=["GET", "POST"])
def search_students():
    if 'role' not in session or session['role'] not in ['student', 'faculty']:
        return redirect(url_for('login_page'))

    search_term = request.form.get("search_term", "") if request.method == "POST" else ""
    students = []

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if search_term:
            cursor.execute("SELECT id, name, mail FROM Student WHERE id LIKE %s OR name LIKE %s", (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("SELECT id, name, mail FROM Student")
        students = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template("search_students.html", students=students, search_term=search_term)

# ---------------- CREATE GROUP ----------------
@app.route("/create_group", methods=["GET", "POST"])
def create_group():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT group_id FROM Student WHERE id = %s", (user_id,))
        current_group = cursor.fetchone()['group_id']
        if current_group is not None:
            return "<h1>You are already in a group</h1>"

        if request.method == "POST":
            group_name = request.form.get("group_name")
            if group_name:
                cursor.execute("INSERT INTO `Group` (name) VALUES (%s)", (group_name,))
                conn.commit()
                group_id = cursor.lastrowid
                cursor.execute("UPDATE Student SET group_id = %s WHERE id = %s", (group_id, user_id))
                conn.commit()
                return redirect(url_for('student_dashboard'))

    finally:
        cursor.close()
        conn.close()

    return render_template("create_group.html")

# ---------------- REQUEST TO JOIN GROUP ----------------
@app.route("/request_join_group/<int:group_id>", methods=["GET"])
def request_join_group(group_id):
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT group_id FROM Student WHERE id = %s", (user_id,))
        current_group = cursor.fetchone()['group_id']
        if current_group is not None:
            return "<h1>You are already in a group</h1>"

        # Check if already requested
        cursor.execute("SELECT COUNT(*) as count FROM GroupJoinRequests WHERE group_id = %s AND student_id = %s", (group_id, user_id))
        requested = cursor.fetchone()['count']
        if requested > 0:
            return "<h1>Request already sent</h1>"

        # Check group size
        cursor.execute("SELECT COUNT(*) as count FROM Student WHERE group_id = %s", (group_id,))
        group_size = cursor.fetchone()['count']
        if group_size >= 5:
            return "<h1>Group is full (max 5 members)</h1>"

        # Send request
        cursor.execute("INSERT INTO GroupJoinRequests (group_id, student_id, status) VALUES (%s, %s, 'pending')", (group_id, user_id))
        conn.commit()
        return "<h1>Request sent successfully</h1>"

    finally:
        cursor.close()
        conn.close()

# ---------------- ACCEPT JOIN REQUEST ----------------
@app.route("/accept_join_request/<int:group_id>/<int:student_id>", methods=["POST"])
def accept_join_request(group_id, student_id):
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if current user is in the group
        cursor.execute("SELECT group_id FROM Student WHERE id = %s", (user_id,))
        current_group = cursor.fetchone()['group_id']
        if current_group != group_id:
            return "<h1>You are not a member of this group</h1>"

        # Check if request exists and pending
        cursor.execute("SELECT * FROM GroupJoinRequests WHERE group_id = %s AND student_id = %s AND status = 'pending'", (group_id, student_id))
        request_exists = cursor.fetchone()
        if not request_exists:
            return "<h1>No such pending request</h1>"

        # Check group size
        cursor.execute("SELECT COUNT(*) as count FROM Student WHERE group_id = %s", (group_id,))
        group_size = cursor.fetchone()['count']
        if group_size >= 5:
            return "<h1>Group is full</h1>"

        # Accept: update student's group_id
        cursor.execute("UPDATE Student SET group_id = %s WHERE id = %s", (group_id, student_id))

        # Remove request
        cursor.execute("DELETE FROM GroupJoinRequests WHERE group_id = %s AND student_id = %s", (group_id, student_id))
        conn.commit()
        return redirect(url_for('group_profile', group_id=group_id))

    finally:
        cursor.close()
        conn.close()

# ---------------- REJECT JOIN REQUEST ----------------
@app.route("/reject_join_request/<int:group_id>/<int:student_id>", methods=["POST"])
def reject_join_request(group_id, student_id):
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if current user is in the group
        cursor.execute("SELECT group_id FROM Student WHERE id = %s", (user_id,))
        current_group = cursor.fetchone()['group_id']
        if current_group != group_id:
            return "<h1>You are not a member of this group</h1>"

        # Check if request exists and pending
        cursor.execute("SELECT * FROM GroupJoinRequests WHERE group_id = %s AND student_id = %s AND status = 'pending'", (group_id, student_id))
        request_exists = cursor.fetchone()
        if not request_exists:
            return "<h1>No such pending request</h1>"

        # Reject: remove request
        cursor.execute("DELETE FROM GroupJoinRequests WHERE group_id = %s AND student_id = %s", (group_id, student_id))
        conn.commit()
        return redirect(url_for('group_profile', group_id=group_id))

    finally:
        cursor.close()
        conn.close()

# ---------------- LEAVE GROUP ----------------
@app.route("/leave_group/<int:group_id>", methods=["POST"])
def leave_group(group_id):
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if current user is in the group
        cursor.execute("SELECT group_id FROM Student WHERE id = %s", (user_id,))
        current_group = cursor.fetchone()['group_id']
        if current_group != group_id:
            return "<h1>You are not a member of this group</h1>"

        # Remove user from group
        cursor.execute("UPDATE Student SET group_id = NULL WHERE id = %s", (user_id,))
        conn.commit()
        return redirect(url_for('student_dashboard'))

    finally:
        cursor.close()
        conn.close()

# ---------------- SEARCH GROUPS ----------------
@app.route("/search_groups", methods=["GET", "POST"])
def search_groups():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    search_term = request.form.get("search_term", "") if request.method == "POST" else ""
    groups = []

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        if search_term:
            cursor.execute("SELECT id, name FROM `Group` WHERE id LIKE %s OR name LIKE %s", (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("SELECT id, name FROM `Group`")
        groups = cursor.fetchall()

        # Fetch member count for each group
        for group in groups:
            cursor.execute("SELECT COUNT(*) as count FROM Student WHERE group_id = %s", (group['id'],))
            group['member_count'] = cursor.fetchone()['count']

    finally:
        cursor.close()
        conn.close()

    return render_template("search_groups.html", groups=groups, search_term=search_term)

# ---------------- GROUP PROFILE ----------------
@app.route("/group_profile/<int:group_id>", methods=["GET"])
def group_profile(group_id):
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch group info including topic and supervisor/cosupervisor IDs
        cursor.execute("SELECT id, name, topic, sup_id, cosup1_id, cosup2_id FROM `Group` WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        if not group:
            return "<h1>Group not found</h1>"

        # Fetch supervisor and cosupervisor names
        supervisor_name = None
        cosup1_name = None
        cosup2_name = None
        if group['sup_id']:
            cursor.execute("SELECT name FROM Faculty WHERE id = %s", (group['sup_id'],))
            row = cursor.fetchone()
            supervisor_name = row['name'] if row else None
        if group['cosup1_id']:
            cursor.execute("SELECT name FROM Faculty WHERE id = %s", (group['cosup1_id'],))
            row = cursor.fetchone()
            cosup1_name = row['name'] if row else None
        if group['cosup2_id']:
            cursor.execute("SELECT name FROM Faculty WHERE id = %s", (group['cosup2_id'],))
            row = cursor.fetchone()
            cosup2_name = row['name'] if row else None

        # Fetch members
        cursor.execute("SELECT id, name, mail FROM Student WHERE group_id = %s", (group_id,))
        members = cursor.fetchall()

        # Check if current user is member
        cursor.execute("SELECT group_id FROM Student WHERE id = %s", (user_id,))
        current_group = cursor.fetchone()['group_id']
        is_member = (current_group == group_id)

        # Fetch pending requests if member
        requests = []
        if is_member:
            cursor.execute("""
                SELECT s.id, s.name, s.mail 
                FROM GroupJoinRequests r 
                JOIN Student s ON r.student_id = s.id 
                WHERE r.group_id = %s AND r.status = 'pending'
            """, (group_id,))
            requests = cursor.fetchall()

        # Fetch group interests
        cursor.execute("SELECT interest FROM GroupInterests WHERE group_id = %s", (group_id,))
        interests = [row['interest'] for row in cursor.fetchall()]

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "group_profile.html",
        group=group,
        members=members,
        group_id=group_id,
        is_member=is_member,
        requests=requests,
        supervisor_name=supervisor_name,
        cosup1_name=cosup1_name,
        cosup2_name=cosup2_name,
        interests=interests
    )

# ---------------- FACULTY DASHBOARD / PROFILE ----------------
@app.route("/faculty_dashboard", methods=["GET", "POST"])
def faculty_dashboard():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch profile data
        cursor.execute("SELECT id, name, mail FROM Faculty WHERE id = %s", (user_id,))
        profile = cursor.fetchone()

        # Fetch interests
        cursor.execute("SELECT interest FROM FacultyInterests WHERE fac_id = %s", (user_id,))
        interests = [row['interest'] for row in cursor.fetchall()]

        # Fetch links
        cursor.execute("SELECT link FROM FacultyLinks WHERE fac_id = %s", (user_id,))
        links = [row['link'] for row in cursor.fetchall()]

        # Fetch consultation hours
        cursor.execute("SELECT con_hour FROM FacultyConsultationHrs WHERE fac_id = %s", (user_id,))
        consultation_hours = [row['con_hour'] for row in cursor.fetchall()]

        if request.method == "POST":
            if 'add_interest' in request.form:
                interest = request.form.get("interest")
                if interest:
                    cursor.execute("INSERT INTO FacultyInterests (fac_id, interest) VALUES (%s, %s)", (user_id, interest))
                    conn.commit()
            elif 'add_link' in request.form:
                link = request.form.get("link")
                if link:
                    cursor.execute("INSERT INTO FacultyLinks (fac_id, link) VALUES (%s, %s)", (user_id, link))
                    conn.commit()
            elif 'add_con_hour' in request.form:
                day = request.form.get("day")
                start_time = request.form.get("start_time")
                end_time = request.form.get("end_time")
                if day and start_time and end_time:
                    con_hour = f"[{day} ({start_time}-{end_time})]"
                    cursor.execute("INSERT INTO FacultyConsultationHrs (fac_id, con_hour) VALUES (%s, %s)", (user_id, con_hour))
                    conn.commit()
            return redirect(url_for('faculty_dashboard'))

    finally:
        cursor.close()
        conn.close()

    return render_template("faculty_profile.html", profile=profile, interests=interests, links=links, consultation_hours=consultation_hours, is_own=True)

# ---------------- EDIT FACULTY PROFILE ----------------
@app.route("/edit_faculty_profile", methods=["GET", "POST"])
def edit_faculty_profile():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch current data
        cursor.execute("SELECT id, name, mail FROM Faculty WHERE id = %s", (user_id,))
        profile = cursor.fetchone()

        cursor.execute("SELECT interest FROM FacultyInterests WHERE fac_id = %s", (user_id,))
        interests = [row['interest'] for row in cursor.fetchall()]

        cursor.execute("SELECT link FROM FacultyLinks WHERE fac_id = %s", (user_id,))
        links = [row['link'] for row in cursor.fetchall()]

        cursor.execute("SELECT con_hour FROM FacultyConsultationHrs WHERE fac_id = %s", (user_id,))
        consultation_hours = [row['con_hour'] for row in cursor.fetchall()]

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")

            # Update basic profile
            cursor.execute("UPDATE Faculty SET name = %s, mail = %s WHERE id = %s",
                          (name, email, user_id))

            # Handle interests
            delete_interests = request.form.getlist("delete_interests")
            for interest in delete_interests:
                cursor.execute("DELETE FROM FacultyInterests WHERE fac_id = %s AND interest = %s", (user_id, interest))

            update_interests = request.form.getlist("update_interests")
            original_interests = request.form.getlist("original_interests")
            for orig, new in zip(original_interests, update_interests):
                if orig != new:
                    cursor.execute("UPDATE FacultyInterests SET interest = %s WHERE fac_id = %s AND interest = %s", (new, user_id, orig))

            new_interest = request.form.get("new_interest")
            if new_interest:
                cursor.execute("INSERT INTO FacultyInterests (fac_id, interest) VALUES (%s, %s)", (user_id, new_interest))

            # Handle links
            delete_links = request.form.getlist("delete_links")
            for link in delete_links:
                cursor.execute("DELETE FROM FacultyLinks WHERE fac_id = %s AND link = %s", (user_id, link))

            update_links = request.form.getlist("update_links")
            original_links = request.form.getlist("original_links")
            for orig, new in zip(original_links, update_links):
                if orig != new:
                    cursor.execute("UPDATE FacultyLinks SET link = %s WHERE fac_id = %s AND link = %s", (new, user_id, orig))

            new_link = request.form.get("new_link")
            if new_link:
                cursor.execute("INSERT INTO FacultyLinks (fac_id, link) VALUES (%s, %s)", (user_id, new_link))

            # Handle consultation hours
            delete_con_hours = request.form.getlist("delete_con_hours")
            for hour in delete_con_hours:
                cursor.execute("DELETE FROM FacultyConsultationHrs WHERE fac_id = %s AND con_hour = %s", (user_id, hour))

            new_day = request.form.get("new_day")
            new_start_time = request.form.get("new_start_time")
            new_end_time = request.form.get("new_end_time")
            if new_day and new_start_time and new_end_time:
                new_con_hour = f"[{new_day} ({new_start_time}-{new_end_time})]"
                cursor.execute("INSERT INTO FacultyConsultationHrs (fac_id, con_hour) VALUES (%s, %s)", (user_id, new_con_hour))

            conn.commit()
            return redirect(url_for('faculty_dashboard'))

    finally:
        cursor.close()
        conn.close()

    return render_template("edit_faculty_profile.html", profile=profile, interests=interests, links=links, consultation_hours=consultation_hours)

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login_page'))

    search_id = request.form.get("search_id", "") if request.method == "POST" else ""
    users = []  # Combined list of students and faculty

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch students
        if search_id:
            cursor.execute("SELECT id, name, mail, 'student' as role FROM Student WHERE id LIKE %s", (f"%{search_id}%",))
        else:
            cursor.execute("SELECT id, name, mail, 'student' as role FROM Student")
        students = cursor.fetchall()
        users.extend(students)

        # Fetch faculty
        if search_id:
            cursor.execute("SELECT id, name, mail, 'faculty' as role FROM Faculty WHERE id LIKE %s", (f"%{search_id}%",))
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

# ---------------- EDIT GROUP PROFILE ----------------
@app.route("/edit_group_profile/<int:group_id>", methods=["GET", "POST"])
def edit_group_profile(group_id):
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Check if user is in this group
        cursor.execute("SELECT group_id FROM Student WHERE id = %s", (user_id,))
        current_group = cursor.fetchone()['group_id']
        if current_group != group_id:
            return "<h1>You are not a member of this group</h1>"

        cursor.execute("SELECT id, name, topic FROM `Group` WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        cursor.execute("SELECT interest FROM GroupInterests WHERE group_id = %s", (group_id,))
        interests = [row['interest'] for row in cursor.fetchall()]

        if request.method == "POST":
            topic = request.form.get("topic")
            cursor.execute("UPDATE `Group` SET topic = %s WHERE id = %s", (topic, group_id))

            # Delete interests
            delete_interests = request.form.getlist("delete_interests")
            for interest in delete_interests:
                cursor.execute("DELETE FROM GroupInterests WHERE group_id = %s AND interest = %s", (group_id, interest))

            # Update interests
            update_interests = request.form.getlist("update_interests")
            original_interests = request.form.getlist("original_interests")
            for orig, new in zip(original_interests, update_interests):
                if orig != new:
                    cursor.execute("UPDATE GroupInterests SET interest = %s WHERE group_id = %s AND interest = %s", (new, group_id, orig))

            # Add new interest
            new_interest = request.form.get("new_interest")
            if new_interest:
                cursor.execute("INSERT INTO GroupInterests (group_id, interest) VALUES (%s, %s)", (group_id, new_interest))

            conn.commit()
            return redirect(url_for('group_profile', group_id=group_id))

    finally:
        cursor.close()
        conn.close()

    return render_template("edit_group_profile.html", group=group, interests=interests, group_id=group_id)

if __name__ == "__main__":
    app.run(debug=True)