import time
import uuid
from datetime import datetime
from fastapi import FastAPI
from bot import compose, respond

app = FastAPI()
START_TIME = time.time()

store = {
    "category": {},
    "merchant": {},
    "customer": {},
    "trigger": {}
}

versions = {
    "category": {},
    "merchant": {},
    "customer": {},
    "trigger": {}
}

conversations = {}


@app.get("/")
def root():
    return {"message": "Vera bot is running"}


@app.get("/v1/healthz")
def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": {
            "category": len(store["category"]),
            "merchant": len(store["merchant"]),
            "customer": len(store["customer"]),
            "trigger": len(store["trigger"])
        }
    }


@app.get("/v1/metadata")
def metadata():
    return {
        "team_name": "Ashish Bot",
        "team_members": ["Ashish Jha"],
        "model": "deterministic-rule-engine",
        "approach": "4-context composer with trigger routing, consent checks, urgency ranking, and multi-turn handling",
        "version": "4.0",
        "submitted_at": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/v1/context")
def context(data: dict):
    scope = data.get("scope")
    cid = data.get("context_id")
    version = data.get("version", 1)
    payload = data.get("payload", {})

    if scope not in store:
        return {
            "accepted": False,
            "reason": "invalid_scope",
            "details": f"Unknown scope: {scope}"
        }

    current_version = versions[scope].get(cid, 0)

    if version < current_version:
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": current_version
        }

    if version == current_version:
        return {
            "accepted": True,
            "ack_id": f"ack_{scope}_{cid}_{version}",
            "stored_at": datetime.utcnow().isoformat() + "Z"
        }

    store[scope][cid] = payload
    versions[scope][cid] = version

    return {
        "accepted": True,
        "ack_id": f"ack_{scope}_{cid}_{version}",
        "stored_at": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/v1/tick")
def tick(data: dict):
    actions = []
    trigger_ids = data.get("available_triggers", [])

    def trigger_priority(tid):
        trigger = store["trigger"].get(tid, {})
        return trigger.get("urgency", 0)

    trigger_ids = sorted(trigger_ids, key=trigger_priority, reverse=True)
    used_merchants = set()

    for trig_id in trigger_ids[:20]:
        trigger = store["trigger"].get(trig_id)
        if not trigger:
            continue

        merchant_id = trigger.get("merchant_id") or trigger.get("payload", {}).get("merchant_id")
        merchant = store["merchant"].get(merchant_id)
        if not merchant:
            continue

        if merchant_id in used_merchants:
            continue

        category_slug = merchant.get("category_slug")
        category = store["category"].get(category_slug, {})

        customer_id = trigger.get("customer_id") or trigger.get("payload", {}).get("customer_id")
        customer = store["customer"].get(customer_id) if customer_id else None

        result = compose(category, merchant, trigger, customer)

        if not result:
            continue

        conv_id = f"conv_{uuid.uuid4().hex[:10]}"

        action = {
            "conversation_id": conv_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": result.get("send_as", "vera"),
            "trigger_id": trig_id,
            "template_name": result.get("template_name", f"vera_{trigger.get('kind', 'general')}_v1"),
            "template_params": result.get("template_params", []),
            "body": result.get("body", ""),
            "cta": result.get("cta", "YES/NO"),
            "suppression_key": result.get("suppression_key", trigger.get("suppression_key")),
            "rationale": result.get("rationale", "Context-aware Vera message.")
        }

        if not action["body"]:
            continue

        conversations[conv_id] = {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "trigger_id": trig_id,
            "trigger_kind": trigger.get("kind"),
            "trigger_payload": trigger.get("payload", {}),
            "merchant_name": merchant.get("identity", {}).get("name"),
            "send_as": action["send_as"],
            "turns": [
                {
                    "from": "bot",
                    "body": action["body"],
                    "ts": datetime.utcnow().isoformat() + "Z"
                }
            ]
        }

        actions.append(action)
        used_merchants.add(merchant_id)

    return {"actions": actions}


@app.post("/v1/reply")
def reply(data: dict):
    conv_id = data.get("conversation_id")
    msg = data.get("message", "")

    state = conversations.get(conv_id, {
        "merchant_id": data.get("merchant_id"),
        "customer_id": data.get("customer_id"),
        "trigger_id": None,
        "trigger_kind": None,
        "trigger_payload": {},
        "merchant_name": None,
        "send_as": None,
        "turns": []
    })

    state["turns"].append({
        "from": data.get("from_role", "merchant"),
        "body": msg,
        "ts": data.get("received_at", datetime.utcnow().isoformat() + "Z")
    })

    state["last_from_role"] = data.get("from_role", "merchant")

    result = respond(state, msg)

    if result.get("action") == "send":
        state["turns"].append({
            "from": "bot",
            "body": result.get("body", ""),
            "ts": datetime.utcnow().isoformat() + "Z"
        })

    conversations[conv_id] = state
    return result


@app.post("/v1/teardown")
def teardown():
    for scope in store:
        store[scope].clear()
        versions[scope].clear()

    conversations.clear()
    return {"ok": True}