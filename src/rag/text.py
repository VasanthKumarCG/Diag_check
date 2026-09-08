from __future__ import annotations
import re

def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())

def chunk_text(text: str, max_chars: int = 1400, overlap_chars: int = 200) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = f"{tail} {sentence}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks

def build_search_text(case: dict) -> str:
    fields = [
        f"Vehicle model: {case.get('vehicle_model','')}",
        f"Software release: {case.get('sw_release','')}",
        f"Primary ECU: {case.get('primary_ecu','')}",
        "Related ECUs: " + ", ".join(case.get('related_ecus') or []),
        "DTC codes: " + ", ".join(case.get('dtc_codes') or []),
        f"Observed symptoms: {case.get('observed_symptoms','')}",
        f"Environment: {case.get('environment_summary','')}",
    ]
    return normalize_text("\n".join(fields))
