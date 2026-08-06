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
from openai import OpenAI

from src.config.settings import settings
from src.embeddings.listing_text import build_listing_embedding_text


DEFAULT_MODEL = "text-embedding-3-small"
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

    args = parser.parse_args()

    if args.limit <= 0:
        parser.error("--limit must be greater than zero.")

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero.")

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
    client: OpenAI,
    texts: list[str],
    model: str,
    batch_size: int,
) -> np.ndarray:
    """Generate embeddings in batches while preserving input order."""
    if not texts:
        raise ValueError("No listing texts were provided for embedding.")

    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        batch_number = start // batch_size + 1
        total_batches = (len(texts) + batch_size - 1) // batch_size

        print(
            f"Embedding batch {batch_number}/{total_batches} "
            f"({len(batch)} listings)..."
        )

        response = client.embeddings.create(
            model=model,
            input=batch,
            encoding_format="float",
        )

        ordered_data = sorted(response.data, key=lambda item: item.index)
        batch_embeddings = [item.embedding for item in ordered_data]

        if len(batch_embeddings) != len(batch):
            raise RuntimeError(
                "Embedding response count does not match input batch count."
            )

        all_embeddings.extend(batch_embeddings)

    embeddings = np.asarray(all_embeddings, dtype=np.float32)

    if embeddings.ndim != 2:
        raise RuntimeError(
            f"Expected a 2D embedding matrix, received shape {embeddings.shape}."
        )

    if embeddings.shape[0] != len(texts):
        raise RuntimeError(
            "Final embedding row count does not match listing text count."
        )

    if not np.isfinite(embeddings).all():
        raise RuntimeError("Embedding matrix contains NaN or infinite values.")

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


def main() -> None:
    args = parse_args()

    client = OpenAI(api_key=settings.openai_api_key)
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

        embeddings = generate_embeddings(
            client=client,
            texts=texts,
            model=args.model,
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