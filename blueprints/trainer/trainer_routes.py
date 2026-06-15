from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from db_config import get_db_connection

trainer_bp = Blueprint("trainer",__name__,template_folder="templates")



@trainer_bp.route('/dashboard')
def trainer_dashboard():

    # 🔐 security
    if 'user_id' not in session or session.get('role') != 'trainer':
        return redirect(url_for('login'))

    trainer_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # 1️⃣ Check assigned subjects
    cur.execute("""
        SELECT DISTINCT c.course_name, s.subject_name
        FROM  trainer_assign ts
        JOIN course_master c ON ts.course_id = c.course_id
        JOIN su_master s ON ts.subject_id = s.subject_id
        WHERE ts.trainer_id = %s
    """, (trainer_id,))
    assignments = cur.fetchall()

    # ❗ If no assignments
    if not assignments:
        cur.close()
        conn.close()
        return render_template(
            "trainer_dashboard.html",
            assignments=None
        )

    # 2️⃣ Timetable
    cur.execute("""
        SELECT t.day, t.time_slot,
               c.course_name,
               s.subject_name
        FROM timetable_master t
        JOIN course_master c ON t.course_id = c.course_id
        JOIN su_master s ON t.subject_id = s.subject_id
        WHERE t.trainer_id = %s
        ORDER BY t.day, t.time_slot
    """, (trainer_id,))
    timetable = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "trainer_dashboard.html",
        assignments=assignments,
        timetable=timetable
    )




if __name__ == "__main__":
    app.run(debug=True)
