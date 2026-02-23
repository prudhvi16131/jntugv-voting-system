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
# This MUST match the URL in your browser screenshot
ADMIN_SECRET = "JNTUGV_SECRET" 

ELECTION_DATA = {
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"}, 
        {"name": "Laxman", "symbol": "🐘"}
    ],
    "is_active": True,
    "authorized_prefix": "24V11A",
    "range_start": 501,
    "range_end": 580
}

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_votes = []
        self.nullifiers = set()
        self.security_logs = [] 
        self.create_block(previous_hash='1', proof=100)

    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1, 'timestamp': datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                 'votes': self.pending_votes, 'proof': proof, 'previous_hash': previous_hash}
        self.pending_votes = []
        self.chain.append(block)
        return block

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def get_vote_count(self, name):
        count = 0
        for block in self.chain:
            for v in block['votes']:
                if v['candidate'] == name: count += 1
        return count

blockchain = Blockchain()

@app.route('/')
def index():
    candidates_names = [c['name'] for c in ELECTION_DATA["candidates"]]
    return render_template('index.html', candidates=candidates_names)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    student_id = request.form.get('student_id').upper().strip()
    candidate = request.form.get('candidate')
    
    # Range check
    try:
        suffix = int(student_id[-4:])
        if not (student_id.startswith("24V11A") and 501 <= suffix <= 580):
            blockchain.security_logs.append({"id": student_id, "time": datetime.now(IST).strftime("%H:%M"), "reason": "Out of Range"})
            return "<h1>Access Denied</h1>"
    except:
        return "<h1>Invalid ID</h1>"

    nullifier = hashlib.sha256(student_id.encode()).hexdigest()
    if nullifier in blockchain.nullifiers:
        blockchain.security_logs.append({"id": student_id, "time": datetime.now(IST).strftime("%H:%M"), "reason": "Double Vote"})
        return "<h1>Already Voted</h1>"

    blockchain.nullifiers.add(nullifier)
    vote_data = {'candidate': candidate, 'receipt': hashlib.sha256(str(time.time()).encode()).hexdigest()[:8].upper()}
    blockchain.pending_votes.append(vote_data)
    blockchain.create_block(proof=123, previous_hash=blockchain.hash(blockchain.chain[-1]))
    return "<h1>Vote Success! Receipt: " + vote_data['receipt'] + "</h1>"

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_DATA["candidates"]}
    winner = max(vote_counts, key=vote_counts.get) if blockchain.nullifiers else "No votes yet"
    turnout = round((len(blockchain.nullifiers) / 80) * 100, 1)
    return render_template('results.html', winner=winner, turnout=turnout, vote_counts=vote_counts, 
                           candidates=ELECTION_DATA["candidates"], logs=blockchain.security_logs,
                           current_time=datetime.now(IST).strftime("%d/%m/%Y, %H:%M"))

if __name__ == '__main__':
    app.run(debug=True)