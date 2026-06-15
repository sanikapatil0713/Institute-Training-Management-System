from flask import Blueprint, render_template, request, redirect, flash, url_for, jsonify
from db_config import get_db_connection
import csv, io

from werkzeug.security import generate_password_hash, check_password_hash

admin_bp = Blueprint("admin", __name__, template_folder="templates")


# ---------------------- ADMIN DASHBOARD ----------------------
@admin_bp.route("/dashboard")
def dashboard():
    return render_template("admin_dashboard.html")


# ======================== 1) COURSE ==========================
# ------------------- COURSE PAGE -------------------
@admin_bp.route('/course_page')
def course_page():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM course_master")
    courses = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("course.html", courses=courses)


# ADD COURSE
@admin_bp.route('/course', methods=['POST'])
def add_course():
    course_name = request.form['course_name'].strip()
    duration = request.form['duration'].strip()

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO course_master (course_name, duration) VALUES (%s, %s)",
                (course_name, duration))
    
    conn.commit()
    cur.close()
    conn.close()

    flash("✅ Course added successfully!", "success")
    return redirect(url_for('admin.course_page'))


# DELETE COURSE
@admin_bp.route('/course/delete/<int:course_id>')
def delete_course(course_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM course_master WHERE course_id = %s", (course_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("🗑 Course deleted!", "success")
    return redirect(url_for('admin.course_page'))



# ======================== 2) SUBJECT ==========================
# ------------------- SUBJECT PAGE -------------------
@admin_bp.route('/subject_page')
def subject_page():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM course_master")
    courses = cur.fetchall()

    cur.execute("""
        SELECT s.subject_id, s.subject_name, c.course_name 
        FROM su_master s 
        JOIN course_master c ON s.course_id = c.course_id
    """)
    subjects = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("subject.html", courses=courses, subjects=subjects)

@admin_bp.route('/subject', methods=['POST'])
def add_subject():
    subject_name = request.form['subject_name'].strip()
    course_id = request.form['course_id']

    if not course_id:
        flash("⚠ Please select a course!", "error")
        return redirect(url_for('admin.subject_page'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT * FROM su_master 
        WHERE LOWER(subject_name) = LOWER(%s) AND course_id = %s
    """, (subject_name, course_id))
    existing = cur.fetchone()

    if existing:
        flash("⚠ Subject already exists for this course!", "error")
        cur.close()
        conn.close()
        return redirect(url_for('admin.subject_page'))

    cur = conn.cursor()
    cur.execute("INSERT INTO su_master (subject_name, course_id) VALUES (%s, %s)",
                (subject_name, course_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("✅ Subject added successfully!", "success")
    return redirect(url_for('admin.subject_page'))



# DELETE SUBJECT
@admin_bp.route('/subject/delete/<int:subject_id>')
def delete_subject(subject_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM su_master WHERE subject_id = %s", (subject_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("🗑 Subject deleted!", "success")
    return redirect(url_for('admin.subject_page'))



# ======================== 3) TOPIC ==========================
# ------------------- TOPIC PAGE -------------------
@admin_bp.route('/topic_page')
def topic_page():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Load all courses for dropdown
    cur.execute("SELECT * FROM course_master")
    courses = cur.fetchall()

    # Load all topics with subject + course names
    cur.execute("""
        SELECT t.topic_id, t.topic_name, 
               s.subject_name, c.course_name
        FROM topic t
        JOIN su_master s ON t.subject_id = s.subject_id
        JOIN course_master c ON s.course_id = c.course_id
    """)
    topics = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("topic.html", courses=courses, topics=topics)


# ================================================================
#               GET SUBJECTS BASED ON SELECTED COURSE
# ================================================================
@admin_bp.route('/get_subjects/<int:course_id>')
def get_subjects(course_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM su_master WHERE course_id = %s", (course_id,))
    subjects = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(subjects)


# ================================================================
#                           ADD TOPIC
# ================================================================
@admin_bp.route('/topic', methods=['POST'])
def add_topic():
    topic_name = request.form['topic_name'].strip()
    subject_id = request.form['subject_id']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO topic (topic_name, subject_id) VALUES (%s, %s)",
                (topic_name, subject_id))
    conn.commit()

    cur.close()
    conn.close()

    flash("✅ Topic added successfully!", "success")
    return redirect(url_for('admin.topic_page'))


# ================================================================
#                         DELETE TOPIC
# ================================================================
@admin_bp.route('/topic/delete/<int:topic_id>')
def delete_topic(topic_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM topic WHERE topic_id = %s", (topic_id,))
    conn.commit()

    cur.close()
    conn.close()

    flash("🗑 Topic deleted!", "success")
    return redirect(url_for('admin.topic_page'))



# ------------------- TRAINER MANAGEMENT -------------------
@admin_bp.route('/trainer_page')
def trainer_page():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, email FROM users WHERE role='trainer'")
    trainers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("trainer.html", trainers=trainers)

@admin_bp.route('/trainer/add', methods=['POST'])
def add_trainer():
    name = request.form['name'].strip()
    email = request.form['email'].strip()
    password = request.form['password'].strip()

    # Validation
    if not name or not email or not password:
        flash("⚠ All fields are required!", "danger")
        return redirect(url_for('admin.trainer_page'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # Check duplicate email
        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )
        existing_user = cur.fetchone()

        if existing_user:
            flash("⚠ Email already exists!", "warning")
            return redirect(url_for('admin.trainer_page'))

        # Hash password
        hashed_password = generate_password_hash(password)

        # Insert trainer
        cur.execute("""
            INSERT INTO users
            (name, email, password_hash, role)
            VALUES (%s, %s, %s, 'trainer')
        """, (name, email, hashed_password))

        conn.commit()

        flash(f"✅ Trainer '{name}' added successfully!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for('admin.trainer_page'))


@admin_bp.route('/trainer/delete/<int:trainer_id>')
def delete_trainer(trainer_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s AND role='trainer'", (trainer_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("🗑 Trainer deleted!", "success")
    return redirect(url_for('admin.trainer_page'))

# =================== ASSIGN TRAINER ===================
@admin_bp.route('/trainer_assign_page')
def trainer_assign_page():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Load trainers
    cur.execute("SELECT id, name FROM users WHERE role='trainer'")
    trainers = cur.fetchall()

    # Load courses
    cur.execute("SELECT * FROM course_master")
    courses = cur.fetchall()

    # Load current assignments (join for display)
    cur.execute("""
        SELECT ta.id, u.name as trainer_name, c.course_name, s.subject_name
        FROM trainer_assign ta
        JOIN users u ON ta.trainer_id = u.id
        JOIN course_master c ON ta.course_id = c.course_id
        JOIN su_master s ON ta.subject_id = s.subject_id
    """)
    assignments = cur.fetchall()
    print(assignments)

    cur.close()
    conn.close()
    return render_template("trainer_assign.html", trainers=trainers, courses=courses, assignments=assignments)
#------------







# NEW (Trainer assign version)
@admin_bp.route('/get_subjects_by_course/<int:course_id>')
def get_subjects_by_course(course_id):
    """AJAX endpoint: Get subjects by selected course"""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM su_master WHERE course_id=%s", (course_id,))
    subjects = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(subjects)



@admin_bp.route('/trainer_assign', methods=['POST'])
def trainer_assign():
    trainer_id = request.form['trainer_id']
    course_id = request.form['course_id']
    subject_id = request.form['subject_id']

    if not trainer_id or not course_id or not subject_id:
        flash("⚠ Please select trainer, course, and subject!", "error")
        return redirect(url_for('admin.trainer_assign_page'))

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO trainer_assign (trainer_id, course_id, subject_id) VALUES (%s,%s,%s)",
            (trainer_id, course_id, subject_id)
        )
        conn.commit()
        flash("✅ Trainer assigned successfully!", "success")
    except Exception as e:
        flash(f"⚠ Assignment failed: {str(e)}", "error")
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('admin.trainer_assign_page'))


@admin_bp.route('/trainer_assign/delete/<int:assign_id>')
def delete_trainer_assign(assign_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM trainer_assign WHERE id=%s", (assign_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("🗑 Assignment deleted!", "success")
    return redirect(url_for('admin.trainer_assign_page'))


# ---------------- TIMETABLE -----------------
@admin_bp.route('/timetable_page')
def timetable_page():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Courses for dropdown
    cur.execute("SELECT course_id, course_name FROM course_master")
    courses = cur.fetchall()

    # Timetable list
    cur.execute("""
        SELECT t.id,
               c.course_name,
               s.subject_name,
               u.name AS trainer_name,
               t.day,
               t.time_slot
        FROM timetable_master t
        JOIN course_master c ON t.course_id = c.course_id
        JOIN su_master s ON t.subject_id = s.subject_id
        JOIN users u ON t.trainer_id = u.id
        ORDER BY t.id DESC
    """)
    timetable = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'timetable.html',
        courses=courses,
        timetable=timetable
    )


# =========================================================
#                ADD TIMETABLE (POST)
# =========================================================
@admin_bp.route('/timetable', methods=['POST'])
def add_timetable():
    course_id = request.form['course_id']
    subject_id = request.form['subject_id']
    trainer_id = request.form['trainer_id']
    day = request.form['day']
    time_slot = request.form['time_slot']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO timetable_master
        (course_id, subject_id, trainer_id, day, time_slot)
        VALUES (%s, %s, %s, %s, %s)
    """, (course_id, subject_id, trainer_id, day, time_slot))

    conn.commit()
    cur.close()
    conn.close()

    flash("✅ Timetable entry added!", "success")
    return redirect(url_for('admin.timetable_page'))



# =========================================================
#                DELETE TIMETABLE
# =========================================================
@admin_bp.route('/timetable/delete/<int:id>')
def delete_timetable(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM timetable_master WHERE id=%s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    flash("🗑 Timetable entry deleted!", "success")
    return redirect(url_for('admin.timetable_page'))


# =========================================================
#        AJAX: GET SUBJECTS BY COURSE (TIMETABLE)
# =========================================================
@admin_bp.route('/get_subjects_timetable/<int:course_id>')
def get_subjects_timetable(course_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT subject_id, subject_name
        FROM su_master
        WHERE course_id=%s
    """, (course_id,))
    subjects = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(subjects)


# =========================================================
#        AJAX: GET TRAINERS BY SUBJECT
# =========================================================
@admin_bp.route('/get_trainers/<int:subject_id>')
def get_trainers(subject_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT u.id, u.name
        FROM trainer_assign ta
        JOIN users u ON ta.trainer_id = u.id
        WHERE ta.subject_id=%s
    """, (subject_id,))
    trainers = cur.fetchall()
   

    cur.close()
    conn.close()

    return jsonify(trainers)

#----------------------------------------------------------------------------------------------------------------------#
#upload student data
@admin_bp.route('/enroll_student', methods=['GET', 'POST'])
def enroll_student():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']

        # 🔒 CHECK: student already enrolled or not
        cur.execute(
            "SELECT * FROM student_course WHERE student_id=%s AND course_id=%s",
            (student_id, course_id)
        )
        exists = cur.fetchone()

        if exists:
            flash("⚠️ Student already enrolled in this course!", "warning")
            return redirect(url_for('admin.enroll_student'))

        # ✅ INSERT only if not exists
        cur.execute(
            "INSERT INTO student_course (student_id, course_id) VALUES (%s, %s)",
            (student_id, course_id)
        )
        conn.commit()

        flash("✅ Student enrolled successfully!", "success")
        return redirect(url_for('admin.enroll_student'))

    # 🔽 ONLY NOT-ENROLLED STUDENTS
    cur.execute("""
        SELECT id, name
        FROM users
        WHERE role='student'
        AND id NOT IN (
            SELECT student_id FROM student_course
        )
    """)
    students = cur.fetchall()

    cur.execute("SELECT course_id, course_name FROM course_master")
    courses = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'enroll_student.html',
        students=students,
        courses=courses
    )


#FR-Admin-06: CSV / EXCEL BULK STUDENT UPLOAD
@admin_bp.route('/upload_students', methods=['GET', 'POST'])
def upload_students():
    if request.method == 'POST':
        file = request.files['file']

        if not file:
            flash("❌ No file selected", "danger")
            return redirect(request.url)

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        next(csv_reader)  # skip header

        conn = get_db_connection()
        cur = conn.cursor()

        for row in csv_reader:
            name, email, password = row

            password_hash = generate_password_hash(password)

            cur.execute("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
            """, (name, email, password_hash))

        conn.commit()
        cur.close()
        conn.close()

        flash("📥 Students uploaded successfully!", "success")
        return redirect(url_for('admin.upload_students'))

    return render_template('upload_students.html')

#FR-Admin-07: BULK ENROLL STUDENTS (Checkbox)
@admin_bp.route('/bulk_enroll', methods=['GET', 'POST'])
def bulk_enroll():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        course_id = request.form['course_id']

        for sid in student_ids:
            cur.execute(
                """
                INSERT IGNORE INTO student_course (student_id, course_id)
                VALUES (%s, %s)
                """,
                (sid, course_id)
            )

        conn.commit()
        flash("✅ Bulk enrollment successful!", "success")
        return redirect(url_for('admin.bulk_enroll'))

    # 🔴 IMPORTANT PART: show only NOT enrolled students
    cur.execute("""
        SELECT u.id, u.name
        FROM users u
        WHERE u.role = 'student'
        AND u.id NOT IN (
            SELECT student_id FROM student_course
        )
    """)
    students = cur.fetchall()

    cur.execute("SELECT course_id, course_name FROM course_master")
    courses = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'bulk_enroll.html',
        students=students,
        courses=courses
    )

#ADMIN → VIEW ALL ENROLLMENTS

@admin_bp.route('/view_enrollments')
def view_enrollments():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT sc.id,
               u.name AS student_name,
               c.course_name,
               sc.enrolled_at
        FROM student_course sc
        JOIN users u ON sc.student_id = u.id
        JOIN course_master c ON sc.course_id = c.course_id
        ORDER BY sc.enrolled_at DESC
    """)

    enrollments = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'view_enrollments.html',
        enrollments=enrollments
    )

@admin_bp.route("/logout")
def logout():

    return redirect("/")


