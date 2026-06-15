from flask import Flask, render_template, request, redirect, session, flash, url_for
import re
from db_config import get_db_connection
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash



from blueprints.admin import admin_bp
from blueprints.student import student_bp
from blueprints.trainer import trainer_bp

app = Flask(__name__)
app.secret_key = "secret123"

# register blueprints
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(student_bp, url_prefix="/student")
app.register_blueprint(trainer_bp, url_prefix="/trainer")


@app.route("/")
def home_page():
    return render_template("homepage.html")


@app.route("/login")
def home():
    return render_template("login.html")
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    entered_password = request.form["password"]

    con = get_db_connection()
    cur = con.cursor(dictionary=True)

    # ✅ ONLY fetch by email
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    print(entered_password)

    cur.close()
    con.close()

    # ✅ CHECK HASH IN PYTHON
    if user and check_password_hash(user["password_hash"], entered_password):
        

        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        if user["role"] == "admin":
            return redirect("/admin/dashboard")
        elif user["role"] == "student":
            return redirect("/student/dashboard")
        elif user["role"] == "trainer":
            return redirect("/trainer/dashboard")

    else:
        flash("❌ Invalid email or password", "danger")
        return redirect("/")


#registration

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role = request.form['role']

        # 🔒 NAME VALIDATION (only letters & spaces)
        if not re.fullmatch(r"[A-Za-z ]+", name):
            flash("❌ Name should contain only alphabets and spaces", "danger")
            return redirect(url_for('register'))

        # 🔒 EMAIL VALIDATION
        if any(char.isupper() for char in email):
            flash("❌ Email should not contain capital letters", "danger")
            return redirect(url_for('register'))

        if not email.endswith("@gmail.com"):
            flash("❌ Email must end with @gmail.com", "danger")
            return redirect(url_for('register'))

        if role not in ['student', 'trainer']:
            flash("⚠ Invalid role selected!", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                (name, email, hashed_password, role)
            )
            conn.commit()
            flash(f"✅ {role.capitalize()} registered successfully!", "success")
        except Exception as e:
            flash("⚠ Email already exists!", "danger")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('register'))

    return render_template("register.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        new_password = request.form["new_password"]

        con = get_db_connection()
        cur = con.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        # ❌ Admin ला reset allow नाही
        if not user:
            flash("❌ Email not found", "danger")
            return redirect("/forgot-password")

        if user["role"] == "admin":
            flash("❌ Admin password reset is not allowed", "danger")
            return redirect("/forgot-password")

        # ✅ Only student & trainer allowed
        hashed_password = generate_password_hash(new_password)

        cur.execute(
            "UPDATE users SET password_hash=%s WHERE email=%s",
            (hashed_password, email)
        )
        con.commit()

        cur.close()
        con.close()

        flash("✅ Password reset successful. Please login.", "success")
        return redirect("/")

    return render_template("forgot_password.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")





if __name__ == "__main__":
    app.run(debug=True)
