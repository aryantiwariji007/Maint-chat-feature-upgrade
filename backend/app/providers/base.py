from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    text: str
    context_blocks: list[dict] = field(default_factory=list)
    # each context block: {"filename": str, "text": str}


@dataclass
class LLMResult:
    text: str
    model_id: str


SYSTEM_PROMPT = (
    "You are a helpful assistant embedded in a chat product. The user may attach "
    "extracted content from images, including photographed or scanned tables/documents, "
    "diagrams, and figures. Each attachment has an 'Extracted Text' section (verbatim "
    "transcription) and a 'Visual Description' section (a description of diagrams, "
    "figures, charts, or photos, including how components appear to connect or relate "
    "to each other) — use both as needed to answer the question. This content may "
    "contain OCR or vision-model errors. If data looks inconsistent or a table seems "
    "malformed, note that uncertainty rather than presenting it as ground truth. Always "
    "answer using the attached context when it is relevant to the question."
)


def format_turn_text(turn: ChatTurn) -> str:
    """Render a ChatTurn's context blocks + text into a single prompt string."""
    parts = []
    for block in turn.context_blocks:
        parts.append(
            f"[Attached extract — filename: {block['filename']}]\n"
            f"{block['text']}\n"
            f"[End of attachment]"
        )
    parts.append(turn.text)
    return "\n\n".join(parts)


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @abstractmethod
    def generate(self, history: list[ChatTurn]) -> LLMResult: ...
