from typing import Any, Dict

from ..utils.state import ItemState


def detect_type_node(state: ItemState, detector) -> Dict[str, Any]:
    item_type = detector.detect_type(state["item_raw"])
    return {**state, "detected_type": item_type}


def classify_product_node(state: ItemState, classifier) -> Dict[str, Any]:
    item_class = classifier.classify(state["item_raw"])
    return {**state, "detected_class": item_class}


def classify_service_node(state: ItemState, classifier) -> Dict[str, Any]:
    item_class = classifier.classify(state["item_raw"])
    return {**state, "detected_class": item_class}
