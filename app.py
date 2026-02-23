import hashlib
import json
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "JNTUGV_SECURE_VOTING_2026"

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
# This list must match the names in your results.html
CANDIDATES = ["Ganesh", "Vamsi", "Suresh"]
# YOUR SECRET LINK: /admin-results/JNTUGV_ADMIN_2026
ADMIN_SECRET = "JNTUGV_ADMIN_2026"

# --- BLOCKCHAIN SYSTEM ---
class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_votes = []
        self.nullifiers = set()  # To prevent double voting
        self.security_logs = []
        self.create_block(previous_hash='1', proof=100)  # Genesis Block

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

    def get_vote_count(self, candidate_name):
        count = 0
        for block in self.chain:
            for v in block['votes']:
                if v['candidate'] == candidate_name:
                    count += 1
        return count

# Initialize the engine
blockchain = Blockchain()

# --- ROUTES ---

@app.route('/')
def index():
    # Sending 'candidates' fixes the Internal Server Error on the home page
    return render_template('index.html', candidates=CANDIDATES)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    student_id = request.form.get('student_id')
    candidate = request.form.get('candidate')
    
    if not student_id or not candidate:
        return "Error: ID or Candidate missing", 400

    # SHA-256 Nullifier Check
    nullifier = hashlib.sha256(student_id.encode()).hexdigest()
    
    if nullifier in blockchain.nullifiers:
        blockchain.security_logs.append(f"Blocked double vote: {student_id[:5]}***")
        return "<h1>Error: You have already voted!</h1><a href='/'>Go Back</a>"
    
    # Secure the vote
    blockchain.nullifiers.add(nullifier)
    vote_data = {
        'candidate': candidate, 
        'receipt': hashlib.sha256(str(time.time()).encode()).hexdigest()[:8].upper()
    }
    
    blockchain.pending_votes.append(vote_data)
    blockchain.create_block(proof=123, previous_hash=blockchain.hash(blockchain.get_last_block()))
    
    return render_template('success.html', receipt=vote_data['receipt'])

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    # This dictionary provides the data your 'results.html' tally table needs
    vote_counts = {c: blockchain.get_vote_count(c) for c in CANDIDATES}
    
    # Calculate turnout (based on 60 students)
    total_class_size = 60
    turnout_pct = round((len(blockchain.nullifiers) / total_class_size) * 100, 2)
    
    return render_template('results.html', 
                           vote_counts=vote_counts, 
                           turnout=turnout_pct,
                           violations=blockchain.security_logs,
                           winner="Election Active")

if __name__ == '__main__':
    app.run(debug=True)