from src.search.mysql_sold_comp_repository import MySQLSoldCompRepository


def main() -> None:
    repository = MySQLSoldCompRepository()

    city = "Irvine"
    months = 12
    limit = 5

    comps = repository.find_recent_comps(
        city=city,
        months=months,
        limit=limit,
    )

    print("=" * 80)
    print("SOLD COMPS REPOSITORY TEST")
    print("=" * 80)

    print(f"City: {city}")
    print(f"Lookback months: {months}")
    print(f"Requested limit: {limit}")
    print(f"Returned comps: {len(comps)}")

    print("=" * 80)

    if not comps:
        print("No sold comps found.")
        return

    for index, comp in enumerate(comps, start=1):
        print(f"\nComp #{index}")
        print("-" * 80)

        print(f"Listing Key: {comp.listing_key}")
        print(f"Address: {comp.unparsed_address}")
        print(f"City: {comp.city}")
        print(f"Postal Code: {comp.postal_code}")
        print(f"Property Type: {comp.property_sub_type}")

        print(f"Bedrooms: {comp.bedrooms_total}")
        print(f"Bathrooms: {comp.bathrooms_total_integer}")
        print(f"Living Area: {comp.living_area}")

        print(f"Original List Price: {comp.original_list_price}")
        print(f"List Price: {comp.list_price}")
        print(f"Close Price: {comp.close_price}")
        print(f"Close Date: {comp.close_date}")

        print(f"Days on Market: {comp.days_on_market}")
        print(f"Association Fee: {comp.association_fee}")

    print("\n" + "=" * 80)
    print("SOLD COMPS TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()