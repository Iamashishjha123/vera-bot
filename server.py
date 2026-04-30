from fastapi import FastAPI
from bot import compose, respond

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Vera bot is running"}

store = {
    "category": {},
    "merchant": {},
    "customer": {},
    "trigger": {}
}

@app.get("/v1/healthz")
def health():
    return {"status": "ok"}

@app.get("/v1/metadata")
def metadata():
    return {
        "team_name": "Ashish Bot",
        "team_members": ["Ashish"],
        "approach": "Deterministic, data-driven messaging engine",
        "version": "2.0"
    }

@app.post("/v1/context")
def context(data: dict):
    store[data["scope"]][data["context_id"]] = data["payload"]
    return {"accepted": True}

@app.post("/v1/tick")
def tick(data: dict):
    actions = []

    trigger_ids = data.get("available_triggers", [])

    def trigger_priority(tid):
        t = store["trigger"].get(tid, {})
        return t.get("urgency", 0)

    trigger_ids = sorted(trigger_ids, key=trigger_priority, reverse=True)

    for trig_id in trigger_ids[:3]:
        trigger = store["trigger"].get(trig_id)
        if not trigger:
            continue

        merchant = store["merchant"].get(trigger["merchant_id"])
        if not merchant:
            continue

        category = store["category"].get(merchant.get("category_slug"), {})
        customer = store["customer"].get(trigger.get("customer_id"))

        result = compose(category, merchant, trigger, customer)

        if not result:
            continue

        actions.append({
            "conversation_id": trig_id,
            "merchant_id": merchant["merchant_id"],
            "customer_id": trigger.get("customer_id"),
            "send_as": result["send_as"],
            "trigger_id": trig_id,
            "body": result["body"],
            "cta": result["cta"],
            "suppression_key": result["suppression_key"],
            "rationale": result["rationale"]
        })

    return {"actions": actions}

@app.post("/v1/reply")
def reply(data: dict):
    return respond(data.get("message", ""))

    if "yes" in msg:
        return {
            "action": "send",
            "body": "Great 👍 I’ll set this up for you right away.",
            "cta": "none",
            "rationale": "User accepted"
        }

    if "no" in msg:
        return {
            "action": "end",
            "rationale": "User declined"
        }

    return {
        "action": "send",
        "body": "Got it. Want me to suggest something specific?",
        "cta": "open_ended",
        "rationale": "Continue engagement"
    }

from fastapi.responses import HTMLResponse

# ---------------- SIMPLE CHAT API ----------------
@app.post("/chat")
def chat(data: dict):
    user_message = data.get("message", "").lower()

    if "perf" in user_message or "ctr" in user_message:
        return {
            "reply": "Your CTR looks low. I suggest creating one service+price offer and one fresh post. Reply YES and I’ll draft it."
        }

    if "review" in user_message:
        return {
            "reply": "I can help identify review patterns and draft polite replies for customers."
        }

    if "offer" in user_message:
        return {
            "reply": "Best offers are specific, not generic discounts. Example: Haircut @ ₹99 or Dental Cleaning @ ₹299."
        }

    if "customer" in user_message:
        return {
            "reply": "I can create customer recall, refill, appointment, or winback messages based on consent."
        }

    return {
        "reply": "Hi, I’m your Merchant Growth Assistant. Ask me about CTR, reviews, offers, customers, or campaigns."
    }


# ---------------- SIMPLE CHAT UI ----------------
@app.get("/chat-ui", response_class=HTMLResponse)
def chat_ui():
    return """
    <html>
    <head>
        <title>Merchant Growth Assistant</title>
    </head>
    <body style="font-family: Arial; max-width: 700px; margin: 40px auto;">
        <h2>Merchant Growth Assistant</h2>

        <input id="msg" style="width:80%; padding:10px;" 
        placeholder="Ask about CTR, offers, reviews..." />

        <button onclick="sendMsg()" style="padding:10px;">Send</button>

        <div id="reply" style="margin-top:20px; white-space:pre-wrap;"></div>

        <script>
        async function sendMsg() {
            const msg = document.getElementById("msg").value;

            const res = await fetch("/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({message: msg})
            });

            const data = await res.json();
            document.getElementById("reply").innerText = data.reply;
        }
        </script>
    </body>
    </html>
    """