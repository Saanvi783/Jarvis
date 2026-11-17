"""
JARVIS Command Handler
Handles basic computer controls safely on Windows:
- Open configured desktop applications
- Open supported websites
- Execute web searches via default browser
- Report current date and time
- Enforce confirmation protocols for system-level actions
"""

import os
import re
import sys
import datetime
import webbrowser
import subprocess
import urllib.parse

# Whitelist of allowed desktop applications on Windows
ALLOWED_APPS = {
    "notepad": {
        "name": "Notepad",
        "command": ["notepad.exe"],
        "keywords": ["notepad", "text editor", "notes"]
    },
    "calculator": {
        "name": "Calculator",
        "command": ["calc.exe"],
        "keywords": ["calculator", "calc"]
    },
    "explorer": {
        "name": "File Explorer",
        "command": ["explorer.exe"],
        "keywords": ["explorer", "file explorer", "files", "my computer"]
    },
    "cmd": {
        "name": "Command Prompt",
        "command": ["cmd.exe", "/c", "start", "cmd.exe"],
        "keywords": ["cmd", "command prompt", "terminal", "console"]
    },
    "taskmgr": {
        "name": "Task Manager",
        "command": ["taskmgr.exe"],
        "keywords": ["task manager", "taskmgr", "activity monitor"]
    },
    "paint": {
        "name": "Paint",
        "command": ["mspaint.exe"],
        "keywords": ["paint", "mspaint", "drawing"]
    }
}

# Whitelist of popular websites
WEBSITE_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "wikipedia": "https://www.wikipedia.org",
    "reddit": "https://www.reddit.com",
    "stackoverflow": "https://stackoverflow.com",
    "chatgpt": "https://chatgpt.com",
    "linkedin": "https://www.linkedin.com"
}


def get_current_time_and_date():
    """Returns formatted time and date with JARVIS personality."""
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%A, %B %d, %Y")
    return f"The current time is {time_str} on {date_str}."


def open_application(app_key):
    """Safely launches a whitelisted desktop application."""
    if app_key not in ALLOWED_APPS:
        return False, f"Application '{app_key}' is not in the authorized application list."

    app_info = ALLOWED_APPS[app_key]
    try:
        if sys.platform == "win32":
            subprocess.Popen(app_info["command"], shell=False)
            return True, f"Opening {app_info['name']} now."
        else:
            return False, "Desktop application control is currently configured for Windows environments."
    except Exception as e:
        return False, f"I encountered an error attempting to launch {app_info['name']}: {str(e)}"


def open_website(url, site_name=None):
    """Safely opens an approved or validated website."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        url = "https://" + url

    try:
        webbrowser.open_new_tab(url)
    except Exception:
        pass

    label = site_name if site_name else url
    return True, f"Opening {label}.", url


def perform_web_search(query):
    """Performs a web search using the user's default browser."""
    if not query or not query.strip():
        return False, "Please provide a query for me to search.", None

    clean_query = query.strip()
    # Strip unnecessary leading words like 'about', 'for', 'on', 'regarding'
    clean_query = re.sub(r"^(?:about|for|on|regarding)\s+", "", clean_query, flags=re.IGNORECASE).strip()
    encoded = urllib.parse.quote_plus(clean_query)
    search_url = f"https://www.google.com/search?q={encoded}"

    try:
        webbrowser.open_new_tab(search_url)
    except Exception:
        pass

    return True, f"Searching Google for '{clean_query}'.", search_url


