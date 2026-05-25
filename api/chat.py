from http.server import BaseHTTPRequestHandler
import json
import os
import smtplib
import urllib.request
from email.mime.text import MIMEText

SYSTEM_PROMPT = """You are the assistant for AIBros.com — we build done-for-you AI agents for businesses.

YOUR GOAL: Understand their problem, then get their name, phone number, and best time to call so our team can reach out.

SERVICES:
- AI Lead Follow-Up: instant reply, qualifies leads, books calls 24/7
- WhatsApp/SMS Bots: handles orders, bookings, inquiries automatically
- Website Modernization: fix outdated sites, SEO, add AI chat
- Trading Bots: algorithmic gap/options/0DTE bots with backtesting
- Custom AI Automation: any repetitive workflow automated
- Outreach Automation: AI cold email with automatic follow-ups

CONVERSATION FLOW:
1. Ask what their business does and what's eating their time or costing them leads
2. Ask ONE follow-up question to understand the pain better
3. After understanding their need, say our team can walk them through exactly how we'd solve it on a quick free call
4. Get their NAME → then PHONE NUMBER → then BEST TIME TO CALL
5. Confirm details and say the team will reach out shortly

RULES:
- Keep every reply to 2-3 sentences max. One question at a time.
- If asked about pricing: "Our team covers all of that on the call — it's scoped to your exact needs." Then redirect.
- If asked about competitors or other tools: "I'm only across what we build at AIBros — want me to show you how we'd handle your specific situation?"
- Never make up features, timelines, or prices.
- If off-topic: one friendly redirect back to their business problem.
- Once you have name + phone + time, stop selling — just confirm and wrap up warmly."""


EXTRACT_PROMPT = """Look at this chat conversation and extract lead details if ALL THREE are present: name, phone number, and best time to call.

If all three are present reply in this exact format:
NAME: <name>
PHONE: <phone>
TIME: <time>

If any are missing reply with just: INCOMPLETE"""


def extract_and_notify(messages):
    """Check if conversation has full lead details; email if so."""
    try:
        api_key = os.environ["ANTHROPIC_API_KEY"].strip()
        convo_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 80,
            "system": EXTRACT_PROMPT,
            "messages": [{"role": "user", "content": convo_text}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={"Content-Type": "application/json",
                     "x-api-key": api_key,
                     "anthropic-version": "2023-06-01"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        text = result["content"][0]["text"].strip()
        if "INCOMPLETE" in text:
            return
        # Parse the extracted details
        lines = {l.split(":")[0].strip(): l.split(":", 1)[1].strip()
                 for l in text.splitlines() if ":" in l}
        name  = lines.get("NAME", "Unknown")
        phone = lines.get("PHONE", "Unknown")
        time  = lines.get("TIME", "Unknown")
        send_lead_email(name, phone, time, messages)
    except Exception:
        pass  # Never crash the main chat response


def send_lead_email(name, phone, time, messages):
    """Send lead notification email via Zoho SMTP."""
    try:
        zoho_email   = os.environ.get("ZOHO_EMAIL", "teamai@aibrosai.com")
        zoho_pass    = os.environ.get("ZOHO_PASSWORD", "")
        notify_email = os.environ.get("LEAD_NOTIFY_EMAIL", zoho_email)
        # Build chat transcript
        transcript = "\n".join(
            f"{'Bot' if m['role']=='assistant' else 'Visitor'}: {m['content']}"
            for m in messages
        )
        body = f"""New lead from AIBros.com chatbot!

Name:  {name}
Phone: {phone}
Time:  {time}

--- Full conversation ---
{transcript}
"""
        msg = MIMEText(body)
        msg["Subject"] = f"New Lead: {name} — {phone}"
        msg["From"]    = zoho_email
        msg["To"]      = notify_email
        with smtplib.SMTP_SSL("smtp.zoho.com", 465, timeout=10) as server:
            server.login(zoho_email, zoho_pass)
            server.sendmail(zoho_email, notify_email, msg.as_string())
    except Exception:
        pass


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            messages = data.get("messages", [])

            if not messages:
                self._respond(400, {"error": "No messages"})
                return

            api_key = os.environ["ANTHROPIC_API_KEY"].strip()
            payload = json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "system": SYSTEM_PROMPT,
                "messages": messages,
            }).encode()

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
            reply = result["content"][0]["text"]
            # Check if lead details are now complete and notify
            full_history = messages + [{"role": "assistant", "content": reply}]
            if len(full_history) >= 6:
                extract_and_notify(full_history)
            self._respond(200, {"reply": reply})

        except Exception as e:
            self._respond(200, {"reply": "Sorry, having a moment — email teamai@aibrosai.com and we'll respond fast!"})

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, code, data):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, *args):
        pass
