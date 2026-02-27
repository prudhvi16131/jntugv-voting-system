import hashlib
import json
import time
from datetime import datetime
import pytz
from io import BytesIO
import sqlite3 # Persistent Storage
from werkzeug.security import generate_password_hash, check_password_hash # Secure Hashing
from flask import Flask, render_template, request, jsonify, make_response, url_for, session, redirect

# PDF Libraries
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# INITIALIZE FLASK WITH STATIC FOLDER SUPPORT
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = "BCET_BLOCKCHAIN_2026_SECURE"

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
ADMIN_SECRET = "BCET_ADMIN_PRO" 

# --- AUTHORIZED STUDENT LIST ---
AUTHORIZED_STUDENTS = [
    "24V11A0501", "24V11A0502", "24V11A0503", "24V11A0504", "24V11A0505",
    "24V11A0506", "24V11A0507", "24V11A0510", "24V11A0511", "24V11A0512",
    "24V11A0513", "24V11A0514", "24V11A0515", "24V11A0516", "24V11A0517",
    "24V11A0518", "24V11A0519", "24V11A0520", "24V11A0521", "24V11A0522",
    "24V11A0523", "24V11A0525", "24V11A0526", "24V11A0527", "24V11A0528",
    "24V11A0529", "24V11A0530", "24V11A0531", "24V11A0532", "24V11A0534",
    "24V11A0535", "24V11A0536", "24V11A0537", "24V11A0538", "24V11A0539",
    "24V11A0541", "24V11A0542", "24V11A0543", "24V11A0544", "24V11A0545",
    "24V11A0546", "24V11A0547", "24V11A0548", "24V11A0549", "24V11A0550",
    "24V11A0551", "24V11A0552", "24V11A0553", "24V11A0554", "24V11A0555",
    "24V11A0556", "24V11A0557", "24V11A0558", "24V11A0559", "24V11A0560",
    "24V11A0561", "24V11A0563", "24V11A0564", "24V11A0565", "24V11A0566",
    "24V11A0567", "24V11A0568", "24V11A0569", "24V11A0570", "24V11A0571",
    "24V11A0572", "24V11A0573", "24V11A0574", "24V11A0575", "24V11A0576",
    "24V11A0577", "24V11A0578", "24V11A0579", "25V15A0501", "25V15A0502",
    "25V15A0503", "25V15A0504"
]

# --- PERSISTENCE: DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('bcet_production.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (student_id TEXT PRIMARY KEY, email TEXT, password_hash TEXT)''')
    conn.commit()
    conn.close()

init_db()

ELECTION_SETTINGS = {
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"}, 
        {"name": "Laxman", "symbol": "🐘"}
    ],
    "start_time": "2026-02-23T09:00",
    "end_time": "2026-02-28T23:59",
    "is_active": False, # Initially set to False
    "authorized_prefix": "24V11A",
    "range_start": 501,
    "range_end": 580,
    "admin_secret": ADMIN_SECRET
}

# --- BLOCKCHAIN ENGINE ---
class Blockchain:
    def __init__(self):
        self.reset()

    def reset(self):
        self.chain = []
        self.pending_votes = []
        self.nullifiers = set()
        self.security_logs = [] # Feature Added: High-Tech Security Logging
        self.create_block(previous_hash='1', proof=100)

    # Method Added: Records unauthorized or duplicate attempts
    def log_intrusion(self, user_id, reason, ip):
        self.security_logs.append({
            "id": user_id,
            "time": datetime.now(IST).strftime("%H:%M:%S"),
            "reason": reason,
            "ip": ip
        })

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            'votes': list(self.pending_votes),
            'proof': proof,
            'previous_hash': previous_hash,
        }
        self.pending_votes = []
        self.chain.append(block)
        return block

    def get_last_block(self):
        return self.chain[-1]

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def get_vote_count(self, name):
        count = 0
        for block in self.chain:
            for v in block['votes']:
                if v['candidate'] == name:
                    count += 1
        return count

blockchain = Blockchain()

# --- ROUTES ---

