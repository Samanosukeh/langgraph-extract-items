from typing import Any, Dict, cast

from langfuse import get_client, observe
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from src.config import MistralClient, Settings
from src.nodes import (
    aggregate_results_node,
    build_final_item_node,
    check_more_items,
    classify_product_node,
    classify_service_node,
    detect_type_node,
    extract_attributes_node,
    extract_items_batch_node,
    validate_item_node,
)
from src.utils import (
    AttributeExtractor,
    DocumentState,
    ItemExtractor,
    ItemState,
    ProductClassifier,
    ServiceClassifier,
    TypeDetector,
)


class ItemExtractionPipeline:
    def __init__(self):
        settings = Settings()
        self._langfuse = get_client()

        api_key = settings.mistral_api_key

        # Smaller model for simple tasks (list extraction and type detection)
        llm_fast = MistralClient(api_key=api_key, model="ministral-8b-latest")
        # Larger model for tasks requiring more reasoning (classification and attributes)
        llm_large = MistralClient(api_key=api_key, model="mistral-large-latest")  # ministral-14b-2512

        self._extractor = ItemExtractor(llm_large, self._langfuse)
        self._type_detector = TypeDetector(llm_fast, self._langfuse)
        self._product_classifier = ProductClassifier(llm_large, self._langfuse)
        self._service_classifier = ServiceClassifier(llm_large, self._langfuse)
        self._attribute_extractor = AttributeExtractor(llm_large, self._langfuse)

        self._item_graph = self._build_item_graph()
        self._main_graph = self._build_main_graph()

    def _build_item_graph(self) -> CompiledStateGraph:
        graph = StateGraph(ItemState)

        graph.add_node("detect_type", lambda state: detect_type_node(cast(ItemState, state), self._type_detector))
        graph.add_node("classify_product", lambda state: classify_product_node(cast(ItemState, state), self._product_classifier))
        graph.add_node("classify_service", lambda state: classify_service_node(cast(ItemState, state), self._service_classifier))
        graph.add_node("extract_attributes", lambda state: extract_attributes_node(cast(ItemState, state), self._attribute_extractor))
        graph.add_node("build_final", build_final_item_node)
        graph.add_node("validate_item", validate_item_node)

        graph.set_entry_point("detect_type")

        graph.add_conditional_edges(
            "detect_type",
            self._route_by_type,
            {"classify_product": "classify_product", "classify_service": "classify_service"},
        )

        graph.add_edge("classify_product", "extract_attributes")
        graph.add_edge("classify_service", "extract_attributes")
        graph.add_edge("extract_attributes", "build_final")
        graph.add_edge("build_final", "validate_item")
        graph.add_edge("validate_item", END)

        return graph.compile()

    def _build_main_graph(self) -> CompiledStateGraph:
        graph = StateGraph(DocumentState)

        graph.add_node("extract_items_batch", lambda state: extract_items_batch_node(cast(DocumentState, state), self._extractor))
        graph.add_node("process_item", self._process_single_item)
        graph.add_node("aggregate", aggregate_results_node)

        graph.set_entry_point("extract_items_batch")

        graph.add_conditional_edges(
            "extract_items_batch",
            check_more_items,
            {"continue": "extract_items_batch", "finish": "aggregate"},
        )

        graph.add_conditional_edges(
            "aggregate",
            self._fan_out_items,
            ["process_item"],
        )

        graph.add_edge("process_item", END)

        return graph.compile()

    @observe(name="process_single_item")
    def _process_single_item(self, state: ItemState) -> Dict[str, Any]:
        result = self._item_graph.invoke(state)

        self._langfuse.update_current_trace(
            input={"item_index": state["index"], "item": state["item_raw"][:100]},
            output={"type": result.get("detected_type"), "class": result.get("detected_class")},
            user_id=Settings().user,
            tags=["item_processing"],
        )

        return {"items_processed": [result["final_item"]]}

    @observe(name="extract_items")
    def process_document(self, document_text: str, document_id: int) -> Dict[str, Any]:
        initial_state = {
            "document_text": document_text,
            "document_id": document_id,
            "items_raw": [],
            "items_processed": [],
            "document_metadata": {},
            "error": None,
            "extraction_iteration": 1,
            "has_more_items": True,
        }

        self._langfuse.update_current_trace(
            input={"document_id": document_id, "document_size": len(document_text)},
            user_id=Settings().user,
            tags=["pipeline"],
        )

        result = self._main_graph.invoke(initial_state)

        self._langfuse.update_current_trace(
            output={
                "total_items_raw": len(result.get("items_raw", [])),
                "total_items_processed": len(result.get("items_processed", [])),
            },
        )

        self._langfuse.flush()
        return result

    @staticmethod
    def _route_by_type(state: ItemState) -> str:
        if state.get("detected_type") == "product":
            return "classify_product"
        return "classify_service"

    @staticmethod
    def _fan_out_items(state: DocumentState):
        items_raw = state.get("items_raw", [])
        if not items_raw:
            return []
        return [
            Send(
                "process_item",
                {
                    "item_raw": item,
                    "document_id": state["document_id"],
                    "index": idx,
                    "detected_type": "product",
                    "detected_class": "",
                    "attributes_extracted": {},
                    "metadata": {},
                    "final_item": {},
                    "error": None,
                },
            )
            for idx, item in enumerate(items_raw)
        ]
