"""Dukan AI - Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

DB_PATH = "dukan.db"

LOW_STOCK_THRESHOLD_PCT = 20
DEFAULT_PROFIT_MARGIN_PCT = 15

VOICE_LANG = "ur"
VOICE_SLOW = False

YOLO_MODEL = "yolov8n.pt"
YOLO_CONFIDENCE = 0.40

SHOP_NAME = "Meri Dukan"
CURRENCY = "PKR"
