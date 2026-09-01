"""Dukan AI - Stock Counter
Uses Ultralytics YOLO for object detection and counting.
"""
from collections import Counter
from PIL import Image
import config

_model = None


def _load_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO(config.YOLO_MODEL)
    return _model


def detect_items(image: Image.Image) -> list[dict]:
    model = _load_model()
    results = model(image, conf=config.YOLO_CONFIDENCE, verbose=False)
    detections = []

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].tolist()
            detections.append({
                "label": label,
                "confidence": round(confidence, 2),
                "box": [round(v, 1) for v in bbox],
            })
    return detections


def count_items(detections: list[dict]) -> list[dict]:
    counter = Counter(d["label"] for d in detections)
    return [{"label": label, "count": count}
            for label, count in counter.most_common()]


def get_annotated_image(image: Image.Image) -> Image.Image:
    model = _load_model()
    results = model(image, conf=config.YOLO_CONFIDENCE, verbose=False)
    annotated = results[0].plot()
    # Ultralytics returns BGR; convert to RGB for PIL/Streamlit.
    from PIL import Image as PILImage
    return PILImage.fromarray(annotated[:, :, ::-1])


def match_detections_to_products(counts: list[dict], products_df) -> list[dict]:
    matches = []
    yolo_products = products_df[products_df["yolo_label"].notna()].copy()

    for item in counts:
        label = item["label"].lower()
        matching = yolo_products[
            yolo_products["yolo_label"].str.lower() == label
        ]
        for _, product in matching.iterrows():
            matches.append({
                "product_id": int(product["id"]),
                "product_name": product["name"],
                "yolo_label": label,
                "detected_count": item["count"],
                "current_stock": product["quantity"],
                "unit": product["unit"],
                "action": (
                    f"Update stock from {product['quantity']} to "
                    f"{item['count']} {product['unit']}"
                ),
            })
    return matches


def full_analysis(image: Image.Image) -> dict:
    detections = detect_items(image)
    counts = count_items(detections)
    annotated = get_annotated_image(image)

    import database
    try:
        df = database.get_all_products()
        known_labels = set(
            df["yolo_label"].dropna().str.lower().unique()
        )
    except Exception:
        known_labels = set()

    unmatched = [
        c["label"] for c in counts
        if c["label"].lower() not in known_labels
    ]

    return {
        "detections": detections,
        "counts": counts,
        "annotated_image": annotated,
        "unmatched_labels": unmatched,
    }
