import os
import secrets
import sqlite3
from pathlib import Path
from uuid import uuid4

import click
from flask import (
    Flask, abort, flash, g, redirect, render_template, request,
    send_from_directory, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("NETISENS_SECRET_KEY") or secrets.token_hex(32),
    TEACHER_ID=os.environ.get("NETISENS_TEACHER_ID", ""),
    DATA_DIR=Path(app.instance_path),
    MAX_CONTENT_LENGTH=11 * 1024 * 1024,
    SESSION_COOKIE_SAMESITE="Lax",
)
CATEGORIES = ("Assignment", "Classwork", "Project")
EXTENSIONS = {".pdf", ".docx", ".zip"}


def db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATA_DIR"] / "portal.sqlite3")
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_database(error):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


@app.cli.command("init-db")
def init_db():
    (app.config["DATA_DIR"] / "uploads").mkdir(parents=True, exist_ok=True)
    db().executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
    click.echo("Database ready.")


@app.cli.command("add-user")
@click.argument("role", type=click.Choice(["student", "teacher"]))
@click.argument("email")
@click.argument("name")
@click.password_option()
def add_user(role, email, name, password):
    if len(password) < 8 or not name.strip() or "@" not in email:
        raise click.ClickException("Use a name, an email address, and a password of at least 8 characters.")
    try:
        with db() as connection:
            connection.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name.strip(), email.strip(), generate_password_hash(password), role),
            )
    except sqlite3.IntegrityError:
        raise click.ClickException("That email already has an account.") from None
    click.echo(f"Created {role} account for {email}.")


@app.before_request
def load_user_and_check_form():
    if request.method == "POST":
        token = session.get("csrf")
        if not token or not secrets.compare_digest(token.encode(), request.form.get("csrf", "").encode()):
            abort(400, "Refresh the page and try again.")
    user_id = session.get("user_id")
    g.user = db().execute("SELECT id, name, role FROM users WHERE id = ?", (user_id,)).fetchone() if user_id else None


@app.context_processor
def form_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(24)
    return {"csrf": session["csrf"]}


def require_role(role):
    if g.user is None:
        return redirect(url_for("login"))
    if g.user["role"] != role:
        abort(403)
    return None


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for(user["role"]))
        flash("The email or password is incorrect.")
    if g.user:
        return redirect(url_for(g.user["role"]))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for(g.user["role"]))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        account_id = request.form.get("account_id", "").strip()
        teacher_id = app.config["TEACHER_ID"]
        if account_id == "student":
            role = "student"
        elif teacher_id and secrets.compare_digest(account_id.encode(), teacher_id.encode()):
            role = "teacher"
        else:
            flash("Enter a valid account ID.")
            return render_template("register.html"), 400

        if not 1 <= len(name) <= 80 or not 3 <= len(email) <= 254 or "@" not in email:
            flash("Enter your name and a valid email address.")
        elif not 8 <= len(password) <= 128:
            flash("Use a password between 8 and 128 characters.")
        else:
            try:
                with db() as connection:
                    connection.execute(
                        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                        (name, email, generate_password_hash(password), role),
                    )
            except sqlite3.IntegrityError:
                flash("An account with that email already exists. Sign in with it.")
            else:
                flash("Your account was created. Sign in to continue.")
                return redirect(url_for("login"))
    return render_template("register.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def courses():
    return db().execute("SELECT id, name FROM courses ORDER BY name").fetchall()


@app.route("/student", methods=["GET", "POST"])
def student():
    denied = require_role("student")
    if denied:
        return denied
    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        course = db().execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
        category = request.form.get("category")
        title = request.form.get("title", "").strip()
        upload = request.files.get("file")
        filename = secure_filename(upload.filename or "") if upload else ""
        extension = Path(filename).suffix.lower()
        if not course or category not in CATEGORIES or not 1 <= len(title) <= 120:
            flash("Choose a course and category, and enter a title of up to 120 characters.")
        elif extension not in EXTENSIONS or len(request.files.getlist("file")) != 1:
            flash("Choose one PDF, DOCX, or ZIP file.")
        else:
            data = upload.read(10 * 1024 * 1024 + 1)
            if 0 < len(data) <= 10 * 1024 * 1024:
                stored = uuid4().hex + extension
                path = app.config["DATA_DIR"] / "uploads" / stored
                try:
                    path.write_bytes(data)
                    with db() as connection:
                        connection.execute(
                            """INSERT INTO submissions
                               (student_id, course_id, category, title, original_filename, stored_filename)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (g.user["id"], course_id, category, title, filename, stored),
                        )
                except (OSError, sqlite3.Error):
                    path.unlink(missing_ok=True)
                    raise
                flash("Your work was submitted.")
                return redirect(url_for("student"))
            flash("Your file must be between 1 byte and 10 MB.")
    history = db().execute(
        """SELECT submissions.*, courses.name AS course_name
           FROM submissions JOIN courses ON courses.id = course_id
           WHERE student_id = ? ORDER BY submissions.id DESC""", (g.user["id"],)
    ).fetchall()
    return render_template("student.html", courses=courses(), categories=CATEGORIES, history=history)


@app.route("/teacher", methods=["GET", "POST"])
def teacher():
    denied = require_role("teacher")
    if denied:
        return denied
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not 1 <= len(name) <= 80:
            flash("Enter a course name of up to 80 characters.")
        else:
            try:
                with db() as connection:
                    connection.execute("INSERT INTO courses (name) VALUES (?)", (name,))
                flash("Course added.")
            except sqlite3.IntegrityError:
                flash("That course already exists.")
        return redirect(url_for("teacher"))
    selected = request.args.get("course_id", type=int)
    submissions = db().execute(
        """SELECT submissions.*, users.name AS student_name, courses.name AS course_name
           FROM submissions
           JOIN users ON users.id = student_id
           JOIN courses ON courses.id = course_id
           WHERE (? IS NULL OR course_id = ?) ORDER BY submissions.id DESC""",
        (selected, selected),
    ).fetchall()
    return render_template("teacher.html", courses=courses(), selected=selected, submissions=submissions)


@app.get("/submissions/<int:submission_id>/download")
def download(submission_id):
    denied = require_role("teacher")
    if denied:
        return denied
    submission = db().execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    if submission is None:
        abort(404)
    response = send_from_directory(
        app.config["DATA_DIR"] / "uploads", submission["stored_filename"],
        as_attachment=True, download_name=submission["original_filename"],
        mimetype="application/octet-stream",
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.cache_control.no_store = True
    return response


@app.errorhandler(413)
def upload_too_large(error):
    return render_template("error.html", message="Choose a file no larger than 10 MB."), 413
