"""
Order Agent — Business Settings (config) ⚙️
===========================================
Har banda apne business ke hisaab se app set kar sakta hai:
  - dukaan ka naam, currency, WhatsApp number
  - products ki list (naam + price + wazahat)
  - delivery info, Order ID prefix

Settings `settings.json` me save hoti hain. File na ho to DEFAULT_SETTINGS
istemal hoti hain.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "settings.json")

DEFAULT_SETTINGS = {
    "shop_name": "Shopora",
    "currency": "AED",
    "whatsapp": "+92 319 6800420",
    "delivery_info": "Cash on Delivery — pooray UAE (7 emirates), 2-4 working days",
    "order_prefix": "SHP",
    "products": [
        {"id": 1, "name": "Smart Sweeping Robot", "price": 59,
         "desc": "Khud safai kare, aap aaram karein! 🤖", "image": ""},
        {"id": 2, "name": "Mini Camera Pen", "price": 59,
         "desc": "Likhnay wala pen jo video bhi banaye! 🖊️", "image": ""},
        {"id": 3, "name": "Kids Instant Print Camera", "price": 59,
         "desc": "Bachon ka camera — photo kheecho, foran print! 📸", "image": ""},
        {"id": 4, "name": "Handheld Steam Cleaner", "price": 69,
         "desc": "Bijli ki taqat se gehra saaf! ✨", "image": ""},
        {"id": 5, "name": "2-in-1 Eyebrow Trimmer", "price": 49,
         "desc": "Salon wali finishing ghar par! 💅", "image": ""},
        {"id": 6, "name": "Vacuum Sealer Machine", "price": 49,
         "desc": "Khana fresh rakhe, zaya na ho! 🍱", "image": ""},
        {"id": 7, "name": "Orange Exfoliating Gel", "price": 49,
         "desc": "Naram o mulaim jild ka raaz! 🍊", "image": ""},
        {"id": 8, "name": "Mini Steam Iron", "price": 39,
         "desc": "Kapron ki silwatein secondon me khatam! 👔", "image": ""},
        {"id": 9, "name": "16-in-1 Vegetable Chopper", "price": 39,
         "desc": "Sabzi kaatna ab khel! 🔪", "image": ""},
        {"id": 10, "name": "Yandou Shaver", "price": 39,
         "desc": "Smooth shave, har roz! 🪒", "image": ""},
        {"id": 11, "name": "Mini Air Cooler", "price": 49,
         "desc": "Garmi me thandi hawa ka saathi! ❄️", "image": ""},
        {"id": 12, "name": "Car Washer Gun", "price": 59,
         "desc": "Gari ghar par chamkayein! 🚗", "image": ""},
    ],
}


def load_settings():
    """settings.json parhein; na mile ya kharab ho to defaults dein."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data or {})
            # products khaali ya ghalat hon to defaults wapas
            if not isinstance(merged.get("products"), list) or not merged["products"]:
                merged["products"] = DEFAULT_SETTINGS["products"]
            # har product me id/price pakki karein
            for i, p in enumerate(merged["products"], 1):
                p.setdefault("id", i)
                p.setdefault("name", "Product {}".format(i))
                p.setdefault("price", 0)
                p.setdefault("desc", "")
                p.setdefault("image", "")
            return merged
        except (json.JSONDecodeError, OSError, AttributeError):
            pass
    return {k: (list(v) if isinstance(v, list) else v)
            for k, v in DEFAULT_SETTINGS.items()}


def save_settings(settings):
    """Settings ko settings.json me save karein."""
    clean = dict(settings)
    products = []
    for i, p in enumerate(clean.get("products") or [], 1):
        products.append({
            "id": i,
            "name": str(p.get("name", "")).strip() or "Product {}".format(i),
            "price": p.get("price", 0),
            "desc": str(p.get("desc", "")).strip(),
            "image": str(p.get("image", "")).strip(),
        })
    clean["products"] = products
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    return clean
