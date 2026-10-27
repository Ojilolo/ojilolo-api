from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# PUT YOUR FOOTBALL-DATA.ORG API KEY HERE
API_KEY = "YOUR_API_KEY_HERE"

# The leagues we want to scan
LEAGUES = ["PL", "BL1", "FL1", "BSA", "CSL", "SA", "PD", "ISL"]

@app.route('/api/tips')
def get_tips():
    try:
        tips = []
        headers = { 'X-Auth-Token': API_KEY }
        today = datetime.utcnow().strftime('%Y-%m-%d')

        # Loop through each league
        for league in LEAGUES:
            # Stop if we already have 3 good tips
            if len(tips) >= 3:
                break
                
            url = f"https://api.football-data.org/v4/competitions/{league}/matches?status=SCHEDULED"
            response = requests.get(url, headers=headers)
            
            # If the API blocks this league (free tier limits), skip to the next one
            if response.status_code != 200:
                continue
                
            data = response.json()
            matches = data.get('matches', [])
            
            # Look through matches to find one to add
            for match in matches:
                if len(tips) >= 3:
                    break
                    
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
