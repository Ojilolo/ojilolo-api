from flask import Flask, jsonify, request
import requests
import sqlite3
import math
import random
from datetime import datetime

app = Flask(__name__)

# PUT YOUR FOOTBALL-DATA.ORG API KEY HERE
API_KEY = "28bd1150cc9446e49039c5718678b10f"
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
    exp_home = home_goals_avg * 1.2
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
        tips = []

        # 1. Try to fetch REAL matches from football-data.org
        url = "https://api.football-data.org/v4/competitions/PL/matches"
        headers = { 'X-Auth-Token': API_KEY }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            matches = response.json().get('matches', [])
            for match in matches:
                if len(tips) >= 3:
                    break
                if match['status'] == 'SCHEDULED':
                    home = match['homeTeam']['name']
                    away = match['awayTeam']['name']
                    
                    # Simulate real math for the API teams
                    p_home = calculate_poisson_probability(1.8, 1.2)
                    odds = 2.50
                    kelly = calculate_kelly(current_balance, odds, p_home)
                    
                    tips.append({
                        "home": home, "away": away, "league": "Premier League",
                        "odds": odds, "confidence": f"{int(p_home*100)}%",
                        "banker": f"{home} Win", "stake": kelly
                    })

        # 2. If API fails or returns 0 matches, use the MOCK ENGINE
        if not tips:
            pool = [
                {"home": "Inter Milan", "away": "Lecce", "league": "Serie A"},
                {"home": "PSG", "away": "Nantes", "league": "Ligue 1"},
                {"home": "Liverpool", "away": "Luton", "league": "Premier League"},
                {"home": "Real Madrid", "away": "Getafe", "league": "La Liga"},
                {"home": "Bayern Munich", "away": "Darmstadt", "league": "Bundesliga"}
            ]
            daily_matches = random.sample(pool, 3)
            for match in daily_matches:
                p_home = calculate_poisson_probability(1.9, 1.1)
                odds = 2.50
                kelly = calculate_kelly(current_balance, odds, p_home)
                tips.append({
                    "home": match["home"], "away": match["away"], "league": match["league"],
                    "odds": odds, "confidence": f"{int(p_home*100)}%",
                    "banker": f"{match['home']} Win", "stake": kelly
                })

        return jsonify({"date": today, "bankroll": current_balance, "tips": tips})

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
