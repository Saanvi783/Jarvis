"""
JARVIS Web Application & Server
Entry point for the JARVIS Personal Assistant.
Serves the futuristic web interface and provides REST API endpoints for
chat, voice interaction support, and system controls.
"""

import os
import sys
import datetime
import platform
from flask import Flask, request, jsonify, send_from_directory
from command_handler import handle_system_command, open_application, open_website, perform_web_search, ALLOWED_APPS
from ai_service import get_ai_response, is_ai_configured, get_api_key, load_env_file

# Initialize Flask application serving root directory as static assets
app = Flask(__name__, static_folder=".", static_url_path="")

# Load environment configuration
load_env_file()


@app.after_request
def add_cors_headers(response):
    """Enable CORS for flexible local development and live-reloading."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/")
def index():
    """Serves the main JARVIS web interface."""
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    """Serves static files (style.css, script.js, assets)."""
    return send_from_directory(".", path)


@app.route("/api/status", methods=["GET"])
def system_status():
    """Returns the operational status, OS details, and AI configuration state."""
    _, provider = get_api_key()
    now = datetime.datetime.now()

    return jsonify({
        "status": "online",
        "name": "JARVIS",
        "full_name": "Just A Rather Very Intelligent System",
        "ai_configured": is_ai_configured(),
        "ai_provider": provider if provider else "None (Set in .env)",
        "os": f"{platform.system()} {platform.release()}",
        "time": now.strftime("%I:%M:%S %p"),
        "date": now.strftime("%A, %B %d, %Y"),
        "supported_apps": [app_data["name"] for app_data in ALLOWED_APPS.values()]
    })


@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    """
    Main communication endpoint.
    1. Evaluates user input for local computer controls (apps, websites, searches, time).
    2. If not a command, delegates to conversational AI with personality and session history.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return jsonify({
                "success": False,
                "reply": "I didn't quite catch that, sir. Could you please repeat?",
                "is_command": False
            }), 400

        # Step 1: Check for basic computer control commands
        cmd_result = handle_system_command(message)
        if cmd_result["handled"]:
            return jsonify({
                "success": cmd_result["success"],
                "reply": cmd_result["response"],
                "is_command": True,
                "action": cmd_result["action"],
                "requires_confirmation": cmd_result["requires_confirmation"]
            })

        # Step 2: Handle via conversational AI
        success, ai_reply = get_ai_response(message, history)
        return jsonify({
            "success": success,
            "reply": ai_reply,
            "is_command": False,
            "action": None,
            "requires_confirmation": False
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "reply": f"An internal diagnostic error occurred: {str(e)}",
            "is_command": False
        }), 500


@app.route("/api/command", methods=["POST"])
def direct_command_endpoint():
    """Direct execution endpoint for pre-validated UI actions."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        action = data.get("action")
        target = data.get("target")

        if action == "open_app":
            success, msg = open_application(target)
            return jsonify({"success": success, "reply": msg})
        elif action == "open_website":
            success, msg = open_website(target)
            return jsonify({"success": success, "reply": msg})
        elif action == "web_search":
            success, msg = perform_web_search(target)
            return jsonify({"success": success, "reply": msg})
        else:
            return jsonify({"success": False, "reply": "Unrecognized action directive, sir."}), 400

    except Exception as e:
        return jsonify({"success": False, "reply": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("=" * 60)
    print("  JARVIS // Just A Rather Very Intelligent System")
    print(f"  Interface initialized at: http://{host}:{port}")
    print(f"  AI Configured: {'Yes' if is_ai_configured() else 'No (configure .env)'}")
    print("=" * 60)
    app.run(host=host, port=port, debug=False)
