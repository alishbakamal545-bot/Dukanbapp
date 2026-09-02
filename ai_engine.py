"""Dukan AI - AI Engine
Gemini-powered chat, pricing advice, and stock analysis with automatic retries and fallback models.
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

# Fallback Models list (agar high demand error 503 aaye to agle model par switch karega)
MODELS_TO_TRY = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]


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
    return """You are Dukan AI (دکان اے آئی), a smart shop assistant built for
small Pakistani shopkeepers (kiryana, clothes, mobile shops, etc.).

Your abilities:
1. STOCK ADVICE – tell the shopkeeper about low stock, overstock, and what to
   reorder based on current inventory data.
2. PRICING ADVICE – suggest a selling price given cost price and desired margin.
   Always give prices in PKR. Do not invent live market prices unless the user
   provides them.
3. BUSINESS INSIGHTS – give simple, actionable business tips.
4. URDU SUPPORT – reply in Roman Urdu if the user writes in Roman Urdu,
   otherwise reply in English.

Rules:
- Keep answers SHORT and PRACTICAL.
- Always show PKR amounts with Rs.
- Never give financial advice beyond basic margin calculations.
- Be friendly and encouraging like a helpful munshi (clerk).
- If unrelated to shop management, politely redirect."""


def _build_context() -> str:
    try:
        df = database.get_all_products()
    except Exception:
        return "(Shop database not available yet.)"

    if df.empty:
        return "(Shop has no products yet.)"

    lines = ["Current Shop Inventory:"]
    for _, row in df.iterrows():
        lines.append(
            f"- {row['name']} ({row['name_urdu'] or ''}): "
            f"qty={row['quantity']} {row['unit']}, "
            f"cost=Rs.{row['cost_price']}, sell=Rs.{row['sell_price']}, "
            f"category={row['category']}"
        )

    alerts = database.get_low_stock_alerts()
    if alerts:
        lines.append("\n⚠ Low Stock Alerts:")
        for a in alerts:
            lines.append(
                f"- {a['name']} ({a['name_urdu'] or ''}): "
                f"only {a['quantity']} {a['unit']} left"
            )
    return "\n".join(lines)


def _generate_content_safe(prompt: str) -> str:
    """Auto-retry on 503 high-demand errors and fallback across Gemini models."""
    client = get_client()
    if client is None:
        return (
            "⚠ Gemini API key is not configured. Add GEMINI_API_KEY to your "
            ".env file or enter it in the sidebar."
        )

    last_error = None

    # Try configured model first if specified, followed by fallback list
    models_sequence = []
    if hasattr(config, "GEMINI_MODEL") and config.GEMINI_MODEL:
        models_sequence.append(config.GEMINI_MODEL)
    
    for m in MODELS_TO_TRY:
        if m not in models_sequence:
            models_sequence.append(m)

    for model_name in models_sequence:
        for attempt in range(2):  # Try 2 times per model
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                err_msg = str(e)
                last_error = e
                # Check for 503 / high demand or temporarily unavailable errors
                if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg.lower():
                    time.sleep(1.5 * (attempt + 1))  # Brief pause before retrying
                    continue
                elif "404" in err_msg or "NOT_FOUND" in err_msg:
                    # If model not found or deprecated, immediately switch to next model
                    break
                else:
                    return f"⚠ AI Error: {e}\n\nPlease check your API key and internet connection."

    return f"⚠ AI Error: Gemini servers are currently under high demand. Details: {last_error}"


def chat(user_message: str) -> str:
    prompt = f"{_system_prompt()}\n\n{_build_context()}\n\nUser Question: {user_message}"
    return _generate_content_safe(prompt)


def suggest_price(product_name: str, cost_price: float, margin_pct: float = None) -> str:
    margin = margin_pct if margin_pct is not None else getattr(config, "DEFAULT_PROFIT_MARGIN_PCT", 15)
    prompt = (
        f"I have a product '{product_name}' that costs me Rs.{cost_price}. "
        f"I want around {margin}% profit. Calculate a sensible selling price "
        f"and explain the calculation briefly. Do not claim to know a live market "
        f"rate unless I provide one."
    )
    return chat(prompt)


def analyze_stock_image(detections: list[dict]) -> str:
    if not detections:
        return "I couldn't detect any items in the image. Try a clearer, well-lit photo."

    det_str = ", ".join(f"{d['label']}: {d['count']}" for d in detections)
    prompt = (
        f"A shelf photo detected these items: {det_str}. "
        "Match them to the current inventory if possible and tell me what stock "
        "updates or reorder actions I should consider."
    )
    return chat(prompt)


def daily_summary() -> str:
    stats = database.get_dashboard_stats()
    prompt = (
        f"Give me a quick daily shop summary. Today's sales: Rs.{stats['sales_today']}, "
        f"Total products: {stats['total_products']}, "
        f"Low stock items: {stats['low_stock_count']}, "
        f"Total stock value: Rs.{stats['stock_value']}. "
        "Give 2-3 actionable tips."
    )
    return chat(prompt)
