# 🦃 Curious Hokies STEM CTF (Capture The Flag)

An interactive, browser-accessible Capture The Flag (CTF) competition engine developed for the **Virginia Tech K-12 STEM Initiative** workshop. Tailored for Virginia 10th–12th grade AP Computer Science and Cybersecurity students.

Designed and developed by **Kayrene Woods** (@kaykayzara).

---

## 🚀 Features

- **Thematic UI/UX:** Styled using official Virginia Tech colors (Chicago Maroon `#861F41`, Burnt Orange `#E5751F`, and Hokie Stone `#75787B`) with a retro cyberpunk terminal aesthetic.
- **Synchronized Global Timer:** Server-authoritative 30-minute competition clock orchestrated from an admin dashboard.
- **Dynamic Leaderboard:** Real-time solve tracking and automated score calculation.
- **Interactive In-Browser Exploitation:** Built-in challenge sandbox environments requiring zero local command-line tools or client dependencies.

---

## 🎯 Challenge Tracks

1. **Ethical Hacking (Offensive Web)**
   - *SQLi Gatekeeper:* Authentication bypass using SQL payload injection (`' OR '1'='1`).
   - *Free Campus Gear:* DevTools DOM parameter tampering on hidden purchase inputs.
   - *The Secret Vault:* Web crawler route enumeration via `robots.txt`.

2. **Computer Science & Logic (AP CS Prep)**
   - *AP Loop Trace:* Code execution and Python string slicing (`[::2]`).
   - *Logic Gate Circuit:* Compound Boolean expression evaluation.

3. **Cybersecurity & Cryptography**
   - *Burnt Orange Hex:* ASCII hex string reverse decoding.
   - *Caesar at Lane Stadium:* Classical ROT13 shift cipher recovery.
   - *Response Headers:* HTTP protocol analysis in browser network developer tools.

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask, SQLite3, Gunicorn
- **Frontend:** Vanilla HTML5, Modern CSS3 (CSS Variables, Radial Gradients), JavaScript (Async/Await Fetch API)
- **Security:** Bcrypt salted password hashing, server-side flag verification
- **Deployment Platform:** Render (PaaS)

---

## 💻 Local Quickstart

1. **Clone the repository:**
    ```bash
    git clone https://github.com/kaykayzara/curious-hokies-ctf.git
    cd curious-hokies-ctf