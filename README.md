# 🤖💬 Shopora WhatsApp COD Order Agent

Real human ki tarah deal karne wala order-taking agent — Roman Urdu me!

## Kya karta hai
- 😊 **Salam ka jawab**, product list, price, discount, delivery info
- 📦 12 products (Shopora ki asal list + asal prices)
- 📝 Naam → Sheher → Mukammal pata → Confirm → Order save
- 🧾 Har order `orders.json` me (Order ID ke saath)
- 🙏 "Insan se baat karni hai" par boss ko escalate karta hai
- ❌ Kisi bhi waqt `cancel` se order cancel

## Chalayein
```bash
python agent.py
```
Demo chat khul jayegi — customer ban kar baat karein!

## Real WhatsApp par lagana
WhatsApp Business Cloud API ka webhook `handle_message(phone, text)` se jor dein:
```python
reply = agent.handle_message(customer_phone, incoming_text)
# reply ko WhatsApp API se wapas bhej dein
```

## Orders dekhein
- `orders.json` — sab orders
- `OrderAgent.export_orders_csv()` — CSV report
