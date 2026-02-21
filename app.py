from flask import Flask, render_template, request, redirect, url_for
from blockchain import Blockchain
from datetime import datetime
import time

app = Flask(__name__)
voting_blockchain = Blockchain()

# --- 1. CONFIGURATION & VOTER DATABASE ---
# These are the default times, but the Admin can change them live
voting_config = {
    "start": datetime(2026, 2, 21, 9, 0),
    "end": datetime(2026, 2, 25, 17, 0)
}

# Authorized Hall Ticket Numbers for JNTU-GV
AUTHORIZED_VOTERS = ["24V11A0522", "24V11A0523", "24V11A0501", "23GV1A0501"]

# --- 2. VOTER ROUTES ---
@app.route('/')
def index():
    now = datetime.now()
    # Checks the live config to see if voting is open
    if now < voting_config["start"]:
        return f"<h1>Voting starts at {voting_config['start']}</h1>"
    if now > voting_config["end"]:
        return "<h1>Voting is now closed!</h1>"
    return render_template('index.html')

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

    # Secure the vote on the Blockchain
    vote_data = {"voter_id": voter_id, "candidate": candidate, "timestamp": time.time()}
    voting_blockchain.add_new_transaction(vote_data)
    voting_blockchain.mine()
    return redirect(url_for('ledger'))

@app.route('/ledger')
def ledger():
    chain_data = []
    for block in voting_blockchain.chain:
        chain_data.append(block.__dict__)
    return render_template('ledger.html', chain=chain_data)

# --- 3. ADMIN & TIME EDIT ROUTES ---
@app.route('/admin-results/JNTUGV_SECRET')
def admin_results():
    tally = {}
    # Skip Genesis block and count votes
    for block in voting_blockchain.chain[1:]:
        for tx in block.transactions:
            candidate = tx.get('candidate')
            if candidate:
                tally[candidate] = tally.get(candidate, 0) + 1
    
    winner = max(tally, key=tally.get) if tally else "No votes yet"
    # Pass 'config' to results.html for the Time Edit form
    return render_template('results.html', tally=tally, winner=winner, config=voting_config)

@app.route('/update-time', methods=['POST'])
def update_time():
    new_start = request.form.get('start_time')
    new_end = request.form.get('end_time')
    
    # Updates the live timing without restarting the server
    voting_config["start"] = datetime.strptime(new_start, '%Y-%m-%dT%H:%M')
    voting_config["end"] = datetime.strptime(new_end, '%Y-%m-%dT%H:%M')
    
    return redirect('/admin-results/JNTUGV_SECRET')

# --- 4. START SERVER (Always at the bottom) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)