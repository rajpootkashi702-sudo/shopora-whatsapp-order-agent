"""
Order Agent — Users (multi-business accounts) 👥
=================================================
Har business owner apna account banata hai (Sign Up) → username + password
WO KHUD chunta hai → har user ka apna settings + apne orders.

Storage: users.json (demo-level — free hosting par redeploy se wipe ho
sakta hai; permanent production ke liye database lagega).
"""

import hashlib
import json
import os
import re

from config import load_settings, DEFAULT_SETTINGS

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "users.json")
ORDERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "orders.json")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "settings.json")

_USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,30}$")


def _clean_username(raw):
    return re.sub(r"[^a-z0-9._-]", "", (raw or "").lower().strip())


def _hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(shop_name, username, password, owner_name="", whatsapp=""):
    """Naya business account — username/password user KHUD chunta hai.

    Returns username. ValueError agar username ghalat/duplicate ho
    ya password kamzor ho.
    """
    username = _clean_username(username)
    if not _USERNAME_RE.match(username):
        raise ValueError("Username kam az kam 3 harf ka ho "
                         "(sirf a-z, 0-9, . _ -).")
    if not password or len(password) < 4:
        raise ValueError("Password kam az kam 4 harf ka rakhein.")
    data = load_users()
    users = data["users"]
    if username in users:
        raise ValueError("Ye username pehle se maujood hai — "
                         "koi aur chunein.")
    settings = load_settings()
    settings["shop_name"] = shop_name.strip() or "My Shop"
    if whatsapp.strip():
        settings["whatsapp"] = whatsapp.strip()
    users[username] = {
        "password_hash": _hash(password),
        "owner": owner_name.strip(),
        "settings": settings,
        "orders": [],
    }
    save_users(data)
    return username


def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "users" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"users": {}}


def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def verify(username, password):
    users = load_users()["users"]
    u = users.get((username or "").strip())
    return bool(u and u.get("password_hash") == _hash(password or ""))


def get_settings(username):
    u = load_users()["users"].get(username, {})
    s = u.get("settings") or load_settings()
    merged = dict(DEFAULT_SETTINGS)
    merged.update(s)
    return merged


def save_settings_for(username, settings):
    data = load_users()
    if username in data["users"]:
        data["users"][username]["settings"] = settings
        save_users(data)


def get_orders(username):
    u = load_users()["users"].get(username, {})
    return u.get("orders") or []


def add_order(username, order):
    data = load_users()
    if username in data["users"]:
        data["users"][username].setdefault("orders", []).append(order)
        save_users(data)


def update_order_status(username, order_id, new_status):
    """Ek order ka status badlein (confirmation agent ke liye)."""
    data = load_users()
    u = data["users"].get(username)
    if not u:
        return False
    for o in u.get("orders") or []:
        if o.get("order_id") == order_id:
            o["status"] = new_status
            save_users(data)
            print("Order", order_id, "->", new_status)
            return True
    print("Order not found:", order_id)
    return False


def ensure_seed():
    """Pehli dafa: purana admin (admin/shopora2026) migrate karein.

    Purani settings.json + orders.json hon to admin ke account me daal dein,
    taake purana login kaam karta rahe aur naya Sign Up bhi chale.
    """
    data = load_users()
    if data["users"]:
        return
    settings = load_settings()
    orders = []
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f) or []
        except (json.JSONDecodeError, OSError):
            orders = []
    data["users"]["admin"] = {
        "password_hash": _hash("shopora2026"),
        "owner": "Shopora Owner",
        "settings": settings,
        "orders": orders if isinstance(orders, list) else [],
    }
    save_users(data)
