# VeriScan

VeriScan is a prototype decision-support tool for Smart India Hackathon problem SIH26188, built by VISIONARY6. It screens document images and returns an explainable 0-100 review score. It does not replace a human verifier and never claims that an image is definitively real or fake.

The upload workflow accepts JPEG/PNG images labelled as fictional specimens, non-Indian MIDV mock IDs, or other document images. Do not upload real government IDs. A score such as `5/100` means that few review signals were detected; it is a low review signal, not proof that the document is genuine.

## Architecture

- `backend/main.py`: FastAPI service. Upload validation, OpenCV preprocessing, Tesseract OCR, Verhoeff and PAN-style checks, OpenCV QR decoding, JPEG ELA, ORB copy-move analysis, local RAG retrieval, and transparent weighted scoring.
- `backend/rag.py`: Offline retrieval knowledge base. It ranks country/document and forensic guidance using deterministic keyword matching; no uploaded image or OCR text leaves the application.
- `frontend`: Vite + React dashboard. It shows the input, score, each check's status/reason, OCR extract, measured elapsed time, and limitations.
- `sample_documents/`: safe specimen guidance. The API exposes a fictional `SPECIMEN` PNG and SVG; no government-ID-like image is included.

## Run locally

Backend (Python 3.10+):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Install the Tesseract executable separately and ensure it is on `PATH` for OCR. The rest of the pipeline remains usable when Tesseract is unavailable, and OCR is reported as inconclusive.

Frontend (Node.js 18+):

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`. The frontend expects the API at `http://localhost:8000`; set `VITE_API_URL` when the API is hosted elsewhere.

## The six stages

1. **Upload:** accepts JPEG/PNG, verifies decoding, minimum dimensions, and blur using Laplacian variance. The UI includes a clearly labelled fictional SPECIMEN PNG.
2. **OCR extraction:** converts to grayscale, denoises, boosts local contrast, then calls Tesseract when installed.
3. **Checksum validation:** applies a real Verhoeff checksum to extracted 12-digit values and a real PAN-style regex to matching values.
4. **QR decode:** uses OpenCV's QR detector and compares decoded pipe-delimited tokens with OCR text.
5. **Forensics:** JPEG inputs receive recompression-based ELA; ORB descriptors search for duplicate-like regions. PNG ELA is explicitly inconclusive because it is lossless.
6. **Scoring:** check points are summed and clamped to 0-100. Every point-bearing signal is listed in the dashboard.

## RAG guidance

After the OCR, checksum, QR, ELA, and copy-move checks run, VeriScan retrieves up to three relevant guidance entries from the bundled knowledge base. Retrieval uses the selected country, document type, and detected check terms. The dashboard labels these entries `LOCAL RAG · HUMAN REVIEW` and shows their source, match score, and recommended review action. This layer provides context for a human verifier; it does not decide whether a document is authentic.

## Limitations

- **ELA is JPEG-specific.** If the uploaded file is PNG or otherwise lossless, show a message that ELA confidence is reduced for this format, and lean more heavily on copy-move detection and file-metadata checks instead of silently running a meaningless ELA pass. Inconclusive checks are neutral and do not add risk points.
- **No labelled fake-vs-genuine dataset exists publicly.** Don't fabricate an accuracy percentage anywhere in the UI or docs (no "99% accurate" claims). If you display a confidence figure, it must come from the actual weighted-scoring logic you implement, not an invented number.
- **Do not hardcode or claim a specific processing-time benchmark** (e.g. "under 2 seconds") unless the build actually measures and displays real elapsed time per scan.
- **Stretch goal, not required for MVP:** a Moiré-pattern detection filter (frequency-domain analysis in OpenCV) to catch screen-recapture spoofing (someone photographing a screen instead of the physical document). Mention it as a "Coming soon" item in the UI if not implemented, rather than skipping it silently.

## Deployment

Docker is not required for local use. Deploy the FastAPI service and static Vite build to any Python/Node-compatible host, set the frontend `VITE_API_URL` to the public API origin, and configure CORS for the deployed frontend origin. No paid or proprietary API is used.
