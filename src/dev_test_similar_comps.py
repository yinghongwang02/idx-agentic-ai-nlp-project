from src.schemas.intent_schema import PropertyIntent
from src.search.mysql_search_repository import MySQLSearchRepository
from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository


def main() -> None:
    search_repository = MySQLSearchRepository()
    sold_comp_repository = MySQLSoldCompRepository()

    intent = PropertyIntent(
        city="Irvine",
        max_price=2000000,
        min_bedrooms=3,
    )

    listings = search_repository.search(
        intent=intent,
        limit=3,
    )

    if not listings:
        print("No active listings found.")
        return

    print("=" * 100)
    print("SIMILAR SOLD COMPS TEST")
    print("=" * 100)

    for index, listing in enumerate(listings, start=1):
        print(f"\nTARGET LISTING #{index}")
        print("-" * 100)

        print(f"Address: {listing.unparsed_address}")
        print(f"City: {listing.city}")
        print(f"Postal Code: {listing.postal_code}")
        print(f"Property Type: {listing.property_sub_type}")
        print(f"Bedrooms: {listing.bedrooms_total}")
        print(f"Bathrooms: {listing.bathrooms_total_integer}")
        print(f"Living Area: {listing.living_area}")
        print(f"List Price: {listing.list_price}")
        print(f"Days on Market: {listing.days_on_market}")

        print("\nMatching Criteria:")
        print(f"- City: {listing.city}")
        print(f"- Postal Code: {listing.postal_code}")
        print(f"- Property Type: {listing.property_sub_type}")

        if listing.bedrooms_total is not None:
            print(
                f"- Bedrooms: "
                f"{max(0, listing.bedrooms_total - 1)}"
                f"–{listing.bedrooms_total + 1}"
            )

        if listing.bathrooms_total_integer is not None:
            print(
                f"- Bathrooms: "
                f"{max(0, listing.bathrooms_total_integer - 1)}"
                f"–{listing.bathrooms_total_integer + 1}"
            )

        if (
            listing.living_area is not None
            and listing.living_area > 0
        ):
            minimum_sqft = listing.living_area * 0.80
            maximum_sqft = listing.living_area * 1.20

            print(
                f"- Living Area: "
                f"{minimum_sqft:,.0f}"
                f"–{maximum_sqft:,.0f} sqft"
            )

        result = sold_comp_repository.find_similar_comps(
            listing=listing,
            months=12,
            limit=100,
            minimum_comps=5,
        )

        comps = result.comps

        print(
            f"\nMatch Level: "
            f"{result.match_level}"
        )

        print(
            f"Matched Comparable Count: "
            f"{result.comp_count}"
        )

        for comp_index, comp in enumerate(
            comps[:5],
            start=1,
        ):
            print(f"\n  Comp #{comp_index}")
            print(f"  Address: {comp.unparsed_address}")
            print(f"  ZIP: {comp.postal_code}")
            print(f"  Property Type: {comp.property_sub_type}")
            print(f"  Bedrooms: {comp.bedrooms_total}")
            print(
                f"  Bathrooms: "
                f"{comp.bathrooms_total_integer}"
            )
            print(f"  Living Area: {comp.living_area}")
            print(f"  List Price: {comp.list_price}")
            print(f"  Close Price: {comp.close_price}")
            print(f"  Close Date: {comp.close_date}")
            print(f"  Days on Market: {comp.days_on_market}")

            if (
                comp.close_price is not None
                and comp.living_area is not None
                and comp.living_area > 0
            ):
                price_per_sqft = (
                    comp.close_price / comp.living_area
                )

                print(
                    f"  Sold Price per Sqft: "
                    f"${price_per_sqft:,.2f}"
                )

        print("\n" + "=" * 100)

    print("\nSIMILAR SOLD COMPS TEST COMPLETED")
    print("=" * 100)


if __name__ == "__main__":
    main()