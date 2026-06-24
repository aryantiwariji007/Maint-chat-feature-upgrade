from google import genai
from google.genai import types

from app.providers.base import SYSTEM_PROMPT, ChatTurn, LLMProvider, LLMResult, format_turn_text


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._model = model
        self._client = genai.Client(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, history: list[ChatTurn]) -> LLMResult:
        contents = [
            types.Content(
                role="user" if turn.role == "user" else "model",
                parts=[types.Part.from_text(text=format_turn_text(turn))],
            )
            for turn in history
        ]
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        return LLMResult(text=response.text or "", model_id=self._model)
