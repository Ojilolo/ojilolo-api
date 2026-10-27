from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# PUT YOUR FOOTBALL-DATA.ORG API KEY HERE
API_KEY = "YOUR_API_KEY_HERE"

@app.route('/api/tips')
def get_tips():
    try:
        # Fetch Premier League matches
        url = "https://api.football-data.org/v4/competitions/PL/matches"
        headers = { 'X-Auth-Token': API_KEY }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        matches = data.get('matches', [])
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        tips = []
        
        # Find the next 3 upcoming matches (ignoring specific dates)
        for match in matches:
            if len(tips) >= 3:
                break
                
            # Check if the match is scheduled (hasn't been played yet)
            if match['status'] == 'SCHEDULED':
                home = match['homeTeam']['name']
                away = match['awayTeam']['name']
                
                tips.append({
                    "home": home,
                    "away": away,
                    "odds": 1.40, # Placeholder odds
                    "confidence": "85%", # Placeholder confidence
                    "banker": f"{home} Win"
                })
                
        if not tips:
            tips.append({
                "home": "No matches available",
                "away": "Check back later",
                "odds": 0.0,
                "confidence": "0%",
                "banker": "None"
            })

        result = {
            "date": today,
            "bankroll": 1500,
            "suggested_stake": 75,
            "tips": tips
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
