from flask import Flask, jsonify, request
import requests
import sqlite3
from datetime import datetime

app = Flask(__name__)

# PUT YOUR API KEY HERE
API_KEY = "YOUR_API_KEY_HERE"
DB_FILE = "bankroll.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vault
                 (id INTEGER PRIMARY KEY, balance REAL)''')
    c.execute('SELECT COUNT(*) FROM vault')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO vault (id, balance) VALUES (1, 1500.0)')
    conn.commit()
    conn.close()

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

def calculate_kelly(balance, odds, prob):
    # Kelly Formula: f* = ( (b * p) - q ) / b
    # where b = odds - 1, p = probability, q = 1 - p
    b = odds - 1
    p = prob
    q = 1 - p
    
    kelly_fraction = ((b * p) - q) / b
    
    # We use "Fractional Kelly" (dividing by 4) to reduce volatility
    # and never bet more than 5% of the bankroll
    fraction = kelly_fraction / 4 
    if fraction > 0.05: 
        fraction = 0.05
    if fraction < 0:
        fraction = 0 # Don't bet if edge is negative
        
    return round(balance * fraction, 2)

@app.route('/api/tips')
def get_tips():
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        current_balance = get_balance()
        
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
                home = match['teams']['home']['name']
                away = match['teams']['away']['name']
                
                # Simulated Odds and Probability (Since free API lacks odds)
                # We pretend the bookie gives 1.50 odds (66% implied)
                # We pretend our model calculates a 75% chance of winning
                simulated_odds = 1.50
                simulated_prob = 0.75 
                
                # Calculate the optimal stake using Kelly Criterion
                kelly_stake = calculate_kelly(current_balance, simulated_odds, simulated_prob)
                
                tips.append({
                    "home": home,
                    "away": away,
                    "league": match['league']['name'],
                    "odds": simulated_odds,
                    "confidence": f"{int(simulated_prob*100)}%",
                    "banker": f"{home} Win",
                    "stake": kelly_stake
                })
                
        if not tips:
            tips.append({"home": "No matches today", "away": "Check back later", "league": "None", "odds": 0.0, "confidence": "0%", "banker": "None", "stake": 0.0})

        result = {
            "date": today,
            "bankroll": current_balance,
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
