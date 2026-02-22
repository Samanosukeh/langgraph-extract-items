import json
from typing import Type

from mistralai import Mistral
from pydantic import BaseModel


class MistralClient:
    def __init__(self, api_key: str, model: str):
        self._model = model
        self._client = Mistral(api_key=api_key)

    def complete(
        self,
        prompt: str,
        system_prompt: str,
        pydantic_model: Type[BaseModel],
        temperature: float = 0.1,
    ) -> dict:
        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        if not isinstance(raw, str):
            raise ValueError(f"Unexpected content type from Mistral: {type(raw)}")
        data = json.loads(raw)
        result = pydantic_model.model_validate(data)
        return {"content": result.model_dump(), "model": self._model}

    @property
    def model(self) -> str:
        return self._model
