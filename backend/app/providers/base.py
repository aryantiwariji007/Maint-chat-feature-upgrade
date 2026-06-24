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
    "extracted text from images, scanned tables/documents, or spreadsheet files. "
    "This extracted text may contain OCR or vision-model errors. If data looks "
    "inconsistent or a table seems malformed, note that uncertainty rather than "
    "presenting it as ground truth. Always answer using the attached context when "
    "it is relevant to the question."
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
