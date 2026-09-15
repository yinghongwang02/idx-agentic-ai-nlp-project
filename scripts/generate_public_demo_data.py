from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


OUTPUT_PATH = Path("data/public_demo/sold_comps.csv")
RANDOM_SEED = 42

CITY_CONFIG = {
    "Irvine": {
        "postal_codes": ["92603", "92612", "92614", "92618", "92620"],
        "base_price": 1_350_000,
        "base_sqft": 2050,
    },
    "Pasadena": {
        "postal_codes": ["91101", "91104", "91105", "91107"],
        "base_price": 1_150_000,
        "base_sqft": 1900,
    },
    "San Diego": {
        "postal_codes": ["92101", "92103", "92109"],
        "base_price": 1_050_000,
        "base_sqft": 1750,
    },
    "Los Angeles": {
        "postal_codes": ["90026", "90042"],
        "base_price": 1_100_000,
        "base_sqft": 1800,
    },
}


def generate_demo_sold_comps() -> list[dict]:
    rng = random.Random(RANDOM_SEED)

    # Fixed anchor date keeps the public demo deterministic.
    anchor_date = date(2026, 9, 1)

    rows: list[dict] = []
    listing_counter = 1

    for city, config in CITY_CONFIG.items():
        # 72 sold comps per city:
        # enough observations for market trends and comparable matching.
        for index in range(72):
            days_ago = 5 + index * 4
            close_date = anchor_date - timedelta(days=days_ago)

            postal_code = rng.choice(config["postal_codes"])
            property_sub_type = rng.choice(
                [
                    "SingleFamilyResidence",
                    "SingleFamilyResidence",
                    "SingleFamilyResidence",
                    "Condominium",
                ]
            )

            bedrooms = rng.choice([2, 3, 3, 4, 4, 5])
            bathrooms = rng.choice([2, 2, 3, 3, 4])

            living_area = max(
                900,
                int(
                    config["base_sqft"]
                    + (bedrooms - 3) * 280
                    + rng.randint(-300, 300)
                ),
            )

            # Slight synthetic upward trend:
            # newer sales receive a modest premium.
            recency_factor = 1.0 + max(
                0,
                (180 - days_ago) / 180 * 0.025,
            )

            size_factor = living_area / config["base_sqft"]

            list_price = (
                config["base_price"]
                * size_factor
                * recency_factor
                * rng.uniform(0.94, 1.06)
            )

            sale_to_list = rng.uniform(0.965, 1.015)
            close_price = list_price * sale_to_list

            original_list_price = list_price * rng.uniform(
                1.00,
                1.04,
            )

            days_on_market = rng.randint(8, 55)

            association_fee = (
                rng.randint(350, 650)
                if property_sub_type == "Condominium"
                else 0
            )

            rows.append(
                {
                    "listing_key": (
                        f"DEMO-SOLD-{listing_counter:04d}"
                    ),
                    "city": city,
                    "postal_code": postal_code,
                    "unparsed_address": (
                        f"{100 + listing_counter} "
                        f"Synthetic Sold Example"
                    ),
                    "property_sub_type": property_sub_type,
                    "bedrooms_total": bedrooms,
                    "bathrooms_total_integer": bathrooms,
                    "living_area": living_area,
                    "list_price": round(list_price, 2),
                    "original_list_price": round(
                        original_list_price,
                        2,
                    ),
                    "close_price": round(close_price, 2),
                    "close_date": close_date.isoformat(),
                    "days_on_market": days_on_market,
                    "association_fee": association_fee,
                }
            )

            listing_counter += 1

    return rows


def main() -> None:
    rows = generate_demo_sold_comps()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(rows[0].keys())

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Generated {len(rows)} synthetic sold comps "
        f"at {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()