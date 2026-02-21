from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from blockchain import Blockchain
from datetime import datetime
import time
import pytz 
import hashlib
import os

app = Flask(__name__)
voting_blockchain = Blockchain()

# --- 1. CONFIGURATION & DATABASE ---
# Updated range: 24V11A0501 to 24V11A0580
voting_config = {
    "start": datetime(2026, 2, 21, 9, 0),
    "end": datetime(2026, 2, 25, 17, 0),
    "candidates": [
        {"name": "Candidate A", "symbol": "🦁"},
        {"name": "Candidate B", "symbol": "🐘"}
    ]
}

AUTHORIZED_VOTERS = [f"24V11A05{str(i).zfill(2)}" for i in range(1, 81)]

# --- 2. PWA / APP SUPPORT ROUTE ---
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

# --- 3. VOTER INTERFACE ---
@app.route('/')
def index():
    # Force India Standard Time for Render
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST).replace(tzinfo=None) 
    
    # Calculate end time in milliseconds for the JS countdown
    end_ms = int(voting_config["end"].timestamp() * 1000)
    
    if now < voting_config["start"]:
        return render_template('index.html', config=voting_config, status="waiting")
    if now > voting_config["end"]:
        return render_template('index.html', config=voting_config, status="closed")
    
    return render_template('index.html', config=voting_config, status="live", end_ms=end_ms)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    voter_id = request.form.get('voter_id')
    candidate = request.form.get('candidate')

    # Security: Database & Double-Voting Checks
    if voter_id not in AUTHORIZED_VOTERS:
        return "<h1>Unauthorized Student ID</h1>", 403

    for block in voting_blockchain.chain:
        for tx in block.transactions:
            if tx.get('voter_id') == voter_id:
                return "<h1>Error: You have already cast your vote!</h1>", 403

    # Upgrade: Generate Digital Receipt (Hash-based Verification)
    receipt_raw = f"{voter_id}{time.time()}"
    receipt = hashlib.sha256(receipt_raw.encode()).hexdigest()[:10].upper()

    vote_data = {
        "voter_id": voter_id, 
        "candidate": candidate, 
        "receipt": receipt,
        "timestamp": time.time()
    }
    
    voting_blockchain.add_new_transaction(vote_data)
    voting_blockchain.mine()
    
    return render_template('success.html', receipt=receipt)

# --- 4. ADMIN DASHBOARD & ANALYTICS ---
@app.route('/admin-results/JNTUGV_SECRET')
def admin_results():
    tally = {}
    total_votes = 0
    for block in voting_blockchain.chain[1:]:
        for tx in block.transactions:
            candidate = tx.get('candidate')
            if candidate:
                tally[candidate] = tally.get(candidate, 0) + 1
                total_votes += 1
    
    # Upgrade: Voter Participation Analytics
    turnout = round((total_votes / len(AUTHORIZED_VOTERS)) * 100, 1)
    winner = max(tally, key=tally.get) if tally else "No votes yet"
    
    return render_template('results.html', tally=tally, winner=winner, 
                           config=voting_config, turnout=turnout, total=total_votes)

@app.route('/update-time', methods=['POST'])
def update_time():
    new_start = request.form.get('start_time')
    new_end = request.form.get('end_time')
    voting_config["start"] = datetime.strptime(new_start, '%Y-%m-%dT%H:%M')
    voting_config["end"] = datetime.strptime(new_end, '%Y-%m-%dT%H:%M')
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/update-candidates', methods=['POST'])
def update_candidates():
    names = request.form.getlist('c_name')
    symbols = request.form.getlist('c_symbol')
    updated_list = []
    for n, s in zip(names, symbols):
        if n.strip(): 
            updated_list.append({"name": n, "symbol": s})
    voting_config["candidates"] = updated_list
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/reset-election', methods=['POST'])
def reset_election():
    global voting_blockchain
    voting_blockchain = Blockchain()
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/ledger')
def ledger():
    chain_data = [block.__dict__ for block in voting_blockchain.chain]
    return render_template('ledger.html', chain=chain_data)

# --- 5. START SERVER ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)