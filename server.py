from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# PUT YOUR API-FOOTBALL.COM API KEY HERE
API_KEY = "e7d3332814a2b188fc6788f2ee35d2f2"

@app.route('/api/tips')
def get_tips():
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Fetch today's live fixtures worldwide
        url = f"https://v3.football.api-sports.io/fixtures?date={today}"
        headers = {
            'x-apisports-key': API_KEY
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        matches = data.get('response', [])
        tips = []
        
        # Filter the matches to find the top leagues you want
        # 78 = Bundesliga, 61 = Ligue 1, 71 = Serie A (Brazil), 169 = CSL (China), 39 = EPL, 140 = La Liga, 135 = Serie A (Italy)
        wanted_leagues = [78, 61, 71, 169, 39, 140, 135, 2, 3]
        
        for match in matches:
            if len(tips) >= 3:
                break
                
            league_id = match['league']['id']
            
            if league_id in wanted_leagues:
                home = match['teams']['home']['name']
                away = match['teams']['away']['name']
                league_name = match['league']['name']
                
                tips.append({
                    "home": home,
                    "away": away,
                    "league": league_name,
                    "odds": 1.50,
                    "confidence": "85%",
                    "banker": f"{home} Win"
                })
                
        if not tips:
            tips.append({
                "home": "No matches today",
                "away": "Check back later",
                "league": "None",
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
