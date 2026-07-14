"""Isolation test for local OCR via rapidocr-onnxruntime."""
import io
from PIL import Image, ImageDraw, ImageFont
import numpy as np

SCAM = [
    "URGENT: This is CBI Officer Sharma.",
    "A parcel in your name has illegal drugs.",
    "You are under DIGITAL ARREST.",
    "Transfer Rs 250000 to UPI cbi.verify@okhdfc",
    "or share the OTP now to avoid arrest.",
]

def make_image() -> bytes:
    img = Image.new("RGB", (900, 360), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
    y = 30
    for line in SCAM:
        d.text((30, y), line, fill="black", font=font)
        y += 60
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def main():
    img_bytes = make_image()
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    arr = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
    result, elapse = engine(arr)
    print("RAW RESULT:")
    texts = []
    confs = []
    for box, text, conf in (result or []):
        print(f"  conf={conf:.3f}  text={text!r}")
        texts.append(text)
        confs.append(float(conf))
    joined = " ".join(texts)
    avg = sum(confs) / len(confs) if confs else 0.0
    print("\nJOINED TEXT:", joined)
    print("AVG CONF:", round(avg, 3))

if __name__ == "__main__":
    main()
