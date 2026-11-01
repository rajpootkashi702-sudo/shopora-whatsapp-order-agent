"""
SaleSathi COD Order Confirmation Agent ✅📲
==========================================
Har COD order ke baad customer ko WhatsApp par "tap to confirm" message
bhejta hai — fake/cancel orders dispatch se PEHLE pakre jate hain.

Flow:
  pending → verify_sent → verified ✅ / cancelled ❌
  (koi jawab na aaye to reminder → verify_reminded → unconfirmed)

Istemaal:
  from confirm_agent import ConfirmationAgent
  ca = ConfirmationAgent(token, phone_number_id)
  ca.send_confirmation(order)          # order = dict (order_id, phone, name, product, price, city, address)
  reply_text = ca.handle_button_reply(phone, button_id)  # webhook se
"""

import requests

GRAPH_URL = "https://graph.facebook.com/v21.0"


class ConfirmationAgent:
    def __init__(self, token, phone_number_id, update_status_fn=None):
        self.token = token
        self.phone_number_id = phone_number_id
        # update_status_fn(order_id, new_status) — caller (webhook) deta hai
        self.update_status_fn = update_status_fn

    # ---------------------------------------------------------- send
    def _post(self, payload):
        url = "{}/{}/messages".format(GRAPH_URL, self.phone_number_id)
        headers = {"Authorization": "Bearer " + self.token,
                   "Content-Type": "application/json"}
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=20)
            print("Confirm send ->", r.status_code)
            if r.status_code >= 400:
                print("Confirm error:", r.text[:400])
                return None
            return (r.json().get("messages") or [{}])[0].get("id")
        except Exception as e:
            print("Confirm send failed:", e)
            return None

    def send_confirmation(self, order):
        """Customer ko interactive Confirm/Cancel buttons bhejein."""
        oid = order.get("order_id", "")
        body = (
            "Assalam o Alaikum {name}! 🙏\n\n"
            "Apka order mil gaya hai — please confirm karein:\n\n"
            "🧾 Order: {oid}\n"
            "📦 {product} — {price} (COD)\n"
            "📍 {city}\n\n"
            "Neeche button dabayein 👇"
        ).format(
            name=order.get("name", "Customer"),
            oid=oid,
            product=order.get("product", ""),
            price=order.get("price", ""),
            city=order.get("city", ""),
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": order.get("phone", ""),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": [
                    {"type": "reply",
                     "reply": {"id": "confirm_" + oid, "title": "✅ Confirm Order"}},
                    {"type": "reply",
                     "reply": {"id": "cancel_" + oid, "title": "❌ Cancel Order"}},
                ]},
            },
        }
        mid = self._post(payload)
        if mid and self.update_status_fn:
            self.update_status_fn(oid, "verify_sent")
        return mid

    def send_reminder(self, order):
        """Pehle confirm ka jawab na aaye to ek reminder."""
        oid = order.get("order_id", "")
        payload = {
            "messaging_product": "whatsapp",
            "to": order.get("phone", ""),
            "type": "text",
            "text": {"body":
                     "Assalam o Alaikum {name}! 🙏 Apka order ({oid}) "
                     "abhi confirm nahi hua. Please upar wale message me "
                     "✅ Confirm ya ❌ Cancel dabayein taake hum dispatch "
                     "kar sakein. Shukriya!".format(
                         name=order.get("name", "Customer"), oid=oid)},
        }
        mid = self._post(payload)
        if mid and self.update_status_fn:
            self.update_status_fn(oid, "verify_reminded")
        return mid

    # ---------------------------------------------------------- reply
    def handle_button_reply(self, phone, button_id):
        """Webhook se button reply aaye to status update + jawab text."""
        if button_id.startswith("confirm_"):
            oid = button_id[len("confirm_"):]
            if self.update_status_fn:
                self.update_status_fn(oid, "verified")
            return ("Shukriya! ✅ Apka order {} CONFIRM ho gaya hai. "
                    "Jald dispatch kar diya jayega. 🙏".format(oid))
        if button_id.startswith("cancel_"):
            oid = button_id[len("cancel_"):]
            if self.update_status_fn:
                self.update_status_fn(oid, "cancelled")
            return ("Koi baat nahi! ❌ Apka order {} cancel kar diya gaya hai. "
                    "Dobara zaroorat ho to hum hazir hain. 🙏".format(oid))
        return None
