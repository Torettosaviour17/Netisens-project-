# Netisens Student Submission Portal

Students submit work given in class. A student chooses a course and submission type, enters a title, and uploads one PDF, DOCX, or ZIP file up to 10 MB. A teacher can add courses and filter or download submissions. The portal starts with Frontend Development, Backend Development, Full Stack Development, Cybersecurity, and Digital Marketing.

## Run locally

Install Python 3.10 or newer. From the repo folder, run these commands. In Windows Git Bash, use `py` in place of `python` for the first command if needed.

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
# On macOS or Linux, use: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app init-db
python -m flask --app app add-user student student@example.test "Demo Student"
python -m flask --app app add-user teacher teacher@example.test "Demo Teacher"
python -m flask --app app run
```

Choose a password of at least eight characters at each prompt. Open <http://127.0.0.1:5000>. Database records and files persist in the local `instance/` directory. Run initialization again safely if needed. The default session signing key is temporary, so restarting the app signs users out unless you set `NETISENS_SECRET_KEY`.

## Demo

1. Sign in as the student and submit a PDF titled **Landing Page** under **Frontend Development**, using **Assignment** as the type.
2. Confirm the submission appears under **My submissions** and sign out.
3. Sign in as the teacher, filter for **Frontend Development**, and download the student's PDF.

## How it works

- **HTML and CSS** define the forms, tables, and layout in `templates/` and `static/`.
- **Python with Flask** connects the forms to server-side logic in `app.py`. Flask looks up the signed-in student, validates the form, saves the file, and records the submission.
- **SQLite** keeps the three tables in one file and needs no separate database server. In `schema.sql`, each submission links a student ID to a course ID. The teacher's page joins those records to show the student's and course's names.

This setup is intended for a local certificate demo.
