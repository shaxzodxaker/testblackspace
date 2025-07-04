from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import random

app = Flask(__name__)
app.secret_key = 'super-secret-key'
DB = 'test_app.db'

# BAZANI BIR MARTA YARATISH
def init_db():
    if not os.path.exists(DB):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                score INTEGER,
                date_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_answer TEXT
            )
        ''')
        # default admin
        c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                  ('admin', 'shaxzod', 1))
        conn.commit()
        conn.close()

init_db()

# LOGIN
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        if user:
            session['username'] = username
            session['is_admin'] = bool(user[3])
            if not session['is_admin']:
                c.execute("UPDATE users SET password=NULL WHERE username=?", (username,))
                conn.commit()
            conn.close()
            if session['is_admin']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash("Noto‘g‘ri login yoki parol!")
    return render_template('login.html')

# ADMIN DASHBOARD
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', username=session['username'])

# USER DASHBOARD
@app.route('/user')
def user_dashboard():
    if not session.get('username') or session.get('is_admin'):
        return redirect(url_for('login'))
    return render_template('user_dashboard.html', username=session['username'])

# FOYDALANUVCHI BOSHQARISH
@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']
        try:
            c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
                      (new_username, new_password, 0))
            conn.commit()
            flash("Yangi foydalanuvchi qo‘shildi!")
        except sqlite3.IntegrityError:
            flash("Bu foydalanuvchi nomi allaqachon mavjud.")
    c.execute("SELECT id, username FROM users WHERE is_admin=0")
    users = c.fetchall()
    conn.close()
    return render_template('manage_users.html', users=users)

@app.route('/admin/users/delete/<int:user_id>')
def delete_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("Foydalanuvchi o‘chirildi.")
    return redirect(url_for('manage_users'))

# SAVOLLARNI BOSHQARISH
@app.route('/admin/questions', methods=['GET', 'POST'])
def manage_questions():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if request.method == 'POST':
        qtext = request.form['question_text']
        a = request.form['option_a']
        b = request.form['option_b']
        c1 = request.form['option_c']
        d = request.form['option_d']
        correct = request.form['correct_answer']
        c.execute('''
            INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (qtext, a, b, c1, d, correct))
        conn.commit()
        flash("Savol qo‘shildi!")
    c.execute("SELECT id, question_text FROM questions")
    questions = c.fetchall()
    conn.close()
    return render_template('manage_questions.html', questions=questions)

@app.route('/admin/questions/delete/<int:q_id>')
def delete_question(q_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM questions WHERE id=?", (q_id,))
    conn.commit()
    conn.close()
    flash("Savol o‘chirildi.")
    return redirect(url_for('manage_questions'))

# ADMIN NATIJALARNI KO‘RISH
@app.route('/admin/results')
def view_results():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT username, score, date_taken FROM results ORDER BY date_taken DESC")
    results = c.fetchall()
    conn.close()
    return render_template('results.html', results=results)

# USER TEST BOSHLASH
@app.route('/test')
def start_test():
    if not session.get('username') or session.get('is_admin'):
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM questions")
    questions = c.fetchall()
    conn.close()

    if not questions:
        flash("Savollar mavjud emas, admin bilan bog‘laning.")
        return redirect(url_for('user_dashboard'))

    random.shuffle(questions)

    session['questions'] = [dict(
        id=q[0],
        question_text=q[1],
        option_a=q[2],
        option_b=q[3],
        option_c=q[4],
        option_d=q[5],
        correct_answer=q[6]
    ) for q in questions]
    session['current'] = 0
    session['score'] = 0

    return redirect(url_for('show_question'))

@app.route('/question', methods=['GET', 'POST'])
def show_question():
    if not session.get('questions'):
        return redirect(url_for('user_dashboard'))

    idx = session['current']
    questions = session['questions']

    if request.method == 'POST':
        answer = request.form.get('answer')
        correct = questions[idx]['correct_answer']
        if answer == correct:
            session['score'] += 1
        session['current'] += 1
        idx += 1
        if idx >= len(questions):
            # test tugadi
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("INSERT INTO results (username, score) VALUES (?, ?)",
                      (session['username'], session['score']))
            conn.commit()
            conn.close()
            score = session['score']
            total = len(questions)
            session.pop('questions')
            session.pop('current')
            session.pop('score')
            return render_template('result.html', score=score, total=total)

    question = questions[idx]
    return render_template('question.html', question=question, idx=idx+1, total=len(questions))

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
