import hashlib
import json
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.secret_key = "JNTUGV_BLOCKCHAIN_2026_SECURE"

IST = pytz.timezone('Asia/Kolkata')
ADMIN_SECRET = "JNTUGV_SECRET" 

# Dynamic Election Data
ELECTION_SETTINGS = {
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"}, 
        {"name": "Laxman", "symbol": "🐘"}
    ],
    "start_time": "2026-02-23T09:00",
    "end_time": "2026-02-23T17:00",
    "is_active": True
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

    def get_vote_count(self, name):
        count = 0
        for block in self.chain:
            for v in block['votes']:
                if v['candidate'] == name: count += 1
        return count

blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html', candidates=[c['name'] for c in ELECTION_SETTINGS["candidates"]])

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_SETTINGS["candidates"]}
    turnout = round((len(blockchain.nullifiers) / 80) * 100, 1)
    return render_template('results.html', 
                           settings=ELECTION_SETTINGS, 
                           vote_counts=vote_counts, 
                           turnout=turnout,
                           logs=blockchain.security_logs)

# --- NEW: EDIT CANDIDATES ROUTE ---
@app.route('/update_candidates', methods=['POST'])
def update_candidates():
    data = request.json
    ELECTION_SETTINGS["candidates"] = data['candidates']
    return jsonify({"status": "success", "message": "Candidates Updated!"})

# --- NEW: EDIT SCHEDULE ROUTE ---
@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    data = request.json
    ELECTION_SETTINGS["start_time"] = data['start']
    ELECTION_SETTINGS["end_time"] = data['end']
    return jsonify({"status": "success", "message": "Schedule Updated!"})

if __name__ == '__main__':
    app.run(debug=True)