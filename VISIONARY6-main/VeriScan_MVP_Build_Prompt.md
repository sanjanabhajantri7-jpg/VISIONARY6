# Build Prompt: VeriScan — AI-Based Fake Identity & Document Screening System

Copy everything below the line into Claude Code, Claude Cowork, or any coding agent that can write, run, and deploy a project. It is self-contained — the agent does not need the original PPTX/DOCX to build from it.

---

## Project Identity

Build **VeriScan**, a working web-based prototype (MVP) for Smart India Hackathon problem statement **SIH26188 — "AI-Based Fake Identity & Document Screening System,"** sponsored by the Ministry of Home Affairs (theme: Miscellaneous, category: Software). Team name: **VISIONARY6**. The system screens identity-document images (Aadhaar, PAN, driving licence, passport) and returns an **explainable 0–100 risk score** — never a bare "real/fake" label.

## Core Pipeline (implement all six stages, in this order)

1. **Upload** — web form accepts a document image (JPEG/PNG). Reject files that are unreadable, extremely low-resolution, or too blurry, with a clear error message before running the rest of the pipeline.
2. **OCR Extraction** — use Tesseract (`pytesseract`) or EasyOCR to pull text fields (name, ID number, DOB, address). Pre-process with OpenCV first: deskew, denoise, boost contrast.
3. **Checksum Validation** — implement the **Verhoeff algorithm** to validate Aadhaar-style numbers, and a regex rule (`[A-Z]{5}[0-9]{4}[A-Z]`) for PAN-style numbers. This must run as real, working code, not a stub.
4. **QR Decode** — use `pyzbar` (or OpenCV's QR detector) to decode any embedded QR code and cross-check its payload against the OCR-extracted text. Flag any mismatch.
5. **Forensic Scan** — implement two real, working techniques:
   - **Error Level Analysis (ELA)**: re-compress the image at a known JPEG quality and diff against the original to surface regions with inconsistent compression history.
   - **Copy-move detection**: SIFT or ORB keypoint matching (OpenCV) to flag duplicated regions within the same image.
6. **Risk Scoring & Dashboard** — combine every signal from stages 3–5 into one weighted 0–100 score (`scikit-learn` or straightforward weighted-sum logic is fine for an MVP). The dashboard must show **the specific reasons behind the score** (e.g. "QR mismatch on DOB," "ELA anomaly in photograph region") — never just a number or a yes/no.

## Tech Stack (use exactly this — it's what's documented and pitched)

- **Backend:** Python, FastAPI
- **OCR/CV:** Tesseract or EasyOCR, OpenCV, PIL, pyzbar
- **Scoring:** scikit-learn (or transparent weighted-sum logic if a trained model is out of scope for an MVP)
- **Frontend:** React, calling the FastAPI backend
- **No paid or proprietary APIs anywhere in the pipeline** — this is a stated design principle (zero licensing cost), not a budget suggestion.

## Critical Constraint — Test Data (read carefully)

**Do not generate, fetch, or embed any image resembling a real Aadhaar card, PAN card, Indian driving licence, or Indian passport** — real or fabricated-but-realistic. This applies to seed/demo data too. Instead:

- Build the demo using **clearly-labeled synthetic "SPECIMEN" documents**: a fictional format, a large diagonal "SPECIMEN" watermark, placeholder photo, obviously fake numbers (e.g. `TEST-0000-0000`), and a fictional issuing authority name.
- Optionally support loading test images from the **MIDV-500 / MIDV-2020** dataset structure (non-Indian mock ID documents, publicly distributable) for OCR/field-extraction testing — but don't attempt to download it automatically from `smartengines.com`'s FTP server inside the build (that host is typically unreachable from sandboxed build environments); instead, add a `sample_documents/README.md` explaining how a user can drop their own MIDV-500 files into a folder for local testing.
- Add a visible banner on the live site: **"Demo mode — do not upload real government ID documents. Use the provided SPECIMEN samples."**

## Known, Documented Limitations — Build These In Honestly

- **ELA is JPEG-specific.** If the uploaded file is PNG or otherwise lossless, show a message that ELA confidence is reduced for this format, and lean more heavily on copy-move detection and file-metadata checks instead of silently running a meaningless ELA pass.
- **No labelled fake-vs-genuine dataset exists publicly.** Don't fabricate an accuracy percentage anywhere in the UI or docs (no "99% accurate" claims). If you display a confidence figure, it must come from the actual weighted-scoring logic you implement, not an invented number.
- **Do not hardcode or claim a specific processing-time benchmark** (e.g. "under 2 seconds") unless the build actually measures and displays real elapsed time per scan.
- **Stretch goal, not required for MVP:** a Moiré-pattern detection filter (frequency-domain analysis in OpenCV) to catch screen-recapture spoofing (someone photographing a screen instead of the physical document). Mention it as a "Coming soon" item in the UI if not implemented, rather than skipping it silently.

## Deliverable

1. A working full-stack app (FastAPI backend + React frontend) implementing all six pipeline stages with real, functioning code — not mocked responses.
2. A results dashboard showing: the uploaded image, the 0–100 risk score, and an itemized breakdown of every check performed and whether it passed, failed, or was inconclusive.
3. A small set of bundled SPECIMEN sample documents (per the constraint above) so the site is demoable immediately without needing a real ID.
4. Deploy it and give me a **live, shareable link** I can open in a browser. If your environment supports one-command deploy (e.g. to a free hosting tier), use it; otherwise give me exact local run instructions (`docker compose up`, or equivalent) plus a note on what's needed to deploy it publicly.
5. A short `README.md` covering: architecture overview, how each of the six stages works, how to run it, and the limitations section above verbatim (judges and reviewers should see the same honest caveats documented in the project's research paper).

## Tone/Framing for any UI copy or README text

Match the project's actual positioning: a **decision-support tool for a human verifier**, not an automated fraud-detector that replaces human judgment. Every place the UI would be tempted to say "FAKE" or "GENUINE," say instead something like "Risk Score: 68/100 — review recommended" with the reasons listed.

---
*This prompt is derived from Team VISIONARY6's SIH26188 research paper and pitch deck. All technical claims above (algorithms, tech stack, limitations) are drawn directly from that documentation — build to match it, don't invent additional capabilities beyond what's listed here.*
