from __future__ import annotations

import io
import re
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

try:
    from .rag import retrieve_guidance
except ImportError:
    from rag import retrieve_guidance

try:
    import pytesseract
except ImportError:
    pytesseract = None

app = FastAPI(title="VeriScan API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 7, 9, 0, 6, 2, 5, 3, 1, 4),
    (9, 4, 3, 8, 2, 1, 6, 5, 7, 0),
    (4, 2, 8, 6, 1, 7, 5, 0, 9, 3),
    (2, 8, 6, 3, 0, 5, 9, 1, 4, 7),
    (6, 3, 5, 1, 9, 8, 7, 4, 0, 2),
    (1, 5, 7, 2, 0, 9, 3, 8, 6, 4),
    (5, 7, 0, 9, 3, 4, 8, 6, 1, 2),
)
VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (0, 5, 7, 6, 2, 8, 3, 9, 4, 1),
    (0, 8, 6, 3, 7, 9, 2, 5, 1, 4),
    (0, 9, 5, 2, 8, 6, 3, 7, 4, 1),
    (0, 4, 2, 7, 9, 3, 8, 6, 1, 5),
    (0, 2, 9, 6, 4, 8, 1, 3, 5, 7),
    (0, 1, 8, 9, 5, 7, 4, 2, 6, 3),
    (0, 5, 4, 8, 6, 3, 7, 9, 2, 1),
)
ALLOWED_DOCUMENT_CATEGORIES = {
    "Aadhaar", "PAN", "Passport", "Birth Certificate", "Driving Licence",
    "Visa", "SSN", "ID/Driving Licence", "Health Insurance", "Visa/eVisa",
    "National Insurance Number", "ID", "Health/NHS", "TFN", "Medicare/Insurance",
    "Residence Visa", "Emirates ID", "Visa/Pass", "FIN", "Visa/Permit", "SIN",
    "Health Card",
}


def verhoeff_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 12:
        return False
    checksum = 0
    for position, digit in enumerate(reversed(digits)):
        checksum = VERHOEFF_D[checksum][VERHOEFF_P[position % 8][int(digit)]]
    return checksum == 0


def result(name: str, status: str, detail: str, points: int = 0) -> dict[str, Any]:
    return {"name": name, "status": status, "detail": detail, "points": points}


def preprocess(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)


def extract_text(image: np.ndarray) -> tuple[str, str]:
    prepared = preprocess(image)
    if pytesseract is None:
        return "", "OCR unavailable: install Tesseract and pytesseract to enable extraction."
    try:
        text = pytesseract.image_to_string(prepared, config="--psm 6")
        return text, "OCR text extracted after denoise, contrast enhancement, and grayscale conversion."
    except Exception as exc:
        return "", f"OCR inconclusive: {exc}"


def decode_qr(image: np.ndarray) -> tuple[str | None, str]:
    detector = cv2.QRCodeDetector()
    value, _, _ = detector.detectAndDecode(image)
    if value:
        return value, "QR payload decoded by OpenCV QRCodeDetector."
    return None, "No readable QR code found; this is inconclusive rather than proof of tampering."


def ela_scan(image_bytes: bytes, image: np.ndarray, image_format: str) -> tuple[dict[str, Any], np.ndarray | None]:
    if image_format.upper() not in {"JPEG", "JPG"}:
        return result("Error level analysis", "inconclusive", "ELA confidence is reduced for PNG/lossless input; copy-move and metadata signals carry more weight.", 0), None
    source = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    recompressed = io.BytesIO()
    sobre_quality = 85
    source.save(recompressed, format="JPEG", quality=sobre_quality)
    reference = np.asarray(source, dtype=np.int16)
    comparison = np.asarray(Image.open(io.BytesIO(recompressed.getvalue())).convert("RGB"), dtype=np.int16)
    diff = np.abs(reference - comparison).mean(axis=2)
    anomaly = float(np.percentile(diff, 99))
    heatmap = np.uint8(np.clip(diff * 8, 0, 255))
    points = 15 if anomaly > 35 else 0
    status = "review" if points else "pass"
    return result("Error level analysis", status, f"JPEG quality {sobre_quality}; high-percentile difference {anomaly:.1f}.", points), heatmap


