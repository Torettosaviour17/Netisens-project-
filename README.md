# Netisens Student Submission Portal

Students submit work given in class. A student chooses a course, selects Assignment, Classwork, or Project, enters a title, and uploads one file. A teacher filters submissions by course and sees the student's name, title, type, submission date, and a download link. Teachers can add courses.

## Technology

- HTML and CSS provide the login page, submission form, and teacher's table.
- Python and Flask will handle login, check form input, and control access to uploads and downloads.
- SQLite stores users, courses, and submission details in a local database file, so the demo needs no separate database server.

## How a submission works

1. The HTML form sends the selected course, category, title, and file to Flask.
2. Flask identifies the student from their login session and checks the form.
3. The app saves the file and records the student ID, course ID, category, title, filename, and date.
4. The teacher selects a course. SQLite finds its submissions and joins each student ID to a name.

## First demo

Sign in as a student, submit a PDF under Frontend Development, then sign in as a teacher and download that same file.

The database schema and initial courses are in `schema.sql`. The web interface and upload flow are planned next.
