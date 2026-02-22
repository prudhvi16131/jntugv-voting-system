from flask import Flask, render_template, request, redirect, url_for
from blockchain import Blockchain
from datetime import datetime
import time
import pytz 
import hashlib
import os
import json

app = Flask(__name__)
voting_blockchain = Blockchain()

# --- 1. CONFIGURATION & LOGS ---
voting_config = {
    "start": datetime(2026, 2, 22, 13, 0),
    "end": datetime(2026, 2, 22, 14, 0),
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"},
        {"name": "Laxman", "symbol": "🐘"}
    ]
}

# JNTU-GV Authorized Range
AUTHORIZED_VOTERS = [f"24V11A05{str(i).zfill(2)}" for i in range(1, 81)]
STORAGE_FILE = 'blockchain_storage.json'
security_logs = []

# --- 2. PERSISTENCE ---
def save_blockchain():
    """Saves blockchain state for Render persistence."""
    chain_data = [block.__dict__ for block in voting_blockchain.chain]
    with open(STORAGE_FILE, 'w') as f:
        json.dump(chain_data, f)

# --- 3. VOTER INTERFACE ---
@app.route('/')
def index():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST).replace(tzinfo=None) 
    remaining_seconds = int((voting_config["end"] - now).total_seconds())
    
    if now < voting_config["start"]:
        status = "waiting"
    elif now > voting_config["end"]:
        status = "closed"
        remaining_seconds = 0
    else:
        status = "live"
    
    return render_template('index.html', 
                           config=voting_config, 
                           status=status, 
                           remaining_s=max(0, remaining_seconds))

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    voter_id = request.form.get('voter_id').strip().upper()
    candidate = request.form.get('candidate')
    IST = pytz.timezone('Asia/Kolkata')
    log_time = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

    if voter_id not in AUTHORIZED_VOTERS:
        security_logs.append({"id": voter_id, "time": log_time, "reason": "Unauthorized ID"})
        return "<h1>Unauthorized Student ID</h1>", 403

    nullifier = hashlib.sha256(f"jntugv_salt_{voter_id}".encode()).hexdigest()

    # Detect Double Voting (e.g., 24V11A0522)
    for block in voting_blockchain.chain:
        for tx in block.transactions:
            if tx.get('nullifier') == nullifier:
                security_logs.append({"id": voter_id, "time": log_time, "reason": "Double Voting Attempt"})
                return "<h1>Error: Already voted!</h1>", 403

    receipt = hashlib.sha256(f"{nullifier}{time.time()}".encode()).hexdigest()[:10].upper()
    voting_blockchain.add_new_transaction({"nullifier": nullifier, "candidate": candidate, "receipt": receipt, "timestamp": time.time()})
    voting_blockchain.mine()
    save_blockchain()
    return render_template('success.html', receipt=receipt)

# --- 4. ADMIN DASHBOARD LOGIC ---
@app.route('/admin-results/JNTUGV_SECRET')
def admin_results():
    tally = {}
    total_votes = 0
    for block in voting_blockchain.chain[1:]:
        for tx in block.transactions:
            c = tx.get('candidate')
            tally[c] = tally.get(c, 0) + 1
            total_votes += 1
    
    # Calculate Turnout and Winner for Top Stats
    turnout = round((total_votes / len(AUTHORIZED_VOTERS)) * 100, 1) if AUTHORIZED_VOTERS else 0
    winner = max(tally, key=tally.get) if tally else "No votes yet"
    
    return render_template('results.html', 
                           tally=tally, 
                           winner=winner, 
                           config=voting_config, 
                           turnout=turnout, 
                           logs=security_logs)

@app.route('/update-candidates', methods=['POST'])
def update_candidates():
    names = request.form.getlist('c_name')
    symbols = request.form.getlist('c_symbol')
    voting_config["candidates"] = [{"name": n.strip(), "symbol": s.strip() or "🗳️"} for n, s in zip(names, symbols) if n.strip()]
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/update-time', methods=['POST'])
def update_time():
    voting_config["start"] = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
    voting_config["end"] = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
    return redirect('/admin-results/JNTUGV_SECRET')

# Restored Stop Clock Logic
@app.route('/stop-early', methods=['POST'])
def stop_early():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST).replace(tzinfo=None)
    voting_config["end"] = now
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/reset-election', methods=['POST'])
def reset_election():
    global voting_blockchain, security_logs
    voting_blockchain, security_logs = Blockchain(), []
    if os.path.exists(STORAGE_FILE): os.remove(STORAGE_FILE)
    return redirect('/admin-results/JNTUGV_SECRET')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)