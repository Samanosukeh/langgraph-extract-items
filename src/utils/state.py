import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict


class DocumentState(TypedDict):
    document_text: str
    document_id: int
    items_raw: List[str]
    items_processed: Annotated[List[Dict[str, Any]], operator.add]
    document_metadata: Dict[str, Any]
    error: Optional[str]
    extraction_iteration: int
    has_more_items: bool


class ItemState(TypedDict):
    item_raw: str
    document_id: int
    index: int
    detected_type: Literal["product", "service"]
    detected_class: str
    attributes_extracted: Dict[str, Any]
    metadata: Dict[str, Any]
    final_item: Dict[str, Any]
    error: Optional[str]
