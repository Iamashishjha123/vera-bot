def compose(category, merchant, trigger, customer=None):
    name = merchant.get("identity", {}).get("name", "there")
    merchant_id = merchant.get("merchant_id")

    ctr = merchant.get("performance", {}).get("ctr", 0)
    impressions = merchant.get("performance", {}).get("impressions", 0)

    peer_ctr = category.get("peer_stats", {}).get("avg_ctr", 0)

    kind = trigger.get("kind")

    # ---------------- PERFORMANCE DIP ----------------
    if kind == "perf_dip":
        if ctr >= peer_ctr * 0.9:
            return None  # not bad enough → skip

        gap = peer_ctr - ctr

        body = (
            f"{name}, your listing CTR is {ctr:.2%} vs category avg {peer_ctr:.2%}.\n\n"
            f"You're missing ~{gap:.2%} potential clicks.\n"
            "Top fix: add 1 strong offer + better cover image.\n\n"
            "Reply YES and I’ll create a high-converting offer for you."
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": f"{merchant_id}_perf_dip",
            "rationale": "CTR significantly below category benchmark"
        }

    # ---------------- RESEARCH DIGEST ----------------
    if kind == "research_digest":
        digest = category.get("digest", [])

        if not digest:
            return None

        insight = digest[0]

        body = (
            f"{name}, new trend in your category:\n"
            f"{insight.get('title', 'Customers prefer bundled offers')}.\n\n"
            "Shops using this saw higher conversions.\n"
            "Want me to create a campaign using this?"
        )

        return {
            "body": body,
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": f"{merchant_id}_research",
            "rationale": "Category trend can improve conversions"
        }

    # ---------------- CUSTOMER RECALL ----------------
    if kind == "recall_due" and customer:
        cname = customer.get("identity", {}).get("name", "Customer")
        shop = merchant.get("identity", {}).get("name", "Store")

        last_seen = customer.get("last_seen_days", 30)

        if last_seen < 15:
            return None  # too soon → skip

        offer = merchant.get("offers", [{}])[0].get("title", "Special offer")

        body = (
            f"Hi {cname}, {shop} here 👋\n\n"
            f"We haven’t seen you in {last_seen} days.\n"
            f"{offer} is waiting for you.\n\n"
            "Reply YES to book now."
        )

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": f"{cname}_recall",
            "rationale": "Customer inactive → recall opportunity"
        }

    # ---------------- FALLBACK ----------------
    body = (
        f"{name}, I can help improve your visibility and conversions.\n"
        "Want quick suggestions?"
    )

    return {
        "body": body,
        "cta": "open_ended",
        "send_as": "vera",
        "suppression_key": f"{merchant_id}_general",
        "rationale": "General engagement"
    }