def copy_move_scan(image: np.ndarray) -> dict[str, Any]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1200)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    if descriptors is None or len(keypoints) < 12:
        return result("Copy-move detection", "inconclusive", "Not enough stable keypoints for a reliable duplicate-region comparison.", 0)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(descriptors, descriptors, k=2)
    duplicate_pairs = [pair for pair in pairs if len(pair) == 2 and pair[0].trainIdx != pair[0].queryIdx and pair[0].distance < 0.6 * pair[1].distance]
    points = 20 if len(duplicate_pairs) >= 8 else 0
    status = "review" if points else "pass"
    return result("Copy-move detection", status, f"{len(keypoints)} keypoints examined; {len(duplicate_pairs)} duplicate-like matches.", points)


def score_checks(checks: list[dict[str, Any]]) -> tuple[int, str]:
    score = min(100, max(0, sum(int(check["points"]) for check in checks)))
    label = "low review signal" if score < 25 else "review recommended" if score < 60 else "high review signal"
    return score, label


def parse_fields(text: str) -> dict[str, str | None]:
    pan = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text.upper())
    aadhaar = re.search(r"\b(?:\d[ -]?){12}\b", text)
    return {"pan": pan.group(0) if pan else None, "aadhaar": re.sub(r"\D", "", aadhaar.group(0)) if aadhaar else None}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "veriscan-api"}


@app.get("/api/specimen.svg")
def specimen() -> StreamingResponse:
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760"><rect width="1200" height="760" fill="#f5f0e7"/><rect x="36" y="36" width="1128" height="688" rx="24" fill="#fffdf7" stroke="#263a35" stroke-width="5"/><text x="78" y="110" font-family="sans-serif" font-size="24" fill="#6d7d75">FICTIONAL CIVIC REGISTRY</text><text x="78" y="170" font-family="sans-serif" font-weight="bold" font-size="58" fill="#142822">SPECIMEN ID</text><rect x="78" y="220" width="224" height="286" fill="#d8e2dc" stroke="#263a35" stroke-width="4"/><circle cx="190" cy="315" r="56" fill="#91aaa0"/><path d="M110 470 Q190 380 270 470" fill="#91aaa0"/><text x="350" y="280" font-family="sans-serif" font-size="22" fill="#6d7d75">REGISTERED NAME</text><text x="350" y="322" font-family="sans-serif" font-weight="bold" font-size="34" fill="#142822">ALEX SAMPLE</text><text x="350" y="390" font-family="sans-serif" font-size="22" fill="#6d7d75">REFERENCE NUMBER</text><text x="350" y="432" font-family="monospace" font-size="32" fill="#142822">TEST-0000-0000</text><text x="350" y="500" font-family="sans-serif" font-size="22" fill="#6d7d75">ISSUER</text><text x="350" y="540" font-family="sans-serif" font-size="28" fill="#142822">Northstar Civic Lab</text><text x="600" y="620" transform="rotate(-22 600 620)" font-family="sans-serif" font-weight="bold" font-size="100" fill="#d1a45f" opacity=".35">SPECIMEN</text><rect x="980" y="560" width="112" height="112" fill="#d8e2dc"/><path d="M990 580h28v28h-28zm40 0h28v28h-28zm-40 40h28v28h-28zm40 0h10v10h-10zm18 18h10v10h-10z" fill="#263a35"/></svg>'''
    return StreamingResponse(io.BytesIO(svg.encode()), media_type="image/svg+xml")


