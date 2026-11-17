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
    # Validate URL
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        url = "https://" + url

    try:
        webbrowser.open_new_tab(url)
        label = site_name if site_name else url
        return True, f"Opening {label}."
    except Exception as e:
        return False, f"I was unable to open the requested website: {str(e)}"


def perform_web_search(query):
    """Performs a web search using the user's default browser."""
    if not query or not query.strip():
        return False, "Please provide a query for me to search."

    clean_query = query.strip()
    encoded = urllib.parse.quote_plus(clean_query)
    search_url = f"https://www.google.com/search?q={encoded}"

    try:
        webbrowser.open_new_tab(search_url)
        return True, f"Searching Google for '{clean_query}'."
    except Exception as e:
        return False, f"I encountered an issue executing the web search: {str(e)}"


def handle_system_command(text):
    """
    Parses user input to determine if it matches a basic computer control command.
    Returns:
        dict: {
            "handled": bool,
            "action": str,
            "response": str,
            "success": bool,
            "requires_confirmation": bool
        }
    """
    raw = text.strip()

    # Normalize: strip leading address ('hey jarvis', 'jarvis,')
    clean = re.sub(r"^(?:hey\s+|ok\s+|hi\s+|hello\s+)?jarvis[,:\s]*", "", raw, flags=re.IGNORECASE).strip()
    # Strip trailing punctuation
    clean = re.sub(r"[?!.,]+$", "", clean).strip()
    # Strip trailing polite tags
    clean = re.sub(r"[, ]+(?:please|jarvis|saanvi)$", "", clean, flags=re.IGNORECASE).strip()

    lower = clean.lower()

    # 1. Date & Time Queries
    time_patterns = [
        r"^(what('s| is) the time|what time is it|tell me the time|time check|current time)$",
        r"^(what('s| is) (the |today('?s) )?date|tell me the date|today('?s)? date|current date)$",
        r"^(what day is it|what is today)$"
    ]
    for pattern in time_patterns:
        if re.search(pattern, lower):
            return {
                "handled": True,
                "action": "datetime",
                "response": get_current_time_and_date(),
                "success": True,
                "requires_confirmation": False
            }

    # 2. Safety confirmation check for destructive / power commands
    if any(k in lower for k in ["shutdown", "restart", "reboot", "power off"]):
        return {
            "handled": True,
            "action": "system_power",
            "response": "Safety protocol active, Saanvi. Shutting down or restarting the system requires explicit manual confirmation. For your security, this action will not be executed automatically.",
            "success": False,
            "requires_confirmation": True
        }

    # 3. Web Search Queries
    # Examples: "search for quantum computing", "google weather in new york", "search artificial intelligence"
    search_match = re.search(
        r"^(?:please\s+)?(?:search(?:\s+for|\s+google\s+for)?|google|look\s+up)\s+(.+)$",
        lower
    )
    if search_match:
        query = search_match.group(1).strip()
        # Ensure it's not simply "google" alone
        if query and query not in ["google", "it"]:
            success, resp = perform_web_search(query)
            return {
                "handled": True,
                "action": "web_search",
                "response": resp,
                "success": success,
                "requires_confirmation": False
            }

    # 4. Open Website Queries
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
            success, resp = open_website(url, site_name)
            return {
                "handled": True,
                "action": "open_website",
                "response": resp,
                "success": success,
                "requires_confirmation": False
            }

        # Check domain-like string (e.g. twitter.com)
        if "." in target:
            success, resp = open_website(target, target)
            return {
                "handled": True,
                "action": "open_website",
                "response": resp,
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
