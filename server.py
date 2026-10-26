from flask import Flask, jsonify
import time

app = Flask(__name__)

@app.route('/api/tips')
def get_tips():
    data = {
        "date": time.strftime("%Y-%m-%d"),
        "bankroll": 1500,
        "suggested_stake": 75,
        "tips": [
            {"home": "Inter Milan", "away": "Lecce", "odds": 1.25, "confidence": "96%", "banker": "Inter Win"},
            {"home": "PSG", "away": "Nantes", "odds": 1.30, "confidence": "92%", "banker": "PSG Win"},
            {"home": "Liverpool", "away": "Luton", "odds": 1.22, "confidence": "95%", "banker": "Liverpool Win"}
        ]
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
