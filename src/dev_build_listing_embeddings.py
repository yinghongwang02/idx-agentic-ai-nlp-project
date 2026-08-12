from __future__ import annotations
from decimal import Decimal

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import mysql.connector
import numpy as np
from mysql.connector import MySQLConnection

from src.providers.embedding_base import BaseEmbeddingProvider
from src.providers.factory import get_embedding_provider

from src.config.settings import settings
from src.embeddings.listing_text import build_listing_embedding_text

CHECKPOINT_DIRNAME = "checkpoints"
CHECKPOINT_STATE_FILENAME = "checkpoint_state.json"

DEFAULT_MODEL = settings.openai_embedding_model
DEFAULT_BATCH_SIZE = 50
DEFAULT_LIMIT = 100
DEFAULT_OUTPUT_DIR = Path("artifacts/embeddings")

LISTING_COLUMNS = [
    "L_ListingID",
    "L_DisplayId",
    "L_Address",
    "L_City",
    "L_State",
    "L_Zip",
    "L_SystemPrice",
    "L_Keyword2",
    "LM_Dec_3",
    "LM_Int2_3",
    "L_Type_",
    "DaysOnMarket",
    "AssociationFee",
    "L_Remarks",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate OpenAI embeddings for active MLS listings."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of listings to embed.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of listing texts per embedding request.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenAI embedding model.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory used to store embedding artifacts.",
    )

    parser.add_argument(
        "--checkpoint",
        action="store_true",
        help=(
            "Persist each embedding batch as a checkpoint "
            "before final consolidation."
        ),
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume from existing batch checkpoints "
            "in the output directory."
        ),
    )

    args = parser.parse_args()

    if args.limit <= 0:
        parser.error("--limit must be greater than zero.")

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero.")

    if args.resume and not args.checkpoint:
        parser.error(
            "--resume requires --checkpoint."
        )

    return args


def get_database_connection() -> MySQLConnection:
    """
    Create a MySQL connection.

    Rename the settings attributes below if your existing settings.py uses
    different names.
    """
    return mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset=settings.mysql_charset,
    )


def load_listings(
    connection: MySQLConnection,
    limit: int,
) -> list[dict[str, Any]]:
    """Load active listings that contain usable descriptive information."""
    selected_columns = ", ".join(LISTING_COLUMNS)

    sql = f"""
        SELECT {selected_columns}
        FROM rets_property
        WHERE
            L_Remarks IS NOT NULL
            AND TRIM(L_Remarks) <> ''
            AND L_ListingID IS NOT NULL
        ORDER BY L_ListingID
        LIMIT %s
    """

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
    finally:
        cursor.close()

    return list(rows)


