"""Sales Assistant — Mobile App 📱
==============================
Multi-business WhatsApp-style order agent.

🔑 Login | 📝 Sign Up (apna username + password KHUD chunein)
Har business ka apna: settings, products (tasveeron ke saath!), orders, agent.

Chalayein:
  streamlit run order_app.py
"""

import os
import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from extra_streamlit_components import CookieManager

from agent import OrderAgent
from config import DEFAULT_SETTINGS
from users import (ensure_seed, create_user, verify, get_settings,
                   save_settings_for, get_orders, add_order,
                   update_order_status, create_session_token,
                   verify_session_token, revoke_session_token)


def _build_agent(settings, username):
    """OrderAgent banayein — auto-confirm callback ke saath.

    Naya order bante hi (agar settings me auto_confirm on ho aur
    phone number asli ho) webhook ko /send_confirm bhej kar
    WhatsApp Confirm buttons lagwayein.
    """
    def _on_order(order):
        try:
            if not settings.get("auto_confirm", True):
                return
            phone = str(order.get("phone") or "")
            if not re.fullmatch(r"\+?\d{7,15}", phone):
                return  # demo chat ("app-customer") — asli number nahi
            import requests as rq
            webhook_url = (settings.get("webhook_url")
                           or "https://salesathi-webhook.onrender.com").rstrip("/")
            r = rq.post(webhook_url + "/send_confirm",
                        json={"order": order}, timeout=25)
            if r.ok and r.json().get("ok"):
                update_order_status(username, order.get("order_id"),
                                    "verify_sent")
                print("auto-confirm sent:", order.get("order_id"))
        except Exception as e:
            print("auto-confirm failed:", e)

    return OrderAgent(settings=settings,
                      save_fn=lambda o: add_order(username, o),
                      on_order_fn=_on_order)

st.set_page_config(page_title="Sales Assistant", page_icon="🤖",
                   layout="centered")

ensure_seed()  # pehli dafa purana admin migrate ho jaye

# ------------------------------------------------------------ remember-me
# Ek dafa login → 30 din tak cookie me token → dobara login nahi mangega.
# Logout khud karein to cookie + token dono khatam.
_cookies = CookieManager()
_SS_COOKIE = "sa_token"


def _do_login(username):
    st.session_state.username = username
    st.session_state.settings = get_settings(username)
    st.session_state.agent = _build_agent(
        st.session_state.settings, username)
    st.session_state.chat = []

# ------------------------------------------------------------ mobile CSS
st.markdown("""
<style>
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    h1 { font-size: 1.6rem !important; }
    .stButton > button { width: 100%; padding: 0.75rem 1rem; font-size: 1rem; }
}
.big-cred { font-size: 1.4rem; font-weight: bold; background: #f0f2f6;
            padding: 0.6rem 1rem; border-radius: 0.5rem; text-align: center; }
</style>
""", unsafe_allow_html=True)


def _img_ok(path):
    """Local file ho to maujood hona chahiye, URL ho to theek hai."""
    if not path:
        return False
    if re.match(r"^https?://", path):
        return True
    return os.path.exists(path)


def _show_product_images(reply_text, settings):
    """Agent ke jawab me jin products ka zikr ho, unki tasveer dikhayein."""
    prods = settings.get("products", [])
    cur = settings.get("currency", "")
    low = (reply_text or "").lower()
    # poori list wali surat me sab dikhayein
    show_all = "products ki list" in low
    hits = [p for p in prods
            if _img_ok(p.get("image"))
            and (show_all or p["name"].lower() in low)]
    if not hits:
        return
    cols = st.columns(min(3, len(hits)))
    for col, p in zip(cols, hits[:6]):
        with col:
            st.image(p["image"],
                     caption="{} — {} {}".format(p["name"], p["price"], cur),
                     use_container_width=True)

# ------------------------------------------------------------ auth screen
if "username" not in st.session_state:
    st.session_state.username = ""

# Cookie me purana token ho to khud-ba-khud login (remember me)
if not st.session_state.username:
    _saved = _cookies.get(_SS_COOKIE)
    _auto_user = verify_session_token(_saved) if _saved else None
    if _auto_user:
        _do_login(_auto_user)
        st.rerun()

