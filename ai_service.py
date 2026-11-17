"""
JARVIS AI Service
Handles conversational intelligence via LLM REST API (Google Gemini / OpenAI compatible)
- Loads API credentials from .env safely
- Formats JARVIS persona and system instruction
- Maintains multi-turn conversation context
- Gracefully handles missing keys, rate limits, network errors, and API failures
"""

import os
import json
import requests

SYSTEM_INSTRUCTION = """You are JARVIS (Just A Rather Very Intelligent System), a sophisticated personal AI assistant inspired by Tony Stark's AI in Iron Man.

Personality & Behavioral Guidelines:
- Intelligent, composed, polite, and professional.
- Occasionally witty with mild, dry sarcasm. Never excessively sarcastic, rude, or arrogant.
- Helpful and concise by default (usually 2 to 3 sentences, unless the user requests detailed analysis or code).
- Empathetic, respectful, and serious when the user discusses personal, difficult, or critical matters.
- Address the user respectfully (e.g., 'sir' or polite natural address).
- Maintain consistency across text and voice interactions.
- You are JARVIS; never break character or claim to be a generic language model.
"""


def load_env_file(filepath=".env"):
    """Lightweight .env loader without requiring external packages."""
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        print(f"Warning: Failed to load .env file: {e}")


# Initialize environment on module import
load_env_file()


def get_api_key():
    """Retrieves configured API key with provider detection."""
    load_env_file()
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ.get("GEMINI_API_KEY"), "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ.get("OPENAI_API_KEY"), "openai"
    if os.environ.get("GROQ_API_KEY"):
        return os.environ.get("GROQ_API_KEY"), "groq"
    return None, None


def is_ai_configured():
    """Checks whether an AI API key is configured."""
    key, _ = get_api_key()
    return key is not None and len(key.strip()) > 0


def call_gemini_api(api_key, user_message, conversation_history=None):
    """
    Calls Google Gemini REST API using generateContent endpoint.
    Supports multi-turn conversational history.
    """
    # Available models in order of preference
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]
    
    # Format contents for multi-turn chat
    contents = []
    if conversation_history:
        for turn in conversation_history[-10:]:  # Keep recent 10 turns for context
            role = turn.get("role", "user")
            text = turn.get("text", "")
            if text:
                gemini_role = "user" if role == "user" else "model"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": text}]
                })

    # Append current message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 450
        }
    }

    last_error = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=18
            )

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return True, parts[0]["text"].strip()
                return False, "I processed your request, sir, but received an empty response from the neural engine."

            if resp.status_code == 429:
                return False, "I seem to be experiencing rate limitations from the API service, sir. Please allow me a brief moment to cool down."

            if resp.status_code in (400, 401, 403):
                return False, f"The configured API key appears to be invalid or unauthorized (HTTP {resp.status_code}). Please verify your GEMINI_API_KEY in the .env file, sir."

            last_error = f"HTTP {resp.status_code}: {resp.text}"

        except requests.exceptions.Timeout:
            return False, "The neural servers did not respond within the allocated timeframe, sir. Network latency appears unusually high."
        except requests.exceptions.ConnectionError:
            return False, "I am unable to establish a secure network connection to the AI servers, sir. Please inspect your internet connectivity."
        except Exception as e:
            last_error = str(e)

    return False, f"I encountered an unexpected issue contacting the AI core: {last_error}"


def call_openai_compatible_api(api_key, provider, user_message, conversation_history=None):
    """Calls OpenAI or Groq compatible chat completions REST API."""
    if provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        model = "llama-3.1-8b-instant"
    else:
        url = "https://api.openai.com/v1/chat/completions"
        model = "gpt-4o-mini"

    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    if conversation_history:
        for turn in conversation_history[-10:]:
            role = turn.get("role", "user")
            text = turn.get("text", "")
            if text:
                messages.append({
                    "role": "user" if role == "user" else "assistant",
                    "content": text
                })

    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 400
    }

    try:
        resp = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
            timeout=18
        )

        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return True, choices[0]["message"]["content"].strip()
            return False, "Received empty reply from AI service."

        if resp.status_code == 429:
            return False, "Rate limit reached for the configured AI provider, sir."

        if resp.status_code in (401, 403):
            return False, f"Unauthorized: Please check your {provider.upper()}_API_KEY in the .env file."

        return False, f"AI service responded with HTTP status {resp.status_code}."

    except requests.exceptions.Timeout:
        return False, "Request to the AI provider timed out, sir."
    except requests.exceptions.ConnectionError:
        return False, "Unable to connect to the AI provider network endpoint."
    except Exception as e:
        return False, f"AI request failed: {str(e)}"


def get_ai_response(user_message, conversation_history=None):
    """
    Main entry point for AI conversation.
    Returns: (success: bool, response_text: str)
    """
    api_key, provider = get_api_key()

    if not api_key:
        return False, (
            "Sir, an AI API key has not been configured yet. "
            "To enable conversational intelligence, please add your GEMINI_API_KEY to the .env file. "
            "In the meantime, I can still assist you with computer commands—such as opening applications, "
            "navigating to websites, searching Google, or checking the current time."
        )

    if provider == "gemini":
        return call_gemini_api(api_key, user_message, conversation_history)
    else:
        return call_openai_compatible_api(api_key, provider, user_message, conversation_history)