def prepare_embedding_records(
    listings: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Create embedding texts and aligned metadata records."""
    texts: list[str] = []
    metadata: list[dict[str, Any]] = []

    skipped_count = 0

    for listing in listings:
        try:
            embedding_text = build_listing_embedding_text(listing)
        except ValueError:
            skipped_count += 1
            continue

        texts.append(embedding_text)
        metadata.append(
            {
                "listing_id": listing.get("L_ListingID"),
                "display_id": listing.get("L_DisplayId"),
                "address": listing.get("L_Address"),
                "city": listing.get("L_City"),
                "state": listing.get("L_State"),
                "zip": listing.get("L_Zip"),
                "list_price": listing.get("L_SystemPrice"),
                "bedrooms": listing.get("L_Keyword2"),
                "bathrooms": listing.get("LM_Dec_3"),
                "living_area": listing.get("LM_Int2_3"),
                "property_type": listing.get("L_Type_"),
                "days_on_market": listing.get("DaysOnMarket"),
                "association_fee": listing.get("AssociationFee"),
                "embedding_text": embedding_text,
            }
        )

    if skipped_count:
        print(f"Skipped listings with no usable text: {skipped_count}")

    return texts, metadata


def generate_embeddings(
    provider: BaseEmbeddingProvider,
    texts: list[str],
    batch_size: int,
) -> np.ndarray:
    """Generate embeddings in batches while preserving input order."""
    if not texts:
        raise ValueError(
            "No listing texts were provided for embedding."
        )

    all_embeddings: list[list[float]] = []

    total_batches = (
        len(texts) + batch_size - 1
    ) // batch_size

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        batch_number = start // batch_size + 1

        print(
            f"Embedding batch {batch_number}/{total_batches} "
            f"({len(batch)} listings)..."
        )

        batch_embeddings = provider.embed_documents(batch)

        if len(batch_embeddings) != len(batch):
            raise RuntimeError(
                "Embedding response count does not match "
                "input batch count."
            )

        all_embeddings.extend(batch_embeddings)

    embeddings = np.asarray(
        all_embeddings,
        dtype=np.float32,
    )

    if embeddings.ndim != 2:
        raise RuntimeError(
            "Expected a 2D embedding matrix, "
            f"received shape {embeddings.shape}."
        )

    if embeddings.shape[0] != len(texts):
        raise RuntimeError(
            "Final embedding row count does not match "
            "listing text count."
        )

    if not np.isfinite(embeddings).all():
        raise RuntimeError(
            "Embedding matrix contains NaN or infinite values."
        )

    return embeddings


def json_safe(value: Any) -> Any:
    """Recursively convert values into JSON-serializable objects."""
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def write_metadata_jsonl(
    output_path: Path,
    metadata: list[dict[str, Any]],
) -> None:
    """Save one metadata record per embedding row."""
    temporary_path = output_path.with_suffix(
        f"{output_path.suffix}.tmp"
    )

    with temporary_path.open("w", encoding="utf-8") as file:
        for row_index, record in enumerate(metadata):
            serializable_record = {
                "embedding_row": row_index,
                **{
                    key: json_safe(value)
                    for key, value in record.items()
                },
            }
            file.write(
                json.dumps(
                    serializable_record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    os.replace(temporary_path, output_path)


def save_artifacts(
    output_dir: Path,
    embeddings: np.ndarray,
    metadata: list[dict[str, Any]],
    model: str,
    batch_size: int,
) -> None:
    """Persist embeddings, aligned metadata, and generation information."""
    output_dir.mkdir(parents=True, exist_ok=True)

    embeddings_path = output_dir / "listing_embeddings.npy"
    metadata_path = output_dir / "listing_metadata.jsonl"
    manifest_path = output_dir / "embedding_manifest.json"

    temporary_embeddings_path = output_dir / "listing_embeddings.tmp.npy"
    np.save(temporary_embeddings_path, embeddings)
    os.replace(temporary_embeddings_path, embeddings_path)

    write_metadata_jsonl(metadata_path, metadata)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "embedding_model": model,
        "listing_count": int(embeddings.shape[0]),
        "embedding_dimension": int(embeddings.shape[1]),
        "batch_size": batch_size,
        "embedding_dtype": str(embeddings.dtype),
        "embeddings_file": embeddings_path.name,
        "metadata_file": metadata_path.name,
        "metadata_alignment": (
            "metadata embedding_row equals the corresponding row "
            "in listing_embeddings.npy"
        ),
    }

    temporary_manifest_path = manifest_path.with_suffix(".json.tmp")

    with temporary_manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    os.replace(temporary_manifest_path, manifest_path)

    print("\nEmbedding artifacts created successfully:")
    print(f"  Embeddings: {embeddings_path}")
    print(f"  Metadata:   {metadata_path}")
    print(f"  Manifest:   {manifest_path}")
    print(f"  Shape:      {embeddings.shape}")
    print(f"  Dtype:      {embeddings.dtype}")

def get_checkpoint_dir(
    output_dir: Path,
) -> Path:
    return output_dir / CHECKPOINT_DIRNAME


def get_checkpoint_state_path(
    output_dir: Path,
) -> Path:
    return output_dir / CHECKPOINT_STATE_FILENAME


def load_checkpoint_state(
    output_dir: Path,
) -> dict[str, Any]:
    state_path = get_checkpoint_state_path(
        output_dir
    )

    if not state_path.exists():
        return {
            "completed_batches": 0,
            "completed_listing_ids": [],
        }

    with state_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        state = json.load(file)

    return state


def save_checkpoint_state(
    output_dir: Path,
    state: dict[str, Any],
) -> None:
    state_path = get_checkpoint_state_path(
        output_dir
    )

    temporary_path = state_path.with_suffix(
        ".json.tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            state,
            file,
            indent=2,
        )

    os.replace(
        temporary_path,
        state_path,
    )

def write_batch_checkpoint(
    output_dir: Path,
    batch_number: int,
    embeddings: np.ndarray,
    metadata: list[dict[str, Any]],
) -> None:
    checkpoint_dir = get_checkpoint_dir(
        output_dir
    )

    checkpoint_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    embedding_path = (
        checkpoint_dir
        / f"embeddings_{batch_number:06d}.npy"
    )

    metadata_path = (
        checkpoint_dir
        / f"metadata_{batch_number:06d}.jsonl"
    )

    temporary_embedding_path = (
        checkpoint_dir
        / f"embeddings_{batch_number:06d}.tmp.npy"
    )

    np.save(
        temporary_embedding_path,
        embeddings,
    )

    os.replace(
        temporary_embedding_path,
        embedding_path,
    )

    temporary_metadata_path = (
        metadata_path.with_suffix(
            ".jsonl.tmp"
        )
    )

    with temporary_metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        for record in metadata:
            safe_record = {
                key: json_safe(value)
                for key, value in record.items()
            }

            file.write(
                json.dumps(
                    safe_record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    os.replace(
        temporary_metadata_path,
        metadata_path,
    )

def consolidate_checkpoints(
    output_dir: Path,
    model: str,
    batch_size: int,
) -> None:
    checkpoint_dir = get_checkpoint_dir(
        output_dir
    )

    embedding_files = sorted(
        checkpoint_dir.glob(
            "embeddings_*.npy"
        )
    )

    metadata_files = sorted(
        checkpoint_dir.glob(
            "metadata_*.jsonl"
        )
    )

    if not embedding_files:
        raise RuntimeError(
            "No embedding checkpoints were found."
        )

    if len(embedding_files) != len(
        metadata_files
    ):
        raise RuntimeError(
            "Embedding checkpoint count does not "
            "match metadata checkpoint count."
        )

    embedding_parts: list[np.ndarray] = []
    metadata: list[dict[str, Any]] = []

    for embedding_path, metadata_path in zip(
        embedding_files,
        metadata_files,
    ):
        batch_embeddings = np.load(
            embedding_path
        )

        if batch_embeddings.ndim != 2:
            raise RuntimeError(
                f"Invalid checkpoint shape: "
                f"{embedding_path}"
            )

        embedding_parts.append(
            batch_embeddings
        )

        with metadata_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                if not line.strip():
                    continue

                metadata.append(
                    json.loads(line)
                )

    embeddings = np.concatenate(
        embedding_parts,
        axis=0,
    ).astype(
        np.float32,
        copy=False,
    )

    if embeddings.shape[0] != len(
        metadata
    ):
        raise RuntimeError(
            "Consolidated embedding count does "
            "not match metadata count."
        )

    listing_ids = [
        str(record["listing_id"])
        for record in metadata
        if record.get("listing_id") is not None
    ]

    if len(listing_ids) != len(
        set(listing_ids)
    ):
        raise RuntimeError(
            "Duplicate listing IDs detected across "
            "embedding checkpoints."
        )

    # Reassign final global embedding_row values.
    for row_index, record in enumerate(
        metadata
    ):
        record["embedding_row"] = (
            row_index
        )

    save_artifacts(
        output_dir=output_dir,
        embeddings=embeddings,
        metadata=metadata,
        model=model,
        batch_size=batch_size,
    )

def generate_embeddings_with_checkpoints(
    provider: BaseEmbeddingProvider,
    texts: list[str],
    metadata: list[dict[str, Any]],
    output_dir: Path,
    batch_size: int,
    resume: bool,
) -> None:
    if not texts:
        raise ValueError(
            "No listing texts were provided."
        )

    if len(texts) != len(metadata):
        raise RuntimeError(
            "Text and metadata counts do not match."
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint_dir = get_checkpoint_dir(
        output_dir
    )

    if (
        checkpoint_dir.exists()
        and any(checkpoint_dir.iterdir())
        and not resume
    ):
        raise RuntimeError(
            "Checkpoint directory already contains files. "
            "Use --resume to continue or choose a new "
            "--output-dir."
        )

    state_path = get_checkpoint_state_path(
        output_dir
    )

    if resume and not state_path.exists():
        raise RuntimeError(
            "Cannot resume because checkpoint_state.json "
            "does not exist."
        )

    state = (
        load_checkpoint_state(
            output_dir
        )
        if resume
        else {
            "completed_batches": 0,
            "completed_listing_ids": [],
        }
    )

    completed_listing_ids = {
        str(listing_id)
        for listing_id in state.get(
            "completed_listing_ids",
            []
        )
    }

    pending_records: list[
        tuple[str, dict[str, Any]]
    ] = []

    for text, record in zip(
        texts,
        metadata,
    ):
        listing_id = record.get(
            "listing_id"
        )

        if listing_id is None:
            continue

        normalized_id = str(
            listing_id
        )

        if normalized_id in completed_listing_ids:
            continue

        pending_records.append(
            (
                text,
                record,
            )
        )

    print(
        f"Already completed listings: "
        f"{len(completed_listing_ids)}"
    )

    print(
        f"Remaining listings: "
        f"{len(pending_records)}"
    )

    if not pending_records:
        print(
            "No remaining listings to embed."
        )
        return

    completed_batches = int(
        state.get(
            "completed_batches",
            0,
        )
    )

    total_pending_batches = (
        len(pending_records)
        + batch_size
        - 1
    ) // batch_size

    for start in range(
        0,
        len(pending_records),
        batch_size,
    ):
        batch_records = (
            pending_records[
                start : start + batch_size
            ]
        )

        batch_texts = [
            text
            for text, _ in batch_records
        ]

        batch_metadata = [
            record
            for _, record in batch_records
        ]

        checkpoint_batch_number = (
            completed_batches + 1
        )

        progress_number = (
            start // batch_size + 1
        )

        print(
            f"Embedding batch "
            f"{progress_number}/"
            f"{total_pending_batches} "
            f"({len(batch_texts)} listings)..."
        )

        raw_embeddings = (
            provider.embed_documents(
                batch_texts
            )
        )

        batch_embeddings = np.asarray(
            raw_embeddings,
            dtype=np.float32,
        )

        if batch_embeddings.ndim != 2:
            raise RuntimeError(
                "Expected a 2D batch embedding matrix."
            )

        if (
            batch_embeddings.shape[0]
            != len(batch_metadata)
        ):
            raise RuntimeError(
                "Embedding response count does "
                "not match batch metadata count."
            )

        if not np.isfinite(
            batch_embeddings
        ).all():
            raise RuntimeError(
                "Batch embeddings contain NaN "
                "or infinite values."
            )

        write_batch_checkpoint(
            output_dir=output_dir,
            batch_number=(
                checkpoint_batch_number
            ),
            embeddings=batch_embeddings,
            metadata=batch_metadata,
        )

        batch_listing_ids = [
            str(record["listing_id"])
            for record in batch_metadata
            if record.get(
                "listing_id"
            )
            is not None
        ]

        completed_listing_ids.update(
            batch_listing_ids
        )

        completed_batches += 1

        state = {
            "completed_batches": (
                completed_batches
            ),
            "completed_listing_ids": sorted(
                completed_listing_ids
            ),
            "updated_at_utc": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

        # Write state only AFTER the batch files
        # have been safely persisted.
        save_checkpoint_state(
            output_dir,
            state,
        )

        print(
            f"Checkpoint saved: "
            f"{len(completed_listing_ids)} "
            f"listings completed."
        )

def main() -> None:
    args = parse_args()

    provider = get_embedding_provider(
        model=args.model,
    )

    connection: MySQLConnection | None = None

    try:
        connection = get_database_connection()

        listings = load_listings(
            connection=connection,
            limit=args.limit,
        )

        if not listings:
            raise RuntimeError(
                "No eligible listings were returned from rets_property."
            )

        print(f"Loaded listings: {len(listings)}")

        texts, metadata = prepare_embedding_records(listings)

        if not texts:
            raise RuntimeError(
                "No valid embedding texts were generated."
            )

        print(f"Prepared embedding texts: {len(texts)}")
        print("\nSample embedding text:")
        print("-" * 80)
        print(texts[0])
        print("-" * 80)


        if args.checkpoint:
            generate_embeddings_with_checkpoints(
                provider=provider,
                texts=texts,
                metadata=metadata,
                output_dir=args.output_dir,
                batch_size=args.batch_size,
                resume=args.resume,
            )

            consolidate_checkpoints(
                output_dir=args.output_dir,
                model=args.model,
                batch_size=args.batch_size,
            )

        else:
            embeddings = generate_embeddings(
                provider=provider,
                texts=texts,
                batch_size=args.batch_size,
            )

            save_artifacts(
                output_dir=args.output_dir,
                embeddings=embeddings,
                metadata=metadata,
                model=args.model,
                batch_size=args.batch_size,
            )


    finally:
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()