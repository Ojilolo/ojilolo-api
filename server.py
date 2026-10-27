from flask import Flask, jsonify, request
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)

# PUT YOUR API KEY HERE
API_KEY = "e7d3332814a2b188fc6788f2ee35d2f2"
DB_FILE = "bankroll.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS vault
                 (id INTEGER PRIMARY KEY, balance REAL)''')
    # Check if we have a row, if not, insert $1500
    c.execute('SELECT COUNT(*) FROM vault')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO vault (id, balance) VALUES (1, 1500.0)')
    conn.commit()
    conn.close()

# Initialize the DB on startup
init_db()

def get_balance():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT balance FROM vault WHERE id=1')
    balance = c.fetchone()[0]
    conn.close()
    return balance

def update_balance(amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE vault SET balance = balance + ? WHERE id=1', (amount,))
    conn.commit()
    conn.close()

@app.route('/api/tips')
def get_tips():
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        current_balance = get_balance()
        suggested_stake = round(current_balance * 0.05, 2) # 5% flat stake
        
        url = f"https://v3.football.api-sports.io/fixtures?date={today}"
        headers = { 'x-apisports-key': API_KEY }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        matches = data.get('response', [])
        tips = []
        
        wanted_leagues = [78, 61, 71, 169, 39, 140, 135, 2, 3]
        
        for match in matches:
            if len(tips) >= 3:
                break
            if match['league']['id'] in wanted_leagues:
                tips.append({
                    "home": match['teams']['home']['name'],
                    "away": match['teams']['away']['name'],
                    "league": match['league']['name'],
                    "odds": 1.50,
                    "confidence": "85%",
                    "banker": f"{match['teams']['home']['name']} Win"
                })
                
        if not tips:
            tips.append({"home": "No matches today", "away": "Check back later", "league": "None", "odds": 0.0, "confidence": "0%", "banker": "None"})

        result = {
            "date": today,
            "bankroll": current_balance,
            "suggested_stake": suggested_stake,
            "tips": tips
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_vault():
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        update_balance(amount)
        new_balance = get_balance()
        return jsonify({"status": "success", "new_balance": new_balance})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
