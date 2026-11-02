# Sales Assistant — WhatsApp Bridge (Baileys)

Meta Cloud API ke **baghair** WhatsApp connection — QR scan wala tareeqa.

## Kaam kaise karta hai
1. Ye service Baileys se WhatsApp se **linked device** ki tarah jurti hai
   (jaise WhatsApp Web).
2. `/qr` page par QR code aata hai — apne phone ke WhatsApp
   (⋮ → Linked devices → Link a device) se scan karein.
3. Customer ka message aaye to ye Python webhook ke `/baileys_inbound`
   route ko bhejti hai, agent ka jawab wapas customer ko deti hai.

## Deploy (Render, free)
- New Web Service → repo `shopora-whatsapp-order-agent`
- Root Directory: `wa-bridge`
- Build Command: `npm install`
- Start Command: `npm start`
- Env vars:
  - `WEBHOOK_URL` = `https://salesathi-webhook.onrender.com`
  - `BAILEYS_SECRET` = (koi lamba random text — webhook par bhi same lagayein)

## Zaroori baatein
- **Ek dafa QR scan** ho jaye to session save rehta hai — dobara scan
  sirf **redeploy** ke baad chahiye hoga.
- Free server 15 min idle par **so jata hai** — is liye keep-alive ping
  (har 10 min `/health` par) lagayein taake WhatsApp connected rahe.
- Ye **unofficial** tareeqa hai — bahut zyada automatic messages par
  WhatsApp number **ban** kar sakta hai. Normal order-volume par risk kam.
- Baileys orders **in-chat "han"** se confirm hote hain (agent ka apna flow);
  Meta wale Confirm/Cancel buttons yahan nahi chalte.