@app.get("/api/specimen.png")
def specimen_png() -> StreamingResponse:
    image = Image.new("RGB", (1200, 760), "#f5f0e7")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((36, 36, 1164, 724), radius=24, fill="#fffdf7", outline="#263a35", width=5)
    draw.text((78, 92), "FICTIONAL CIVIC REGISTRY", fill="#6d7d75")
    draw.text((78, 140), "SPECIMEN ID", fill="#142822", stroke_width=1)
    draw.rectangle((78, 220, 302, 506), fill="#d8e2dc", outline="#263a35", width=4)
    draw.ellipse((134, 260, 246, 372), fill="#91aaa0")
    draw.arc((110, 350, 270, 500), 180, 360, fill="#91aaa0", width=22)
    draw.text((350, 248), "REGISTERED NAME", fill="#6d7d75")
    draw.text((350, 292), "ALEX SAMPLE", fill="#142822")
    draw.text((350, 370), "REFERENCE NUMBER", fill="#6d7d75")
    draw.text((350, 414), "TEST-0000-0000", fill="#142822")
    draw.text((350, 490), "ISSUER", fill="#6d7d75")
    draw.text((350, 534), "Northstar Civic Lab", fill="#142822")
    draw.text((600, 620), "SPECIMEN", fill="#d1a45f", stroke_width=2, stroke_fill="#d1a45f")
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return StreamingResponse(output, media_type="image/png")


@app.post("/api/scan")
async def scan(
    file: UploadFile = File(...),
    country: str | None = Form(None),
    document_category: str | None = Form(None),
) -> dict[str, Any]:
    started = time.perf_counter()
    if document_category not in ALLOWED_DOCUMENT_CATEGORIES:
        raise HTTPException(422, "Select a supported country and document category before screening.")
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(415, "Upload a JPEG or PNG document image.")
    content = await file.read()
    try:
        pil_image = Image.open(io.BytesIO(content))
        pil_image.verify()
        image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Unreadable image")
        width, height = pil_image.size
        if width < 500 or height < 300:
            raise HTTPException(422, "Image resolution is too low for reliable screening. Use at least 500 x 300 pixels.")
        if cv2.Laplacian(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < 35:
            raise HTTPException(422, "Image is too blurry for reliable screening. Use a sharper document image.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, f"Unreadable image: {exc}") from exc

    checks: list[dict[str, Any]] = []
    text, ocr_detail = extract_text(image)
    fields = parse_fields(text)
    checks.append(result("OCR extraction", "pass" if text else "inconclusive", ocr_detail, 0))
    if fields["aadhaar"]:
        valid = verhoeff_valid(fields["aadhaar"])
        checks.append(result("Aadhaar-style checksum", "pass" if valid else "review", "Verhoeff checksum " + ("valid." if valid else "did not validate."), 0 if valid else 25))
    if fields["pan"]:
        valid = bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", fields["pan"]))
        checks.append(result("PAN-style format", "pass" if valid else "review", "PAN format " + ("matches the documented pattern." if valid else "does not match."), 0 if valid else 20))
    if not fields["aadhaar"] and not fields["pan"]:
        checks.append(result("Identity number validation", "inconclusive", "No Aadhaar-style or PAN-style number was confidently extracted; this is neutral for certificates, marks cards, passports, licences, ration cards, and passbooks.", 0))

    qr_value, qr_detail = decode_qr(image)
    qr_mismatch = bool(qr_value and text and not all(token.lower() in text.lower() for token in qr_value.split("|") if token.strip()))
    checks.append(result("QR decode and cross-check", "review" if qr_mismatch else "pass" if qr_value else "inconclusive", "QR payload conflicts with OCR text." if qr_mismatch else qr_detail, 20 if qr_mismatch else 0))
    ela, _ = ela_scan(content, image, pil_image.format or "")
    checks.append(ela)
    checks.append(copy_move_scan(image))
    retrieved_guidance = retrieve_guidance(country, document_category, checks)
    score, label = score_checks(checks)
    return {"filename": file.filename, "country": country, "document_category": document_category, "dimensions": {"width": width, "height": height}, "score": score, "label": label, "extracted_text": text[:4000], "fields": fields, "qr_payload": qr_value, "checks": checks, "retrieved_guidance": retrieved_guidance, "elapsed_ms": round((time.perf_counter() - started) * 1000, 1), "limitations": ["This is decision support for a human verifier, not an automated authenticity verdict.", "A low score means fewer detected review signals; it does not prove the document is genuine.", "ELA confidence is reduced for PNG/lossless input.", "No accuracy percentage is claimed because no public labelled fake-vs-genuine dataset exists."]}
