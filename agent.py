"""
WhatsApp COD Order Agent 🤖💬
============================
Real human ki tarah deal karne wala order-taking agent.

Har business ke liye configurable: OrderAgent(settings=...) me us business
ki settings dein (dukaan ka naam, products, prices, currency...). Settings
na dein to settings.json/defaults istemal hoti hain.

Kaam:
  - Customer se Roman Urdu me natural baat karta hai (salam, price, discount...)
  - Product select karwata hai, COD confirm karta hai
  - Naam + sheher + mukammal pata leta hai
  - Order confirm karke save karta hai (save_fn ya orders.json)

Chalane ka tareeqa:
  python agent.py
  (demo chat terminal me khul jayegi — customer ban kar baat karein!)

Real WhatsApp par lagane ke liye:
  WhatsApp Business Cloud API ka webhook is file ke handle_message()
  function se jor dein — baqi logic same rahega.
"""

import json
import os
import random
import re
from datetime import datetime

from config import load_settings, DEFAULT_SETTINGS

# ------------------------------------------------- default (single-business)
# Webhook/demo purane tareeqe se bhi chal sakte hain — ye defaults hain.
_CFG = load_settings()

SHOP_NAME = _CFG["shop_name"]
WHATSAPP_NUMBER = _CFG["whatsapp"]
CURRENCY = _CFG["currency"]
DELIVERY_INFO = _CFG["delivery_info"]
ORDER_PREFIX = _CFG["order_prefix"]
PRODUCTS = _CFG["products"]
ORDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "orders.json")


def reload_config():
    """settings.json dobara parh kar default config refresh karein."""
    global _CFG, SHOP_NAME, WHATSAPP_NUMBER, CURRENCY, DELIVERY_INFO, \
        ORDER_PREFIX, PRODUCTS
    _CFG = load_settings()
    SHOP_NAME = _CFG["shop_name"]
    WHATSAPP_NUMBER = _CFG["whatsapp"]
    CURRENCY = _CFG["currency"]
    DELIVERY_INFO = _CFG["delivery_info"]
    ORDER_PREFIX = _CFG["order_prefix"]
    PRODUCTS = _CFG["products"]


# ------------------------------------------------------- human-like replies

GREETINGS = [
    "Walaikum Assalam! 😊 {shop} me khush aamdeed! Main aapki kya madad kar sakta hoon?",
    "Assalam o Alaikum! 🙌 {shop} me welcome! Bataiye, kya lena chahenge?",
    "Hello hello! 😄 {shop} hazir hai! Koi product dekhna hai ya order karna hai?",
]

ASK_PRODUCT = (
    "Zaroor! Ye rahi hamari products ki list 👇\n{plist}\n\n"
    "Koi **number** likhein (jaise: 1) ya **naam** likhein, main detail bata dunga! 😊"
)

PRODUCT_DETAIL = (
    "👉 **{name}**\n{desc}\n💰 Price: **{price} {cur}** ({delivery})\n\n"
    "Order karna hai? To bas **'order'** likhein! 👍\n"
    "Ya koi aur product dekhna hai to number bhej dein."
)

DISCOUNT_REPLIES = [
    "Haha, samajh gaya! 😄 Dekhein, hamari prices pehle hi bohat munasib hain — "
    "{name} sirf {price} {cur} me! Quality ki guarantee ke saath. Order karein? 👍",
    "Aap ke liye khas riayat to banti hai! 😉 Lekin sach kahun to ye price pehle hi "
    "discount wali hai — {name} sirf {price} {cur}! Kya khayal hai?",
]

DELIVERY_REPLIES = [
    "{delivery} 🚚 Payment cash me rider ko deni hai — koi advance nahi! 😊",
]

HUMAN_REPLIES = [
    "Bilkul! Main apne boss ko abhi ittila de deta hoon, wo khud aap se baat karein ge. "
    "Thora intezar kijiye ga! 🙏 (Ya direct call karein: {wa})",
]

FALLBACK_REPLIES = [
    "Hmm, ye baat meri samajh se bahar ho gayi! 😅 Kya aap product ki **price** "
    "poochna chahte hain, ya **order** karna hai? Number bhej kar product select karein!",
    "Maazrat, main theek se samjha nahi! 🤔 Product list dekhne ke liye **'products'** "
    "likhein, ya seedha **'order'** likh kar booking shuru karein!",
]

