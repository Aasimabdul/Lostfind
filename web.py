import os
import uuid
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, session, render_template_string, send_from_directory, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lost_found_secure_2026_pro")

# Configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
DB_NAME = "lost_found_render.db" 

# ---------- DATABASE SETUP ----------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, author TEXT, title TEXT, description TEXT, status TEXT, file_name TEXT, created_at TEXT)")
    conn.commit()
    conn.close()

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
init_db()

# ---------- AUTH ----------
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user" not in session: return redirect("/")
        return f(*args, **kwargs)
    return wrap

# ---------- UI: MIDNIGHT CRIMSON THEME ----------
# Using a Red/Navy theme to distinguish it from the Blue Notes Hub
BASE_UI = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Lost & Found Pro</title>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
        :root { --lost: #ef4444; --found: #10b981; --bg: #f8fafc; --dark: #0f172a; }
        * { box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { margin: 0; background: var(--bg); padding-bottom: 90px; }
        
        .header { background: var(--dark); padding: 30px 20px 50px; text-align: center; color: white; position: sticky; top: 0; z-index: 100; }
        .container { max-width: 500px; margin: auto; padding: 0 15px; }

        .search-container { margin: -28px auto 20px; position: relative; z-index: 101; }
        .search-box { width: 100%; padding: 16px 20px 16px 50px; border-radius: 20px; border: none; outline: none; background: white; box-shadow: 0 10px 25px rgba(0,0,0,0.08); font-size: 15px; }
        .search-icon { position: absolute; left: 18px; top: 16px; color: #94a3b8; width: 20px; }

        .item-card { background: white; border-radius: 24px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #f1f5f9; }
        .status-badge { font-size: 10px; font-weight: 800; padding: 4px 12px; border-radius: 6px; text-transform: uppercase; color: white; }
        .status-lost { background: var(--lost); }
        .status-found { background: var(--found); }
        
        .item-img { width: 100%; border-radius: 16px; margin-top: 15px; max-height: 300px; object-fit: cover; }
        
        .bottom-nav { position: fixed; bottom: 0; width: 100%; background: rgba(255, 255, 255, 0.95); display: flex; justify-content: space-around; padding: 12px 0; border-top: 1px solid #e2e8f0; backdrop-filter: blur(10px); z-index: 1000; }
        .nav-link { text-decoration: none; color: #94a3b8; display: flex; flex-direction: column; align-items: center; }
        .nav-link.active { color: var(--lost); }
        .nav-link i { width: 24px; height: 24px; }
        .nav-text { font-size: 10px; font-weight: 800; margin-top: 4px; }
        
        input, textarea, select { width: 100%; padding: 14px; border: 1px solid #e2e8f0; border-radius: 16px; background: #f8fafc; font-size: 15px; margin-bottom: 12px; outline: none; }
        .btn-submit { width: 100%; padding: 16px; border: none; background: var(--dark); color: white; border-radius: 16px; font-weight: 700; cursor: pointer; }
    </style>
</head>
<body>
"""

FOOTER = """<script>lucide.createIcons();</script></body></html>"""

# ---------- ROUTES ----------

@app.route("/")
def auth():
    if "user" in session: return redirect("/home")
    return render_template_string(BASE_UI + """
    <div style="height: 100vh; display: flex; align-items: center; justify-content: center; padding: 25px; background: #0f172a;">
        <div class="item-card" style="width: 100%; max-width: 380px; text-align: center;">
            <i data-lucide="search" style="width: 50px; height: 50px; color: #ef4444; margin: 0 auto 15px;"></i>
            <h2 style="margin:0;">Lost & Found Hub</h2>
            <form action="/login" method="POST">
                <input name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button class="btn-submit" style="background:#ef4444;">Sign In</button>
            </form>
            <p style="font-size:14px; margin-top:15px;">New? <a href="/signup" style="color:#ef4444; font-weight:700; text-decoration:none;">Create Account</a></p>
        </div>
    </div>""" + FOOTER)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (request.form["username"], generate_password_hash(request.form["password"])))
            conn.commit()
            return redirect("/")
        except: return "Error: User exists."
    return render_template_string(BASE_UI + """<div class="container" style="margin-top:50px;"><div class="item-card"><h2>Join Hub</h2><form method="POST"><input name="username" placeholder="Name"><input type="password" name="password" placeholder="Password"><button class="btn-submit">Register</button></form></div></div>""" + FOOTER)

@app.route("/login", methods=["POST"])
def login():
    u, p = request.form["username"], request.form["password"]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
    if user and check_password_hash(user["password"], p):
        session["user"] = u
        return redirect("/home")
    return redirect("/")

@app.route("/home")
@login_required
def home():
    q = request.args.get("q", "")
    conn = get_db()
    query = "SELECT * FROM items WHERE title LIKE ? OR description LIKE ? ORDER BY id DESC"
    items = conn.execute(query, (f"%{q}%", f"%{q}%")).fetchall()
    
    html = BASE_UI + f'<div class="header"><p style="font-weight:800; font-size:22px; margin:0;"><i data-lucide="shield-alert"></i> Lost & Found</p></div><div class="container">'
    html += f'<div class="search-container"><form action="/home" method="GET"><i data-lucide="search" class="search-icon"></i><input name="q" class="search-box" placeholder="Search items..." value="{q}"></form></div>'
    
    for i in items:
        badge_cls = "status-lost" if i['status'] == "LOST" else "status-found"
        html += f"""<div class="item-card">
            <span class="status-badge {badge_cls}">{i['status']}</span>
            <h3 style="margin:12px 0 5px 0;">{i['title']}</h3>
            <p style="font-size:14px; color:#64748b; margin-bottom:10px;">{i['description']}</p>
            """
        if i['file_name']:
            html += f'<img src="/uploads/{i["file_name"]}" class="item-img">'
        
        html += f"""<div style="font-size:11px; color:#94a3b8; margin-top:15px; border-top:1px solid #f1f5f9; padding-top:10px;">
                Reported by <b>{i['author']}</b> • {i['created_at']}
                {" | <a href='/delete/"+str(i['id'])+"' style='color:#ef4444; text-decoration:none;'>Remove</a>" if i['author']==session['user'] else ""}
            </div>
        </div>"""
    
    html += """</div><div class="bottom-nav">
        <a href="/home" class="nav-link active"><i data-lucide="home"></i><span class="nav-text">Home</span></a>
        <a href="/upload" class="nav-link"><i data-lucide="plus-circle"></i><span class="nav-text">Post</span></a>
        <a href="/profile" class="nav-link"><i data-lucide="user"></i><span class="nav-text">Profile</span></a>
    </div>""" + FOOTER
    conn.close()
    return html

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        f = request.files.get("file")
        fname = ""
        if f and f.filename != "":
            fname = str(uuid.uuid4())[:8] + "_" + secure_filename(f.filename)
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
        
        conn = get_db()
        conn.execute("INSERT INTO items (author, title, description, status, file_name, created_at) VALUES (?,?,?,?,?,?)",
                     (session["user"], request.form["title"], request.form["description"], request.form["status"], fname, datetime.now().strftime("%d %b")))
        conn.commit()
        return redirect("/home")
    
    return render_template_string(BASE_UI + """<div class="header">Report Item</div><div class="container"><div class="item-card" style="margin-top:20px;">
        <form method="POST" enctype="multipart/form-data">
            <select name="status" required>
                <option value="LOST">I Lost Something</option>
                <option value="FOUND">I Found Something</option>
            </select>
            <input name="title" placeholder="Item Name (e.g. Blue Titan Watch)" required>
            <textarea name="description" placeholder="Where and when? Add contact info..."></textarea>
            <input type="file" name="file">
            <button class="btn-submit" style="background:#ef4444;">Submit Report</button>
        </form>
    </div></div><div class="bottom-nav"><a href="/home">🏠</a><a href="/upload" class="active">➕</a><a href="/profile">👤</a></div>""" + FOOTER)

@app.route("/uploads/<f>")
def uploads(f):
    return send_from_directory(app.config["UPLOAD_FOLDER"], f)

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM items WHERE id=? AND author=?", (id, session["user"]))
    conn.commit()
    conn.close()
    return redirect("/home")

@app.route("/profile")
@login_required
def profile():
    return render_template_string(BASE_UI + f"""<div class="header">Account</div><div class="container" style="margin-top:20px; text-align:center;"><div class="item-card" style="padding:40px 20px;"><i data-lucide="user-circle" style="width:60px; height:60px; color:#ef4444; margin-bottom:15px;"></i><h2 style="margin:0;">{session['user']}</h2><a href="/logout" style="color:#ef4444; font-weight:700; text-decoration:none; margin-top:20px; display:inline-block;">Log Out</a></div></div><div class="bottom-nav"><a href="/home">🏠</a><a href="/upload">➕</a><a href="/profile" class="active">👤</a></div>""" + FOOTER)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

