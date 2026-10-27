"""Small, transparent retrieval layer for verifier guidance.

This is intentionally local and deterministic for the MVP: no document images,
OCR text, or personal data are sent to an external model or vector database.
"""

from __future__ import annotations

import re
from typing import Any

KNOWLEDGE_BASE = [
    {
        "title": "Human review principle",
        "source": "VeriScan verification guidance",
        "countries": set(),
        "documents": set(),
        "terms": {"review", "human", "risk", "score"},
        "guidance": "Treat the score as a triage signal. Confirm identity, document ownership, and issuer records through an authorized human workflow.",
    },
    {
        "title": "India document checks",
        "source": "VeriScan country guidance",
        "countries": {"india"},
        "documents": {"aadhaar", "pan", "passport", "birth certificate", "driving licence"},
        "terms": {"verhoeff", "pan", "qr", "issuer"},
        "guidance": "For India selections, review extracted identity fields, Aadhaar-style Verhoeff results, PAN format signals, QR consistency, and issuing-authority details together.",
    },
    {
        "title": "United States document checks",
        "source": "VeriScan country guidance",
        "countries": {"usa"},
        "documents": {"passport", "visa", "ssn", "id/driving licence", "health insurance"},
        "terms": {"issuer", "expiry", "number", "qr"},
        "guidance": "For USA selections, compare the name, document number, dates, photograph, and issuing authority against the authorized source; do not infer validity from OCR alone.",
    },
    {
        "title": "United Kingdom document checks",
        "source": "VeriScan country guidance",
        "countries": {"uk"},
        "documents": {"passport", "visa/evisa", "national insurance number", "id", "health/nhs"},
        "terms": {"issuer", "expiry", "number", "qr"},
        "guidance": "For UK selections, pay particular attention to document number, expiry or status dates, name consistency, and the issuing authority before escalating for manual verification.",
    },
    {
        "title": "Australia document checks",
        "source": "VeriScan country guidance",
        "countries": {"australia"},
        "documents": {"passport", "visa", "tfn", "medicare/insurance", "driving licence"},
        "terms": {"issuer", "expiry", "number", "qr"},
        "guidance": "For Australia selections, compare identity fields and expiry dates with the authorized issuing channel; forensic anomalies should prompt a closer look at the image regions involved.",
    },
    {
        "title": "UAE document checks",
        "source": "VeriScan country guidance",
        "countries": {"uae"},
        "documents": {"passport", "residence visa", "emirates id", "health insurance", "driving licence"},
        "terms": {"issuer", "expiry", "number", "qr"},
        "guidance": "For UAE selections, verify name, document number, validity dates, photograph, and issuing authority through an approved verification channel.",
    },
    {
        "title": "Forensic signal interpretation",
        "source": "VeriScan forensic guidance",
        "countries": set(),
        "documents": set(),
        "terms": {"ela", "copy-move", "blur", "metadata", "png", "jpeg"},
        "guidance": "ELA and copy-move results are review signals, not proof of alteration. PNG inputs make ELA inconclusive; inspect the reported image region and surrounding context manually.",
    },
]


def _normalise(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def retrieve_guidance(country: str | None, document: str | None, checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    country_key = _normalise(country)
    document_key = _normalise(document)
    signal_text = " ".join(f"{item['name']} {item['detail']}" for item in checks).lower()
    results: list[tuple[int, dict[str, Any]]] = []
    for item in KNOWLEDGE_BASE:
        score = 0
        if country_key in item["countries"]:
            score += 6
        if document_key in item["documents"]:
            score += 5
        score += sum(1 for term in item["terms"] if term in signal_text or term in document_key)
        if score:
            results.append((score, item))
    results.sort(key=lambda match: match[0], reverse=True)
    return [
        {"title": item["title"], "source": item["source"], "guidance": item["guidance"], "match_score": score}
        for score, item in results[:3]
    ]