ASK_NAME = "Zabardast choice! 🎉 Order book karte hain.\nSab se pehle **aapka naam** bata dein? 😊"
ASK_CITY = "Shukriya {name}! 🙏 Ab **sheher ka naam** likhein (jaise: Dubai, Sharjah...)"
ASK_ADDRESS = "Perfect! Ab **mukammal pata** (ghar/villa number, street, area) bhej dein 📍"
ASK_CONFIRM = (
    "Order ki tafseel check kar lein 👇\n\n"
    "📦 Product: {pname}\n💰 Price: {price} {cur}\n"
    "👤 Naam: {name}\n🏙️ Sheher: {city}\n📍 Pata: {address}\n"
    "🚚 {delivery}\n\n"
    "Sab theek hai? **'han'** likhein confirm karne ke liye, ya **'cancel'** likhein! 😊"
)
ORDER_DONE = (
    "Mubarak ho {name}! 🎉🎉 Aapka order **confirm** ho gaya!\n\n"
    "🧾 Order ID: **{oid}**\n📦 {pname} — {price} {cur} (COD)\n"
    "🚚 2-4 working days me aapke darwazay par!\n\n"
    "Koi aur cheez chahiye ho to bas likhiye ga! {shop} ka shukriya! ❤️"
)
ORDER_CANCELLED = "Koi baat nahi {name}! 😊 Order cancel kar diya hai. Jab dil kare, wapas aa jaiye ga!"

THANKS_REPLIES = [
    "Khush rahein! ❤️ {shop} hamesha hazir hai!",
    "Aap ka bohat shukriya! 😊 Kuch aur chahiye ho to bataiye ga!",
]


# ------------------------------------------------------------- agent core

