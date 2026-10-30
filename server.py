from flask import Flask, jsonify, request
import requests
import sqlite3
import math
import random
import os
import subprocess
from datetime import datetime
from groq import Groq

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

# --- BETTING ROUTES ---

@app.route('/api/tips')
def get_tips():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    current_balance = get_balance()
    tips = []
    
    pool = [
        {"home": "Inter Milan", "away": "Lecce", "league": "Serie A"},
        {"home": "PSG", "away": "Nantes", "league": "Ligue 1"},
        {"home": "Liverpool", "away": "Luton", "league": "Premier League"},
        {"home": "Real Madrid", "away": "Getafe", "league": "La Liga"},
        {"home": "Bayern Munich", "away": "Darmstadt", "league": "Bundesliga"}
    ]
    daily_matches = random.sample(pool, 3)
    
    for match in daily_matches:
        p_home = calculate_poisson_probability(1.8, 1.2)
        kelly_stake = calculate_kelly(current_balance, 2.50, p_home)
        tips.append({
            "home": match["home"], "away": match["away"], "league": match["league"],
            "odds": 2.50, "confidence": f"{int(p_home*100)}%",
            "banker": f"{match['home']} Win", "stake": kelly_stake
        })
    return jsonify({"date": today, "bankroll": current_balance, "tips": tips})

@app.route('/api/manual_tips', methods=['POST'])
def get_manual_tips():
    try:
        data = request.get_json()
        matches = data.get('matches', [])
        current_balance = get_balance()
        tips = []

        for match in matches:
            home_name = match.get('home')
            away_name = match.get('away')
            league_name = match.get('league', 'Manual Entry')

            p_home = calculate_poisson_probability(random.uniform(1.2, 2.5), random.uniform(0.8, 1.5))
            
            kelly_stake = calculate_kelly(current_balance, 2.50, p_home)
            tips.append({
                "home": home_name, "away": away_name, "league": league_name,
                "odds": 2.50, "confidence": f"{int(p_home*100)}%",
                "banker": f"{home_name} Win", "stake": kelly_stake
            })
            
        return jsonify({"date": datetime.utcnow().strftime('%Y-%m-%d'), "bankroll": current_balance, "tips": tips})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_vault():
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        update_balance(amount)
        return jsonify({"status": "success", "new_balance": get_balance()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- AI AGENT ROUTE ---

@app.route('/api/run_agent', methods=['POST'])
def run_agent():
    try:
        data = request.get_json()
        goal = data.get('goal', '')
        if not goal:
            return jsonify({"error": "No goal provided"}), 400

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return jsonify({"error": "GROQ_API_KEY environment variable is missing."}), 500

        client = Groq(api_key=api_key)
        history = []
        final_output = ""
        
        system_prompt = """
        You are an autonomous AI agent running inside Termux on an Android phone.
        You have access to the `subprocess` module to run terminal commands.
        If the user asks you to find or locate something (like a YouTube video), you MUST write Python code that uses the `subprocess` module to run `yt-dlp "ytsearch5:QUERY" --get-id --get-title` to find it.
        Do not make up links. Use the tool.
        
        Write ONLY Python code to achieve the next step. No markdown formatting like ```python. 
        The code must print its results to the terminal.
        """

        for i in range(3): 
            prompt = f"Goal: {goal}\nPrevious history: {history}"
            
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            generated_code = response.choices[0].message.content.strip()
            
            if generated_code.startswith("```python"): generated_code = generated_code[9:]
            if generated_code.endswith("```"): generated_code = generated_code[:-3]
            
            with open("agent_action.py", "w") as f:
                f.write(generated_code)
                
            try:
                result = subprocess.run(["python", "agent_action.py"], capture_output=True, text=True, timeout=30)
                output = result.stdout + result.stderr
            except Exception as e:
                output = f"Execution Error: {str(e)}"
            
            final_output += f"--- Iteration {i+1} ---\nCode:\n{generated_code}\n\nOutput:\n{output}\n\n"
            history.append(f"Code: {generated_code} Output: {output}")
            
            if "youtube.com/watch" in output or "youtu.be" in output:
                break
            
        return jsonify({"result": final_output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
