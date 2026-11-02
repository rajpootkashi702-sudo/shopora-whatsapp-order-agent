/*
Sales Assistant — WhatsApp Bridge (Baileys)
============================================
WhatsApp se Sales Assistant agent ka connection — BINA Meta Cloud API ke.

Kaam:
  1. /qr page par QR code dikhata hai — apne WhatsApp
     (Linked devices → Link a device) se scan karein. Ek dafa link
     ho jaye to dobara scan ki zaroorat nahi (jab tak redeploy na ho).
  2. Customer ka message aaye → Python webhook (/baileys_inbound)
     ko bhejein → agent ka jawab wapas customer ko WhatsApp par.

Env:
  WEBHOOK_URL     Python webhook ka URL
                  (default: https://salesathi-webhook.onrender.com)
  BAILEYS_SECRET  webhook se baat karte waqt bheja jane wala secret
                  (webhook par bhi same value honi chahiye; khaali ho to check skip)
  PORT            (Render khud deta hai)
*/

const express = require("express");
const QRCode = require("qrcode");
const pino = require("pino");
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} = require("@whiskeysockets/baileys");

const PORT = process.env.PORT || 3000;
const WEBHOOK_URL = (process.env.WEBHOOK_URL ||
  "https://salesathi-webhook.onrender.com").replace(/\/$/, "");
const BAILEYS_SECRET = process.env.BAILEYS_SECRET || "";

let sock = null;
let currentQR = null;
let connectedJid = null;

const app = express();
app.use(express.json());

// ------------------------------------------------- Baileys connection
async function connectWA() {
  const { state, saveCreds } = await useMultiFileAuthState("./auth");
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: "silent" }),
    printQRInTerminal: false,
    browser: ["Sales Assistant", "Chrome", "1.0"],
    syncFullHistory: false,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      currentQR = qr;
      connectedJid = null;
      console.log("QR ready — /qr kholein aur scan karein");
    }
    if (connection === "open") {
      currentQR = null;
      connectedJid = sock.user && sock.user.id;
      console.log("WhatsApp connected:", connectedJid);
    }
    if (connection === "close") {
      const code = lastDisconnect && lastDisconnect.error &&
        lastDisconnect.error.output && lastDisconnect.error.output.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      console.log("Connection closed, code:", code, "loggedOut:", loggedOut);
      currentQR = null;
      connectedJid = null;
      // loggedOut ho to bhi dobara connectWA — naya QR ban jayega
      setTimeout(connectWA, 3000);
    }
  });

  // ------------------------------------------------- incoming messages
  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    for (const msg of messages) {
      try {
        if (msg.key.fromMe) continue;
        const jid = msg.key.remoteJid || "";
        if (!jid.endsWith("@s.whatsapp.net")) continue; // group/status skip
        const m = msg.message || {};
        const text =
          m.conversation ||
          (m.extendedTextMessage && m.extendedTextMessage.text) ||
          "";
        if (!text.trim()) continue;
        const phone = jid.split("@")[0].split(":")[0];
        console.log("WA <-", phone, ":", text.slice(0, 80));
        const reply = await askAgent(phone, text.trim());
        if (reply) {
          await sock.sendMessage(jid, { text: reply });
          console.log("WA ->", phone, ":", reply.slice(0, 80));
        }
      } catch (e) {
        console.log("msg handle error:", e.message);
      }
    }
  });
}

async function askAgent(phone, text) {
  try {
    const r = await fetch(WEBHOOK_URL + "/baileys_inbound", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, text, secret: BAILEYS_SECRET }),
    });
    if (!r.ok) {
      console.log("webhook error:", r.status);
      return null;
    }
    const data = await r.json();
    return data.reply || null;
  } catch (e) {
    console.log("webhook call failed:", e.message);
    return null;
  }
}

// ------------------------------------------------- web pages
function shortJid(jid) {
  return String(jid || "").split("@")[0].split(":")[0];
}

app.get("/", (req, res) => {
  res.send(
    "<h2>Sales Assistant — WhatsApp Bridge</h2>" +
    "<p>Status: <b>" +
    (connectedJid
      ? "Connected ✅ (" + shortJid(connectedJid) + ")"
      : "Not connected ❌") +
    "</b></p>" +
    '<p><a href="/qr">QR code dekhein / scan karein</a></p>'
  );
});

app.get("/qr", async (req, res) => {
  if (connectedJid) {
    return res.send(
      "<h2>✅ WhatsApp connected!</h2>" +
      "<p>Number: <b>" + shortJid(connectedJid) + "</b></p>" +
      "<p>Agent customer messages ka jawab de raha hai. 🤖</p>"
    );
  }
  if (!currentQR) {
    return res.send(
      "<h2>QR tayyar ho raha hai…</h2>" +
      "<p>10 second baad page refresh karein.</p>" +
      "<script>setTimeout(()=>location.reload(),10000)</script>"
    );
  }
  try {
    const img = await QRCode.toDataURL(currentQR, { width: 300, margin: 2 });
    res.send(
      "<h2>📱 WhatsApp se scan karein</h2>" +
      "<p>WhatsApp kholein → <b>⋮ → Linked devices → Link a device</b><br>" +
      "neeche QR scan karein:</p>" +
      '<img src="' + img + '" />' +
      "<p><i>QR thori der me badal jata hai — page khud refresh ho jayega.</i></p>" +
      "<script>setTimeout(()=>location.reload(),25000)</script>"
    );
  } catch (e) {
    res.send("<h2>QR banane me masla</h2><p>Page refresh karein.</p>");
  }
});

// In-app QR (Streamlit app ke andar) — secret ke saath, taake sirf
// login-shuda app se QR nikle. Returns {connected, number, qr(dataURL|null)}
app.get("/qr.json", async (req, res) => {
  const secret = (req.query && req.query.secret) || "";
  if (BAILEYS_SECRET && secret !== BAILEYS_SECRET) {
    return res.status(403).json({ ok: false, error: "forbidden" });
  }
  if (connectedJid) {
    return res.json({ ok: true, connected: true,
                      number: shortJid(connectedJid) });
  }
  if (!currentQR) {
    return res.json({ ok: true, connected: false, qr: null });
  }
  try {
    const img = await QRCode.toDataURL(currentQR, { width: 300, margin: 2 });
    res.json({ ok: true, connected: false, qr: img });
  } catch (e) {
    res.json({ ok: true, connected: false, qr: null });
  }
});

// Python webhook yahan se bridge ke zariye WhatsApp text bhej sakta hai
// (mustaqbil me kaam aayega — abhi istemal nahi ho raha)
app.post("/send", async (req, res) => {
  const { to, text, secret } = req.body || {};
  if (BAILEYS_SECRET && secret !== BAILEYS_SECRET) {
    return res.status(403).json({ ok: false, error: "forbidden" });
  }
  if (!sock || !connectedJid) {
    return res.status(503).json({ ok: false, error: "whatsapp not connected" });
  }
  if (!to || !text) {
    return res.status(400).json({ ok: false, error: "to + text required" });
  }
  try {
    const jid = String(to).includes("@")
      ? String(to)
      : String(to).replace(/\D/g, "") + "@s.whatsapp.net";
    await sock.sendMessage(jid, { text: String(text) });
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

app.get("/health", (req, res) => {
  res.json({ ok: true, connected: !!connectedJid });
});

app.listen(PORT, () => {
  console.log("Bridge :%s — webhook: %s", PORT, WEBHOOK_URL);
  connectWA().catch((e) => console.log("connectWA failed:", e.message));
});
