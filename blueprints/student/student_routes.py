from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from db_config import get_db_connection

student_bp = Blueprint("student",__name__,template_folder="templates")

# Dashboard
@student_bp.route('/dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('auth.login'))

    student_id = session['user_id']
    

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Enrolled Course (ONLY ONE)
    cur.execute("""
        SELECT c.course_id, c.course_name, c.duration
        FROM student_course sc
        JOIN course_master c ON sc.course_id = c.course_id
        WHERE sc.student_id = %s
        LIMIT 1
    """, (student_id,))
    course = cur.fetchone()

    # ❗ If NOT enrolled
    if not course:
        cur.close()
        conn.close()
        return render_template(
            'student_dashboard.html',
            course=None,
            subjects=[],
            timetable=[]
        )

    # Subjects
    cur.execute("""
        SELECT subject_name
        FROM su_master
        WHERE course_id = %s
    """, (course['course_id'],))
    subjects = cur.fetchall()

    # Timetable
    cur.execute("""
        SELECT t.day, t.time_slot, s.subject_name
        FROM timetable_master t
        JOIN su_master s ON t.subject_id = s.subject_id
        WHERE t.course_id = %s
        ORDER BY t.day, t.time_slot
    """, (course['course_id'],))
    timetable = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'student_dashboard.html',
        course=course,
        subjects=subjects,
        timetable=timetable
    )

  

if __name__ == "__main__":
    app.run(debug=True)
