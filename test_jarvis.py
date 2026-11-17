"""
Comprehensive Automated Test Suite for JARVIS Personal Assistant
Verifies:
1. Command Handler parsing & safety protocols
2. AI Service fallback, personality formatting, and session history
3. Flask endpoints (/api/status, /api/chat, /api/command, static file serving)
"""

import unittest
import json
import os
import sys

from command_handler import handle_system_command, ALLOWED_APPS, WEBSITE_SHORTCUTS
from ai_service import get_ai_response, SYSTEM_INSTRUCTION
from app import app


class TestJarvisCommandHandler(unittest.TestCase):
    """Test suite for command_handler.py"""

    def test_time_and_date_queries(self):
        queries = [
            "what time is it",
            "what's the time",
            "tell me the time",
            "what is the date",
            "today's date",
            "what day is it"
        ]
        for q in queries:
            result = handle_system_command(q)
            self.assertTrue(result["handled"], f"Failed to handle time query: '{q}'")
            self.assertEqual(result["action"], "datetime")
            self.assertIn("current time is", result["response"].lower())

    def test_safety_protocol_power_commands(self):
        power_queries = ["shutdown the computer", "restart system", "reboot now"]
        for q in power_queries:
            result = handle_system_command(q)
            self.assertTrue(result["handled"], f"Failed to catch power command: '{q}'")
            self.assertTrue(result["requires_confirmation"], "Power command must require confirmation")
            self.assertFalse(result["success"], "Destructive action should not execute automatically")

    def test_website_shortcuts(self):
        result = handle_system_command("open youtube")
        self.assertTrue(result["handled"])
        self.assertEqual(result["action"], "open_website")

        result2 = handle_system_command("go to github")
        self.assertTrue(result2["handled"])
        self.assertEqual(result2["action"], "open_website")

    def test_web_search(self):
        result = handle_system_command("search for quantum computing")
        self.assertTrue(result["handled"])
        self.assertEqual(result["action"], "web_search")
        self.assertIn("quantum computing", result["response"])

        result2 = handle_system_command("google artificial intelligence")
        self.assertTrue(result2["handled"])
        self.assertEqual(result2["action"], "web_search")

    def test_polite_prefixes_and_suffixes(self):
        queries = [
            "Hey JARVIS, open YouTube please!",
            "Jarvis, what's the time?",
            "ok jarvis, search for artificial intelligence"
        ]
        for q in queries:
            result = handle_system_command(q)
            self.assertTrue(result["handled"], f"Failed to handle with polite affix: '{q}'")

    def test_app_keywords_matching(self):
        result = handle_system_command("open notepad")
        self.assertTrue(result["handled"])
        self.assertEqual(result["action"], "open_app")

        result2 = handle_system_command("launch calculator")
        self.assertTrue(result2["handled"])
        self.assertEqual(result2["action"], "open_app")

    def test_arbitrary_commands_not_executed(self):
        # Arbitrary commands or conversational queries must NOT be treated as shell executions
        conversational_queries = [
            "Hello JARVIS, how are you today?",
            "Are you smarter than me?",
            "Can you write a poem about the stars?",
            "rmdir /s /q C:\\"
        ]
        for q in conversational_queries:
            result = handle_system_command(q)
            self.assertFalse(result["handled"], f"Non-command '{q}' was incorrectly marked as handled")


class TestJarvisAIService(unittest.TestCase):
    """Test suite for ai_service.py"""

    def test_system_instruction_persona(self):
        self.assertIn("JARVIS", SYSTEM_INSTRUCTION)
        self.assertIn("Iron Man", SYSTEM_INSTRUCTION)
        self.assertIn("polite", SYSTEM_INSTRUCTION)
        self.assertIn("witty", SYSTEM_INSTRUCTION)

    def test_fallback_when_api_key_missing(self):
        # Save current env if any
        old_gemini = os.environ.pop("GEMINI_API_KEY", None)
        old_openai = os.environ.pop("OPENAI_API_KEY", None)
        old_groq = os.environ.pop("GROQ_API_KEY", None)

        try:
            success, reply = get_ai_response("Who are you?")
            self.assertFalse(success)
            self.assertIn("GEMINI_API_KEY", reply)
            self.assertIn("saanvi", reply.lower())
        finally:
            if old_gemini: os.environ["GEMINI_API_KEY"] = old_gemini
            if old_openai: os.environ["OPENAI_API_KEY"] = old_openai
            if old_groq: os.environ["GROQ_API_KEY"] = old_groq


class TestJarvisFlaskAPI(unittest.TestCase):
    """Test suite for Flask endpoints in app.py"""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_status_endpoint(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["name"], "JARVIS")
        self.assertEqual(data["status"], "online")
        self.assertIn("Notepad", data["supported_apps"])
        self.assertIn("Calculator", data["supported_apps"])

    def test_chat_endpoint_command(self):
        payload = {"message": "What time is it?", "history": []}
        resp = self.client.post("/api/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["is_command"])
        self.assertEqual(data["action"], "datetime")
        self.assertIn("current time is", data["reply"].lower())

    def test_chat_endpoint_empty_message(self):
        payload = {"message": "", "history": []}
        resp = self.client.post("/api/chat", json=payload)
        self.assertEqual(resp.status_code, 400)

    def test_static_files_served(self):
        index_resp = self.client.get("/")
        self.assertEqual(index_resp.status_code, 200)
        self.assertIn(b"JARVIS", index_resp.data)

        css_resp = self.client.get("/style.css")
        self.assertEqual(css_resp.status_code, 200)
        self.assertIn(b"--cyan-primary", css_resp.data)

        js_resp = self.client.get("/script.js")
        self.assertEqual(js_resp.status_code, 200)
        self.assertIn(b"arcReactor", js_resp.data)


if __name__ == "__main__":
    unittest.main()
