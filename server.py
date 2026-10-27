
from flask import Flask, jsonify
import time
import random

app = Flask(__name__)

@app.route('/api/tips')
def get_tips():
    # A larger pool of matches that the server can pick from
    pool = [
        {"home": "Real Madrid", "away": "Barcelona", "odds": 1.85, "confidence": "65%", "banker": "Over 2.5 Goals"},
        {"home": "Man City", "away": "Arsenal", "odds": 1.50, "confidence": "75%", "banker": "Man City Win"},
        {"home": "Bayern Munich", "away": "Dortmund", "odds": 1.40, "confidence": "80%", "banker": "Bayern Win"},
        {"home": "Juventus", "away": "AC Milan", "odds": 2.10, "confidence": "55%", "banker": "Both Teams Score"},
        {"home": "Chelsea", "away": "Liverpool", "odds": 1.65, "confidence": "70%", "banker": "Liverpool Win"},
        {"home": "PSG", "away": "Marseille", "odds": 1.30, "confidence": "88%", "banker": "PSG Win"},
        {"home": "Atletico Madrid", "away": "Sevilla", "odds": 1.45, "confidence": "78%", "banker": "Atletico Win"}
    ]
    
    # Randomly pick 3 matches from the pool
    daily_tips = random.sample(pool, 3)

    data = {
        "date": time.strftime("%Y-%m-%d"),
        "bankroll": 1500,
        "suggested_stake": 75,
        "tips": daily_tips
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
