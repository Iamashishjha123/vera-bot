from fastapi import FastAPI
from bot import compose

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

    for trig_id in data["available_triggers"]:
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
    msg = data.get("message", "").lower()

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