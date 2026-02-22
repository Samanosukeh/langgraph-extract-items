from abc import ABC, abstractmethod
from typing import List, Literal

from langfuse import observe

from ..config.mistral_client import MistralClient
from ..config.settings import Settings
from ..prompts import get_prompt
from .constants import PRODUCT_CLASSES, SERVICE_CLASSES
from .schemas import ItemClassification, ItemTypeDetection


class TypeDetector:
    def __init__(self, llm: MistralClient, langfuse_client):
        self._llm = llm
        self._langfuse = langfuse_client

    @observe(name="detect_item_type")
    def detect_type(self, item_description: str) -> Literal["product", "service"]:
        system_prompt, user_prompt = get_prompt("detect_type")
        prompt = user_prompt.format(item_description=item_description)

        result = self._llm.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            pydantic_model=ItemTypeDetection,
            temperature=0.1,
        )

        content = result.get("content", {})
        item_type = content.get("item_type", "product")

        self._langfuse.update_current_trace(
            input={"item": item_description[:100]},
            output={"type": item_type, "justification": content.get("justification", "")},
            user_id=Settings().user,
            tags=["type_detection"],
        )

        return item_type


class BaseClassifier(ABC):
    def __init__(self, llm: MistralClient, langfuse_client):
        self._llm = llm
        self._langfuse = langfuse_client

    def classify(self, item_description: str) -> str:
        classes_str = self._format_classes()
        system_prompt, user_prompt = get_prompt(self._get_prompt_name())
        prompt = user_prompt.format(classes_str=classes_str, item_description=item_description)

        result = self._llm.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            pydantic_model=ItemClassification,
            temperature=0.1,
        )

        content = result.get("content", {})
        classes = self._get_classes()
        item_class = content.get("item_class", classes[0])

        self._langfuse.update_current_trace(
            input={"item": item_description[:100]},
            output={"class": item_class, "justification": content.get("justification", "")},
            user_id=Settings().user,
            tags=["classification"],
        )

        return item_class

    def _format_classes(self) -> str:
        return "\n".join([f"- {c}" for c in self._get_classes()])

    @abstractmethod
    def _get_classes(self) -> List[str]:
        pass

    @abstractmethod
    def _get_prompt_name(self) -> str:
        pass


class ProductClassifier(BaseClassifier):
    @observe(name="classify_product")
    def classify(self, item_description: str) -> str:
        return super().classify(item_description)

    def _get_classes(self) -> List[str]:
        return PRODUCT_CLASSES

    def _get_prompt_name(self) -> str:
        return "classify_product"


class ServiceClassifier(BaseClassifier):
    @observe(name="classify_service")
    def classify(self, item_description: str) -> str:
        return super().classify(item_description)

    def _get_classes(self) -> List[str]:
        return SERVICE_CLASSES

    def _get_prompt_name(self) -> str:
        return "classify_service"
