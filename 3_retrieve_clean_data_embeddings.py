#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Retrieve Supabase embeddings for clean_data rows and perform RAG search using SQL vector similarity."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import json

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit("Install 'numpy' package before running this script (pip install numpy).") from exc

from config import (
    CLEAN_DATA_TABLE_NAME,
    EMBEDDING_COLUMN,
    EMBEDDING_CONTEXT_LIMIT,
    EMBEDDING_MODEL,
    ROW_IDENTIFIER_COLUMNS,
    SUPABASE_SERVICE_KEY,
    SUPABASE_URL,
)

try:
    from supabase import Client, create_client
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit(
        "Install 'supabase' package before running this script "
        "(pip install supabase)."
    ) from exc

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit(
        "Install 'sentence-transformers' package before running this script "
        "(pip install sentence-transformers)."
    ) from exc


TABLE_NAME = CLEAN_DATA_TABLE_NAME
SUMMARY_CONTEXT_LIMIT = EMBEDDING_CONTEXT_LIMIT


@dataclass
class EmbeddingService:
    """Thin wrapper around a local SentenceTransformer embedding model."""

    model_name: str
    device: str
    model: SentenceTransformer

    def embed(self, text: str) -> List[float]:
        """Create an embedding for the supplied text."""
        try:
            vector = self.model.encode(
                text,
                device=self.device,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except RuntimeError:
            raise
        except Exception as exc:  # pragma: no cover - runtime errors
            raise RuntimeError(f"Failed to generate embedding: {exc}") from exc

        try:
            return vector.tolist()  # type: ignore[no-any-return]
        except AttributeError:
            if isinstance(vector, list):
                return vector
            raise RuntimeError("Embedding response is malformed.")

    def move_to(self, device: str) -> None:
        """Move the underlying model to a different device."""
        previous_device = self.device
        self.device = device
        self.model.to(device)
        if previous_device and previous_device.startswith("cuda") and device == "cpu":
            try:
                import torch  # type: ignore

                torch.cuda.empty_cache()
            except Exception:
                pass
        print(f"[info] Embedding model now using device '{device}'.", file=sys.stderr)


@dataclass
class SimilarRow:
    """Row with similarity score from vector search."""
    key_column: str
    key_value: Any
    similarity: float
    row: Dict[str, Any]


def resolve_device(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():  # type: ignore[attr-defined]
            return "mps"
    except ImportError:
        pass
    return "cpu"


def create_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise SystemExit(
            "Supabase configuration missing. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY)."
        )
    try:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as exc:  # pragma: no cover - connection errors
        raise SystemExit(f"Unable to create Supabase client: {exc}") from exc


def pick_primary_key(row: Dict[str, Any]) -> Optional[str]:
    for candidate in ROW_IDENTIFIER_COLUMNS:
        if candidate in row and row[candidate] not in (None, ""):
            return candidate
    return None


def _coerce_to_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        items = [str(item).strip() for item in value if item not in (None, "")]
        return ", ".join(item for item in items if item)
    if isinstance(value, dict):
        text_fields: List[str] = []
        for key in ("text", "reason", "overall_assessment", "content", "summary"):
            field_value = value.get(key)
            if isinstance(field_value, str) and field_value.strip():
                text_fields.append(field_value.strip())
        if text_fields:
            return " ".join(text_fields)
    return json.dumps(value, ensure_ascii=False)


def _first_non_empty(values: Iterable[Any]) -> str:
    for value in values:
        text = _coerce_to_text(value)
        if text:
            return text
    return ""


CONTEXT_SOURCE_FIELDS: Tuple[str, ...] = (
    "text",
    "original_payload",
)
ASSET_FIELDS: Tuple[str, ...] = ("gpt_assets",)
MARKET_FIELDS: Tuple[str, ...] = (
    "is_market_related_reason",
    "is_market_related_result_json",
)
INFO_FIELDS: Tuple[str, ...] = (
    "info_overall_assessment",
    "info_final_score_json",
    "info_final_score",
    "info_scores",
)


def summarize_row(row: Dict[str, Any]) -> str:
    original = _first_non_empty(row.get(field) for field in CONTEXT_SOURCE_FIELDS)
    assets = _first_non_empty(row.get(field) for field in ASSET_FIELDS)
    market_reason = _first_non_empty(
        (
            row.get("is_market_related_reason"),
            (row.get("is_market_related_reason") or {}).get("text")
            if isinstance(row.get("is_market_related_reason"), dict)
            else None,
            row.get("is_market_related_result_json"),
        )
    )
    info_assessment = _first_non_empty(
        (
            row.get("info_overall_assessment"),
            (row.get("info_final_score_json") or {}).get("overall_assessment")
            if isinstance(row.get("info_final_score_json"), dict)
            else None,
            str(row.get("info_final_score")) if row.get("info_final_score") is not None else None,
        )
    )

    context_parts: List[str] = []
    if original:
        context_parts.append(f"Original Content:\n{original}")
    if assets:
        context_parts.append(f"Asset Notes:\n{assets}")
    if market_reason:
        context_parts.append(f"Market Related Reason:\n{market_reason}")
    if info_assessment:
        context_parts.append(f"Information Assessment:\n{info_assessment}")

    summary = "\n\n".join(context_parts) if context_parts else "[no textual context]"
    if len(summary) > SUMMARY_CONTEXT_LIMIT:
        return summary[: SUMMARY_CONTEXT_LIMIT - 3] + "..."
    return summary


def to_numpy_vector(raw_vector: Any) -> Optional[np.ndarray]:
    if raw_vector in (None, "", []):
        return None
    try:
        array = np.asarray(raw_vector, dtype=np.float32)
    except Exception:
        return None
    if array.ndim != 1:
        return None
    return array


def fetch_embedded_rows(client: Client, chunk_size: int = 500) -> List[EmbeddedRow]:
    selected_fields = sorted(
        set(
            list(ROW_IDENTIFIER_COLUMNS)
            + list(CONTEXT_SOURCE_FIELDS)
            + list(ASSET_FIELDS)
            + list(MARKET_FIELDS)
            + list(INFO_FIELDS)
            + [EMBEDDING_COLUMN]
        )
    )
    select_clause = ",".join(selected_fields)

    rows: List[EmbeddedRow] = []
    offset = 0

    while True:
        try:
            response = (
                client.table(TABLE_NAME)
                .select(select_clause)
                .not_.is_(EMBEDDING_COLUMN, "null")
                .range(offset, offset + chunk_size - 1)
                .execute()
            )
        except Exception as exc:
            raise RuntimeError(f"Supabase fetch failed: {exc}") from exc

        batch: List[Dict[str, Any]] = list(getattr(response, "data", []) or [])
        if not batch:
            break

        for row in batch:
            vector = to_numpy_vector(row.get(EMBEDDING_COLUMN))
            if vector is None:
                continue
            norm = float(np.linalg.norm(vector))
            if norm == 0.0:
                continue
            key_column = pick_primary_key(row)
            if not key_column:
                continue
            rows.append(
                EmbeddedRow(
                    key_column=key_column,
                    key_value=row[key_column],
                    vector=vector,
                    norm=norm,
                    row=row,
                )
            )

        if len(batch) < chunk_size:
            break

        offset += chunk_size

    return rows


def compute_similarities(
    query_vector: np.ndarray, dataset: Sequence[EmbeddedRow]
) -> List[Tuple[EmbeddedRow, float]]:
    query_norm = float(np.linalg.norm(query_vector))
    if query_norm == 0.0:
        raise RuntimeError("Query embedding norm is zero; cannot compute similarity.")

    similarities: List[Tuple[EmbeddedRow, float]] = []
    for row in dataset:
        score = float(np.dot(query_vector, row.vector) / (query_norm * row.norm))
        similarities.append((row, score))
    similarities.sort(key=lambda item: item[1], reverse=True)
    return similarities


def read_query_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text.strip()
    if args.file:
        path = Path(args.file)
        if not path.exists():
            raise FileNotFoundError(path)
        return path.read_text(encoding="utf-8").strip()
    print("Enter the news text to search for. Finish input with Ctrl+Z then Enter:\n")
    return sys.stdin.read().strip()


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Embed an input news article with the same model used for clean_data "
            "and retrieve the top-K closest rows from Supabase."
        )
    )
    parser.add_argument(
        "--text",
        help="Raw news text to embed. If omitted, reads from --file or STDIN.",
    )
    parser.add_argument(
        "--file",
        help="Path to a file containing the news text to embed.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of similar rows to display (default: 10).",
    )
    parser.add_argument(
        "--device",
        help="Force the embedding model device (cpu, cuda, mps).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Supabase fetch size per request (default: 500).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap on the number of rows to load locally.",
    )
    return parser.parse_args(argv)


