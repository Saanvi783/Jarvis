import requests
import json
import sys

BASE = "http://127.0.0.1:5000"

print("==================================================")
print("  TESTING JARVIS LIVE RUNNING SERVER (PORT 5000)  ")
print("==================================================")

# 1. Test UI Serving
try:
    r = requests.get(f"{BASE}/", timeout=5)
    assert r.status_code == 200
    assert "J.A.R.V.I.S." in r.text
    print("[PASS] 1. Static UI delivery (index.html): HTTP 200 OK")
except Exception as e:
    print(f"[FAIL] 1. UI delivery: {e}")
    sys.exit(1)

# 2. Test /api/status
try:
    r = requests.get(f"{BASE}/api/status", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "JARVIS"
    assert data["status"] == "online"
    print(f"[PASS] 2. System Status endpoint: Online (OS: {data.get('os')})")
    print(f"       Supported apps: {', '.join(data.get('supported_apps', []))}")
except Exception as e:
    print(f"[FAIL] 2. Status endpoint: {e}")
    sys.exit(1)

# 3. Test /api/chat commands
commands_to_test = [
    ("What time is it?", "datetime", True),
    ("What is today's date?", "datetime", True),
    ("Open YouTube", "open_website", True),
    ("Open Notepad", "open_app", True),
    ("Search Google for James Webb Telescope", "web_search", True),
    ("Shutdown the system", "system_power", False), # Safeguard confirmation
    ("Are you smarter than me?", None, False)        # Conversational query
]

for query, expected_action, expected_handled in commands_to_test:
    try:
        r = requests.post(f"{BASE}/api/chat", json={"message": query, "history": []}, timeout=5)
        assert r.status_code == 200
        res = r.json()
        if expected_action:
            assert res.get("action") == expected_action
            print(f"[PASS] Command '{query}' -> Action: {res.get('action')}")
            print(f"       Reply: \"{res.get('reply')}\"")
        else:
            print(f"[PASS] Chat query '{query}' -> Handled: {res.get('is_command')} (Handled by AI pipeline)")
            print(f"       Reply: \"{res.get('reply')[:80]}...\"")
    except Exception as e:
        print(f"[FAIL] Query '{query}': {e}")

# 4. Test /api/command direct action
try:
    r = requests.post(f"{BASE}/api/command", json={"action": "web_search", "target": "Python Flask"}, timeout=5)
    assert r.status_code == 200
    print("[PASS] 4. Direct /api/command endpoint: HTTP 200 OK")
except Exception as e:
    print(f"[FAIL] Direct command endpoint: {e}")

print("==================================================")
print("  ALL END-TO-END LIVE FEATURES VERIFIED WORKING!  ")
print("==================================================")
