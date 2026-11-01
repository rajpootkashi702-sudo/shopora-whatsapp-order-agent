"""
Shopora WhatsApp Webhook Server 🌐💬
====================================
Meta WhatsApp Business Cloud API se aane wale messages ko OrderAgent se jorta hai.

Setup:
  1. https://developers.facebook.com → nayi App → WhatsApp product add karein
  2. Apna WhatsApp Business number jorein, temporary Access Token lein
  3. Neeche WEBHOOK_VERIFY_TOKEN aur WHATSAPP_TOKEN bharein
  4. Is file ko public URL par chalayein (Render.com / Railway.app free)
     aur wo URL Meta dashboard me Webhook ke tor par lagayein

Chalayein:
  pip install flask requests
  python webhook.py
"""

import os
import requests
from flask import Flask, request

from agent import OrderAgent

# ------------------------------------------------------------ settings
# Inhe apni asal values se badlein (ya environment variables me rakhein)
WEBHOOK_VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "shopora123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "PASTE_YOUR_TOKEN_HERE")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "PASTE_PHONE_NUMBER_ID")
GRAPH_URL = "https://graph.facebook.com/v21.0"

app = Flask(__name__)
agent = OrderAgent()


def send_whatsapp(to_phone, text):
    """Agent ka jawab wapas customer ko WhatsApp par bhejein."""
    url = "{}/{}/messages".format(GRAPH_URL, PHONE_NUMBER_ID)
    headers = {"Authorization": "Bearer " + WHATSAPP_TOKEN,
               "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp",
               "to": to_phone,
               "type": "text",
               "text": {"body": text}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        print("Sent ->", to_phone, r.status_code)
    except Exception as e:
        print("Send failed:", e)


@app.route("/webhook", methods=["GET"])
def verify():
    """Meta webhook verification (sirf pehli dafa)."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def incoming():
    """Customer ka message aaya → agent jawab banaye → wapas bhej dein."""
    data = request.get_json(silent=True) or {}
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages") or []
        for msg in messages:
            if msg.get("type") != "text":
                continue
            phone = msg["from"]
            text = msg["text"]["body"]
            print("Incoming <-", phone, ":", text)
            reply = agent.handle_message(phone, text)
            send_whatsapp(phone, reply)
    except (KeyError, IndexError, TypeError) as e:
        print("Parse note:", e)
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "Shopora Order Agent webhook chal raha hai! ✅", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("Webhook server :{}".format(port))
    app.run(host="0.0.0.0", port=port)
