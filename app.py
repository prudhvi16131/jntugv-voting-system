import hashlib
import json
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = "JNTUGV_BLOCKCHAIN_2026_FINAL_PRO"

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
    "end_time": "2026-02-23T18:00",
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
    candidate_names = [c['name'] for c in ELECTION_SETTINGS["candidates"]]
    return render_template('index.html', candidates=candidate_names, settings=ELECTION_SETTINGS)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    student_id = request.form.get('student_id', '').upper().strip()
    candidate = request.form.get('candidate')

    # 1. Range Validation (24V11A0501 - 24V11A0580)
    try:
        suffix = int(student_id[-4:])
        is_valid_prefix = student_id.startswith(ELECTION_SETTINGS["authorized_prefix"])
        is_in_range = ELECTION_SETTINGS["range_start"] <= suffix <= ELECTION_SETTINGS["range_end"]

        if not (is_valid_prefix and is_in_range):
            blockchain.security_logs.append({
                "id": student_id, "time": datetime.now(IST).strftime("%H:%M:%S"), "reason": "Out of Range"
            })
            return "<h1>Access Denied</h1><p>ID outside authorized range.</p><a href='/'>Back</a>"
    except:
        return "<h1>Invalid ID Format</h1><a href='/'>Back</a>"

    # 2. Double Voting Check
    nullifier = hashlib.sha256(student_id.encode()).hexdigest()
    if nullifier in blockchain.nullifiers:
        blockchain.security_logs.append({
            "id": student_id, "time": datetime.now(IST).strftime("%H:%M:%S"), "reason": "Double Vote"
        })
        return "<h1>Vote Already Cast</h1><p>Blockchain prevents duplicate entries.</p><a href='/'>Back</a>"

    # 3. Add to Blockchain & Generate Receipt
    blockchain.nullifiers.add(nullifier)
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    receipt_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12].upper()
    
    vote_data = {'candidate': candidate, 'receipt': receipt_id}
    blockchain.pending_votes.append(vote_data)
    blockchain.create_block(proof=123, previous_hash=blockchain.hash(blockchain.get_last_block()))
    
    return render_template('success.html', 
                           candidate=candidate, 
                           receipt=receipt_id, 
                           timestamp=timestamp)

# --- UPDATED AUDIT ROUTE WITH SEARCH LOGIC ---
@app.route('/audit', methods=['GET', 'POST'])
def audit_ledger():
    searched_id = None
    result = None

    if request.method == 'POST':
        searched_id = request.form.get('receipt', '').upper().strip()
        
        # Search blockchain for the receipt
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
    total_eligible = (ELECTION_SETTINGS["range_end"] - ELECTION_SETTINGS["range_start"]) + 1
    turnout = round((len(blockchain.nullifiers) / total_eligible) * 100, 1)
    
    return render_template('results.html', 
                           settings=ELECTION_SETTINGS,
                           winner=winner, 
                           turnout=turnout, 
                           vote_counts=vote_counts,
                           logs=blockchain.security_logs,
                           current_time=datetime.now(IST).strftime("%d/%m/%Y, %H:%M"))

# --- API ENDPOINTS ---

@app.route('/update_settings', methods=['POST'])
def update_settings():
    data = request.json
    if 'candidates' in data: ELECTION_SETTINGS["candidates"] = data['candidates']
    if 'start' in data: ELECTION_SETTINGS["start_time"] = data['start']
    if 'end' in data: ELECTION_SETTINGS["end_time"] = data['end']
    return jsonify({"status": "success"})

@app.route('/reset_election', methods=['POST'])
def reset_election():
    global blockchain
    blockchain = Blockchain()
    ELECTION_SETTINGS["candidates"] = [{"name": "Candidate 1", "symbol": "🗳️"}]
    return jsonify({"status": "success", "message": "Blockchain Fully Reset"})

# --- DEPLOYMENT ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)