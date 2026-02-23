import hashlib
import json
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = "JNTUGV_BLOCKCHAIN_2026_MASTER_PRO"

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
ADMIN_SECRET = "JNTUGV_SECRET" 

# Dynamic Election Data
ELECTION_SETTINGS = {
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"}, 
        {"name": "Laxman", "symbol": "🐘"}
    ],
    "start_time": "2026-02-23T09:00",
    "end_time": "2026-02-24T23:59",
    "is_active": True,
    "authorized_prefix": "24V11A",
    "range_start": 501,
    "range_end": 580,
    "admin_secret": ADMIN_SECRET
}

# --- BLOCKCHAIN ENGINE ---
class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_votes = []
        self.nullifiers = set()
        self.security_logs = [] 
        self.create_block(previous_hash='1', proof=100)

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            'votes': self.pending_votes,
            'proof': proof,
            'previous_hash': previous_hash,
        }
        self.pending_votes = []
        self.chain.append(block)
        return block

    def get_last_block(self):
        return self.chain[-1]

    def hash(self, block):
        # Using a fixed sort_keys to ensure consistent hashing
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

@app.route('/')
def index():
    return render_template('index.html', 
                           candidate_list=ELECTION_SETTINGS["candidates"], 
                           settings=ELECTION_SETTINGS)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    if not ELECTION_SETTINGS["is_active"]:
        return "<h1>Election Closed</h1><p>The election has been stopped by the administrator.</p><a href='/'>Back</a>"

    student_id = request.form.get('student_id', '').upper().strip()
    candidate = request.form.get('candidate')
    
    # IP Cleaning logic to handle Render/Proxy strings
    raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_ip = raw_ip.split(',')[0].strip() if raw_ip and ',' in raw_ip else raw_ip

    try:
        suffix = int(student_id[-4:])
        is_valid = student_id.startswith(ELECTION_SETTINGS["authorized_prefix"]) and \
                   ELECTION_SETTINGS["range_start"] <= suffix <= ELECTION_SETTINGS["range_end"]

        if not is_valid:
            blockchain.security_logs.append({
                "id": student_id, 
                "time": datetime.now(IST).strftime("%H:%M:%S"), 
                "reason": "Invalid ID Range", 
                "ip": user_ip
            })
            return "<h1>Access Denied</h1><a href='/'>Back</a>"
    except:
        return "<h1>Invalid ID Format</h1><a href='/'>Back</a>"

    # Double Vote Check
    nullifier = hashlib.sha256(student_id.encode()).hexdigest()
    if nullifier in blockchain.nullifiers:
        blockchain.security_logs.append({
            "id": student_id, 
            "time": datetime.now(IST).strftime("%H:%M:%S"), 
            "reason": "Double Vote Attempt", 
            "ip": user_ip
        })
        return render_template('already_cast.html')

    blockchain.nullifiers.add(nullifier)
    receipt_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12].upper()
    blockchain.pending_votes.append({'candidate': candidate, 'receipt': receipt_id})
    blockchain.create_block(proof=123, previous_hash=blockchain.hash(blockchain.get_last_block()))
    
    return render_template('success.html', candidate=candidate, receipt=receipt_id, timestamp=datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"))

# --- AUDIT PORTAL ROUTE (FIXES THE 404 ERROR) ---
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

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_SETTINGS["candidates"]}
    winner = max(vote_counts, key=vote_counts.get) if blockchain.nullifiers else "TBD"
    turnout = round((len(blockchain.nullifiers) / 80) * 100, 1)
    
    return render_template('results.html', 
                           settings=ELECTION_SETTINGS, 
                           winner=winner, 
                           turnout=turnout, 
                           vote_counts=vote_counts, 
                           logs=blockchain.security_logs, 
                           candidates=ELECTION_SETTINGS["candidates"],
                           current_time=datetime.now(IST).strftime("%Y-%m-%d %H:%M"))

@app.route(f'/admin/security-center/{ADMIN_SECRET}')
def security_center():
    return render_template('security_center.html', 
                           logs=blockchain.security_logs, 
                           settings=ELECTION_SETTINGS)

# --- API CONTROL ENDPOINTS ---
@app.route('/sync_candidates', methods=['POST'])
def sync_candidates():
    ELECTION_SETTINGS["candidates"] = request.json['candidates']
    return jsonify({"status": "success"})

@app.route('/update_timing', methods=['POST'])
def update_timing():
    data = request.json
    ELECTION_SETTINGS["start_time"] = data['start']
    ELECTION_SETTINGS["end_time"] = data['end']
    return jsonify({"status": "success"})

@app.route('/stop_election', methods=['POST'])
def stop_election():
    ELECTION_SETTINGS["is_active"] = False
    return jsonify({"status": "success"})

@app.route('/reset_election', methods=['POST'])
def reset_election():
    global blockchain
    blockchain = Blockchain()
    ELECTION_SETTINGS["is_active"] = True
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Render uses port 10000 by default for Python apps
    app.run(host='0.0.0.0', port=10000)