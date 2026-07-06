import base64
import io
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image

from app.config import settings

EXTRACTION_PROMPT = """
You are a visual analysis engine. Convert an image into structured Markdown
that a text-only assistant (which cannot see the image) can use to answer
questions about both the words AND the visual/diagrammatic content of the
image. You do not answer questions or hold a conversation — you only produce
the structured description below.

INPUT: An image, which will be one of:
- A phone photo of a printed document, table, diagram, whiteboard, or sign
- A screenshot or screen clipping of an application, spreadsheet, technical
  drawing, or webpage

Produce exactly two Markdown sections, in this order:

## Extracted Text
Transcribe ALL visible text exactly as it appears, including labels, headers,
footnotes, and partially visible text at the edges.
- If the image contains one or more tables, reconstruct each as a
  GitHub-Flavored Markdown (GFM) pipe table. Preserve row/column structure
  exactly — do not merge, split, reorder, or drop rows or columns, even if
  cells appear empty or the table is irregular.
- If the image contains non-tabular text (paragraphs, signage, UI labels),
  transcribe it as plain text, preserving reading order (top-to-bottom,
  left-to-right unless layout clearly indicates otherwise, e.g. multi-column).
- If text is unclear, cut off, blurry, or ambiguous, mark it inline as
  [unclear] or [cut off] rather than guessing or silently omitting it. Never
  fabricate text that isn't visibly there.
- If there is no visible text at all, write exactly: (no text in image)

## Visual Description
Describe the non-text visual content in enough detail that someone who
cannot see the image could reason about it:
- For diagrams, mechanical drawings, or figures: name the components/parts
  visible, their approximate spatial layout, and how they appear to connect
  or relate to each other. Refer to parts by the labels transcribed above
  where possible.
- For charts/graphs: describe the type of chart, axes, trend, and any
  standout data points.
- For photos: describe the scene, objects, and layout.
- Base descriptions only on what is visibly present — do not guess at
  functionality or purpose beyond what's visually evident.
- If the image is genuinely blank, a solid color, or has nothing describable
  beyond what's already in Extracted Text, write exactly: NOTHING_ELSE_TO_DESCRIBE

STRICT RULES:
- Do not answer any question implied by the image content — describe only.
- Do not wrap output in conversational framing ("Here's what I found...").
- Do not use your reasoning/thinking mode for this task — respond directly.

OUTPUT FORMAT:
Markdown with exactly the two headed sections above, in that order. Nothing
before the first heading or after the last section.
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
        # Ollama's local vision backend (llama.cpp's image loader) can't decode WebP,
        # only JPEG/PNG/BMP/GIF — re-encode every upload to PNG so format never matters.
        with Image.open(path) as img:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
        image_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        # Ollama's OpenAI-compatible endpoint (/v1/chat/completions) silently ignores
        # Ollama-specific fields like `options`, so num_ctx below would be a no-op there —
        # Ollama would then auto-size context to available VRAM (262144 tokens on a
        # 48GB GPU) instead of the ~4K a single-image extraction actually needs. The
        # native API respects `options.num_ctx`, hence calling /api/chat directly.
        payload = {
            "model": settings.ollama_vlm_model,
            "messages": [
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": [image_b64],
                }
            ],
            "options": {"temperature": 0.1, "num_ctx": settings.ollama_num_ctx},
            "stream": False,
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{settings.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        text = data["message"]["content"].strip()

        # Model doesn't always match the prompt's exact casing/spacing for the two
        # "nothing here" sentinels, so compare normalized rather than exact-match.
        # Only treat extraction as failed when BOTH sections come back empty — a
        # diagram with no text but a real visual description is still a success.
        normalized = re.sub(r"[^A-Z]", "", text.upper())
        no_text = "NOTEXTINIMAGE" in normalized
        no_visual = "NOTHINGELSETODESCRIBE" in normalized
        if no_text and no_visual:
            return ExtractionResult(
                status="failed",
                error=(
                    "No readable text or describable visual content detected in this "
                    "image. If it contains dense or small text (e.g. technical "
                    "drawings, tables with many rows), try cropping it into smaller "
                    "sections and uploading each separately."
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
