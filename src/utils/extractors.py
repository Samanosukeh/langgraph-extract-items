import logging
from typing import List, Tuple

from langfuse import observe

from ..config.mistral_client import MistralClient
from ..config.settings import Settings
from ..prompts import get_prompt
from .schemas import ExtractedItemsBatch, ExtractedItemsList

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15


class ItemExtractor:
    def __init__(self, llm: MistralClient, langfuse_client):
        self._llm = llm
        self._langfuse = langfuse_client

    @observe(name="extract_items_from_document")
    def extract_items(self, document_text: str) -> List[str]:
        system_prompt, user_prompt = get_prompt("extract_items")
        prompt = user_prompt.format(documento_texto=document_text)

        result = self._llm.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            pydantic_model=ExtractedItemsList,
            temperature=0.1,
        )

        content = result.get("content", {})
        items = content.get("items", [])

        self._langfuse.update_current_trace(
            input={"document_size": len(document_text)},
            output={"total_items": len(items)},
            user_id=Settings().user,
            metadata={"model": result.get("model")},
            tags=["extraction"],
        )

        return items

    @observe(name="extract_items_batch")
    def extract_items_batch_iterative(
        self,
        document_text: str,
        iteration: int = 1,
        already_extracted: List[str] | None = None,
    ) -> Tuple[List[str], bool]:
        already_extracted = already_extracted or []

        system_prompt, prompt = self._build_prompts(iteration, document_text, already_extracted)

        result = self._llm.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            pydantic_model=ExtractedItemsBatch,
            temperature=0.1,
        )

        content = result.get("content", {})
        new_items = content.get("items", [])
        has_more = content.get("has_more", False)

        self._langfuse.update_current_trace(
            input={
                "document_size": len(document_text),
                "iteration": iteration,
                "already_extracted": len(already_extracted),
            },
            output={"new_items": len(new_items), "has_more": has_more},
            user_id=Settings().user,
            metadata={"model": result.get("model"), "strategy": "iterative"},
            tags=["extraction", "iterative"],
        )

        return new_items, has_more

    def _build_prompts(
        self,
        iteration: int,
        document_text: str,
        already_extracted: List[str],
    ) -> Tuple[str, str]:
        if iteration == 1:
            return self._build_first_iteration_prompt(document_text)
        return self._build_next_iteration_prompt(iteration, document_text, already_extracted)

    def _build_first_iteration_prompt(self, document_text: str) -> Tuple[str, str]:
        system_prompt, user_prompt = get_prompt("extract_items_batch_first")
        prompt = user_prompt.format(documento_texto=document_text)
        return system_prompt, prompt

    def _build_next_iteration_prompt(
        self,
        iteration: int,
        document_text: str,
        already_extracted: List[str],
    ) -> Tuple[str, str]:
        system_prompt, user_prompt = get_prompt("extract_items_batch_next")
        items_preview = self._build_items_preview(already_extracted)
        prompt = user_prompt.format(
            iteracao=iteration,
            num_itens_extraidos=len(already_extracted),
            documento_texto=document_text,
            itens_ja_extraidos_preview=items_preview,
        )
        return system_prompt, prompt

    def _build_items_preview(self, already_extracted: List[str]) -> str:
        preview_items = [f"- {item[:150]}..." for item in already_extracted[:3]]
        return "\n".join(preview_items)
