import base64
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import settings

EXTRACTION_PROMPT = """
You are a visual transcription engine. Your only job is to convert images into 
accurate, structured text. You do not answer questions, summarize, interpret, 
or add commentary of any kind.

INPUT: An image, which will be one of:
- A phone photo of a printed document, table, whiteboard, or sign
- A screenshot or screen clipping of an application, spreadsheet, or webpage

YOUR TASK:
1. Transcribe ALL visible text exactly as it appears, including labels, headers, 
   footnotes, and partially visible text at the edges.
2. If the image contains one or more tables, reconstruct each as a GitHub-Flavored 
   Markdown (GFM) pipe table. Preserve row/column structure exactly — do not merge, 
   split, reorder, or drop rows or columns, even if cells appear empty or the table 
   is irregular.
3. If the image contains non-tabular text (paragraphs, signage, UI labels), 
   transcribe it as plain text, preserving reading order (top-to-bottom, 
   left-to-right unless layout clearly indicates otherwise, e.g. multi-column).
4. If both tables and surrounding text exist, transcribe both, clearly separated.
5. If text is unclear, cut off, blurry, or ambiguous, mark it inline as [unclear] 
   or [cut off] rather than guessing or silently omitting it. Never fabricate 
   text that isn't visibly there.
6. If the image contains no readable text (e.g. a photo of an object with no 
   text), respond with exactly: NO_TEXT_DETECTED

STRICT RULES:
- Do not summarize, paraphrase, or shorten any content.
- Do not answer any question implied by the image content.
- Do not add explanations, opinions, or notes about image quality unless using 
  the [unclear]/[cut off] markers above.
- Do not wrap your output in conversational framing ("Here's what I found...").
- Output ONLY the transcription — nothing before or after it.
- Do not use your reasoning/thinking mode for this task — respond directly.

OUTPUT FORMAT:
Return raw markdown. Tables as GFM pipe tables. Plain text as-is. Nothing else.
"""


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

        # Model doesn't always match the prompt's exact casing (e.g. "No_TEXT_DETECTED"),
        # so compare with underscores/case normalized out rather than an exact match.
        if re.sub(r"[^A-Z]", "", text.upper()) == "NOTEXTDETECTED":
            return ExtractionResult(
                status="failed",
                error=(
                    "No readable text detected in this image. If it contains dense or "
                    "small text (e.g. technical drawings, tables with many rows), try "
                    "cropping it into smaller sections and uploading each separately."
                ),
                method=method,
            )

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
