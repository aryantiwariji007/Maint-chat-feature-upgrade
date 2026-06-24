import anthropic

from app.providers.base import SYSTEM_PROMPT, ChatTurn, LLMProvider, LLMResult, format_turn_text


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, history: list[ChatTurn]) -> LLMResult:
        messages = [
            {"role": turn.role, "content": format_turn_text(turn)} for turn in history
        ]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResult(text=text, model_id=self._model)
