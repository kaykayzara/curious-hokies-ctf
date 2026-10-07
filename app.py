from flask import Flask, request, jsonify, session, render_template, make_response
from flask_cors import CORS
import sqlite3
import bcrypt
import os
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'hokie-curious-ctf-secret-2026')
CORS(app, supports_credentials=True)

DB_PATH = 'ctf.db'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'hokieadmin2026')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Global competition config/timer table
    c.execute('''CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('start_time', '0')")
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('duration_seconds', '1800')") # 30 mins = 1800s
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('remaining_seconds', '1800')")
    c.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('is_active', '0')")

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        points INTEGER NOT NULL,
        flag TEXT NOT NULL,
        hint TEXT,
        active INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        challenge_id INTEGER NOT NULL,
        flag TEXT NOT NULL,
        correct INTEGER NOT NULL,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (challenge_id) REFERENCES challenges(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS solves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        challenge_id INTEGER NOT NULL,
        solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, challenge_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (challenge_id) REFERENCES challenges(id)
    )''')
    conn.commit()

    challenges = [
        # Ethical Hacking
        ("SQLi Gatekeeper",
         "The mock VT Department Portal login is vulnerable to classic SQL injection. Bypass authentication without knowing the password to reveal the flag.<br><br><a href='/challenge/sqli' target='_blank' style='color:#E5751F;font-weight:bold;'>Launch Target Portal →</a>",
         "Ethical Hacking", 125, "HOKIE{sql_injection_master}",
         "Think about how strings close in SQL: try entering ' OR '1'='1 in the username field."),
        
        ("Free Campus Gear",
         "The campus merchandise checkout page trusts client input. Inspect the page elements, tamper with the hidden form value, and purchase the hoodie for $0!<br><br><a href='/challenge/store' target='_blank' style='color:#E5751F;font-weight:bold;'>Open Campus Store →</a>",
         "Ethical Hacking", 75, "HOKIE{client_side_tampering}",
         "Right-click the Buy button -> Inspect Element. Find <input type='hidden' name='price' value='100'> and modify value to '0'."),

        ("The Secret Vault",
         "The web server has a crawler exclusion file. What path is restricted from web crawlers?<br><br><a href='/challenge/robots-site' target='_blank' style='color:#E5751F;font-weight:bold;'>Open Challenge Server →</a>",
         "Ethical Hacking", 100, "HOKIE{robots_cannot_hide}",
         "Add /robots.txt to the end of the site URL, read the disallowed folder path, and visit that path."),

        # Computer Science
        ("AP Loop Trace",
         "Trace the output of this Python slicing snippet:<br><br><pre style='background:#111;padding:10px;border-left:3px solid #861F41;color:#eee;'>word = 'H1o0k2i4e6_8C!y@b#e$r%'\nflag = word[::2]\n# format: HOKIE{result}</pre>",
         "Computer Science", 50, "HOKIE{hokie_cyber}",
         "Paste the code into <a href='https://www.online-python.com/' target='_blank' style='color:#E5751F;font-weight:bold;'>Online Python Compiler</a>. Remember: Python stores variables in memory silently—add a print statement to display the result on screen!"),

        ("Logic Gate Circuit",
         "An access lock opens when the circuit evaluates to <strong>True</strong>:<br><br><code style='background:#111;padding:8px 12px;border-left:3px solid #E5751F;display:block;color:#eee;'>(A and not B) and (C or not D)</code><br>Determine the binary values (1=True, 0=False). For (C or not D), assume both inputs are in optimal active state (C=1, D=0).<br><br>Map each input to its keyword to form the 4-word flag:<br>• <strong>A:</strong> 1 = alpha, 0 = amber<br>• <strong>B:</strong> 1 = bravo, 0 = burnt<br>• <strong>C:</strong> 1 = chicago, 0 = copper<br>• <strong>D:</strong> 1 = delta, 0 = drillfield",
         "Computer Science", 75, "HOKIE{alpha_burnt_chicago_drillfield}",
         "For (A and not B) to be True, A must be 1 and B must be 0 (so that not B becomes 1). For (C or not D), C is 1 and D is 0. Combine the 4 matching words in order!"),

        # Cybersecurity
        ("Burnt Orange Hex",
         "Decode this hex string to reveal the secret pass:<br><br><code style='background:#111;padding:8px;border-radius:4px;display:block;word-break:break-all;'>484f4b49457b63796265725f686f6b6965735f72756c657d</code><br><br>🔧 Tool: <a href='https://gchq.github.io/CyberChef' target='_blank' style='color:#E5751F;'>Open CyberChef</a> (Recipe: 'From Hex')",
         "Cybersecurity", 50, "HOKIE{cyber_hokies_rule}",
         "In CyberChef, search for the 'From Hex' recipe and drag it into Recipe."),

        ("Caesar at Lane Stadium",
         "Julius Caesar shifted his messages. Decode this (ROT13):<br><br><code style='background:#111;padding:8px;border-radius:4px;display:block;'>UBXVR{ynar_fgnqvhz_abvfr}</code><br><br>🔧 Tool: <a href='https://gchq.github.io/CyberChef' target='_blank' style='color:#E5751F;'>Open CyberChef</a> (Recipe: 'ROT13')",
         "Cybersecurity", 75, "HOKIE{lane_stadium_noise}",
         "Use the ROT13 recipe in CyberChef to reverse the 13-character shift."),

        ("Inspect Response Headers",
         "Click the ping link and check the HTTP Response Headers in your DevTools Network tab.<br><br><a href='/challenge/header-ping' target='_blank' style='color:#E5751F;font-weight:bold;'>Send Network Ping →</a>",
         "Cybersecurity", 75, "HOKIE{http_header_spotted}",
         "Press F12 -> Network Tab -> Refresh -> Click the request -> Look at 'Response Headers' for X-Hokie-Flag.")
    ]
    c.executemany("""
        INSERT INTO challenges (name, description, category, points, flag, hint)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET
            description=excluded.description,
            category=excluded.category,
            points=excluded.points,
            flag=excluded.flag,
            hint=excluded.hint,
            active=1
    """, challenges)
    conn.commit()
    conn.close()

