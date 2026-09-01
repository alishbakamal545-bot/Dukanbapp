"""Dukan AI - Utilities"""
import re
from datetime import datetime
import config


def format_pkr(amount: float) -> str:
    if amount >= 100000:
        return f"Rs. {amount:,.0f}"
    return f"Rs. {amount:,.2f}" if amount != int(amount) else f"Rs. {int(amount):,}"


def stock_level_badge(quantity: float, max_stock: float) -> tuple[str, str]:
    if max_stock <= 0:
        return ("N/A", "grey")
    pct = (quantity / max_stock) * 100
    if pct <= 10:
        return ("Critical", "red")
    if pct <= config.LOW_STOCK_THRESHOLD_PCT:
        return ("Low", "orange")
    if pct >= 90:
        return ("Full", "green")
    return ("OK", "green")


def profit_margin(cost: float, sell: float) -> float:
    if cost <= 0:
        return 0.0
    return ((sell - cost) / cost) * 100


def parse_voice_command(text: str) -> dict:
    text = text.lower().strip()

    sell_match = re.match(
        r"(?:sell|bech|becho)\s+(\d+(?:\.\d+)?)\s*(kg|ltr|pcs|piece|dozen)?\s*(.*)",
        text,
    )
    if sell_match:
        return {
            "action": "sell",
            "quantity": float(sell_match.group(1)),
            "unit": sell_match.group(2) or "pcs",
            "product": sell_match.group(3).strip(),
        }

    stock_match = re.match(
        r"(?:how much|kitna|kitni|ktna|ktni)\s+(.*?)\s+(?:left|baki|hai|baccha)",
        text,
    )
    if stock_match:
        return {"action": "query", "product": stock_match.group(1).strip()}

    price_match = re.match(
        r"(?:price|rate|qeemat|kya rate)\s+(?:of|ka|ki)?\s*(.*)",
        text,
    )
    if price_match:
        return {"action": "price_query", "product": price_match.group(1).strip()}

    restock_match = re.match(
        r"(?:restock|add|lao|mangwa)\s+(\d+(?:\.\d+)?)\s*(kg|ltr|pcs|piece|dozen)?\s*(.*)",
        text,
    )
    if restock_match:
        return {
            "action": "restock",
            "quantity": float(restock_match.group(1)),
            "unit": restock_match.group(2) or "pcs",
            "product": restock_match.group(3).strip(),
        }

    return {"action": "chat", "message": text}


def time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Assalam-o-Alaikum! Subah bakhair ☀️"
    if hour < 17:
        return "Assalam-o-Alaikum! Dopahar bakhair 🌤️"
    if hour < 21:
        return "Assalam-o-Alaikum! Shaam bakhair 🌆"
    return "Assalam-o-Alaikum! Raat bakhair 🌙"
