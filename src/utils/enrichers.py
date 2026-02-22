from typing import Any, Dict

from langfuse import observe

from ..config.mistral_client import MistralClient
from ..config.settings import Settings
from ..prompts import get_prompt
from .schemas import ItemAttributes


class AttributeExtractor:
    def __init__(self, llm: MistralClient, langfuse_client):
        self._llm = llm
        self._langfuse = langfuse_client

    @observe(name="extract_item_attributes")
    def extract_attributes(
        self, item_description: str, item_type: str, item_class: str
    ) -> Dict[str, Any]:
        prompt_path = f"extract_attributes/{item_type}/general"
        system_prompt, user_prompt = get_prompt(prompt_path)
        prompt = user_prompt.format(
            item_description=item_description, tipo=item_type, classe=item_class
        )

        result = self._llm.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            pydantic_model=ItemAttributes,
            temperature=0.1,
        )

        content = result.get("content", {})

        self._langfuse.update_current_trace(
            input={"item": item_description[:100], "type": item_type, "class": item_class},
            output={"attributes_extracted": True},
            user_id=Settings().user,
            tags=["attribute_extraction"],
        )

        return content
