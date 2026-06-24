import base64
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import settings

EXTRACTION_PROMPT = """You are a precise document and table extraction engine. You will be given one image, which may be either:
(a) a photo taken with a phone camera of a printed document, receipt, or table — possibly with skew, perspective distortion, glare, shadows, or slightly blurred text, or
(b) a screenshot or cropped screen clipping of a table, spreadsheet, or UI showing tabular data — possibly with partial UI chrome (scrollbars, toolbars, browser frame) visible at the edges.

Your task:
1. Identify all tabular data in the image. Reconstruct each table as a GitHub-flavored Markdown table, preserving column headers, row order, and cell values exactly as written. Do not invent, round, or "correct" values you are uncertain about — if a character or number is genuinely illegible, write [unclear] in that cell rather than guessing.
2. If the image contains non-tabular text (titles, labels, footnotes, captions) that provides context for interpreting the table, include it as plain text immediately before or after the relevant table.
3. Ignore irrelevant UI chrome (scrollbars, browser tabs, toolbars, application menus) — do not transcribe it.
4. If the image is rotated, skewed, or has perspective distortion, mentally correct for this and extract the logical reading order of rows and columns — do not transcribe in the visually-skewed order.
5. If there are multiple separate tables in the image, output each as its own Markdown table with a one-line bolded label above it (e.g. **Table 1: Q1 Sales**) describing what it appears to represent.
6. If the image contains no tabular data at all, simply transcribe all visible text as plain text/markdown, preserving paragraph and heading structure.
7. Output ONLY the extracted Markdown/text. Do not add commentary, do not say "Here is the extracted table," do not wrap the output in a code block — output the raw Markdown directly."""


@dataclass
class ExtractionResult:
    status: str  # "success" | "failed"
    text: str | None = None
    error: str | None = None
    method: str = "vlm"


def extract_image(path: Path, mime_type: str) -> ExtractionResult:
    method = f"vlm:{settings.ollama_vlm_model}"
    try:
        image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        data_uri = f"data:{mime_type};base64,{image_b64}"

        payload = {
            "model": settings.ollama_vlm_model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{settings.ollama_base_url}/chat/completions", json=payload
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"].strip()
        return ExtractionResult(status="success", text=text, method=method)

    except httpx.ConnectError:
        return ExtractionResult(
            status="failed",
            error="Local extraction model unreachable — is Ollama running?",
            method=method,
        )
    except httpx.TimeoutException:
        return ExtractionResult(
            status="failed",
            error="Local extraction model timed out — Ollama may be cold-starting, try again.",
            method=method,
        )
    except Exception as exc:
        return ExtractionResult(status="failed", error=f"Extraction failed: {exc}", method=method)
