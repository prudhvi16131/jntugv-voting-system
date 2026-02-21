from flask import Flask, render_template, request, redirect, url_for
from blockchain import Blockchain
import time

app = Flask(__name__)
voting_blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    voter_id = request.form.get('voter_id')
    candidate = request.form.get('candidate')

    if not voter_id or not candidate:
        return "Error: Missing details", 400

    vote_data = {
        "voter_id": voter_id,
        "candidate": candidate,
        "timestamp": time.time()
    }

    voting_blockchain.add_new_transaction(vote_data)
    voting_blockchain.mine()
    return redirect(url_for('ledger'))

@app.route('/dashboard')
def dashboard():
    tally = {}
    # Count votes directly from the blockchain
    for block in voting_blockchain.chain[1:]:
        for tx in block.transactions:
            candidate = tx.get('candidate')
            if candidate:
                tally[candidate] = tally.get(candidate, 0) + 1
                
    return render_template('dashboard.html', tally=tally)

@app.route('/ledger')
def ledger():
    chain_data = [
        {
            "index": block.index,
            "transactions": block.transactions,
            "timestamp": block.timestamp,
            "previous_hash": block.previous_hash,
            "hash": block.hash
        }for block in voting_blockchain.chain
    ]
    return render_template('ledger.html', chain=chain_data)
@app.route('/admin-results/JNTUGV_SECRET')
def admin_results():
    # This counts the votes from the blockchain ledger
    tally = {}
    for block in voting_blockchain.chain[1:]:  # We skip the first "Genesis" block
        candidate = block.transactions[0].get('candidate')
        if candidate:
            tally[candidate] = tally.get(candidate, 0) + 1
            
    # This finds which candidate has the most votes
    winner = max(tally, key=tally.get) if tally else "No votes cast yet"
    return render_template('results.html', tally=tally, winner=winner)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
    from flask import Flask, render_template, request, redirect, url_for
from blockchain import Blockchain
from datetime import datetime
import time

app = Flask(__name__)
voting_blockchain = Blockchain()

# --- CONFIGURATION & DATABASE ---
VOTING_START = datetime(2026, 2, 21, 9, 0)
VOTING_END = datetime(2026, 2, 25, 17, 0)
# Add your JNTU-GV Hall Ticket Numbers here
AUTHORIZED_VOTERS = ["24V11A0522", "24V11A0523", "23GV1A0501"] 

@app.route('/')
def index():
    now = datetime.now()
    if now < VOTING_START:
        return f"<h1>Voting starts at {VOTING_START}</h1>"
    if now > VOTING_END:
        return "<h1>Voting is now closed!</h1>"
    return render_template('index.html')

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    voter_id = request.form.get('voter_id')
    candidate = request.form.get('candidate')

    # Security Check: Authorized ID
    if voter_id not in AUTHORIZED_VOTERS:
        return "Error: Unauthorized ID", 403

    # Security Check: Double Voting
    for block in voting_blockchain.chain:
        for tx in block.transactions:
            if tx.get('voter_id') == voter_id:
                return "Error: Already Voted!", 403

    vote_data = {"voter_id": voter_id, "candidate": candidate, "timestamp": time.time()}
    voting_blockchain.add_new_transaction(vote_data)
    voting_blockchain.mine()
    return redirect(url_for('ledger'))

@app.route('/ledger')
def ledger():
    chain_data = []
    for block in voting_blockchain.chain:
        chain_data.append({
            "index": block.index,
            "transactions": block.transactions,
            "timestamp": block.timestamp,
            "previous_hash": block.previous_hash,
            "hash": block.hash
        })
    return render_template('ledger.html', chain=chain_data)

@app.route('/admin-results/JNTUGV_SECRET')
def admin_results():
    tally = {}
    for block in voting_blockchain.chain[1:]:
        for tx in block.transactions:
            candidate = tx.get('candidate')
            if candidate:
                tally[candidate] = tally.get(candidate, 0) + 1
    
    winner = max(tally, key=tally.get) if tally else "No votes cast"
    return render_template('results.html', tally=tally, winner=winner)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)# Make these variables global so they can be edited
voting_config = {
    "start": datetime(2026, 2, 21, 9, 0),
    "end": datetime(2026, 2, 25, 17, 0)
}

@app.route('/admin-results/JNTUGV_SECRET')
def admin_results():
    tally = {}
    for block in voting_blockchain.chain[1:]:
        for tx in block.transactions:
            candidate = tx.get('candidate')
            if candidate:
                tally[candidate] = tally.get(candidate, 0) + 1
    
    winner = max(tally, key=tally.get) if tally else "No votes yet"
    # Pass the timing to the template
    return render_template('results.html', tally=tally, winner=winner, config=voting_config)

@app.route('/update-time', methods=['POST'])
def update_time():
    new_start = request.form.get('start_time')
    new_end = request.form.get('end_time')
    
    # Convert string from form back to Python datetime objects
    voting_config["start"] = datetime.strptime(new_start, '%Y-%m-%dT%H:%M')
    voting_config["end"] = datetime.strptime(new_end, '%Y-%m-%dT%H:%M')
    
    return redirect('/admin-results/JNTUGV_SECRET')
