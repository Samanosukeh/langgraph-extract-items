import logging
from typing import Any, Dict

from langfuse import observe

from ..utils.state import DocumentState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15


@observe(name="extract_items_node")
def extract_items_node(state: DocumentState, extractor) -> Dict[str, Any]:
    items_raw = extractor.extract_items(state["document_text"])
    print(f"✅ {len(items_raw)} items extracted from document {state['document_id']}")
    return {**state, "items_raw": items_raw}


@observe(name="extract_items_batch_node")
def extract_items_batch_node(state: DocumentState, extractor) -> Dict[str, Any]:
    iteration = state.get("extraction_iteration", 1)
    already_extracted = state.get("items_raw", [])

    new_items, has_more = extractor.extract_items_batch_iterative(
        document_text=state["document_text"],
        iteration=iteration,
        already_extracted=already_extracted,
    )

    unique_new_items = _remove_duplicates(new_items, already_extracted)
    updated_items_raw = already_extracted + unique_new_items

    _print_iteration_status(iteration, unique_new_items, updated_items_raw, has_more)

    return {
        **state,
        "items_raw": updated_items_raw,
        "extraction_iteration": iteration + 1,
        "has_more_items": has_more,
    }


def check_more_items(state: DocumentState) -> str:
    has_more = state.get("has_more_items", False)
    iteration = state.get("extraction_iteration", 1)

    if iteration > MAX_ITERATIONS:
        logger.warning(f"Max iterations limit reached ({iteration}/{MAX_ITERATIONS})")
        return "finish"

    if has_more:
        return "continue"

    return "finish"


def aggregate_results_node(state: DocumentState) -> DocumentState:
    return state


def _remove_duplicates(new_items: list, already_extracted: list) -> list:
    existing_hashes = {_hash_item(item) for item in already_extracted}
    unique = []
    for item in new_items:
        item_hash = _hash_item(item)
        if item_hash not in existing_hashes:
            unique.append(item)
            existing_hashes.add(item_hash)
    return unique


def _hash_item(item: str) -> int:
    return hash(item.strip().lower()[:200])


def _print_iteration_status(
    iteration: int,
    unique_new_items: list,
    updated_items_raw: list,
    has_more: bool,
):
    total_new = len(unique_new_items)
    total_overall = len(updated_items_raw)
    print(f"✅ Iteration {iteration}: {total_new} new items (total: {total_overall})")
    if has_more:
        print("   ⏳ More items to extract...")
    else:
        print(f"   ✅ Extraction complete! Total: {total_overall} items")