if not st.session_state.username:
    st.title("🤖 Sales Assistant")
    st.caption("Apne business ke liye AI order-taking agent! "
               "Aapka apna sales assistant! 💪")
    tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up"])

    with tab_login:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("➡️ Login", use_container_width=True):
            if verify(u, p):
                _do_login(u.strip())
                # 30 din ka remember-me cookie lagayein
                _tok = create_session_token(u.strip())
                if _tok:
                    _cookies.set(_SS_COOKIE, _tok,
                                 expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("❌ Ghalat username ya password!")

    with tab_signup:
        st.write("**Naya business account banayein** — apna username aur "
                 "password khud chunein! 🎉")
        shop = st.text_input("🏪 Business / Dukaan ka naam *", key="su_shop")
        owner = st.text_input("👤 Aapka naam", key="su_owner")
        wa = st.text_input("📞 WhatsApp number", key="su_wa")
        new_u = st.text_input("👤 Username chunein * (kam az kam 3 harf)",
                              key="su_user")
        new_p = st.text_input("🔑 Password chunein * (kam az kam 4 harf)",
                              type="password", key="su_pass")
        new_p2 = st.text_input("🔑 Password dobara likhein *",
                               type="password", key="su_pass2")
        if st.button("✨ Account Banayein", use_container_width=True):
            if not shop.strip():
                st.error("❌ Business ka naam to likhein!")
            elif not new_u.strip():
                st.error("❌ Username to chunein!")
            elif new_p != new_p2:
                st.error("❌ Dono password mil nahi rahe — dobara likhein!")
            else:
                try:
                    username = create_user(shop, new_u, new_p, owner, wa)
                except ValueError as e:
                    st.error("❌ {}".format(e))
                else:
                    st.session_state.new_user = username
                    st.rerun()

    # sign-up ke baad kamyabi ka paigham — login tab par bhejein
    if st.session_state.get("new_user"):
        st.success("🎉 **Account ban gaya, {}!** Ab 🔑 Login tab me apna "
                   "username aur password likh kar login karein!".format(
                       st.session_state.new_user))
        if st.button("✅ Login par jayein", use_container_width=True):
            del st.session_state.new_user
            st.rerun()

    st.stop()

# ------------------------------------------------------------ logged-in app
username = st.session_state.username
settings = st.session_state.settings

if "agent" not in st.session_state:
    st.session_state.agent = _build_agent(settings, username)
if "chat" not in st.session_state:
    st.session_state.chat = []
if "phone" not in st.session_state:
    st.session_state.phone = "app-customer"

tab_chat, tab_orders, tab_settings = st.tabs(
    ["💬 Customer Chat", "📦 Orders", "⚙️ Settings"])

with tab_chat:
    st.title("🤖 {} Order Agent".format(settings["shop_name"]))
    st.caption("Customer ban kar baat karein — bilkul WhatsApp jaisa! "
               "| 👤 {} | ⚡ by Sales Assistant".format(username))
    if st.button("🚪 Logout"):
        revoke_session_token(username)
        _cookies.delete(_SS_COOKIE)
        for k in ("username", "settings", "agent", "chat"):
            st.session_state.pop(k, None)
        st.rerun()

    # 🛍️ visual catalog — tasveeron wala
    _catalog = [p for p in settings.get("products", []) if _img_ok(p.get("image"))]
    if _catalog:
        with st.expander("🛍️ Products ki tasveerain dekhein", expanded=False):
            _cols = st.columns(3)
            for _i, _p in enumerate(_catalog):
                with _cols[_i % 3]:
                    st.image(_p["image"],
                             caption="{} — {} {}".format(
                                 _p["name"], _p["price"],
                                 settings.get("currency", "")),
                             use_container_width=True)

    for who, text in st.session_state.chat:
        with st.chat_message(who):
            st.write(text)
        if who == "assistant":
            _show_product_images(text, st.session_state.settings)

    prompt = st.chat_input("Message likhein...")
    if prompt:
        st.session_state.chat.append(("user", prompt))
        with st.chat_message("user"):
            st.write(prompt)
        reply = st.session_state.agent.handle_message(
            st.session_state.phone, prompt)
        st.session_state.chat.append(("assistant", reply))
        with st.chat_message("assistant"):
            st.write(reply)
        _show_product_images(reply, st.session_state.settings)

    if st.button("🔄 Nayi chat shuru karein"):
        st.session_state.chat = []
        st.session_state.agent = _build_agent(
            st.session_state.settings, username)
        st.rerun()

with tab_orders:
    st.title("📦 Orders")
    orders = get_orders(username)
    if orders:
        df = pd.DataFrame(orders)
        if "price" not in df.columns and "price_aed" in df.columns:
            df["price"] = df["price_aed"]
        cols = [c for c in ["order_id", "name", "phone", "product",
                            "price", "city", "status", "time"]
                if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
        st.metric("Total orders", len(df),
                  "{} {}".format(int(df["price"].sum()), settings["currency"])
                  if "price" in df.columns else None)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV Download", csv,
                           "orders_{}.csv".format(username), "text/csv")

        # ---- COD Confirmation Agent ----
        st.subheader("✅ COD Confirmation")
        st.caption("Customer ko WhatsApp par Confirm/Cancel buttons bhejein — "
                   "fake orders dispatch se pehle pakrein!")
        webhook_url = (settings.get("webhook_url")
                       or "https://salesathi-webhook.onrender.com").rstrip("/")
        need = [o for o in orders
                if o.get("status") in ("confirmed", "pending", "verify_reminded")]
        if need:
            for o in need:
                c1, c2 = st.columns([4, 1])
                c1.write("🧾 {} — {} ({} {}) — *{}*".format(
                    o.get("order_id"), o.get("product"),
                    o.get("price"), settings.get("currency", "AED"),
                    o.get("status")))
                if c2.button("📲 Confirm", key="cf_" + str(o.get("order_id"))):
                    try:
                        import requests as rq
                        r = rq.post(webhook_url + "/send_confirm",
                                    json={"order": o},
                                    timeout=25)
                        if r.ok and r.json().get("ok"):
                            st.success("Confirm message bhej diya! ✅")
                        else:
                            st.error("Nahi bheja: {}".format(r.text[:120]))
                    except Exception as e:
                        st.error("Webhook se rabta nahi: {}".format(e))
        else:
            st.info("Sab orders verified ya cancelled hain. 🎉")
    else:
        st.info("Abhi koi order nahi — pehle 💬 chat me order karein!")

with tab_settings:
    st.title("⚙️ Business Settings")
    st.caption("Apne business ke hisaab se set karein — **Save** karte hi "
               "agent foran naye settings par chal parega! 🚀")

    s = st.session_state.settings
    shop = st.text_input("🏪 Dukaan / Business ka naam",
                         value=s.get("shop_name", ""))
    c1, c2 = st.columns(2)
    currency = c1.text_input("💱 Currency (jaise: AED, PKR, Rs)",
                             value=s.get("currency", ""))
    order_prefix = c2.text_input("🧾 Order ID prefix (jaise: SHP)",
                                 value=s.get("order_prefix", ""))
    whatsapp = st.text_input("📞 WhatsApp number (orders ke liye)",
                             value=s.get("whatsapp", ""))
    delivery = st.text_area("🚚 Delivery info",
                            value=s.get("delivery_info", ""))
    auto_confirm = st.checkbox(
        "🤖 Auto-confirm: naya order aate hi customer ko WhatsApp par "
        "Confirm/Cancel buttons bhejein",
        value=s.get("auto_confirm", True))

    st.subheader("📦 Products")
    st.caption("Neeche table me **direct edit** karein — naam, price, wazahat. "
               "Nayi row add karne ke liye aakhri khaali row use karein, "
               "hatane ke liye row select karke 🗑️ dabayein.")
    df_prod = pd.DataFrame(s.get("products", []))
    for col in ["name", "price", "desc"]:
        if col not in df_prod.columns:
            df_prod[col] = "" if col != "price" else 0
    edited = st.data_editor(
        df_prod[["name", "price", "desc"]],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn("Product ka naam",
                                                required=True),
            "price": st.column_config.NumberColumn("Price", min_value=0,
                                                   required=True),
            "desc": st.column_config.TextColumn("Wazahat"),
        },
        key="products_editor",
    )

    b1, b2 = st.columns(2)
    if b1.button("💾 Save Settings", use_container_width=True):
        products = []
        # purani tasveerain naam se milayein taake zaya na hon
        _old_imgs = {p.get("name"): p.get("image", "")
                     for p in s.get("products", [])}
        for i, row in enumerate(edited.to_dict("records"), 1):
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            try:
                price = int(float(row.get("price") or 0))
            except (TypeError, ValueError):
                price = 0
            products.append({"id": i, "name": name, "price": price,
                             "desc": str(row.get("desc", "")).strip(),
                             "image": _old_imgs.get(name, "")})
        if not products:
            st.error("❌ Kam az kam 1 product to rakhein!")
        else:
            new_settings = {
                "shop_name": shop.strip() or "My Shop",
                "currency": currency.strip() or "AED",
                "whatsapp": whatsapp.strip(),
                "delivery_info": delivery.strip(),
                "order_prefix": order_prefix.strip() or "SHP",
                "auto_confirm": bool(auto_confirm),
                "products": products,
            }
            save_settings_for(username, new_settings)
            st.session_state.settings = new_settings
            st.session_state.agent = _build_agent(new_settings, username)
            st.success("✅ Save ho gaya! Agent ab **{}** ke naye settings "
                       "par chal raha hai! 🎉".format(new_settings["shop_name"]))
            st.rerun()

    if b2.button("↩️ Reset (default Shopora)", use_container_width=True):
        save_settings_for(username, DEFAULT_SETTINGS)
        st.session_state.settings = get_settings(username)
        st.session_state.agent = _build_agent(
            st.session_state.settings, username)
        st.success("✅ Default settings wapas laga di!")
        st.rerun()

    st.divider()
    st.subheader("🖼️ Product ki Photo")
    st.caption("Har product ki tasveer lagayein — customer ko chat me "
               "tasveer ke saath nazar aayega! 📷")
    _prods = st.session_state.settings.get("products", [])
    if _prods:
        _pname = st.selectbox("Product chunein",
                              [p["name"] for p in _prods],
                              key="photo_product")
        _pobj = next(p for p in _prods if p["name"] == _pname)
        _cu, _cl = st.columns(2)
        _up = _cu.file_uploader("📤 Photo upload karein",
                                type=["png", "jpg", "jpeg", "webp"],
                                key="photo_upload")
        _url = _cl.text_input("🔗 ya photo ka link (URL) lagayein",
                              key="photo_url")
        if _img_ok(_pobj.get("image")):
            st.image(_pobj["image"], width=220, caption="Maujooda photo")
        _b1, _b2 = st.columns(2)
        if _b1.button("💾 Photo save karein", use_container_width=True,
                      key="photo_save"):
            _img_val = _pobj.get("image", "")
            if _up is not None:
                _ext = _up.name.rsplit(".", 1)[-1].lower() or "jpg"
                _slug = re.sub(r"[^a-z0-9]+", "",
                               _pname.lower())[:20] or "product"
                os.makedirs("product_images", exist_ok=True)
                _fname = "product_images/{}_{}.{}".format(username, _slug,
                                                          _ext)
                with open(_fname, "wb") as _f:
                    _f.write(_up.getbuffer())
                _img_val = _fname
            elif _url.strip():
                _img_val = _url.strip()
            if _img_val:
                _pobj["image"] = _img_val
                save_settings_for(username, st.session_state.settings)
                st.success("✅ Photo lag gayi! Ab chat me tasveer ke "
                           "saath nazar aayega! 🎉")
                st.rerun()
            else:
                st.warning("Pehle photo upload karein ya link likhein!")
        if _img_ok(_pobj.get("image")) and _b2.button(
                "🗑️ Photo hatayein", use_container_width=True,
                key="photo_del"):
            _pobj["image"] = ""
            save_settings_for(username, st.session_state.settings)
            st.success("✅ Photo hata di!")
            st.rerun()
