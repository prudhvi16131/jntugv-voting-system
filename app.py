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

# --- 1. CONFIGURATION ---
# Default settings can be overwritten via the Admin Dashboard
voting_config = {
    "start": datetime(2026, 2, 22, 11, 25),
    "end": datetime(2026, 2, 22, 11, 41),
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"},
        {"name": "Laxman", "symbol": "🐘"}
    ]
}

# JNTU-GV Authorized Range
AUTHORIZED_VOTERS = [f"24V11A05{str(i).zfill(2)}" for i in range(1, 81)]
STORAGE_FILE = 'blockchain_storage.json'

# --- 2. PERSISTENCE LOGIC ---
def save_blockchain():
    """Saves the chain to a JSON file to prevent data loss on Render restarts."""
    chain_data = [block.__dict__ for block in voting_blockchain.chain]
    with open(STORAGE_FILE, 'w') as f:
        json.dump(chain_data, f)

# --- 3. VOTER INTERFACE ---
@app.route('/')
def index():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST).replace(tzinfo=None) 
    
    # CALCULATE REMAINING SECONDS:
    # This forces the countdown to follow your Admin Page settings
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
                           remaining_s=remaining_seconds)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    voter_id = request.form.get('voter_id')
    candidate = request.form.get('candidate')

    if voter_id not in AUTHORIZED_VOTERS:
        return "<h1>Unauthorized Student ID</h1>", 403

    # ZKP NULLIFIER for privacy and double-vote protection
    nullifier = hashlib.sha256(f"jntugv_salt_{voter_id}".encode()).hexdigest()

    for block in voting_blockchain.chain:
        for tx in block.transactions:
            if tx.get('nullifier') == nullifier:
                return "<h1>Error: This ID has already cast a vote!</h1>", 403

    receipt = hashlib.sha256(f"{nullifier}{time.time()}".encode()).hexdigest()[:10].upper()

    vote_data = {
        "nullifier": nullifier, 
        "candidate": candidate, 
        "receipt": receipt,
        "timestamp": time.time()
    }
    
    voting_blockchain.add_new_transaction(vote_data)
    voting_blockchain.mine()
    save_blockchain()
    
    return render_template('success.html', receipt=receipt)

# --- 4. ADMIN DASHBOARD & MANAGEMENT ---
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
    
    turnout = round((total_votes / len(AUTHORIZED_VOTERS)) * 100, 1)
    winner = max(tally, key=tally.get) if tally else "No votes yet"
    
    return render_template('results.html', tally=tally, winner=winner, 
                           config=voting_config, turnout=turnout, total=total_votes)

# FIX: Added this specific route to stop the "Not Found" error
@app.route('/update-candidates', methods=['POST'])
def update_candidates():
    """Handles dynamic candidate and symbol updates."""
    names = request.form.getlist('c_name')
    symbols = request.form.getlist('c_symbol')
    updated_list = []
    for n, s in zip(names, symbols):
        if n.strip():
            updated_list.append({"name": n.strip(), "symbol": s.strip()})
    voting_config["candidates"] = updated_list
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/update-time', methods=['POST'])
def update_time():
    """Updates the election window manually."""
    new_start = request.form.get('start_time')
    new_end = request.form.get('end_time')
    voting_config["start"] = datetime.strptime(new_start, '%Y-%m-%dT%H:%M')
    voting_config["end"] = datetime.strptime(new_end, '%Y-%m-%dT%H:%M')
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/stop-early', methods=['POST'])
def stop_early():
    """Ends election instantly."""
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST).replace(tzinfo=None)
    voting_config["end"] = now
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/reset-election', methods=['POST'])
def reset_election():
    global voting_blockchain
    voting_blockchain = Blockchain()
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)
    return redirect('/admin-results/JNTUGV_SECRET')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)  