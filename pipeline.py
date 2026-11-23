"""Read sales.csv, clean it up, add revenue, write revenue per region."""
import sys

import pandas as pd

from solution import add_virtual_column

INPUT = "sales.csv"
OUTPUT = "revenue_by_region.csv"

COLUMNS = {
    "Order ID": "order_id",
    "Region": "region",
    "Product": "product",
    "Quantity": "quantity",
    "Unit Price": "unit_price",
    "Discount": "discount",
    "Order Date": "order_date",
}


def to_number(series):
    """'1 762' -> 1762, '59,00' -> 59.0, '' -> NaN"""
    cleaned = series.str.replace(r"\s+", "", regex=True).str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned.mask(cleaned == ""), errors="raise")


def clean(raw):
    """Takes the raw file (everything as text), returns a clean df + what got fixed."""
    report = {}
    df = raw.copy()

    # header has "Quantity " with a trailing space, so strip all names
    df.columns = df.columns.str.strip()
    df = df.rename(columns=COLUMNS)

    # header got pasted again in the middle of the file
    is_header = df["order_id"] == "Order ID"
    report["repeated header rows"] = int(is_header.sum())
    df = df[~is_header]

    # TOTAL row at the bottom, it's not an order
    is_total = df["order_id"].str.upper() == "TOTAL"
    report["TOTAL rows"] = int(is_total.sum())
    df = df[~is_total]

    for col in df.columns:
        df[col] = df[col].str.strip()

    # " South", "EAST", "west  " etc. -> "South", "East", "West"
    fixed_region = df["region"].str.title()
    report["messy region names"] = int((raw.loc[df.index, "Region"] != fixed_region).sum())
    df["region"] = fixed_region

    raw_qty = df["quantity"]
    raw_price = df["unit_price"]
    report["quantity with a space as thousands separator"] = int(raw_qty.str.contains(" ").sum())
    report["unit price with a comma as decimal"] = int(raw_price.str.contains(",").sum())

    df["quantity"] = to_number(raw_qty)
    df["unit_price"] = to_number(raw_price)
    df["discount"] = to_number(df["discount"])

    # empty discount just means no discount
    report["empty discount (set to 0)"] = int(df["discount"].isna().sum())
    df["discount"] = df["discount"].fillna(0.0)

    # every product has one fixed price in this file, so fill gaps from that
    missing_price = df["unit_price"].isna()
    report["missing unit price (filled from product price)"] = int(missing_price.sum())
    product_price = df.loc[~missing_price].groupby("product")["unit_price"].agg(lambda s: s.mode()[0])
    df["unit_price"] = df["unit_price"].fillna(df["product"].map(product_price))
    if df["unit_price"].isna().any():
        raise ValueError("couldn't figure out a price for some rows")

    # same line twice (same order id and everything) -> keep one
    dupes = df.duplicated()
    report["exact duplicate rows (removed)"] = int(dupes.sum())
    df = df[~dupes]

    # negative quantity = a return, we keep it, it lowers revenue
    report["negative quantity (kept as returns)"] = int((df["quantity"] < 0).sum())
    # normal lines are 1-40 pcs, a few are 1000+. weird but the TOTAL row counts them, so we keep them
    report["huge quantity over 1000 (kept)"] = int((df["quantity"] > 1000).sum())

    df["quantity"] = df["quantity"].astype("int64")
    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d")

    return df.reset_index(drop=True), report


def revenue_by_region(df):
    with_revenue = add_virtual_column(df, "quantity * unit_price - discount", "revenue")
    if with_revenue.empty:
        raise ValueError("add_virtual_column returned an empty df, check the role")
    totals = with_revenue.groupby("region", as_index=False)["revenue"].sum()
    totals["revenue"] = totals["revenue"].round(2)
    return totals.sort_values("region").reset_index(drop=True)


def main(input_path=INPUT, output_path=OUTPUT):
    # read everything as text so pandas doesn't guess and break stuff
    raw = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    df, report = clean(raw)
    totals = revenue_by_region(df)
    totals.to_csv(output_path, index=False)

    print(f"rows in file: {len(raw)}, clean rows: {len(df)}")
    for problem, count in report.items():
        print(f"  {problem}: {count}")
    print()
    print(totals.to_string(index=False))
    print(f"\nsaved to {output_path}")
    return totals


if __name__ == "__main__":
    main(*sys.argv[1:])