def handle_system_command(text):
    """
    Parses user input to determine if it matches a basic computer control command.
    Returns:
        dict: {
            "handled": bool,
            "action": str,
            "response": str,
            "url": str or None,
            "success": bool,
            "requires_confirmation": bool
        }
    """
    raw = text.strip()

    # Normalize: strip trailing punctuation
    clean = re.sub(r"[?!.,]+$", "", raw).strip()

    # Iteratively strip conversational preambles (greetings, address, polite openers)
    for _ in range(3):
        clean = re.sub(r"^(?:hello|hi|hey|ok|good\s+(?:morning|afternoon|evening|day)|greetings)\b[,\s]*", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"^(?:jarvis|saanvi)\b[,\s]*", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"^(?:(?:can|could|would)\s+you\s+(?:please\s+)?(?:tell\s+me|show\s+me|give\s+me|check)?\s*)", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"^(?:please\s+|kindly\s+|tell\s+me\s+|show\s+me\s+|check\s+)", "", clean, flags=re.IGNORECASE).strip()

    # Strip trailing polite affixes
    clean = re.sub(r"[, ]+(?:please|jarvis|saanvi|for\s+me|now)$", "", clean, flags=re.IGNORECASE).strip()

    lower = clean.lower()

    # 1. Location-based Time & Weather Queries -> Search Google directly for the location
    # Examples: "time in the usa", "weather in tokyo", "temperature in new york"
    if re.search(r"\b(?:time|weather|temperature)\s+(?:in|at|for|of)\s+(.+)", lower):
        success, resp, search_url = perform_web_search(clean)
        return {
            "handled": True,
            "action": "web_search",
            "response": resp,
            "url": search_url,
            "success": success,
            "requires_confirmation": False
        }

    # 2. Local Date & Time Queries (Current device time/date)
    # Handles: "what's the time", "hello what's the time", "what time is it", "tell me the time", "time check", etc.
    is_time_query = bool(re.search(r"\btime\b", lower) and re.search(r"\b(what|whats|what's|tell|check|current|is|give)\b", lower)) or lower in ["time", "current time", "the time"]
    is_date_query = bool(re.search(r"\bdate\b", lower) and re.search(r"\b(what|whats|what's|tell|check|current|is|today|today's|todays)\b", lower)) or lower in ["date", "today's date", "todays date", "current date"]
    is_day_query = bool(re.search(r"\bday\b", lower) and re.search(r"\b(what|which|today|is)\b", lower)) or lower in ["what day is it", "what is today"]

    if is_time_query or is_date_query or is_day_query:
        return {
            "handled": True,
            "action": "datetime",
            "response": get_current_time_and_date(),
            "url": None,
            "success": True,
            "requires_confirmation": False
        }

    # 3. Safety confirmation check for destructive / power commands
    if any(k in lower for k in ["shutdown", "restart", "reboot", "power off"]):
        return {
            "handled": True,
            "action": "system_power",
            "response": "Safety protocol active, Saanvi. Shutting down or restarting the system requires explicit manual confirmation. For your security, this action will not be executed automatically.",
            "url": None,
            "success": False,
            "requires_confirmation": True
        }

    # 4. Web Search Queries
    # Examples: "search about doomsday", "search for quantum computing", "fetch anything from google about x", "google weather"
    search_match = re.search(
        r"^(?:please\s+)?(?:search(?:\s+(?:for|about|google\s+for|up|on|regarding))?|google|look\s+up|fetch(?:\s+(?:from\s+google|anything\s+from\s+google|about|for))?|find(?:\s+(?:about|for|out))?)\s+(.+)$",
        lower
    )
    if search_match:
        query = search_match.group(1).strip()
        # Strip leading prepositions
        query = re.sub(r"^(?:about|for|on|regarding|me)\s+", "", query, flags=re.IGNORECASE).strip()
        query = re.sub(r"\s+(?:on|from)\s+google$", "", query, flags=re.IGNORECASE).strip()

        if query and query not in ["google", "it"]:
            success, resp, search_url = perform_web_search(query)
            return {
                "handled": True,
                "action": "web_search",
                "response": resp,
                "url": search_url,
                "success": success,
                "requires_confirmation": False
            }

    # 5. Open Website Queries
    # Examples: "open youtube", "go to github", "open website reddit.com"
    open_site_match = re.search(
        r"^(?:please\s+)?(?:open(?:\s+website)?|go\s+to|navigate\s+to|launch)\s+([a-zA-Z0-9\.\-\_]+(?:\.[a-zA-Z]{2,})?)$",
        lower
    )
    if open_site_match:
        target = open_site_match.group(1).strip()

        # Check known website shortcuts
        if target in WEBSITE_SHORTCUTS:
            url = WEBSITE_SHORTCUTS[target]
            site_name = target.capitalize()
            success, resp, site_url = open_website(url, site_name)
            return {
                "handled": True,
                "action": "open_website",
                "response": resp,
                "url": site_url,
                "success": success,
                "requires_confirmation": False
            }

        # Check domain-like string (e.g. twitter.com)
        if "." in target:
            success, resp, site_url = open_website(target, target)
            return {
                "handled": True,
                "action": "open_website",
                "response": resp,
                "url": site_url,
                "success": success,
                "requires_confirmation": False
            }

    # 5. Open Application Queries
    # Examples: "open notepad", "launch calculator", "start task manager"
    app_match = re.search(
        r"^(?:please\s+)?(?:open|launch|start|run)\s+(.+)$",
        lower
    )
    if app_match:
        target_name = app_match.group(1).strip()

        # Match against whitelist
        for app_key, app_data in ALLOWED_APPS.items():
            if target_name in app_data["keywords"] or any(k in target_name for k in app_data["keywords"]):
                success, resp = open_application(app_key)
                return {
                    "handled": True,
                    "action": "open_app",
                    "response": resp,
                    "success": success,
                    "requires_confirmation": False
                }

        # Check if it might be an unlisted website
        if "." in target_name:
            success, resp = open_website(target_name, target_name)
            return {
                "handled": True,
                "action": "open_website",
                "response": resp,
                "success": success,
                "requires_confirmation": False
            }

    # Not a local computer command - delegate to AI conversational intelligence
    return {
        "handled": False,
        "action": None,
        "response": None,
        "success": False,
        "requires_confirmation": False
    }
