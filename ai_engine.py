"""Dukan AI - AI Engine
Gemini-powered chat, pricing advice, and stock analysis.
"""
from typing import Optional
import config
import database

try:
    from google import genai
except ImportError:
    genai = None

_client = None


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


def chat(user_message: str) -> str:
    client = get_client()
    if client is None:
        return (
            "⚠ Gemini API key is not configured. Add GEMINI_API_KEY to your "
            ".env file or enter it in the sidebar."
        )

    prompt = f"{_system_prompt()}\n\n{_build_context()}\n\nUser Question: {user_message}"
    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
        )
        return response.text or "I couldn't generate a response."
    except Exception as e:
        return f"⚠ AI Error: {e}\n\nPlease check your API key and internet connection."


def suggest_price(product_name: str, cost_price: float, margin_pct: float = None) -> str:
    margin = margin_pct if margin_pct is not None else config.DEFAULT_PROFIT_MARGIN_PCT
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
