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
         "Right-click the Buy button -> Inspect Element. Find <input type='hidden' name='price' value='50'> and modify value to '0'."),

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
    if request.method == 'POST':
        uname = request.form.get('username', '')
        if "' or '" in uname.lower() or "' or 1=1" in uname.lower() or "admin'--" in uname.lower():
            msg = "ACCESS GRANTED! Welcome SuperAdmin. Flag: <strong>HOKIE{sql_injection_master}</strong>"
        else:
            msg = "Access Denied: Invalid credentials."
    return f'''<!DOCTYPE html>
<html>
<head><title>VT Admin Portal</title>
<style>
  body{{background:#0d0d0d;color:#fff;font-family:monospace;padding:40px;text-align:center;}}
  .box{{max-width:400px;margin:50px auto;border:2px solid #861F41;padding:24px;background:#151515;border-radius:6px;}}
  input{{width:90%;padding:10px;margin:8px 0;background:#222;border:1px solid #444;color:#fff;}}
  button{{background:#861F41;color:#fff;border:none;padding:10px 20px;cursor:pointer;font-weight:bold;margin-top:10px;}}
  button:hover{{background:#E5751F;}}
</style>
</head>
<body>
  <div class="box">
    <h2 style="color:#E5751F;">Virginia Tech Portal</h2>
    <p style="color:#aaa;font-size:12px;">Authorized Hokies Only</p>
    <form method="POST">
      <input type="text" name="username" placeholder="Username / PID" required><br>
      <input type="password" name="password" placeholder="Password"><br>
      <button type="submit">LOGIN</button>
    </form>
    <p style="margin-top:16px;color:#E5751F;">{msg}</p>
  </div>
</body>
</html>'''

@app.route('/challenge/store', methods=['GET', 'POST'])
def target_store():
    feedback = ""
    if request.method == 'POST':
        price = request.form.get('price', '50')
        if price == '0':
            feedback = "<div style='color:#00ff00;margin-top:16px;'>Order Successful for $0! Flag: HOKIE{client_side_tampering}</div>"
        else:
            feedback = "<div style='color:#ff4444;margin-top:16px;'>Insufficient funds! You only have $0.00 in your Hokie Wallet.</div>"
    return f'''<!DOCTYPE html>
<html>
<head><title>Hokie Merch Store</title>
<style>
  body{{background:#0d0d0d;color:#fff;font-family:monospace;padding:40px;text-align:center;}}
  .card{{background:#1a1a1a;border:1px solid #861F41;padding:20px;max-width:350px;margin:20px auto;border-radius:8px;}}
  button{{background:#E5751F;border:none;padding:10px 20px;color:#fff;font-weight:bold;cursor:pointer;}}
</style>
</head>
<body>
  <h1>Virginia Tech Cybersecurity Merch</h1>
  <div class="card">
    <h3>VT Cyber Maroon Hoodie</h3>
    <p style="color:#E5751F;font-size:18px;">Price: $50.00</p>
    <p style="color:#75787b;">Your Balance: $0.00</p>
    <form method="POST">
      <input type="hidden" name="price" value="50">
      <button type="submit">Buy Hoodie</button>
    </form>
    {feedback}
  </div>
</body>
</html>'''

@app.route('/challenge/robots-site')
def target_robots():
    return '''<!DOCTYPE html>
<html>
<head><title>Hokie Central</title><style>body{background:#0d0d0d;color:#75787B;font-family:monospace;padding:40px;text-align:center;}</style></head>
<body>
  <h1 style="color:#861F41;">Hokie Web Hub</h1>
  <p>Search engines index this site publically.</p>
</body>
</html>'''

@app.route('/robots.txt')
@app.route('/challenge/robots-site/robots.txt')
def target_robots_file():
    return "User-agent: *\nDisallow: /restricted-drillfield-vault/\n", 200, {'Content-Type': 'text/plain'}

@app.route('/restricted-drillfield-vault/')
def target_drillfield_vault():
    return "<body style='background:#0d0d0d;color:#E5751F;font-family:monospace;padding:40px;'><h1>Vault Opened</h1><p>Flag: HOKIE{robots_cannot_hide}</p></body>"

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