# ── AUTH ROUTES ──────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'success': True, 'username': username})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already taken'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not user or not bcrypt.checkpw(password.encode(), user['password'].encode()):
        return jsonify({'error': 'Invalid username or password'}), 401
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({'success': True, 'username': username})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me')
def me():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn = get_db()
    user = conn.execute("SELECT id, username, score FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 401
    return jsonify({'id': user['id'], 'username': user['username'], 'score': user['score']})

# ── GLOBAL SYNCHRONIZED TIMER API ─────────────────────────────
@app.route('/api/timer')
def get_timer():
    conn = get_db()
    rows = dict(conn.execute("SELECT key, value FROM config").fetchall())
    conn.close()
    
    is_active = rows.get('is_active') == '1'
    start_time = float(rows.get('start_time', 0))
    duration = int(rows.get('duration_seconds', 1800))
    remaining_saved = int(rows.get('remaining_seconds', duration))
    
    if start_time == 0:
        return jsonify({'status': 'waiting', 'remaining': duration, 'active': False})
    
    if not is_active:
        return jsonify({'status': 'paused', 'remaining': remaining_saved, 'active': False})
    
    elapsed = time.time() - start_time
    remaining = max(0, int(remaining_saved - elapsed))
    
    if remaining <= 0:
        return jsonify({'status': 'ended', 'remaining': 0, 'active': False})
        
    return jsonify({'status': 'running', 'remaining': remaining, 'active': True})

@app.route('/api/admin/timer', methods=['POST'])
def admin_timer_control():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    action = (request.json or {}).get('action')
    conn = get_db()
    rows = dict(conn.execute("SELECT key, value FROM config").fetchall())
    duration = int(rows.get('duration_seconds', 1800))
    
    if action == 'start':
        conn.execute("UPDATE config SET value=? WHERE key='start_time'", (str(time.time()),))
        conn.execute("UPDATE config SET value='1' WHERE key='is_active'")
    elif action == 'pause':
        start_time = float(rows.get('start_time', 0))
        remaining_saved = int(rows.get('remaining_seconds', duration))
        if start_time > 0 and rows.get('is_active') == '1':
            elapsed = time.time() - start_time
            new_remaining = max(0, int(remaining_saved - elapsed))
        else:
            new_remaining = remaining_saved
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('remaining_seconds', ?)", (str(new_remaining),))
        conn.execute("UPDATE config SET value='0' WHERE key='is_active'")
    elif action == 'reset':
        conn.execute("UPDATE config SET value='0' WHERE key='start_time'")
        conn.execute("UPDATE config SET value='0' WHERE key='is_active'")
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('duration_seconds', '1800')")
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('remaining_seconds', '1800')")
          
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── CHALLENGE SUBMISSIONS ────────────────────────────────────
@app.route('/api/challenges')
def get_challenges():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn = get_db()
    challenges = conn.execute("SELECT id, name, description, category, points, hint FROM challenges WHERE active=1").fetchall()
    solves = conn.execute("SELECT challenge_id FROM solves WHERE user_id=?", (session['user_id'],)).fetchall()
    solve_counts = conn.execute("SELECT challenge_id, COUNT(*) as count FROM solves GROUP BY challenge_id").fetchall()
    conn.close()
    solved_ids = {s['challenge_id'] for s in solves}
    solve_count_map = {s['challenge_id']: s['count'] for s in solve_counts}
    
    result = []
    for ch in challenges:
        result.append({
            'id': ch['id'],
            'name': ch['name'],
            'description': ch['description'],
            'category': ch['category'],
            'points': ch['points'],
            'hint': ch['hint'],
            'solved': ch['id'] in solved_ids,
            'solves': solve_count_map.get(ch['id'], 0)
        })
    return jsonify(result)

@app.route('/api/submit', methods=['POST'])
def submit_flag():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json or {}
    challenge_id = data.get('challenge_id')
    submitted_flag = data.get('flag', '').strip()

    conn = get_db()
    existing = conn.execute("SELECT id FROM solves WHERE user_id=? AND challenge_id=?",
                           (session['user_id'], challenge_id)).fetchone()
    if existing:
        conn.close()
        return jsonify({'error': 'Already solved!'}), 400

    challenge = conn.execute("SELECT * FROM challenges WHERE id=? AND active=1", (challenge_id,)).fetchone()
    if not challenge:
        conn.close()
        return jsonify({'error': 'Challenge not found'}), 404

    correct = submitted_flag.lower() == challenge['flag'].strip().lower()
    conn.execute("INSERT INTO submissions (user_id, challenge_id, flag, correct) VALUES (?,?,?,?)",
                (session['user_id'], challenge_id, submitted_flag, 1 if correct else 0))
    if correct:
        conn.execute("INSERT INTO solves (user_id, challenge_id) VALUES (?,?)",
                    (session['user_id'], challenge_id))
        conn.execute("UPDATE users SET score = score + ? WHERE id=?",
                    (challenge['points'], session['user_id']))
    conn.commit()
    conn.close()

    if correct:
        return jsonify({'success': True, 'message': f'Hokie Touchdown! +{challenge["points"]} pts!'})
    return jsonify({'success': False, 'message': 'Incorrect flag. Check formatting and retry.'}), 400

# ── LEADERBOARD ──────────────────────────────────────────────
@app.route('/api/leaderboard')
def leaderboard():
    conn = get_db()
    users = conn.execute("""
        SELECT u.username, u.score, COUNT(s.id) as solves
        FROM users u
        LEFT JOIN solves s ON u.id = s.user_id
        GROUP BY u.id
        ORDER BY u.score DESC, MIN(s.solved_at) ASC
    """).fetchall()
    conn.close()
    return jsonify([{'rank': i+1, 'username': u['username'], 'score': u['score'], 'solves': u['solves']}
                   for i, u in enumerate(users)])

# ── ADMIN ROUTES ─────────────────────────────────────────────
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json or {}
    if data.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid admin password'}), 401

@app.route('/api/admin/submissions')
def admin_submissions():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    subs = conn.execute("""
        SELECT u.username, c.name as challenge, s.flag, s.correct, s.submitted_at
        FROM submissions s
        JOIN users u ON s.user_id = u.id
        JOIN challenges c ON s.challenge_id = c.id
        ORDER BY s.submitted_at DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([dict(s) for s in subs])

@app.route('/api/admin/reset', methods=['POST'])
def admin_reset():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db()
    conn.execute("UPDATE users SET score=0")
    conn.execute("DELETE FROM solves")
    conn.execute("DELETE FROM submissions")
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── INTERACTIVE TARGET ROUTES ────────────────────────────────
@app.route('/challenge/sqli', methods=['GET', 'POST'])
def target_sqli():
    msg = ""
    success = False
    if request.method == 'POST':
        uname = request.form.get('username', '')
        if "' or '" in uname.lower() or "' or 1=1" in uname.lower() or "admin'--" in uname.lower():
            success = True
            msg = "AUTHENTICATION BYPASS DETECTED<br>Welcome, Root Administrator.<br><br>FLAG: <span style='color:#00ff66;font-size:16px;'>HOKIE{sql_injection_master}</span>"
        else:
            msg = "ACCESS DENIED // Invalid credentials or database query rejected."
            
    return f'''<!DOCTYPE html>
<html>
<head>
  <title>VT Central Authentication Service</title>
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      background: radial-gradient(circle at 50% 30%, #20040B 0%, #0A0103 100%);
      color: #eee; font-family:'Share Tech Mono', monospace; min-height:100vh;
      display:flex; align-items:center; justify-content:center; padding:20px;
    }}
    .panel {{
      width:100%; max-width:440px; background:rgba(20,4,10,0.95);
      border:1px solid #861F41; box-shadow:0 0 35px rgba(134,31,65,0.4);
      border-radius:4px; overflow:hidden;
    }}
    .panel-hdr {{
      background:#861F41; padding:12px 18px; display:flex; justify-content:space-between; align-items:center;
    }}
    .panel-hdr h3 {{ font-family:'Orbitron', monospace; font-size:13px; color:#fff; letter-spacing:1px; }}
    .status-dot {{ width:8px; height:8px; background:#00ff66; border-radius:50%; box-shadow:0 0 8px #00ff66; }}
    .panel-body {{ padding:28px 24px; }}
    .tagline {{ color:#E5751F; font-size:12px; margin-bottom:16px; text-transform:uppercase; letter-spacing:1.5px; }}
    .form-group {{ margin-bottom:14px; text-align:left; }}
    label {{ display:block; font-size:11px; color:#aaa; margin-bottom:6px; letter-spacing:1px; }}
    input {{
      width:100%; padding:11px 14px; background:#0e0205; border:1px solid #441120;
      color:#fff; font-family:'Share Tech Mono', monospace; font-size:14px; outline:none;
    }}
    input:focus {{ border-color:#E5751F; box-shadow:0 0 8px rgba(229,117,31,0.3); }}
    button {{
      width:100%; background:#E5751F; color:#000; font-family:'Orbitron', monospace;
      font-size:12px; font-weight:bold; padding:12px; border:none; cursor:pointer;
      letter-spacing:1px; margin-top:8px; transition:0.2s;
    }}
    button:hover {{ background:#ff8c37; box-shadow:0 0 14px rgba(229,117,31,0.5); }}
    .result-box {{
      margin-top:18px; padding:12px; font-size:12px; line-height:1.5;
      background: {'rgba(0,255,102,0.08)' if success else 'rgba(255,68,68,0.08)'};
      border-left: 3px solid {'#00ff66' if success else '#ff4444'};
      color: {'#00ff66' if success else '#ff6666'};
    }}
  </style>
</head>
<body>
  <div class="panel">
    <div class="panel-hdr">
      <h3>VT AUTH // GATEWAY-01</h3>
      <div class="status-dot"></div>
    </div>
    <div class="panel-body">
      <div class="tagline">Restricted Department Portal</div>
      <form method="POST">
        <div class="form-group">
          <label>CAMPUS PID / USERNAME</label>
          <input type="text" name="username" placeholder="e.g. hokie_admin" required autocomplete="off">
        </div>
        <div class="form-group">
          <label>ACCESS KEY / PASSWORD</label>
          <input type="password" name="password" placeholder="••••••••••••">
        </div>
        <button type="submit">AUTHORIZE SESSION</button>
      </form>
      {'<div class="result-box">' + msg + '</div>' if msg else ''}
    </div>
  </div>
</body>
</html>'''

@app.route('/challenge/store', methods=['GET', 'POST'])
def target_store():
    feedback = ""
    is_success = False
    if request.method == 'POST':
        price = request.form.get('price', '100')
        if price == '0':
            is_success = True
            feedback = "TRANSACTION APPROVED ($0.00)<br>Order dispatched! Flag: <strong style='color:#00ff66;'>HOKIE{client_side_tampering}</strong>"
        else:
            feedback = f"TRANSACTION REJECTED: Insufficient balance. Your Hokie Wallet has $0.00, but checkout total is ${price}.00."

    return f'''<!DOCTYPE html>
<html>
<head>
  <title>VT Campus Gear Vault</title>
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      background: radial-gradient(circle at 50% 30%, #1c050c 0%, #080104 100%);
      color: #eee; font-family:'Share Tech Mono', monospace; min-height:100vh;
      display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px;
    }}
    .store-card {{
      max-width:400px; width:100%; background:rgba(20,5,11,0.95);
      border:1px solid #861F41; border-radius:8px; box-shadow:0 0 35px rgba(134,31,65,0.4);
      overflow:hidden; text-align:center;
    }}
    .badge {{ background:#861F41; color:#fff; font-size:11px; padding:8px; letter-spacing:1.5px; font-weight:bold; }}
    .card-content {{ padding:24px; }}

    /* Holographic 3D Spinning Hoodie Showcase */
    .showcase-stage {{
      perspective: 900px;
      width: 100%;
      height: 180px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 12px;
    }}
    .hoodie-hologram {{
      width: 140px;
      height: 160px;
      animation: holoSpin 7s ease-in-out infinite alternate;
      transform-style: preserve-3d;
      filter: drop-shadow(0 10px 20px rgba(134,31,65,0.6));
    }}
    @keyframes holoSpin {{
      0%   {{ transform: rotateY(-32deg) rotateX(8deg); }}
      50%  {{ transform: rotateY(0deg) translateY(-8px); }}
      100% {{ transform: rotateY(32deg) rotateX(-8deg); }}
    }}

    h2 {{ font-family:'Orbitron', monospace; font-size:18px; color:#fff; margin-bottom:6px; }}
    .price-tag {{ font-size:26px; color:#E5751F; font-weight:bold; margin-bottom:12px; }}
    .wallet-box {{
      background:rgba(0,0,0,0.5); padding:10px; border:1px dashed #555;
      font-size:12px; color:#aaa; margin-bottom:18px;
    }}
    button {{
      width:100%; background:#E5751F; color:#000; font-family:'Orbitron', monospace;
      font-size:12px; font-weight:bold; padding:12px; border:none; cursor:pointer;
      transition:0.2s;
    }}
    button:hover {{ background:#ff8c37; box-shadow:0 0 14px rgba(229,117,31,0.5); }}
    .alert {{
      margin-top:16px; padding:12px; font-size:12px; line-height:1.5;
      background: {'rgba(0,255,102,0.1)' if is_success else 'rgba(255,68,68,0.1)'};
      border-left: 3px solid {'#00ff66' if is_success else '#ff4444'};
      color: {'#00ff66' if is_success else '#ff7777'};
    }}
  </style>
</head>
<body>
  <div class="store-card">
    <div class="badge">OFFICIAL HOKIE MERCHANDISE</div>
    <div class="card-content">
      
      <!-- Embedded Cyber VT Hoodie Vector -->
      <div class="showcase-stage">
        <svg class="hoodie-hologram" viewBox="0 0 200 220" fill="none" xmlns="http://www.w3.org/2000/svg">
          <ellipse cx="100" cy="205" rx="55" ry="10" fill="#000" opacity="0.4"/>
          <path d="M50 70 L30 170 L65 175 L70 200 L130 200 L135 175 L170 170 L150 70 L125 50 L75 50 Z" fill="#6B132F" stroke="#861F41" stroke-width="3"/>
          <path d="M50 70 L10 135 L30 148 L55 95 Z" fill="#500E23"/>
          <path d="M150 70 L190 135 L170 148 L145 95 Z" fill="#500E23"/>
          <path d="M75 50 Q100 20 125 50 Q100 75 75 50 Z" fill="#3D0A1B" stroke="#861F41" stroke-width="2"/>
          <path d="M90 62 L88 105" stroke="#E5751F" stroke-width="3" stroke-linecap="round"/>
          <path d="M110 62 L112 105" stroke="#E5751F" stroke-width="3" stroke-linecap="round"/>
          <path d="M75 140 L125 140 L130 175 L70 175 Z" fill="#5A1027" stroke="#861F41" stroke-width="2"/>
          <text x="100" y="112" font-family="'Orbitron', sans-serif" font-weight="900" font-size="20" fill="#E5751F" text-anchor="middle" letter-spacing="1">VT</text>
          <text x="100" y="125" font-family="'Share Tech Mono', monospace" font-weight="bold" font-size="8" fill="#FFF" text-anchor="middle" letter-spacing="2">HOKIES</text>
        </svg>
      </div>

      <h2>VT Cyber Maroon Hoodie</h2>
      <div class="price-tag">$100.00</div>
      
      <div class="wallet-box">
        HOKIE WALLET BALANCE: <strong style="color:#ff6666;">$0.00</strong>
      </div>

      <form method="POST">
        <!-- Target Parameter for Inspection: Change 100 to 0 -->
        <input type="hidden" name="price" value="100">
        <button type="submit">CHECKOUT / BUY ITEM</button>
      </form>

      {'<div class="alert">' + feedback + '</div>' if feedback else ''}
    </div>
  </div>
</body>
</html>'''

# ── FLEXIBLE ROBOTS TARGET & VAULT ROUTES ────────────────────
@app.route('/challenge/robots-site')
@app.route('/challenge/robots-site/')
def target_robots():
    robot_svg = '''
    <svg class="mech-svg" viewBox="0 0 100 90" fill="none" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="50" cy="85" rx="36" ry="5" fill="#E5751F" opacity="0.3" class="ground-shadow"/>
      <polygon points="20,40 32,22 68,22 80,40 72,66 28,66" fill="#1C1D24" stroke="#861F41" stroke-width="2.5"/>
      <polygon points="32,22 68,22 60,38 40,38" fill="#2E303E"/>
      <polygon points="20,40 40,38 28,66" fill="#14151B"/>
      <polygon points="80,40 60,38 72,66" fill="#262833"/>
      <rect x="42" y="44" width="16" height="14" rx="2" fill="#0A0B0E" stroke="#555" stroke-width="1.5"/>
      <line x1="45" y1="48" x2="55" y2="48" stroke="#E5751F" stroke-width="1.5"/>
      <line x1="45" y1="52" x2="55" y2="52" stroke="#E5751F" stroke-width="1.5"/>
      <rect x="30" y="27" width="40" height="7" rx="3.5" fill="#0A0B0E" stroke="#861F41" stroke-width="1"/>
      <rect class="visor-laser" x="33" y="29" width="34" height="3" rx="1.5" fill="#E5751F"/>
      <line x1="50" y1="22" x2="50" y2="10" stroke="#8E9094" stroke-width="2"/>
      <circle class="antenna-beacon" cx="50" cy="8" r="3.5" fill="#FF3300"/>
      <path class="leg-l1" d="M22 52 L6 62 L4 80" stroke="#75787B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <path class="leg-l2" d="M26 62 L14 74 L16 84" stroke="#505257" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <path class="leg-r1" d="M78 52 L94 62 L96 80" stroke="#75787B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <path class="leg-r2" d="M74 62 L86 74 L84 84" stroke="#505257" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    '''

    return f'''<!DOCTYPE html>
<html>
<head>
  <title>Hokie Central — Web Hub</title>
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      background: radial-gradient(circle at 50% 40%, #1A030A 0%, #070103 100%);
      color: #8E9094; font-family:'Share Tech Mono', monospace;
      min-height:100vh; overflow:hidden; position:relative;
      display:flex; flex-direction:column; align-items:center; justify-content:center;
    }}
    .radar-grid {{
      position: absolute; inset:0;
      background-image: 
        linear-gradient(rgba(134,31,65,0.08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(134,31,65,0.08) 1px, transparent 1px);
      background-size: 50px 50px;
      pointer-events: none;
    }}
    .hub-content {{
      position: relative; z-index: 10; text-align: center;
      padding: 30px 40px; background: rgba(14, 2, 6, 0.85);
      border: 1px solid rgba(134,31,65,0.6); border-radius: 6px;
      box-shadow: 0 0 40px rgba(134,31,65,0.3);
    }}
    h1 {{ font-family:'Orbitron', monospace; color:#D13867; font-size:28px; letter-spacing:2px; margin-bottom:8px; }}
    p {{ color:#aaa; font-size:14px; letter-spacing:1px; }}

    .crawler-lane {{ position: absolute; width:100%; height:110px; pointer-events: none; }}
    .lane-top {{ top: 12%; }}
    .lane-mid {{ top: 48%; opacity: 0.35; filter: blur(0.5px) scale(0.65); z-index: 2; }}
    .lane-bot {{ bottom: 12%; }}

    .mech-unit {{ position: absolute; width: 110px; height: 100px; animation: marchAcross linear infinite; }}
    .mech-svg {{ width: 100%; height: 100%; filter: drop-shadow(0 6px 14px rgba(0,0,0,0.8)); }}
    .mech-fast {{ animation-duration: 10s; }}
    .mech-med  {{ animation-duration: 14s; animation-delay: 4s; }}
    .mech-rev  {{ animation-duration: 12s; animation-name: marchReverse; transform: scaleX(-1); }}

    .antenna-beacon {{ animation: pulseLight 0.8s infinite alternate; }}
    .visor-laser {{ animation: laserSweep 1.5s infinite alternate; }}

    @keyframes pulseLight {{
      from {{ fill: #FF1A00; filter: drop-shadow(0 0 2px #FF1A00); }}
      to   {{ fill: #00FF66; filter: drop-shadow(0 0 8px #00FF66); }}
    }}
    @keyframes laserSweep {{
      from {{ fill: #E5751F; opacity: 0.7; }}
      to   {{ fill: #FF0055; opacity: 1; filter: drop-shadow(0 0 6px #FF0055); }}
    }}
    @keyframes marchAcross {{
      0%   {{ left: -140px; transform: translateY(0px); }}
      25%  {{ transform: translateY(-4px); }}
      50%  {{ transform: translateY(0px); }}
      75%  {{ transform: translateY(-4px); }}
      100% {{ left: 105vw; transform: translateY(0px); }}
    }}
    @keyframes marchReverse {{
      0%   {{ right: -140px; transform: scaleX(-1) translateY(0px); }}
      25%  {{ transform: scaleX(-1) translateY(-4px); }}
      50%  {{ transform: scaleX(-1) translateY(0px); }}
      75%  {{ transform: scaleX(-1) translateY(-4px); }}
      100% {{ right: 105vw; transform: scaleX(-1) translateY(0px); }}
    }}
  </style>
</head>
<body>
  <div class="radar-grid"></div>
  <div class="crawler-lane lane-top">
    <div class="mech-unit mech-fast">{robot_svg}</div>
  </div>
  <div class="crawler-lane lane-mid">
    <div class="mech-unit mech-rev" style="animation-duration: 18s;">{robot_svg}</div>
  </div>
  <div class="hub-content">
    <h1>// HOKIE WEB HUB</h1>
    <p>Search engine crawlers index this portal publicly.</p>
  </div>
  <div class="crawler-lane lane-bot">
    <div class="mech-unit mech-med mech-rev">{robot_svg}</div>
  </div>
</body>
</html>'''

@app.route('/robots.txt')
@app.route('/challenge/robots-site/robots.txt')
@app.route('/challenge/robots.txt')
def target_robots_file():
    return "User-agent: *\nDisallow: /restricted-drillfield-vault/\n", 200, {'Content-Type': 'text/plain'}

# Comprehensive aliases so students can append without 404 errors
@app.route('/restricted-drillfield-vault/')
@app.route('/restricted-drillfield-vault')
@app.route('/challenge/robots-site/restricted-drillfield-vault/')
@app.route('/challenge/robots-site/restricted-drillfield-vault')
@app.route('/challenge/restricted-drillfield-vault/')
@app.route('/challenge/restricted-drillfield-vault')
@app.route('/robots.txt/restricted-drillfield-vault/')
@app.route('/robots.txt/restricted-drillfield-vault')
@app.route('/challenge/robots-site/robots.txt/restricted-drillfield-vault/')
@app.route('/challenge/robots-site/robots.txt/restricted-drillfield-vault')
def target_drillfield_vault():
    return '''<!DOCTYPE html>
<html>
<head>
  <title>Restricted Drillfield Archive</title>
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing:border-box; margin:0; padding:0; }
    body {
      background:#080104; color:#00ff66; font-family:'Share Tech Mono', monospace;
      min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px;
    }
    .vault-box {
      max-width:520px; width:100%; border:1px solid #00ff66; background:rgba(0,255,102,0.03);
      box-shadow:0 0 30px rgba(0,255,102,0.2); padding:32px; text-align:center;
    }
    h1 { font-family:'Orbitron', monospace; font-size:20px; margin-bottom:14px; letter-spacing:2px; }
    p { color:#bbb; font-size:13px; line-height:1.6; margin-bottom:20px; }
    .flag {
      background:#111; border:1px dashed #00ff66; padding:12px;
      font-size:16px; font-weight:bold; color:#fff; word-break:break-all;
    }
  </style>
</head>
<body>
  <div class="vault-box">
    <h1>// VAULT UNLOCKED</h1>
    <p>Crawler Exclusion Protocol bypassed successfully.<br>Classified archive index accessed.</p>
    <div class="flag">HOKIE{robots_cannot_hide}</div>
  </div>
</body>
</html>'''

@app.route('/challenge/header-ping')
def target_header_ping():
    resp = make_response("<body style='background:#0d0d0d;color:#fff;font-family:monospace;padding:40px;'><h2>Ping response received! Check DevTools Network Headers.</h2></body>")
    resp.headers['X-Hokie-Flag'] = 'HOKIE{http_header_spotted}'
    return resp

# ── PAGES ────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)