"""Illustrative header matching, not industry prediction or calibrated confidence."""
SIGNALS = {
    "Commerce": ["order", "sku", "warehouse", "shipping", "return"],
    "Service delivery": ["ticket", "subscription", "sla", "support"],
    "Finance": ["transaction", "invoice", "payment", "reconciliation", "currency"],
    "Supply chain": ["shipment", "inventory", "supplier", "lead_time", "procurement"],
    "People analytics": ["employee", "department", "tenure", "onboarding", "attrition"],
}
def detect_context(df):
    text = " ".join(str(c).lower() for c in df.columns)
    found = {k:[t for t in terms if t in text] for k,terms in SIGNALS.items()}
    best = max(map(len, found.values()))
    winners = [k for k,v in found.items() if len(v)==best]
    if best==0 or len(winners)!=1:
        return "Generic / mixed dataset", best, sorted({t for terms in found.values() for t in terms})
    return winners[0], best, found[winners[0]]
