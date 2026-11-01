"""
Sales Assistant WhatsApp Webhook Server 🌐💬
=====================================
Meta WhatsApp Business Cloud API se aane wale customer messages ko
Sales Assistant agent se jorta hai — customer likhe, agent foran jawab de!

Multi-user: jis business ka WhatsApp number jura ho, usi ki settings
(ORDER_AGENT_USER env se, default: admin) istemal hoti hain aur orders
usi ke account me save hote hain.

Setup:
  1. https://developers.facebook.com → nayi App → WhatsApp product add karein
  2. WhatsApp Business number jorein (alag number — personal WhatsApp wala nahi),
     temporary Access Token + Phone Number ID lein
  3. Neeche env vars set karein, is file ko public URL par chalayein
     (Render.com / Railway.app free), wo URL Meta me Webhook lagayein

Chalayein:
  pip install flask requests
  python webhook.py
"""

import os
import requests
from flask import Flask, request

from agent import OrderAgent
from users import ensure_seed, get_settings, add_order, update_order_status
from confirm_agent import ConfirmationAgent

# ------------------------------------------------------------ settings
# Inhe apni asal values se badlein (ya environment variables me rakhein)
WEBHOOK_VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN", "shopora123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "PASTE_YOUR_TOKEN_HERE")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "PASTE_PHONE_NUMBER_ID")
GRAPH_URL = "https://graph.facebook.com/v21.0"
# Kaun se business account ki settings/orders istemal hon (default: admin)
ORDER_AGENT_USER = os.environ.get("ORDER_AGENT_USER", "admin")

app = Flask(__name__)

ensure_seed()
agent = OrderAgent(
    settings=get_settings(ORDER_AGENT_USER),
    save_fn=lambda o: add_order(ORDER_AGENT_USER, o),
)
confirm_agent = ConfirmationAgent(
    token=WHATSAPP_TOKEN,
    phone_number_id=PHONE_NUMBER_ID,
    update_status_fn=lambda oid, st: update_order_status(ORDER_AGENT_USER, oid, st),
)
print("Sales Assistant webhook ready — business: {}".format(ORDER_AGENT_USER))


def _auto_confirm(order):
    """Naya order (real WhatsApp se) aate hi Confirm buttons bhejein."""
    try:
        if not get_settings(ORDER_AGENT_USER).get("auto_confirm", True):
            return
        mid = confirm_agent.send_confirmation(order)
        print("auto-confirm sent:", order.get("order_id"), mid)
    except Exception as e:
        print("auto-confirm failed:", e)


agent.on_order_fn = _auto_confirm


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
        if r.status_code >= 400:
            print("Send error body:", r.text[:500])
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
            mtype = msg.get("type")
            phone = msg["from"]
            if mtype == "interactive":
                # Confirm/Cancel button ka jawab (confirmation agent)
                try:
                    button_id = msg["interactive"]["button_reply"]["id"]
                except (KeyError, TypeError):
                    continue
                print("Incoming button <-", phone, ":", button_id)
                reply = confirm_agent.handle_button_reply(phone, button_id)
                if reply:
                    send_whatsapp(phone, reply)
                continue
            if mtype != "text":
                continue
            text = msg["text"]["body"]
            print("Incoming <-", phone, ":", text)
            reply = agent.handle_message(phone, text)
            send_whatsapp(phone, reply)
    except (KeyError, IndexError, TypeError) as e:
        print("Parse note:", e)
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "Sales Assistant webhook chal raha hai! ✅", 200


@app.route("/send_confirm", methods=["POST"])
def send_confirm():
    """Dashboard se: ek order ke liye WhatsApp confirm message bhejein.
    Body: poora order dict {"order": {...}} bhejein (dashboard aur webhook
    alag servers par hain, is liye order_id se lookup nahi ho sakta).
    Purana format {"order_id": "..."} bhi fallback ke tor par chalta hai.
    Token server-side rehta hai."""
    from users import get_orders
    data = request.get_json(silent=True) or {}
    order = data.get("order")
    if isinstance(order, dict) and order.get("phone"):
        mid = confirm_agent.send_confirmation(order)
        return {"ok": bool(mid), "message_id": mid}, 200
    oid = data.get("order_id", "")
    for o in get_orders(ORDER_AGENT_USER):
        if o.get("order_id") == oid:
            mid = confirm_agent.send_confirmation(o)
            return {"ok": bool(mid), "message_id": mid}, 200
    return {"ok": False, "error": "order not found"}, 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("Webhook server :{}".format(port))
    app.run(host="0.0.0.0", port=port)
