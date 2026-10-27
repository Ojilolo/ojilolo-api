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
    # Simulates probability of Home Win, Draw, Away Win
    # This is a simplified Poisson model
    home_attack = home_goals_avg
    away_defense = away_goals_avg
    away_attack = away_goals_avg
    home_defense = home_goals_avg
    
    # Expected goals
    exp_home = home_attack * away_defense * 1.2 # 1.2 is home advantage
    exp_away = away_attack * home_defense * 0.9
    
    # Poisson formula: P(k; λ) = (λ^k * e^-λ) / k!
    def poisson(k, lam):
        return (lam**k * math.exp(-lam)) / math.factorial(k)
    
    prob_home_win = 0
    prob_draw = 0
    prob_away_win = 0
    
    # Calculate probabilities for 0 to 5 goals
    for i in range(6):
        for j in range(6):
            prob = poisson(i, exp_home) * poisson(j, exp_away)
            if i > j: prob_home_win += prob
            elif i == j: prob_draw += prob
            else: prob_away_win += prob
            
    return prob_home_win, prob_draw, prob_away_win

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
        
        # We will use the first 3 matches that have stats
        for match in matches:
            if len(tips) >= 3:
                break
                
            home_id = match['teams']['home']['id']
            away_id = match['teams']['away']['id']
            home_name = match['teams']['home']['name']
            away_name = match['teams']['away']['name']
            league = match['league']['name']
            
            # Get last 5 matches for Home team
            url_home = f"https://v3.football.api-sports.io/fixtures?team={home_id}&last=5"
            res_home = requests.get(url_home, headers=headers).json()
            home_goals = sum([m['goals']['home'] if m['teams']['home']['id'] == home_id else m['goals']['away'] for m in res_home.get('response', []) if m['goals']['home'] is not None])
            
            # Get last 5 matches for Away team
            url_away = f"https://v3.football.api-sports.io/fixtures?team={away_id}&last=5"
            res_away = requests.get(url_away, headers=headers).json()
            away_goals = sum([m['goals']['away'] if m['teams']['away']['id'] == away_id else m['goals']['home'] for m in res_away.get('response', []) if m['goals']['home'] is not None])
            
            # Average goals
            home_avg = home_goals / 5 if home_goals > 0 else 1.0
            away_avg = away_goals / 5 if away_goals > 0 else 1.0
            
            # Calculate probabilities
            p_home, p_draw, p_away = calculate_poisson_probability(home_avg, away_avg)
            
            # We only bet if the Home team has a > 50% chance of winning
            if p_home > 0.50:
                simulated_odds = 1.50 # Assume bookie gives 1.50
                # If our math says probability is higher than implied by odds (1/1.5 = 66%), we have an edge
                if p_home > 0.66:
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
            tips.append({"home": "No Value Bets", "away": "Check back later", "league": "None", "odds": 0.0, "confidence": "0%", "banker": "None", "stake": 0.0})

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