def ensure_query_text(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        raise SystemExit("Query text is empty. Provide --text/--file or STDIN input.")
    return normalized


def limit_dataset(dataset: List[EmbeddedRow], limit: Optional[int]) -> List[EmbeddedRow]:
    if limit is None or limit >= len(dataset):
        return dataset
    return dataset[:limit]


def run(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    query_text = ensure_query_text(read_query_text(args))

    device_env = os.getenv("EMBEDDING_DEVICE")
    device = resolve_device(args.device or device_env)

    embedding_service = EmbeddingService(
        model_name=EMBEDDING_MODEL,
        device=device,
        model=SentenceTransformer(EMBEDDING_MODEL, device=device),
    )
    print(
        f"[info] Embedding model '{embedding_service.model_name}' loaded on device "
        f"'{embedding_service.device}'."
    )

    try:
        query_vector = embedding_service.embed(query_text)
    except RuntimeError as exc:
        raise SystemExit(f"Failed to embed query text: {exc}") from exc

    supabase_client = create_supabase_client()
    print("[info] Fetching rows with stored embeddings from Supabase ...")
    dataset = fetch_embedded_rows(supabase_client, chunk_size=args.chunk_size)
    if not dataset:
        raise SystemExit("No rows with embeddings were found in Supabase.")

    if args.max_rows is not None:
        dataset = limit_dataset(dataset, args.max_rows)
        print(f"[info] Using the first {len(dataset)} rows after applying max_rows cap.")
    else:
        print(f"[info] Loaded {len(dataset)} rows with embeddings.")

    similarities = compute_similarities(np.asarray(query_vector, dtype=np.float32), dataset)
    top_k = max(1, min(args.top_k, len(similarities)))
    print(f"\nTop {top_k} most similar clean_data rows:\n")

    for rank, (row, score) in enumerate(similarities[:top_k], start=1):
        summary = summarize_row(row.row)
        print(f"{rank:02d}. {row.key_column}={row.key_value!r} | cosine={score:.4f}")
        print(summary)
        print("-" * 80)


if __name__ == "__main__":
    run()


