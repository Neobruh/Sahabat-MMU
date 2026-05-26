from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# Replace with your Discord webhook URL
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL"


@app.route("/report", methods=["POST"])
def report_user():
    try:
        data = request.json

        reported_user = data.get("reported_user")
        reason = data.get("reason")
        reporter = data.get("reporter")

        if not reported_user or not reason or not reporter:
            return jsonify({
                "success": False,
                "message": "Missing required fields"
            }), 400

        # Discord embed message
        embed = {
            "title": "🚨 New User Report",
            "color": 16711680,  # Red
            "fields": [
                {
                    "name": "Reported User",
                    "value": reported_user,
                    "inline": False
                },
                {
                    "name": "Reported By",
                    "value": reporter,
                    "inline": False
                },
                {
                    "name": "Reason",
                    "value": reason,
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Report System • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
        }

        payload = {
            "embeds": [embed]
        }

        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)

        if response.status_code == 204:
            return jsonify({
                "success": True,
                "message": "Report sent successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to send webhook"
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)from flask import Flask, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

# Replace with your Discord webhook URL
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL"


@app.route("/report", methods=["POST"])
def report_user():
    try:
        data = request.json

        reported_user = data.get("reported_user")
        reason = data.get("reason")
        reporter = data.get("reporter")

        if not reported_user or not reason or not reporter:
            return jsonify({
                "success": False,
                "message": "Missing required fields"
            }), 400

        # Discord embed message
        embed = {
            "title": "🚨 New User Report",
            "color": 16711680,  # Red
            "fields": [
                {
                    "name": "Reported User",
                    "value": reported_user,
                    "inline": False
                },
                {
                    "name": "Reported By",
                    "value": reporter,
                    "inline": False
                },
                {
                    "name": "Reason",
                    "value": reason,
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Report System • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
        }

        payload = {
            "embeds": [embed]
        }

        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)

        if response.status_code == 204:
            return jsonify({
                "success": True,
                "message": "Report sent successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to send webhook"
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