class OrderAgent:
    """Ek customer (phone number) ke liye conversation state machine.

    settings: is business ki settings dict (config.load_settings() jaisi).
    save_fn:  order save karne ka tareeqa — na dein to orders.json me jayega.
    on_order_fn: naya order save hote hi call ho (auto-confirm waghera ke liye).
    """

    def __init__(self, settings=None, save_fn=None, on_order_fn=None):
        self.cfg = dict(settings) if settings else load_settings()
        for k, v in DEFAULT_SETTINGS.items():
            self.cfg.setdefault(k, v)
        if not self.cfg.get("products"):
            self.cfg["products"] = DEFAULT_SETTINGS["products"]
        self.save_fn = save_fn
        self.on_order_fn = on_order_fn
        self.sessions = {}  # phone -> {"state":..., "product":..., ...}

    # -- session helpers -------------------------------------------------
    def _session(self, phone):
        return self.sessions.setdefault(phone, {"state": "idle"})

    def _reset(self, phone):
        self.sessions[phone] = {"state": "idle"}

    # -- product helpers -------------------------------------------------
    def _product_list_text(self):
        lines = ["{}. {} — {} {}".format(p["id"], p["name"], p["price"],
                                         self.cfg["currency"])
                 for p in self.cfg["products"]]
        return "\n".join(lines)

    def _find_product(self, text):
        text = text.strip().lower()
        products = self.cfg["products"]
        m = re.fullmatch(r"\d{1,2}", text)
        if m:
            for p in products:
                if p["id"] == int(m.group(0)):
                    return p
        for p in products:
            if p["name"].lower() in text or text in p["name"].lower():
                if len(text) >= 3:
                    return p
        return None

    # -- order storage ---------------------------------------------------
    def _save_order(self, order):
        if self.save_fn:
            self.save_fn(order)
        else:
            orders = []
            if os.path.exists(ORDERS_FILE):
                try:
                    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                        orders = json.load(f)
                except (json.JSONDecodeError, OSError):
                    orders = []
            orders.append(order)
            with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(orders, f, ensure_ascii=False, indent=2)
        # naya order save hua — auto-confirm callback (agar laga ho)
        if self.on_order_fn:
            try:
                self.on_order_fn(order)
            except Exception as e:
                print("on_order_fn failed:", e)

    # -- main entry point ------------------------------------------------
    def handle_message(self, phone, text):
        """WhatsApp webhook ya demo loop — dono isi ko call karein."""
        cfg = self.cfg
        s = self._session(phone)
        t = text.strip()
        low = t.lower()
        state = s["state"]

        # --- global commands (kisi bhi state me) ---
        if re.search(r"\b(cancel|mansookh)\b", low):
            name = s.get("name", "dost")
            self._reset(phone)
            return ORDER_CANCELLED.format(name=name)
        if re.search(r"(insan|human|boss|manager|call|phone).*(baat|bat|chahiye|kar)",
                     low) or "insan se" in low:
            return random.choice(HUMAN_REPLIES).format(wa=cfg["whatsapp"])

        # --- state machine ---
        if state == "idle":
            if re.search(r"(salam|aoa|hello|hi|adab)\b", low):
                s["state"] = "awaiting_product"
                return random.choice(GREETINGS).format(shop=cfg["shop_name"])
            if "product" in low or "list" in low or "cheez" in low:
                s["state"] = "awaiting_product"
                return ASK_PRODUCT.format(plist=self._product_list_text())
            p = self._find_product(t)
            if p:
                s["state"] = "awaiting_product"
                s["product"] = p
                return PRODUCT_DETAIL.format(name=p["name"], desc=p["desc"],
                                             price=p["price"],
                                             cur=cfg["currency"],
                                             delivery=cfg["delivery_info"])
            if re.search(r"(price|rate|qeemat|kitne ka|paisa)", low):
                s["state"] = "awaiting_product"
                return ("Qeemat jan'na hai? Koi masla nahi! 😊 Pehle product select karein:\n"
                        + self._product_list_text()
                        + "\n\nNumber ya naam likhein!")
            return random.choice(GREETINGS).format(shop=cfg["shop_name"]).replace(
                "khush aamdeed! Main aapki kya madad kar sakta hoon?",
                "khush aamdeed! Product dekhne ke liye **'products'** likhein! 😊")

        if state == "awaiting_product":
            p = self._find_product(t)
            if p:
                s["product"] = p
                if re.search(r"(discount|riayat|sasta|kam karo)", low):
                    return random.choice(DISCOUNT_REPLIES).format(
                        name=p["name"], price=p["price"],
                        cur=cfg["currency"])
                return PRODUCT_DETAIL.format(name=p["name"], desc=p["desc"],
                                             price=p["price"],
                                             cur=cfg["currency"],
                                             delivery=cfg["delivery_info"])
            if re.search(r"(discount|riayat|sasta|kam karo)", low):
                p0 = s.get("product") or cfg["products"][0]
                return random.choice(DISCOUNT_REPLIES).format(
                    name=p0["name"], price=p0["price"],
                    cur=cfg["currency"])
            if re.search(r"(deliver|kitne din|kab aye|shipping)", low):
                return random.choice(DELIVERY_REPLIES).format(
                    delivery=cfg["delivery_info"])
            if re.search(r"\b(order|book|chahiye|lena hai|done karo)\b", low):
                if s.get("product"):
                    s["state"] = "awaiting_name"
                    return ASK_NAME
                return "Pehle product to select karein! 😊\n" + self._product_list_text()
            if "product" in low or "list" in low:
                return ASK_PRODUCT.format(plist=self._product_list_text())
            return random.choice(FALLBACK_REPLIES)

        if state == "awaiting_name":
            if len(t) < 2:
                return "Naam thora wazeh likhein please! 😊"
            s["name"] = t
            s["state"] = "awaiting_city"
            return ASK_CITY.format(name=t)

        if state == "awaiting_city":
            if len(t) < 2:
                return "Sheher ka naam likhein (jaise: Dubai)! 🏙️"
            s["city"] = t
            s["state"] = "awaiting_address"
            return ASK_ADDRESS

        if state == "awaiting_address":
            if len(t) < 8:
                return ("Pata thora tafseel se likhein please! 📍\n"
                        "(ghar number, street, area — taake rider aasani se pohnch sake)")
            s["address"] = t
            s["state"] = "awaiting_confirm"
            p = s["product"]
            return ASK_CONFIRM.format(pname=p["name"], price=p["price"],
                                      cur=cfg["currency"], name=s["name"],
                                      city=s["city"], address=s["address"],
                                      delivery=cfg["delivery_info"])

        if state == "awaiting_confirm":
            if re.search(r"\b(han|haan|yes|confirm|ok|theek|done|sahi)\b", low):
                p = s["product"]
                oid = (cfg["order_prefix"] + "-"
                       + datetime.now().strftime("%y%m%d%H%M%S"))
                order = {"order_id": oid, "phone": phone, "name": s["name"],
                         "city": s["city"], "address": s["address"],
                         "product": p["name"], "price": p["price"],
                         "status": "confirmed",
                         "time": datetime.now().isoformat(timespec="seconds")}
                self._save_order(order)
                name = s["name"]
                self._reset(phone)
                return ORDER_DONE.format(name=name, oid=oid, pname=p["name"],
                                         price=p["price"],
                                         cur=cfg["currency"],
                                         shop=cfg["shop_name"])
            return ("Samajh nahi aaya! 😅 Confirm karne ke liye **'han'** likhein, "
                    "ya cancel ke liye **'cancel'**.")

        # unknown state — recover
        self._reset(phone)
        return random.choice(FALLBACK_REPLIES)

    # -- reports ----------------------------------------------------------
    @staticmethod
    def export_orders_csv(csv_path="orders.csv"):
        import csv
        if not os.path.exists(ORDERS_FILE):
            return 0
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            orders = json.load(f)
        if not orders:
            return 0
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(orders[0].keys()))
            w.writeheader()
            w.writerows(orders)
        return len(orders)


# ------------------------------------------------------------- demo loop

def demo():
    print("=" * 60)
    print("  {} WhatsApp COD Order Agent — DEMO".format(SHOP_NAME))
    print("  (customer ban kar baat karein — 'quit' likh kar niklein)")
    print("=" * 60)
    agent = OrderAgent()
    phone = "demo-customer"
    import time
    while True:
        try:
            msg = input("\nCustomer: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDemo khatam!")
            break
        if msg.lower() in ("quit", "exit", "q"):
            print("Demo khatam!")
            break
        if not msg:
            continue
        print("Agent typing...", flush=True)
        time.sleep(random.uniform(0.6, 1.4))  # real human jaisa waqfa
        print("Agent:", agent.handle_message(phone, msg))


if __name__ == "__main__":
    demo()