@app.route('/welcome')
def welcome():
    # If student is already verified, don't show welcome, take them to vote
    if 'user_id' in session and session.get('token_verified'):
        return redirect(url_for('index'))
    return render_template('welcome.html')

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/')
def index():
    # SECURITY GATE 1: Must be logged in
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    
    # SECURITY GATE 2: Must have verified the Blockchain Token
    if not session.get('token_verified'):
        return redirect(url_for('auth_token_display'))
    
    # --- DYNAMIC ELECTION STATUS CHECK ---
    now = datetime.now(IST)
    start = datetime.strptime(ELECTION_SETTINGS["start_time"], "%Y-%m-%dT%H:%M").replace(tzinfo=IST)
    end = datetime.strptime(ELECTION_SETTINGS["end_time"], "%Y-%m-%dT%H:%M").replace(tzinfo=IST)
    
    status = "OPEN"
    if not ELECTION_SETTINGS["is_active"] or now > end:
        status = "CLOSED"
    elif now < start:
        status = "NOT_STARTED"
    
    display_settings = ELECTION_SETTINGS.copy()
    return render_template('index.html', 
                           candidate_list=ELECTION_SETTINGS["candidates"], 
                           settings=display_settings,
                           election_status=status)

# --- NEW: BLOCKCHAIN AUTH TOKEN ROUTES ---

@app.route('/auth_token_display')
def auth_token_display():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    # Generate unique 12-char Blockchain Token based on ID and Time
    sid = session['user_id']
    raw_data = f"{sid}{time.time()}{app.secret_key}"
    blockchain_token = hashlib.sha256(raw_data.encode()).hexdigest().upper()[:12]
    
    session['generated_token'] = blockchain_token
    session['token_verified'] = False 
    
    return render_template('auth_token_display.html', token=blockchain_token)

@app.route('/verify_token_page')
def verify_token_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('token_verification_input.html')

@app.route('/verify_token', methods=['POST'])
def verify_token():
    user_input = request.form.get('input_token', '').strip().upper()
    actual_token = session.get('generated_token')

    if user_input and user_input == actual_token:
        # This unlocks the 'index' route
        session['token_verified'] = True
        return redirect(url_for('index'))
    else:
        return render_template('token_verification_input.html', error="Invalid Token! Please ensure you copied correctly.")

# --- AUTHENTICATION ROUTES ---

@app.route('/signup_page')
def signup_page():
    return render_template('signup.html')

@app.route('/register', methods=['POST'])
def register():
    student_id = request.form.get('student_id', '').upper().strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()

    if student_id not in AUTHORIZED_STUDENTS:
        return jsonify({"status": "error", "message": "ID not authorized by BCET!"})
    
    hashed_password = generate_password_hash(password)

    try:
        conn = sqlite3.connect('bcet_production.db')
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM users WHERE student_id=?", (student_id,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "This Hall Ticket is already registered!"})

        cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (student_id, email, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Account created! Redirecting to Login..."})
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": "Database Error occurred."})

@app.route('/login', methods=['POST'])
def login():
    student_id = request.form.get('student_id', '').upper().strip()
    password = request.form.get('password', '').strip()

    conn = sqlite3.connect('bcet_production.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE student_id=?", (student_id,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[0], password):
        session['user_id'] = student_id
        session['token_verified'] = False # Reset token status for fresh session
        # Redirect to Token Display bridge instead of voting page
        return redirect(url_for('auth_token_display'))
    
    return render_template('login_error.html')

@app.route('/forgot_password_page')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    student_id = request.form.get('student_id', '').upper().strip()
    email = request.form.get('email', '').strip().lower()
    new_password = request.form.get('password', '').strip()
    
    conn = sqlite3.connect('bcet_production.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE student_id=? AND email=?", (student_id, email))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"status": "error", "message": "Hall Ticket and Email do not match our records!"})

    hashed_password = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password_hash=? WHERE student_id=?", (hashed_password, student_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Password Reset Successful!"})

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('welcome'))

