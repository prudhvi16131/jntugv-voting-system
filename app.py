import hashlib
import json
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "JNTUGV_SUPER_SECRET_KEY"

# --- CONFIGURATION ---
class VotingConfig:
    def __init__(self):
        self.candidates = ["Ramu", "Laxman"] # You can add more here
        self.election_end_time = "2026-03-01 17:00:00" # Set your demo end time
        self.admin_secret = "JNTUGV_ADMIN_2026" # Your secret URL key
        self.is_active = True

config = VotingConfig()
IST = pytz.timezone('Asia/Kolkata')

# --- BLOCKCHAIN ENGINE ---
class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_votes = []
        self.nullifiers = set() # Stores hashed student IDs to prevent double-voting
        self.security_logs = []
        self.create_block(previous_hash='1', proof=100) # Genesis Block

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

    def add_vote(self, student_id, candidate):
        # 1. Create Nullifier (SHA-256 of Student ID)
        nullifier = hashlib.sha256(student_id.encode()).hexdigest()
        
        # 2. Check for double voting
        if nullifier in self.nullifiers:
            log_msg = f"Double-voting attempt detected for ID: {student_id[:5]}***"
            self.security_logs.append(log_msg)
            return False, "You have already cast your vote."

        # 3. Add to pending and update nullifiers
        receipt_id = hashlib.sha256(f"{student_id}{time.time()}".encode()).hexdigest()[:10].upper()
        vote_data = {
            'receipt': receipt_id,
            'candidate': candidate,
            'timestamp': datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        }
        self.pending_votes.append(vote_data)
        self.nullifiers.add(nullifier)
        
        # Mine block immediately for this demo
        self.create_block(proof=123, previous_hash=self.hash(self.get_last_block()))
        return True, receipt_id

    def get_vote_count(self, candidate_name):
        count = 0
        for block in self.chain:
            for vote in block['votes']:
                if vote['candidate'] == candidate_name:
                    count += 1
        return count

    def get_winner(self):
        counts = {c: self.get_vote_count(c) for c in config.candidates}
        return max(counts, key=counts.get) if any(counts.values()) else "No Votes Yet"

blockchain = Blockchain()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html', candidates=config.candidates, active=config.is_active)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    if not config.is_active:
        return "Election Closed"
    
    student_id = request.form.get('student_id')
    candidate = request.form.get('candidate')
    
    success, result = blockchain.add_vote(student_id, candidate)
    if success:
        return render_template('success.html', receipt=result)
    else:
        flash(result)
        return redirect(url_for('index'))

@app.route('/audit', methods=['GET', 'POST'])
def audit():
    result = None
    searched_id = None
    if request.method == 'POST':
        searched_id = request.form.get('receipt').upper()
        for block in blockchain.chain:
            for vote in block['votes']:
                if vote['receipt'] == searched_id:
                    result = {
                        'block_index': block['index'],
                        'timestamp': vote['timestamp'],
                        'candidate': vote['candidate']
                    }
    return render_template('audit.html', result=result, searched_id=searched_id)

@app.route(f'/admin-results/{config.admin_secret}')
def admin_results():
    total_votes = len(blockchain.nullifiers)
    turnout = round((total_votes / 80) * 100, 2) # Assuming 80 students
    
    # Calculate live standings for results.html
    vote_counts = {c: blockchain.get_vote_count(c) for c in config.candidates}
    
    return render_template('results.html', 
                           winner=blockchain.get_winner(), 
                           turnout=turnout, 
                           vote_counts=vote_counts,
                           violations=blockchain.security_logs)

@app.route('/stop_clock', methods=['POST'])
def stop_clock():
    config.is_active = False
    return redirect(url_for('admin_results'))

if __name__ == '__main__':
    app.run(debug=True)