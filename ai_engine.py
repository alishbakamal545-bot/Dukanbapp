"""Dukan AI - AI Engine (Optimized for Gemini 3.6 Flash)
Dedicated for smooth AI Chat & inventory advice without rate-limit issues.
"""
from typing import Optional
import time
import config
import database

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

_client = None

# Single official standard model for AI engine
PRIMARY_MODEL = "gemini-3.6-flash"


def _init_gemini():
    global _client
    if genai is None or not config.GEMINI_API_KEY:
        return None
    _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def get_client():
    global _client
    if _client is None:
        _client = _init_gemini()
    return _client


def _system_prompt() -> str:
    return """You are Dukan AI (دکان اے آئی), a smart shop assistant built for small Pakistani shopkeepers.
Rules:
- Keep answers VERY SHORT, PRACTICAL, and DIRECT.
- Always show PKR amounts with 'Rs.'.
- Answer in Roman Urdu if the user writes in Roman Urdu or English.
- Be friendly, encouraging, and clear like a digital clerk (munshi)."""


def _build_context() -> str:
    """Build a lightweight inventory context to prevent huge prompts and 429/404 errors."""
    try:
        df = database.get_all_products()
    except Exception:
        return "(Inventory unavailable)"

    if df.empty:
        return "(Inventory empty)"

    # Limit inventory context to top 20 items to keep requests fast & lightweight
    lines = ["Shop Inventory Summary:"]
    for _, row in df.head(20).iterrows():
        lines.append(
            f"- {row['name']}: {row['quantity']} {row['unit']} left | Cost: Rs.{row['cost_price']} | Sell: Rs.{row['sell_price']}"
        )

    alerts = database.get_low_stock_alerts()
    if alerts:
        lines.append("\nLow Stock Alerts:")
        for a in alerts[:5]:
            lines.append(f"- {a['name']}: only {a['quantity']} left")

    return "\n".join(lines)


def _generate_content_safe(prompt: str) -> str:
    client = get_client()
    if client is None:
        return "⚠ Gemini API key is not configured. Streamlit secrets check karein."

    try:
        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=prompt,
        )
        if response and response.text:
            return response.text
        return "⚠ Empty response from AI."
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return "⚠ AI Request limit hit ho gayi hai. Please 30 seconds baad dobara message karein."
        return f"⚠ AI Error: {err_msg}"


def chat(user_message: str) -> str:
    """Optimized direct AI Chat without infinite recursion or heavy token overload."""
    prompt = f"{_system_prompt()}\n\n{_build_context()}\n\nUser Question: {user_message}"
    return _generate_content_safe(prompt)


def suggest_price(product_name: str, cost_price: float, margin_pct: float = None) -> str:
    margin = margin_pct if margin_pct is not None else 15
    prompt = (
        f"{_system_prompt()}\n\n"
        f"Product '{product_name}' ki cost price Rs.{cost_price} hai. "
        f"Mujhe {margin}% profit margin chahiye. Recommended selling price aur choti calculation batayein."
    )
    return _generate_content_safe(prompt)


def analyze_stock_image(detections: list[dict]) -> str:
    if not detections:
        return "Photo mein koi item detect nahi hua."

    det_str = ", ".join(f"{d['label']}: {d['count']}" for d in detections)
    prompt = (
        f"{_system_prompt()}\n\n"
        f"Shelf photo detection: {det_str}. Matches and inventory advice batayein."
    )
    return _generate_content_safe(prompt)


def daily_summary() -> str:
    stats = database.get_dashboard_stats()
    prompt = (
        f"{_system_prompt()}\n\n"
        f"Daily Shop Stats: Sales Today: Rs.{stats['sales_today']}, "
        f"Total Products: {stats['total_products']}, Low Stock Items: {stats['low_stock_count']}. "
        f"Give 2-3 quick actionable shop tips."
    )
    return _generate_content_safe(prompt)
