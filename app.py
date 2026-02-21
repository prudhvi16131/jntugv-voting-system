from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from blockchain import Blockchain
from datetime import datetime
import time
import pytz 
import hashlib
import os

app = Flask(__name__)
voting_blockchain = Blockchain()

# --- 1. CONFIGURATION ---
# JNTU-GV Authorized Range: 24V11A0501 to 24V11A0580
voting_config = {
    "start": datetime(2026, 2, 21, 9, 0),
    "end": datetime(2026, 2, 25, 17, 0),
    "candidates": [
        {"name": "Candidate A", "symbol": "🦁"},
        {"name": "Candidate B", "symbol": "🐘"}
    ]
}

AUTHORIZED_VOTERS = [f"24V11A05{str(i).zfill(2)}" for i in range(1, 81)]

# --- 2. PWA / APP SUPPORT ---
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

# --- 3. VOTER INTERFACE ---
@app.route('/')
def index():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST).replace(tzinfo=None) 
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

    if voter_id not in AUTHORIZED_VOTERS:
        return "<h1>Unauthorized Student ID</h1>", 403

    # ZKP NULLIFIER: Prevents double-voting while keeping ID off the blockchain
    nullifier = hashlib.sha256(f"jntugv_salt_{voter_id}".encode()).hexdigest()

    for block in voting_blockchain.chain:
        for tx in block.transactions:
            if tx.get('nullifier') == nullifier:
                return "<h1>Error: This ID has already cast a vote!</h1>", 403

    # Generate the Digital Receipt
    receipt = hashlib.sha256(f"{nullifier}{time.time()}".encode()).hexdigest()[:10].upper()

    vote_data = {
        "nullifier": nullifier, 
        "candidate": candidate, 
        "receipt": receipt,
        "timestamp": time.time()
    }
    
    voting_blockchain.add_new_transaction(vote_data)
    voting_blockchain.mine()
    
    return render_template('success.html', receipt=receipt)

# --- 4. PUBLIC AUDIT INTERFACE ---
@app.route('/audit', methods=['GET', 'POST'])
def audit():
    search_result = None
    receipt_to_find = request.form.get('receipt') if request.method == 'POST' else None

    if receipt_to_find:
        # Search the blockchain for the specific digital receipt
        for block in voting_blockchain.chain:
            for tx in block.transactions:
                if tx.get('receipt') == receipt_to_find.strip().upper():
                    search_result = {
                        "block_index": block.index,
                        "merkle_root": block.merkle_root,
                        "timestamp": datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                        "candidate": tx.get('candidate'),
                        "prev_hash": block.previous_hash
                    }
                    break
    
    return render_template('audit.html', result=search_result, searched_id=receipt_to_find)

# --- 5. ADMIN DASHBOARD & ANALYTICS ---
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
    chain_data = []
    for block in voting_blockchain.chain:
        chain_data.append(block.__dict__)
    return render_template('ledger.html', chain=chain_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)