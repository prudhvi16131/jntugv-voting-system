import hashlib
import json
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = "JNTUGV_BLOCKCHAIN_2026_SECURE"

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
ADMIN_SECRET = "JNTUGV_SECRET" 

# Election Data & Authorized Range
ELECTION_DATA = {
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"}, 
        {"name": "Laxman", "symbol": "🐘"},
        {"name": "Sita", "symbol": "🏹"}
    ],
    "is_active": True,
    "authorized_prefix": "24V11A",
    "range_start": 501,
    "range_end": 580
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
    candidates_names = [c['name'] for c in ELECTION_DATA["candidates"]]
    return render_template('index.html', candidates=candidates_names, active=ELECTION_DATA["is_active"])

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    student_id = request.form.get('student_id').upper().strip()
    candidate = request.form.get('candidate')

    if not ELECTION_DATA["is_active"]:
        return "<h1>Election Closed</h1><p>The voting window has ended.</p>"

    # 1. RANGE VALIDATION (24V11A0501 - 24V11A0580)
    try:
        suffix = int(student_id[-4:])
        is_valid_prefix = student_id.startswith(ELECTION_DATA["authorized_prefix"])
        is_in_range = ELECTION_DATA["range_start"] <= suffix <= ELECTION_DATA["range_end"]

        if not (is_valid_prefix and is_in_range):
            blockchain.security_logs.append({
                "id": student_id,
                "time": datetime.now(IST).strftime("%H:%M:%S"),
                "reason": "Out of Range"
            })
            return "<h1>Access Denied</h1><p>ID not in authorized voting range.</p>"
    except:
        return "<h1>Invalid ID</h1><p>Please enter a valid Roll Number.</p>"

    # 2. DOUBLE VOTING CHECK
    nullifier = hashlib.sha256(student_id.encode()).hexdigest()
    if nullifier in blockchain.nullifiers:
        blockchain.security_logs.append({
            "id": student_id,
            "time": datetime.now(IST).strftime("%H:%M:%S"),
            "reason": "Double Vote"
        })
        return "<h1>Vote Already Cast</h1><p>This ID has already participated.</p>"

    # 3. RECORD VOTE
    blockchain.nullifiers.add(nullifier)
    vote_data = {
        'candidate': candidate, 
        'receipt': hashlib.sha256(str(time.time()).encode()).hexdigest()[:10].upper()
    }
    blockchain.pending_votes.append(vote_data)
    blockchain.create_block(proof=123, previous_hash=blockchain.hash(blockchain.get_last_block()))
    
    return render_template('success.html', receipt=vote_data['receipt'])

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_DATA["candidates"]}
    
    # Calculate Winner
    if not blockchain.nullifiers:
        winner = "TBD"
    else:
        winner = max(vote_counts, key=vote_counts.get)

    total_eligible = (ELECTION_DATA["range_end"] - ELECTION_DATA["range_start"]) + 1
    turnout = round((len(blockchain.nullifiers) / total_eligible) * 100, 1)
    
    return render_template('results.html', 
                           winner=winner, 
                           turnout=turnout, 
                           vote_counts=vote_counts,
                           candidates=ELECTION_DATA["candidates"],
                           logs=blockchain.security_logs,
                           current_time=datetime.now(IST).strftime("%d/%m/%Y, %H:%M"))

@app.route('/stop_election', methods=['POST'])
def stop_election():
    ELECTION_DATA["is_active"] = False
    return jsonify({"status": "Success", "message": "Election Terminated"})

if __name__ == '__main__':
    app.run(debug=True)