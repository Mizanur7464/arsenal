"""Quantity, price, section, and seats-together filters from config."""


def apply_filters(config: dict, available: dict, *, seats_strict: bool = True) -> bool:
    """
    Check if a ticket option passes filters.
    available example: {"price": 50, "section": "North Bank", "qty_available": 2, "raw_text": "..."}
    """
    f = config.get("filters", {})
    qty = f.get("quantity", 1)
    max_price = f.get("max_price")
    sections = f.get("sections") or []

    if available.get("qty_available", 0) < qty:
        return False
    if max_price is not None and available.get("price", 0) > max_price:
        return False
    if sections:
        sec = (available.get("section") or "").lower()
        if not any(s.lower() in sec for s in sections):
            return False

    if seats_strict and f.get("seats_together"):
        text = (available.get("raw_text") or available.get("section") or "").lower()
        if any(x in text for x in ("not together", "separate seats", "split", "non-adjacent")):
            return False

    return True


def filter_reason(config: dict, available: dict, *, seats_strict: bool = True) -> str:
    """Why a ticket passed or failed (for reports)."""
    f = config.get("filters", {})
    qty = f.get("quantity", 1)
    max_price = f.get("max_price")
    sections = f.get("sections") or []

    if available.get("qty_available", 0) < qty:
        return f"FAIL: need qty {qty}, available {available.get('qty_available', 0)}"
    if max_price is not None and available.get("price", 0) > max_price:
        return f"FAIL: price {available.get('price')} > max {max_price}"
    if sections:
        sec = (available.get("section") or "").lower()
        if not any(s.lower() in sec for s in sections):
            return f"FAIL: section not in {sections}"
    if seats_strict and f.get("seats_together"):
        text = (available.get("raw_text") or "").lower()
        if any(x in text for x in ("not together", "separate", "split")):
            return "FAIL: not seats-together"
    return "PASS"


def rank_ticket_option(config: dict, available: dict) -> tuple:
    """Lower is better: prefer seats-together wording, then lower price."""
    f = config.get("filters", {})
    text = (available.get("raw_text") or available.get("section") or "").lower()
    together_rank = 0
    if f.get("seats_together"):
        if any(x in text for x in ("together", "adjacent")):
            together_rank = 0
        else:
            together_rank = 1
    price = available.get("price")
    price_rank = price if price is not None else 999999.0
    return (together_rank, price_rank)
