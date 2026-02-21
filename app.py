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
    for block in blockchain.chain[1:]:  # We skip the first "Genesis" block
        candidate = block.data.get('candidate')
        if candidate:
            tally[candidate] = tally.get(candidate, 0) + 1
            
    # This finds which candidate has the most votes
    winner = max(tally, key=tally.get) if tally else "No votes cast yet"
    return render_template('results.html', tally=tally, winner=winner)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)