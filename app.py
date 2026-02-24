import hashlib
import json
import time
from datetime import datetime
import pytz
from io import BytesIO
from flask import Flask, render_template, request, jsonify, make_response

# PDF Libraries
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "BCET_BLOCKCHAIN_2026_SECURE"

# --- CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
ADMIN_SECRET = "BCET_ADMIN_PRO" 

ELECTION_SETTINGS = {
    "candidates": [
        {"name": "Ramu", "symbol": "🦁"}, 
        {"name": "Laxman", "symbol": "🐘"}
    ],
    "start_time": "2026-02-23T09:00",
    "end_time": "2026-02-24T23:59",
    "is_active": True,
    "authorized_prefix": "24V11A",
    "range_start": 501,
    "range_end": 580,
    "admin_secret": ADMIN_SECRET
}

class Blockchain:
    def __init__(self):
        self.reset()

    def reset(self):
        self.chain = []
        self.pending_votes = []
        self.nullifiers = set()
        self.security_logs = [] 
        self.create_block(previous_hash='1', proof=100)

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            'votes': list(self.pending_votes),
            'proof': proof,
            'previous_hash': previous_hash,
        }
        self.pending_votes = []
        self.chain.append(block)
        return block

    def get_last_block(self):
        return self.chain[-1]

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def get_vote_count(self, name):
        count = 0
        for block in self.chain:
            for v in block['votes']:
                if v['candidate'] == name:
                    count += 1
        return count

blockchain = Blockchain()

# --- ROUTES ---

@app.route('/')
def index():
    display_settings = ELECTION_SETTINGS.copy()
    if not ELECTION_SETTINGS["is_active"]:
        display_settings["end_time"] = datetime.now(IST).strftime("%Y-%m-%dT%H:%M")
    return render_template('index.html', candidate_list=ELECTION_SETTINGS["candidates"], settings=display_settings)

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    if not ELECTION_SETTINGS["is_active"]:
        return "<h1>Election Closed</h1><a href='/'>Back</a>"
    
    student_id = request.form.get('student_id', '').upper().strip()
    candidate = request.form.get('candidate')
    raw_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_ip = raw_ip.split(',')[0].strip() if raw_ip and ',' in raw_ip else raw_ip

    nullifier = hashlib.sha256(student_id.encode()).hexdigest()
    if nullifier in blockchain.nullifiers:
        blockchain.security_logs.append({"id": student_id, "time": datetime.now(IST).strftime("%H:%M:%S"), "reason": "Double Vote Attempt", "ip": user_ip})
        return render_template('already_cast.html')

    blockchain.nullifiers.add(nullifier)
    receipt_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12].upper()
    blockchain.pending_votes.append({'candidate': candidate, 'receipt': receipt_id})
    blockchain.create_block(proof=123, previous_hash=blockchain.hash(blockchain.get_last_block()))
    return render_template('success.html', candidate=candidate, receipt=receipt_id, timestamp=datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"))

@app.route(f'/admin-results/{ADMIN_SECRET}')
def admin_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_SETTINGS["candidates"]}
    return render_template('results.html', settings=ELECTION_SETTINGS, vote_counts=vote_counts, logs=blockchain.security_logs)

# --- ADMIN API ---
@app.route('/sync_candidates', methods=['POST'])
def sync_candidates():
    ELECTION_SETTINGS["candidates"] = request.json['candidates']
    return jsonify({"status": "success"})

@app.route('/stop_election', methods=['POST'])
def stop_election():
    ELECTION_SETTINGS["is_active"] = False
    return jsonify({"status": "success"})

@app.route('/reset_election', methods=['POST'])
def reset_election():
    blockchain.reset()
    return jsonify({"status": "success"})

# --- BCET BRANDED PDF ---
@app.route(f'/download-results/{ADMIN_SECRET}')
def download_results():
    vote_counts = {c['name']: blockchain.get_vote_count(c['name']) for c in ELECTION_SETTINGS["candidates"]}
    total_votes = sum(vote_counts.values())
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Theme Colors
    slate = colors.HexColor("#1e293b")
    blue = colors.HexColor("#2563eb")

    # Header
    p.setFillColor(slate)
    p.rect(0, height - 100, width, 100, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, height - 60, "BCET OFFICIAL ELECTION REPORT")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 80, f"Behara College of Engineering & Technology | {datetime.now(IST).strftime('%d %b %Y')}")

    # Content
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 150, "FINAL VOTE TALLY")
    
    y = height - 180
    for name, count in vote_counts.items():
        p.setFont("Helvetica", 12)
        p.drawString(50, y, f"{name}:")
        p.drawRightString(width - 50, y, f"{count} Votes")
        y -= 25

    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf)
    response.headers['Content-Disposition'] = "attachment; filename=BCET_Results.pdf"
    response.headers['Content-Type'] = 'application/pdf'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)