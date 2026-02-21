from flask import Flask, render_template, request, redirect, url_for
from blockchain import Blockchain
from datetime import datetime
import time
import pytz 

app = Flask(__name__)
voting_blockchain = Blockchain()

# --- 1. CONFIGURATION & DATABASE ---
# Admin can change all of this live from the secret admin dashboard
voting_config = {
    "start": datetime(2026, 2, 21, 9, 0),
    "end": datetime(2026, 2, 25, 17, 0),
    "candidates": [
        {"name": "Candidate A", "symbol": "🦁"},
        {"name": "Candidate B", "symbol": "🐘"}
    ]
}

# Automatically generates JNTU-GV IDs from 24V11A0501 to 24V11A0580
AUTHORIZED_VOTERS = [f"24V11A05{str(i).zfill(2)}" for i in range(1, 81)]

# --- 2. VOTER ROUTES ---
@app.route('/')
def index():
    # Force the app to use India Standard Time (IST) for Render servers
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST).replace(tzinfo=None) 
    
    if now < voting_config["start"]:
        return f"<h1>Voting starts at {voting_config['start']} (IST)</h1>"
    if now > voting_config["end"]:
        return "<h1>Voting is now closed!</h1>"
    
    # Pass config so index.html can show the dynamic candidate list
    return render_template('index.html', config=voting_config)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    voter_id = request.form.get('voter_id')
    candidate = request.form.get('candidate')

    # Security: Database Check
    if voter_id not in AUTHORIZED_VOTERS:
        return "<h1>Error: Unauthorized Student ID</h1>", 403

    # Security: Double-Voting Prevention
    for block in voting_blockchain.chain:
        for tx in block.transactions:
            if tx.get('voter_id') == voter_id:
                return "<h1>Error: You have already cast your vote!</h1>", 403

    # Mine the vote into the Blockchain
    vote_data = {"voter_id": voter_id, "candidate": candidate, "timestamp": time.time()}
    voting_blockchain.add_new_transaction(vote_data)
    voting_blockchain.mine()
    
    # Modern Success Redirect
    return render_template('success.html')

# --- 3. ADMIN & RESULTS ROUTES ---
@app.route('/admin-results/JNTUGV_SECRET')
def admin_results():
    tally = {}
    # Skip Genesis block and calculate totals from the chain
    for block in voting_blockchain.chain[1:]:
        for tx in block.transactions:
            candidate = tx.get('candidate')
            if candidate:
                tally[candidate] = tally.get(candidate, 0) + 1
    
    winner = max(tally, key=tally.get) if tally else "No votes yet"
    return render_template('results.html', tally=tally, winner=winner, config=voting_config)

@app.route('/update-time', methods=['POST'])
def update_time():
    new_start = request.form.get('start_time')
    new_end = request.form.get('end_time')
    voting_config["start"] = datetime.strptime(new_start, '%Y-%m-%dT%H:%M')
    voting_config["end"] = datetime.strptime(new_end, '%Y-%m-%dT%H:%M')
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/update-candidates', methods=['POST'])
def update_candidates():
    # Pulls all names and symbols from the dynamic admin form
    names = request.form.getlist('c_name')
    symbols = request.form.getlist('c_symbol')
    
    updated_list = []
    for n, s in zip(names, symbols):
        if n.strip(): # Only add if the name field is not empty
            updated_list.append({"name": n, "symbol": s})
    
    voting_config["candidates"] = updated_list
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/reset-election', methods=['POST'])
def reset_election():
    # Re-initialize the blockchain to wipe test data
    global voting_blockchain
    voting_blockchain = Blockchain()
    return redirect('/admin-results/JNTUGV_SECRET')

@app.route('/ledger')
def ledger():
    # Public ledger view for verification
    chain_data = [block.__dict__ for block in voting_blockchain.chain]
    return render_template('ledger.html', chain=chain_data)

# --- 4. START SERVER ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)