# --- VOTING & AUDIT ---

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    # Security: Ensure they didn't bypass the token
    if 'user_id' not in session or not session.get('token_verified'):
        return redirect(url_for('welcome'))

    if not ELECTION_SETTINGS["is_active"]:
        return "<h1>Election Closed</h1><a href='/'>Back</a>"
    
    student_id = session['user_id']
    candidate = request.form.get('candidate')
    raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_ip = raw_ip.split(',')[0].strip() if raw_ip and ',' in raw_ip else request.remote_addr

    nullifier = hashlib.sha256(student_id.encode()).hexdigest()
    if nullifier in blockchain.nullifiers:
        # Log intrusion to blockchain security system
        blockchain.log_intrusion(student_id, "Double Vote Attempt", user_ip)
        session.clear() 
        return render_template('already_cast.html')

    # FEATURE: Mining Delay (Simulates block production for the progress bar animation)
    time.sleep(1.5)

    blockchain.nullifiers.add(nullifier)
    receipt_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12].upper()
    blockchain.pending_votes.append({'candidate': candidate, 'receipt': receipt_id})
    blockchain.create_block(proof=123, previous_hash=blockchain.hash(blockchain.get_last_block()))
    
    session.clear() 
    
    return render_template('success.html', 
                            candidate=candidate, 
                            receipt=receipt_id, 
                            timestamp=datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/audit', methods=['GET', 'POST'])
def audit_portal():
    searched_id, result = None, None
    if request.method == 'POST':
        searched_id = request.form.get('receipt', '').upper().strip()
        for block in blockchain.chain:
            for vote in block['votes']:
                if vote.get('receipt') == searched_id:
                    result = {
                        "candidate": vote['candidate'], 
                        "timestamp": block['timestamp'], 
                        "block_index": block['index']
                    }
                    break
            if result: break
    return render_template('audit.html', searched_id=searched_id, result=result)

# --- ADMIN ROUTES ---

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_SETTINGS["candidates"]}
    return render_template('results.html', 
                            settings=ELECTION_SETTINGS, 
                            vote_counts=vote_counts, 
                            logs=blockchain.security_logs)

@app.route('/admin/clear_accounts', methods=['POST'])
def clear_accounts():
    data = request.json
    secret = data.get('secret')
    
    if secret == ADMIN_SECRET:
        try:
            conn = sqlite3.connect('bcet_production.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users")
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Database Cleared."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    
    return jsonify({"status": "error", "message": "Unauthorized!"}), 403

@app.route('/sync_candidates', methods=['POST'])
def sync_candidates():
    ELECTION_SETTINGS["candidates"] = request.json['candidates']
    return jsonify({"status": "success"})

@app.route('/update_timing', methods=['POST'])
def update_timing():
    data = request.json
    ELECTION_SETTINGS["start_time"] = data['start']
    ELECTION_SETTINGS["end_time"] = data['end']
    ELECTION_SETTINGS["is_active"] = True
    return jsonify({"status": "success"})

@app.route('/stop_election', methods=['POST'])
def stop_election():
    ELECTION_SETTINGS["is_active"] = False
    return jsonify({"status": "success"})

@app.route('/reset_election', methods=['POST'])
def reset_election():
    blockchain.reset()
    return jsonify({"status": "success"})

@app.route(f'/download-results/{ADMIN_SECRET}')
def download_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_SETTINGS["candidates"]}
    
    # FEATURE: Winner Calculation for PDF Certificate
    winner_name = max(vote_counts, key=vote_counts.get)
    max_votes = vote_counts[winner_name]

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    p.setFillColor(colors.HexColor("#1e293b"))
    p.rect(0, height - 100, width, 100, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, height - 60, "BCET OFFICIAL ELECTION REPORT")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 80, f"Behara College of Engineering & Technology | {datetime.now(IST).strftime('%d %b %Y')}")

    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 150, "FINAL ELECTION SUMMARY")

    # Winner Announcement on PDF
    p.setFont("Helvetica-Bold", 18)
    if max_votes > 0:
        p.setFillColor(colors.HexColor("#16a34a"))
        p.drawCentredString(width/2, height - 210, f"OFFICIAL WINNER: {winner_name.upper()}")
        p.setFont("Helvetica", 12)
        p.setFillColor(colors.black)
        p.drawCentredString(width/2, height - 230, f"Secured {max_votes} Verified Blockchain Votes")
    else:
        p.drawCentredString(width/2, height - 210, "RESULT: NO VOTES CAST")

    # Full Tally Table
    y = height - 300
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Candidate Vote Tally:")
    y -= 25
    for name, count in vote_counts.items():
        p.setFont("Helvetica", 12)
        p.drawString(70, y, f"• {name}: {count} Votes")
        y -= 20

    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf)
    response.headers['Content-Disposition'] = f"attachment; filename=BCET_Winner_Report_{winner_name}.pdf"
    response.headers['Content-Type'] = 'application/pdf'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)