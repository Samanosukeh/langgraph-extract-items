from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ExtractedItemsList(BaseModel):
    items: List[str] = Field(..., description="List of complete item descriptions found")


class ExtractedItemsBatch(BaseModel):
    items: List[str] = Field(
        ...,
        description="List of complete item descriptions found in this iteration (max 10)",
    )
    has_more: bool = Field(
        ...,
        description="True if there are more items in the document to extract, False if all have been extracted",
    )
    total_estimated: Optional[int] = Field(
        None, description="Estimated total number of items in the document"
    )
    observation: Optional[str] = Field(
        None, description="Observations about the extraction"
    )


class ItemTypeDetection(BaseModel):
    item_type: Literal["product", "service"] = Field(
        ..., description="Item type: product or service"
    )
    justification: str = Field(..., description="Classification justification")


class ItemClassification(BaseModel):
    item_class: str = Field(..., description="Exact class name")
    justification: str = Field(..., description="Classification justification")


class ItemMetadata(BaseModel):
    item: str = Field(..., description="Full item name")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Specific attributes")
    description_optimized: str = Field(..., description="Optimized description")
    item_type: str = Field(..., description="Item type")
    item_class: str = Field(..., description="Item class")
    quantity: int = Field(default=0, description="Item quantity")
    unit_original: str = Field(default="", description="Original unit mentioned in the text")
    unit_norm: str = Field(default="", description="Normalized unit")
    unit_price: float = Field(default=0.0, description="Unit price in BRL (R$)")
    total_price: float = Field(default=0.0, description="Total price in BRL (R$)")
    technical_specs: List[Dict[str, str]] = Field(
        default_factory=list, description="Technical specifications of the item"
    )


class ItemAttributes(BaseModel):
    name: str = Field(..., description="Short item name")
    item_type: str = Field(..., description="Item type")
    value: str = Field(default="0.0", description="Main item value as string (e.g.: '1234.56')")
    description: str = Field(..., description="Item description")
    metadata: ItemMetadata = Field(..., description="Complete metadata including monetary values")
