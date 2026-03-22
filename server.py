"""
AIBros.io website chatbot backend.
Run: python server.py
Serves the site on http://localhost:5000 and handles /chat API calls.
"""
from flask import Flask, request, jsonify, send_from_directory
from anthropic import Anthropic
import os

# Load API key from rudder .env
_env = r"C:\Users\rushit\rudder\.env"
for line in open(_env):
    k, _, v = line.strip().partition("=")
    if k == "ANTHROPIC_API_KEY":
        os.environ["ANTHROPIC_API_KEY"] = v

client = Anthropic()
app = Flask(__name__, static_folder=".")

SYSTEM_PROMPT = """You are the AI assistant for AIBros.io — a company that builds done-for-you AI agents for businesses.

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

CONTACT: hello@aibros.io

HOW IT WORKS:
1. Free 20-min discovery call
2. We build the agent (3-5 days, 1-2 weeks for trading bots)
3. You see it working before going live
4. We deploy and monitor — you just watch it run

KEY SELLING POINTS:
- No technical knowledge needed — we handle everything
- Show working demo before payment
- If it doesn't do what we promised, no setup fee
- Paper trading first for trading bots, live when you're confident
- Works with Claude, GPT-4, or local models

PERSONALITY:
- Friendly, direct, no fluff
- Speak like a smart human, not a corporate bot
- Keep replies concise (2-4 sentences unless they ask for detail)
- Always end with a soft next step (usually: book a free call at hello@aibros.io)
- If you don't know something specific, say so honestly and suggest they email us

Do NOT make up prices, timelines, or features beyond what's listed above."""


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages"}), 400

    last_user_msg = messages[-1]["content"]

    # Keep prompt short to stay within Windows CLI arg limits
    # Include last assistant reply for context if available
    context = ""
    if len(messages) >= 2:
        prev = messages[-2]
        if prev["role"] == "assistant":
            context = f"Previous reply: {prev['content'][:200]}\n"

    prompt = (
        f"You are a friendly AI assistant for AIBros.io. "
        f"We build done-for-you AI agents: lead follow-up, WhatsApp/SMS bots, "
        f"trading bots, website modernization, custom automation. "
        f"Pricing: Starter $299+$99/mo, Growth $499+$199/mo, Custom (trading bots). "
        f"Contact: hello@aibros.io. Keep replies short (2-4 sentences). "
        f"Always end with a soft next step.\n"
        f"{context}"
        f"Visitor asks: {last_user_msg}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=350,
            system=SYSTEM_PROMPT,
            messages=messages[-6:],
        )
        reply = response.content[0].text
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": "Sorry, having a moment — email hello@aibros.io and we'll respond fast!"}), 200


if __name__ == "__main__":
    print("AIBros.io server running → http://localhost:5000")
    app.run(debug=False, port=5000)
