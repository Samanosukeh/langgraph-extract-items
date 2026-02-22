# langgraph-extract-items

```
██╗     █████╗ ███╗   ██╗ ██████╗  ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗
██║    ██╔══██╗████╗  ██║██╔════╝ ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║
██║    ███████║██╔██╗ ██║██║  ███╗██║  ███╗██████╔╝███████║██████╔╝███████║
██║    ██╔══██║██║╚██╗██║██║   ██║██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║
██████╗██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║
╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
                        extract  ·  classify  ·  enrich
```

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Map--Reduce-green?logo=langchain)](https://langchain-ai.github.io/langgraph/)
[![Mistral AI](https://img.shields.io/badge/Mistral-AI-orange)](https://mistral.ai/)
[![Langfuse](https://img.shields.io/badge/Langfuse-Observability-purple)](https://langfuse.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **LangGraph Map-Reduce pipeline** that extracts, classifies, and enriches procurement items from Portuguese public-sector documents (Termos de Referência, Editais).

---

## Overview

Given a raw document text the pipeline:

1. **Extracts** all items iteratively (batch-by-batch) using a structured LLM call
2. **Fans out** every item in parallel via LangGraph's `Send` API
3. **Classifies** each item as *product* or *service*, then assigns a fine-grained category class
4. **Enriches** each item with structured attributes (quantity, unit price, total value, metadata)
5. **Validates** and assembles the final normalized record

All steps are traced end-to-end in **Langfuse** with span-level observability.

---

## Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#e8f4fd',
  'primaryTextColor': '#1e293b',
  'primaryBorderColor': '#93c5fd',
  'lineColor': '#64748b',
  'secondaryColor': '#fef9c3',
  'tertiaryColor': '#f0fdf4',
  'background': '#ffffff',
  'mainBkg': '#ffffff'
}}}%%
flowchart TD
    subgraph MAIN["Main Graph — StateGraph(DocumentState)"]
        A([START]) --> B["extract_items_batch\n(LLM structured call)"]
        B --> C{"add_conditional_edges\n· check_more_items()"}
        C -- "return 'continue'" --> B
        C -- "return 'finish'" --> D[aggregate]
        D --> FAN{"add_conditional_edges\n· _fan_out_items()"}
        FAN -- "Send('process_item', item_0)" --> E0["process_item #0"]
        FAN -- "Send('process_item', item_1)" --> E1["process_item #1"]
        FAN -- "Send('process_item', item_n)" --> EN["process_item #n"]
        E0 --> R["items_processed\n· Annotated[list, operator.add]"]
        E1 --> R
        EN --> R
        R --> F([END])
    end

    subgraph ITEM["Subgraph — StateGraph(ItemState)\nCompiled separately, invoked via .invoke()"]
        G([START]) --> H["detect_type\n(add_conditional_edges)"]
        H -- "product" --> I[classify_product]
        H -- "service" --> J[classify_service]
        I --> K[extract_attributes]
        J --> K
        K --> L[build_final]
        L --> M[validate_item]
        M --> N([END])
    end

    E0 -. "self._item_graph.invoke(state)" .-> G
    E1 -. "self._item_graph.invoke(state)" .-> G
    EN -. "self._item_graph.invoke(state)" .-> G
```

### LangGraph Patterns Used

#### 1. Evaluator Loop — `add_conditional_edges`

<p align="center">
  <img src="https://mintcdn.com/langchain-5e9cc07a/-_xGPoyjhyiDWTPJ/oss/images/evaluator_optimizer.png?w=840&fit=max&auto=format&n=-_xGPoyjhyiDWTPJ&q=85&s=3ad3bfb734a0e509d9b87fdb4e808bfd" width="420" alt="Evaluator pattern" />
</p>

The extraction node loops until the LLM signals there are no more items. LangGraph's `add_conditional_edges` maps the return value of `check_more_items()` to either re-enter the same node (`"continue"` &rarr; `extract_items_batch`) or move forward (`"finish"` &rarr; `aggregate`). A safety cap of 15 iterations prevents infinite loops.


#### 2. Orchestrator-Workers — `Send` API + Subgraph

<p align="center">
  <img src="https://mintcdn.com/langchain-5e9cc07a/ybiAaBfoBvFquMDz/oss/images/worker.png?fit=max&auto=format&n=ybiAaBfoBvFquMDz&q=85&s=2e423c67cd4f12e049cea9c169ff0676" width="420" alt="Orchestrator-Workers pattern" />
</p>

After aggregation, each raw item is dispatched to its own `process_item` worker **in parallel** via `Send`. LangGraph spawns one independent execution per `Send` object, each carrying its own `ItemState`. Every worker invokes a **compiled subgraph** (`StateGraph(ItemState)`) that runs the full classification pipeline independently.


Results from all parallel workers are automatically merged back into `DocumentState.items_processed` using `operator.add` as the reducer — LangGraph's built-in mechanism for collecting outputs from fan-out nodes.


#### 3. Routing — `add_conditional_edges` inside the Subgraph

<p align="center">
  <img src="https://mintcdn.com/langchain-5e9cc07a/dL5Sn6Cmy9pwtY0V/oss/images/routing.png?fit=max&auto=format&n=dL5Sn6Cmy9pwtY0V&q=85&s=272e0e9b681b89cd7d35d5c812c50ee6" width="420" alt="Routing pattern" />
</p>

Inside each worker's subgraph, the `detect_type` node routes the item to the appropriate classifier based on its type. LangGraph's `add_conditional_edges` evaluates the detected type and sends the item down the correct branch — `classify_product` or `classify_service` — before converging back at `extract_attributes`.


## Project Structure

```
langgraph-extract-items/
├── pipeline.py                  # ItemExtractionPipeline (entry point)
├── test_pipeline.py             # Standalone integration tests
├── requirements.txt
├── .env.example
└── src/
    ├── config/
    │   ├── settings.py          # Env var loader
    │   └── mistral_client.py    # Thin LLM wrapper
    ├── utils/
    │   ├── schemas.py           # Pydantic output models
    │   ├── state.py             # DocumentState + ItemState (TypedDict)
    │   ├── constants.py         # Product/service class lists
    │   ├── classifiers.py       # TypeDetector, ProductClassifier, ServiceClassifier
    │   ├── extractors.py        # ItemExtractor (iterative batch)
    │   └── enrichers.py         # AttributeExtractor
    ├── nodes/
    │   ├── extraction.py        # extract_items_batch_node, aggregate, check_more_items
    │   ├── classification.py    # detect_type_node, classify_product_node, classify_service_node
    │   └── transformation.py    # extract_attributes_node, build_final_item_node, validate_item_node
    └── prompts/
        ├── __init__.py          # PromptLoader (parses ## System / ## User sections)
        ├── detect_type.md
        ├── classify_product.md
        ├── classify_service.md
        ├── extract_items.md
        ├── extract_items_batch_first.md
        ├── extract_items_batch_next.md
        └── extract_attributes/
            ├── product/general.md
            └── service/general.md
```

## Item Schema

Each processed item in `items_processed` contains:

```python
{
    "id": "item_1_0",
    "document_id": 1,
    "name": "Resma de Papel A4",
    "type": "product",            # "product" | "service"
    "value": "11000.00",
    "description": "...",
    "metadata": "{...}"           # JSON string with full ItemMetadata
}
```
