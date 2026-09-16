from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.dev_build_listing_embeddings import (
    generate_embeddings,
    prepare_embedding_records,
    save_artifacts,
)
from src.providers.factory import get_embedding_provider


DEFAULT_INPUT_PATH = Path(
    "data/public_demo/active_listings.csv"
)

DEFAULT_OUTPUT_DIR = Path(
    "artifacts/public_demo"
)

DEFAULT_BATCH_SIZE = 15


def load_public_demo_listings(
    input_path: Path = DEFAULT_INPUT_PATH,
) -> list[dict[str, Any]]:
    """
    Load synthetic public-demo listings and adapt them to the
    legacy MLS field names expected by the production embedding
    text builder.
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Public demo listings not found: {input_path}"
        )

    listings: list[dict[str, Any]] = []

    with input_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            listings.append(
                {
                    "L_ListingID": row["listing_id"],
                    "L_DisplayId": row["listing_id"],
                    "L_Address": row["unparsed_address"],
                    "L_City": row["city"],
                    "L_State": "CA",
                    "L_Zip": row["postal_code"],
                    "L_SystemPrice": float(
                        row["list_price"]
                    ),
                    "L_Keyword2": int(
                        row["bedrooms_total"]
                    ),
                    "LM_Dec_3": int(
                        row["bathrooms_total_integer"]
                    ),
                    "LM_Int2_3": float(
                        row["living_area"]
                    ),
                    "L_Type_": row["property_sub_type"],
                    "DaysOnMarket": int(
                        row["days_on_market"]
                    ),
                    "AssociationFee": float(
                        row["association_fee"]
                    ),
                    "L_Remarks": row["public_remarks"],
                }
            )

    return listings


def main() -> None:
    listings = load_public_demo_listings()

    print(
        f"Loaded synthetic listings: {len(listings)}"
    )

    texts, metadata = prepare_embedding_records(
        listings
    )

    if not texts:
        raise RuntimeError(
            "No valid public-demo embedding texts were generated."
        )

    print(
        f"Prepared embedding texts: {len(texts)}"
    )

    print("\nSample embedding text:")
    print("-" * 80)
    print(texts[0])
    print("-" * 80)

    provider = get_embedding_provider()

    embeddings = generate_embeddings(
        provider=provider,
        texts=texts,
        batch_size=DEFAULT_BATCH_SIZE,
    )

    save_artifacts(
        output_dir=DEFAULT_OUTPUT_DIR,
        embeddings=embeddings,
        metadata=metadata,
        model=provider.model,
        batch_size=DEFAULT_BATCH_SIZE,
    )


if __name__ == "__main__":
    main()