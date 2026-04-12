import os
import uuid
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, session, render_template_string, send_from_directory, url_for, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Security: Hardcoded for quick start, change to os.environ.get for production
app.secret_key = "architect_master_secret_2026"

# --- CONFIG & DB ENGINE ---
UPLOAD_FOLDER = "uploads"
DB_NAME = "lostfound_architect.db"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None: db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, author TEXT, title TEXT, description TEXT, status TEXT, file_name TEXT, created_at TEXT)")
        db.commit()
init_db()

# --- LIQUID APPLE UI ENGINE ---
THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    :root {
        --bg: #f5f5f7; --card: rgba(255, 255, 255, 0.7); --text: #1d1d1f;
        --accent: #0071e3; --border: rgba(0,0,0,0.08); --blur: blur(30px);
        --liquid-1: #60a5fa; --liquid-2: #f472b6;
    }
    [data-theme="dark"] {
        --bg: #000000; --card: rgba(28, 28, 30, 0.7); --text: #f5f5f7;
        --accent: #0a84ff; --border: rgba(255,255,255,0.1);
        --liquid-1: #1e3a8a; --liquid-2: #701a75;
    }

    * { box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; -webkit-font-smoothing: antialiased; }
    body { margin: 0; background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }

    /* LIQUID BACKGROUND ANIMATION */
    .liquid-canvas {
        position: fixed; inset: 0; z-index: -1; filter: blur(100px); opacity: 0.4; pointer-events: none;
    }
    .blob { position: absolute; width: 60vw; height: 60vw; border-radius: 50%; animation: move 25s infinite alternate; }
    .blob-1 { background: var(--liquid-1); top: -10%; left: -10%; }
    .blob-2 { background: var(--liquid-2); bottom: -10%; right: -10%; animation-delay: -5s; }
    @keyframes move { from { transform: translate(0,0) scale(1); } to { transform: translate(15%, 15%) scale(1.2); } }

    /* RESPONSIVE AUTH ARCHITECTURE */
    .auth-viewport { height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .glass-auth-card {
        background: var(--card); backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
        border: 1px solid var(--border); border-radius: 40px;
        width: 100%; max-width: 440px; padding: 60px 45px;
        box-shadow: 0 40px 80px rgba(0,0,0,0.1); text-align: center;
    }

    /* DASHBOARD LAYOUT */
    .sidebar { 
        position: fixed; left: 0; top: 0; bottom: 0; width: 280px; 
        background: var(--card); backdrop-filter: var(--blur);
        border-right: 1px solid var(--border); padding: 50px 30px; display: none;
    }
    .main-view { margin-left: 0; padding: 40px 20px 120px; transition: 0.5s ease; }

    @media (min-width: 992px) {
        .sidebar { display: flex; flex-direction: column; }
        .main-view { margin-left: 280px; padding: 60px 8%; }
        .grid-layout { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 30px; }
        .mobile-nav { display: none !important; }
    }

    /* UI COMPONENTS */
    .btn-liquid {
        background: var(--accent); color: white; border: none; padding: 18px;
        border-radius: 18px; font-weight: 700; cursor: pointer; width: 100%;
        display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 16px;
        text-decoration: none;
    }
    .btn-liquid:hover { transform: scale(1.02); }
    .btn-delete {
        background: rgba(255, 59, 48, 0.1); color: #ff3b30; border: none;
        padding: 8px 16px; border-radius: 12px; font-weight: 700; font-size: 12px;
        text-decoration: none; cursor: pointer;
    }
    .btn-delete:hover { background: #ff3b30; color: white; }

    input, textarea, select {
        width: 100%; padding: 18px; border-radius: 16px; border: 1px solid var(--border);
        background: rgba(128,128,128,0.08); color: var(--text); margin-bottom: 20px; outline: none;
    }

    .mobile-nav {
        position: fixed; bottom: 30px; left: 20px; right: 20px;
        background: var(--card); backdrop-filter: var(--blur); border-radius: 30px;
        display: flex; justify-content: space-around; padding: 22px; border: 1px solid var(--border);
    }
</style>
"""

JS_LOGIC = """
<script>
    function toggleMode() {
        const h = document.documentElement;
        const next = h.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        h.setAttribute('data-theme', next);
        localStorage.setItem('architect_theme', next);
    }
    const saved = localStorage.getItem('architect_theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', saved);
</script>
"""

def wrap_pro(content, active="home"):
    return render_template_string(f"""
    <!DOCTYPE html>
    <html data-theme="light">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://unpkg.com/lucide@latest"></script>
        {THEME_CSS}{JS_LOGIC}
    </head>
    <body>
        <div class="liquid-canvas"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
        <div class="sidebar">
            <h1 style="font-size:30px; font-weight:800; color:var(--accent); letter-spacing:-1.5px; margin-bottom:50px;">LostFound</h1>
            <a href="/home" class="btn-liquid" style="background:{'var(--accent)' if active=='home' else 'transparent'}; color:{'white' if active=='home' else 'var(--text)'}; justify-content:flex-start; margin-bottom:15px; border:{'none' if active=='home' else '1px solid var(--border)'};"><i data-lucide="layout"></i> Dashboard</a>
            <a href="/upload" class="btn-liquid" style="background:{'var(--accent)' if active=='post' else 'transparent'}; color:{'white' if active=='post' else 'var(--text)'}; justify-content:flex-start; margin-bottom:15px; border:{'none' if active=='post' else '1px solid var(--border)'};"><i data-lucide="plus-circle"></i> New Report</a>
            <div style="margin-top:auto; display:flex; align-items:center; justify-content:space-between;">
                <button onclick="toggleMode()" style="background:none; border:none; color:var(--text); cursor:pointer;"><i data-lucide="moon"></i></button>
                <a href="/logout" style="color:#ff3b30; text-decoration:none; font-weight:800; font-size:12px;">Sign Out</a>
            </div>
        </div>
        <div class="main-view">
            <header style="display:flex; justify-content:space-between; align-items:center; margin-bottom:50px;">
                <h2 style="margin:0; font-size:40px; font-weight:800; letter-spacing:-2px;">{active.capitalize()}</h2>
                <button onclick="toggleMode()" style="background:var(--card); border:1px solid var(--border); color:var(--text); padding:10px; border-radius:12px; @media (min-width:992px){{display:none;}}"><i data-lucide="sun"></i></button>
            </header>
            {content}
        </div>
        <div class="mobile-nav">
            <a href="/home" style="color:{'var(--accent)' if active=='home' else '#8e8e93'}"><i data-lucide="layout"></i></a>
            <a href="/upload" style="color:{'var(--accent)' if active=='post' else '#8e8e93'}"><i data-lucide="plus-circle"></i></a>
            <a href="/profile" style="color:{'var(--accent)' if active=='profile' else '#8e8e93'}"><i data-lucide="user"></i></a>
        </div>
        <script>lucide.createIcons();</script>
    </body>
    </html>""")

# --- ROUTES ---

@app.route("/")
def auth():
    if "user" in session: return redirect("/home")
    msg = request.args.get("msg", "")
    return render_template_string(f"""
    <html><head>{THEME_CSS}{JS_LOGIC}</head><body>
    <div class="liquid-canvas"><div class="blob blob-1"></div><div class="blob blob-2"></div></div>
    <div class="auth-viewport">
        <div class="glass-auth-card">
            <div style="width:70px; height:70px; background:var(--accent); border-radius:20px; margin:0 auto 30px; display:flex; align-items:center; justify-content:center; color:white;"><i data-lucide="shield-check"></i></div>
            <h1 style="font-size:32px; font-weight:800; letter-spacing:-1.5px; margin:0;">LostFound Pro</h1>
            <p style="opacity:0.5; margin-bottom:40px;">Professional Retrieval Network</p>
            {f'<div style="background:rgba(0,113,227,0.1); padding:15px; border-radius:15px; margin-bottom:20px; color:var(--accent); font-weight:700;">{msg}</div>' if msg else ""}
            <form action="/login" method="POST">
                <input name="username" placeholder="Username" required autocomplete="off">
                <input type="password" name="password" placeholder="Password" required>
                <button class="btn-liquid">Access Dashboard <i data-lucide="arrow-right"></i></button>
            </form>
            <p style="margin-top:25px; font-size:14px; opacity:0.6;">Identity not found? <a href="/signup" style="color:var(--accent); text-decoration:none; font-weight:700;">Create Profile</a></p>
        </div>
    </div><script src="https://unpkg.com/lucide@latest"></script><script>lucide.createIcons();</script></body></html>""")

@app.route("/login", methods=["POST"])
def login():
    u, p = request.form["username"], request.form["password"]
    db = get_db(); user = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
    if not user: return redirect(url_for('auth', msg="User account not found. Please register."))
    if check_password_hash(user["password"], p): session["user"] = u; return redirect("/home")
    return redirect(url_for('auth', msg="Invalid security credentials."))

@app.route("/home")
def home():
    if "user" not in session: return redirect("/")
    db = get_db(); items = db.execute("SELECT * FROM items ORDER BY id DESC").fetchall()
    cards = ""
    for i in items:
        status_bg = "var(--accent)" if i['status'] == 'LOST' else "#34c759"
        img = f'<img src="/uploads/{i["file_name"]}" style="width:100%; height:280px; object-fit:cover;">' if i['file_name'] else '<div style="height:280px; background:rgba(128,128,128,0.1); display:flex; align-items:center; justify-content:center;"><i data-lucide="package" style="width:40px; height:40px; color:#8e8e93;"></i></div>'
        del_btn = f'<a href="/delete/{i["id"]}" class="btn-delete" onclick="return confirm(\'Permanently remove this report?\')">Delete</a>' if i['author'] == session['user'] else ""
        cards += f"""
        <div style="background:var(--card); backdrop-filter:blur(30px); border:1px solid var(--border); border-radius:35px; overflow:hidden; margin-bottom:30px;">
            <div style="position:relative;">{img}<span style="position:absolute; bottom:20px; left:20px; background:{status_bg}; color:white; padding:8px 16px; border-radius:15px; font-size:11px; font-weight:800;">{i['status']}</span></div>
            <div style="padding:30px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; font-size:26px; font-weight:800; letter-spacing:-1px;">{i['title']}</h3>
                    {del_btn}
                </div>
                <p style="opacity:0.6; line-height:1.6; margin-top:10px;">{i['description']}</p>
                <div style="display:flex; justify-content:space-between; margin-top:20px; padding-top:20px; border-top:1px solid var(--border); font-size:11px; font-weight:700; opacity:0.4;">
                    <span>REPORTED BY {i['author'].upper()}</span><span>{i['created_at'].upper()}</span>
                </div>
            </div>
        </div>"""
    return wrap_pro(f'<div class="grid-layout">{cards or "No reports found."}</div>', "home")

@app.route("/delete/<int:item_id>")
def delete(item_id):
    if "user" not in session: return redirect("/")
    db = get_db(); db.execute("DELETE FROM items WHERE id=? AND author=?", (item_id, session["user"])); db.commit()
    return redirect("/home")

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session: return redirect("/")
    if request.method == "POST":
        f = request.files.get("file"); fname = ""
        if f and f.filename:
            fname = f"{uuid.uuid4().hex[:8]}_{secure_filename(f.filename)}"
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
        db = get_db(); db.execute("INSERT INTO items (author, title, description, status, file_name, created_at) VALUES (?,?,?,?,?,?)", (session["user"], request.form["title"], request.form["description"], request.form["status"], fname, datetime.now().strftime("%B %d, %Y"))); db.commit()
        return redirect("/home")
    return wrap_pro("""
        <div style="background:var(--card); border:1px solid var(--border); border-radius:40px; max-width:700px; margin:0 auto; padding:50px;">
            <form method="POST" enctype="multipart/form-data">
                <select name="status"><option value="LOST">Lost</option><option value="FOUND">Found</option></select>
                <input name="title" placeholder="Item Identification" required>
                <textarea name="description" placeholder="Specify location and contact details..." style="height:150px;"></textarea>
                <input type="file" name="file" style="border:none; background:none;">
                <button class="btn-liquid">Publish Official Report</button>
            </form>
        </div>""", "post")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?,?)", (request.form["username"], generate_password_hash(request.form["password"])))
            db.commit(); return redirect(url_for('auth', msg="Account Created! Proceed to Sign In."))
        except: return redirect(url_for('signup', msg="Username unavailable."))
    return render_template_string(f"<html><head>{THEME_CSS}{JS_LOGIC}</head><body><div class='auth-viewport'><div class='glass-auth-card'><h2>Register</h2><form method='POST'><input name='username' placeholder='New Username' required><input type='password' name='password' placeholder='Secure Password' required><button class='btn-liquid'>Register Profile</button></form></div></div></body></html>")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

@app.route("/uploads/<f>")
def uploads(f): return send_from_directory(app.config["UPLOAD_FOLDER"], f)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
