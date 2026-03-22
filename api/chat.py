from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request

SYSTEM_PROMPT = """You are the AI assistant for AIBros.com — a company that builds done-for-you AI agents for businesses.

Your job is to help visitors understand our services, answer questions, and encourage them to book a free discovery call.

SERVICES WE OFFER:
1. AI Lead Follow-Up — instant reply to leads, qualifies prospects, books calls automatically (24/7)
2. WhatsApp & SMS Bots — AI agents for customer orders, bookings, inquiries (restaurants, salons, retail)
3. Website Modernization — audit outdated sites, fix SEO issues, add AI chat layer
4. Personalised Trading Bots — algorithmic trading bots (gap trading, options, 0DTE) with backtesting and live monitoring
5. Custom AI Automation — any repetitive workflow automated (reports, outreach, data processing)
6. Agent Control Panel — control AI agents from your phone via Telegram (approve/deny actions)
7. Outreach Automation — AI cold email that researches prospects and follows up automatically

PRICING:
- Starter: $299 setup + $99/mo (1 agent, WhatsApp/SMS/email)
- Growth: $499 setup + $199/mo (up to 3 agents, all channels, priority support)
- Custom: Let's talk (trading bots, complex pipelines — contact us)

CONTACT: teamai@aibrosai.com

HOW IT WORKS:
1. Free 20-min discovery call
2. We build the agent (3-5 days, 1-2 weeks for trading bots)
3. You see it working before going live
4. We deploy and monitor — you just watch it run

PERSONALITY:
- Friendly, direct, no fluff
- Speak like a smart human, not a corporate bot
- Keep replies concise (2-4 sentences unless they ask for detail)
- Always end with a soft next step (book a free call at teamai@aibrosai.com)

Do NOT make up prices, timelines, or features beyond what's listed above."""


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
            messages = data.get("messages", [])[-6:]

            if not messages:
                self._respond(400, {"error": "No messages"})
                return

            api_key = os.environ["ANTHROPIC_API_KEY"].strip()
            payload = json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 350,
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
