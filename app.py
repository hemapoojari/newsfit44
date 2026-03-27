from flask import Flask, render_template, request, redirect, session
import sqlite3
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

API_KEY = "78edb6dc38524d9b9b19a96ead8989c7"

# DATABASE
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS preferences (
        user_id INTEGER,
        category TEXT,
        score INTEGER
    )''')

    conn.commit()
    conn.close()

init_db()

# REGISTER
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
            conn.commit()
        except:
            return "User already exists"
        finally:
            conn.close()

        return redirect('/')

    return render_template('register.html')

# LOGIN
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            return redirect('/dashboard')
        else:
            return "Invalid Credentials"

    return render_template('login.html')

# DASHBOARD (UPDATED)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM preferences WHERE score=1 AND user_id=?", (user_id,))
    read = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM preferences WHERE score=-1 AND user_id=?", (user_id,))
    skip = cur.fetchone()[0]

    total = read - skip

    # Fetch recommended news
    cur.execute("SELECT category, SUM(score) FROM preferences WHERE user_id=? GROUP BY category", (user_id,))
    prefs = dict(cur.fetchall())

    url = f"https://newsapi.org/v2/everything?q=india&apiKey={API_KEY}"
    articles = requests.get(url).json().get('articles', [])

    for article in articles:
        category = article['source']['name'] if article['source'] else "general"
        article['score'] = prefs.get(category, 0)

    articles = sorted(articles, key=lambda x: x['score'], reverse=True)
    recommended_news = articles[:5]  # Top 5 recommended

    conn.close()

    return render_template('dashboard.html', read=read, skip=skip, total=total, recommended_news=recommended_news)

# UPDATE PREFERENCES
@app.route('/update', methods=['POST'])
def update():
    user_id = session['user_id']
    category = request.form['category']
    action = request.form['action']

    score = 1 if action == "like" else -1

    conn = get_db()
    conn.execute("INSERT INTO preferences VALUES (?,?,?)", (user_id, category, score))
    conn.commit()
    conn.close()

    return redirect('/dashboard')

# NEWS PAGE
@app.route('/news')
def news():
    user_id = session['user_id']
    query = request.args.get('query')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT category, SUM(score) FROM preferences WHERE user_id=? GROUP BY category", (user_id,))
    prefs = dict(cur.fetchall())

    if query:
        url = f"https://newsapi.org/v2/everything?q={query}&apiKey={API_KEY}"
    else:
        url = f"https://newsapi.org/v2/everything?q=india&apiKey={API_KEY}"

    articles = requests.get(url).json().get('articles', [])

    for article in articles:
        category = article['source']['name'] if article['source'] else "general"
        article['score'] = prefs.get(category, 0)

    articles = sorted(articles, key=lambda x: x['score'], reverse=True)

    return render_template('news.html', news=articles)


# PROFILE PAGE
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()

    return render_template('profile.html', user=user)

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    conn.close()

    return render_template('settings.html', user=user)

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect('/')

    # Static notifications sample
    activity = [
        {'message': 'You liked 3 articles about Technology', 'time': '5m ago'},
        {'message': '1 recommended article added to your feed', 'time': '20m ago'},
        {'message': 'Profile updated successfully', 'time': '1h ago'}
    ]
    return render_template('notifications.html', activity=activity)

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

app.run(debug=True)