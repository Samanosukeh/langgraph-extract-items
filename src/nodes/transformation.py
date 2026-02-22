import json
from typing import Any, Dict

from ..utils.state import ItemState


def extract_attributes_node(state: ItemState, extractor) -> Dict[str, Any]:
    attributes = extractor.extract_attributes(
        state["item_raw"],
        state["detected_type"],
        state["detected_class"],
    )
    return {**state, "attributes_extracted": attributes, "metadata": attributes.get("metadata", {})}


def build_final_item_node(state: ItemState) -> Dict[str, Any]:
    final_item = _create_item_structure(state)
    return {**state, "final_item": final_item}


def validate_item_node(state: ItemState) -> Dict[str, Any]:
    item = state.get("final_item", {})
    required_fields = ["id", "document_id", "name", "type", "description", "metadata"]
    missing = _find_missing_fields(item, required_fields)
    if missing:
        return {**state, "error": f"Missing fields: {missing}"}
    return state


def _create_item_structure(state: ItemState) -> Dict[str, Any]:
    attributes = state["attributes_extracted"]
    return {
        "id": f"item_{state['document_id']}_{state['index']}",
        "document_id": state["document_id"],
        "name": attributes.get("name", state["item_raw"][:100]),
        "type": state["detected_type"],
        "value": attributes.get("value", "0.0"),
        "description": attributes.get("description", state["item_raw"]),
        "metadata": _serialize_metadata(state),
    }


def _serialize_metadata(state: ItemState) -> str:
    metadata = state.get("metadata", {})
    if isinstance(metadata, dict):
        return json.dumps(metadata, ensure_ascii=False)
    attributes_metadata = state["attributes_extracted"].get("metadata", {})
    return json.dumps(attributes_metadata, ensure_ascii=False)


def _find_missing_fields(item: dict, required_fields: list) -> list:
    return [field for field in required_fields if field not in item]
