
from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# PUT YOUR FOOTBALL-DATA.ORG API KEY HERE
API_KEY = "28bd1150cc9446e49039c5718678b10f"

@app.route('/api/tips')
def get_tips():
    try:
        # Fetch Premier League matches
        url = "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED"
        headers = { 'X-Auth-Token': API_KEY }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        matches = data.get('matches', [])
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        tips = []
        
        # Filter for today's matches
        for match in matches:
            match_date = match['utcDate'].split('T')[0]
            
            if match_date == today and len(tips) < 3:
                home = match['homeTeam']['name']
                away = match['awayTeam']['name']
                
                tips.append({
                    "home": home,
                    "away": away,
                    "odds": 1.40,
                    "confidence": "85%",
                    "banker": f"{home} Win"
                })
                
        if not tips:
            tips.append({
                "home": "No matches today",
                "away": "Check back tomorrow",
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
