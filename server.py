from flask import Flask, jsonify, request
import requests
import sqlite3
import math
import random
from datetime import datetime

app = Flask(__name__)

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
        
        # Fetch today's matches from TheSportsDB (Free Test Key = 3)
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d={today}&s=Soccer"
        
        response = requests.get(url)
        data = response.json()
        
        # Debug: Print the raw response to Render logs
        print("RAW API RESPONSE:", data)
        
        # Safely get events, handling 'null' responses from the API
        events = data.get('events')
        if not events:
            events = []
        
        # Shuffle the events so you get a different mix every time you refresh
        random.shuffle(events)
        
        tips = []
        
        for match in events:
            if len(tips) >= 3:
                break
                
            home_name = match.get('strHomeTeam')
            away_name = match.get('strAwayTeam')
            league_name = match.get('strLeague')
            
            # If the match doesn't have both teams, skip it
            if not home_name or not away_name:
                continue
            
            # Generate simulated stats for the Poisson math
            home_avg = round(random.uniform(1.2, 2.5), 2)
            away_avg = round(random.uniform(0.8, 1.5), 2)
            
            p_home = calculate_poisson_probability(home_avg, away_avg)
            
            if p_home > 0.40:
                simulated_odds = 2.50
                kelly_stake = calculate_kelly(current_balance, simulated_odds, p_home)
                
                tips.append({
                    "home": home_name,
                    "away": away_name,
                    "league": league_name,
                    "odds": simulated_odds,
                    "confidence": f"{int(p_home*100)}%",
                    "banker": f"{home_name} Win",
                    "stake": kelly_stake
                })
                
        if not tips:
            tips.append({"home": "No Matches Today", "away": "Check back tomorrow", "league": "None", "odds": 0.0, "confidence": "0%", "banker": "None", "stake": 0.0})

        return jsonify({"date": today, "bankroll": current_balance, "tips": tips})

    except Exception as e:
        print("SERVER ERROR:", str(e))
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
