import hashlib
import json
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = "JNTUGV_BLOCKCHAIN_2026"

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
ADMIN_SECRET = "JNTUGV_SECRET" # Matches your screenshot URL
# Initial candidates based on your screenshot
ELECTION_DATA = {
    "candidates": [{"name": "Ramu", "symbol": "🦁"}, {"name": "Laxman", "symbol": "🐘"}],
    "is_active": True,
    "total_voters": 80 # Based on range 24V11A0501 - 24V11A0580
}

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_votes = []
        self.nullifiers = set()
        self.security_logs = [] # Format: {"id": id, "time": time, "reason": reason}
        self.create_block(previous_hash='1', proof=100)

    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1, 'timestamp': datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                 'votes': self.pending_votes, 'proof': proof, 'previous_hash': previous_hash}
        self.pending_votes = []
        self.chain.append(block)
        return block

    def get_vote_count(self, name):
        count = 0
        for block in self.chain:
            for v in block['votes']:
                if v['candidate'] == name: count += 1
        return count

blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html', candidates=[c['name'] for c in ELECTION_DATA["candidates"]], active=ELECTION_DATA["is_active"])

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_DATA["candidates"]}
    
    # Calculate Leading Candidate
    if not blockchain.nullifiers:
        winner = "No votes yet"
    else:
        winner = max(vote_counts, key=vote_counts.get)

    turnout = round((len(blockchain.nullifiers) / ELECTION_DATA["total_voters"]) * 100, 1)
    
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
    return jsonify({"status": "Election Stopped"})

if __name__ == '__main__':
    app.run(debug=True)