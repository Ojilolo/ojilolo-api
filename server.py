from flask import Flask, jsonify, request
import requests
import sqlite3
import math
from datetime import datetime

app = Flask(__name__)

# PUT YOUR API KEY HERE
API_KEY = "e7d3332814a2b188fc6788f2ee35d2f2"
DB_FILE = "bankroll.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vault (id INTEGER PRIMARY KEY, balance REAL)''')
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

def calculate_poisson_probability(home_goals_avg, away_goals_avg):
    # Simplified Poisson Model
    exp_home = home_goals_avg * 1.2 # Home advantage
    exp_away = away_goals_avg * 0.9
    
    def poisson(k, lam):
        return (lam**k * math.exp(-lam)) / math.factorial(k)
    
    prob_home_win = 0
    for i in range(6):
        for j in range(6):
            prob = poisson(i, exp_home) * poisson(j, exp_away)
            if i > j: prob_home_win += prob
            
    return prob_home_win

def calculate_kelly(balance, odds, prob):
    b = odds - 1
    p = prob
    q = 1 - p
    kelly_fraction = ((b * p) - q) / b
    fraction = kelly_fraction / 4 
    if fraction > 0.05: fraction = 0.05
    if fraction < 0: fraction = 0 
    return round(balance * fraction, 2)

@app.route('/api/tips')
def get_tips():
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        current_balance = get_balance()
        
        # Fetch today's fixtures
        url = f"https://v3.football.api-sports.io/fixtures?date={today}"
        headers = { 'x-apisports-key': API_KEY }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'errors' in data and data['errors']:
            return jsonify({"error": data['errors']}), 500
            
        matches = data.get('response', [])
        tips = []
        
        # ONLY loop through the first 4 matches to prevent rate-limiting
        for match in matches[:4]:
            home_id = match['teams']['home']['id']
            away_id = match['teams']['away']['id']
            home_name = match['teams']['home']['name']
            away_name = match['teams']['away']['name']
            league = match['league']['name']
            
            # Get last 5 matches for Home team
            url_home = f"https://v3.football.api-sports.io/fixtures?team={home_id}&last=5"
            res_home = requests.get(url_home, headers=headers).json()
            home_goals = 0
            for m in res_home.get('response', []):
                if m['goals']['home'] is not None:
                    home_goals += m['goals']['home'] if m['teams']['home']['id'] == home_id else m['goals']['away']
            
            # Get last 5 matches for Away team
            url_away = f"https://v3.football.api-sports.io/fixtures?team={away_id}&last=5"
            res_away = requests.get(url_away, headers=headers).json()
            away_goals = 0
            for m in res_away.get('response', []):
                if m['goals']['home'] is not None:
                    away_goals += m['goals']['away'] if m['teams']['away']['id'] == away_id else m['goals']['home']
            
            # Average goals
            home_avg = home_goals / 5 if home_goals > 0 else 1.0
            away_avg = away_goals / 5 if away_goals > 0 else 1.0
            
            # Calculate probabilities using Poisson
            p_home = calculate_poisson_probability(home_avg, away_avg)
            
            # We only bet if the Home team has a > 60% chance of winning
            if p_home > 0.60:
                simulated_odds = 1.50
                kelly_stake = calculate_kelly(current_balance, simulated_odds, p_home)
                
                tips.append({
                    "home": home_name,
                    "away": away_name,
                    "league": league,
                    "odds": simulated_odds,
                    "confidence": f"{int(p_home*100)}%",
                    "banker": f"{home_name} Win",
                    "stake": kelly_stake
                })
                
        if not tips:
            tips.append({"home": "No Value Bets", "away": "Model found no edge", "league": "Poisson Math", "odds": 0.0, "confidence": "0%", "banker": "None", "stake": 0.0})

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
