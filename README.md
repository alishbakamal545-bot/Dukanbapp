# Dukan AI — Digital Munshi

A Streamlit prototype for small Pakistani shops.

## Files

- `app.py` — Streamlit UI
- `config.py` — configuration
- `database.py` — SQLite stock/sales database
- `ai_engine.py` — Gemini integration
- `stock_counter.py` — YOLO object detection
- `voice_assistant.py` — speech input + Urdu TTS
- `utils.py` — helper functions

## Run on Windows

1. Open a terminal in this folder.
2. Create a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create `.env`:

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

5. Start the app:

```bash
streamlit run app.py
```

The app opens in your browser.

## Notes

- The SQLite database `dukan.db` is created automatically.
- YOLO downloads `yolov8n.pt` the first time the Photo Counter is used.
- Voice input needs a working microphone and a compatible PyAudio installation.
- The stock-photo feature uses a general YOLO model. It can detect common object
  classes, but it is NOT a custom grocery-product model, so product-level counting
  (e.g. distinguishing every rice/sugar brand) will require a custom-trained model.
