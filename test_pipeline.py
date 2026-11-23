from pathlib import Path

import pandas as pd
import pytest

from pipeline import clean, main, revenue_by_region, to_number

SALES = str(Path(__file__).parent / "sales.csv")
HEADER = "Order ID,Region,Product,Quantity ,Unit Price,Discount,Order Date\n"


def make_raw(tmp_path, body):
    path = tmp_path / "sales.csv"
    path.write_text(HEADER + body)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def test_to_number():
    s = pd.Series(["1 762", "59,00", "", "12.50", "-3"])
    result = to_number(s)
    assert result[0] == 1762
    assert result[1] == 59.0
    assert pd.isna(result[2])
    assert result[3] == 12.5
    assert result[4] == -3


def test_header_and_total_rows_are_removed(tmp_path):
    raw = make_raw(tmp_path,
        "SO-1,North,Mouse,2,10.00,,2026-01-01\n"
        "Order ID,Region,Product,Quantity ,Unit Price,Discount,Order Date\n"
        "SO-2,North,Mouse,1,10.00,,2026-01-02\n"
        "TOTAL,,,3,,0,\n")
    df, report = clean(raw)
    assert df["order_id"].tolist() == ["SO-1", "SO-2"]
    assert report["repeated header rows"] == 1
    assert report["TOTAL rows"] == 1


def test_regions_get_normalized(tmp_path):
    raw = make_raw(tmp_path,
        "SO-1, south,Mouse,1,10.00,,2026-01-01\n"
        "SO-2,EAST,Mouse,1,10.00,,2026-01-01\n"
        "SO-3,west  ,Mouse,1,10.00,,2026-01-01\n"
        "SO-4,North,Mouse,1,10.00,,2026-01-01\n")
    df, report = clean(raw)
    assert df["region"].tolist() == ["South", "East", "West", "North"]
    assert report["messy region names"] == 3


def test_numbers_get_parsed(tmp_path):
    raw = make_raw(tmp_path,
        'SO-1,North,Mouse,1 200,"29,50",,2026-01-01\n'
        "SO-2,North,Mouse,2,29.50,1.50,2026-01-01\n")
    df, _ = clean(raw)
    assert df["quantity"].tolist() == [1200, 2]
    assert df["unit_price"].tolist() == [29.5, 29.5]
    assert df["discount"].tolist() == [0.0, 1.5]


def test_missing_price_is_filled_from_same_product(tmp_path):
    raw = make_raw(tmp_path,
        "SO-1,North,Keyboard,1,89.00,,2026-01-01\n"
        "SO-2,North,Keyboard,2,,,2026-01-01\n"
        "SO-3,North,Mouse,1,29.50,,2026-01-01\n")
    df, report = clean(raw)
    assert df.loc[df["order_id"] == "SO-2", "unit_price"].item() == 89.0
    assert report["missing unit price (filled from product price)"] == 1


def test_missing_price_with_no_other_row_of_that_product_fails(tmp_path):
    raw = make_raw(tmp_path, "SO-1,North,Keyboard,1,,,2026-01-01\n")
    with pytest.raises(ValueError):
        clean(raw)


def test_duplicates_are_removed_but_negatives_stay(tmp_path):
    raw = make_raw(tmp_path,
        "SO-1,North,Mouse,2,10.00,,2026-01-01\n"
        "SO-1,North,Mouse,2,10.00,,2026-01-01\n"
        "SO-2,North,Mouse,-1,10.00,,2026-01-01\n")
    df, report = clean(raw)
    assert df["order_id"].tolist() == ["SO-1", "SO-2"]
    assert report["exact duplicate rows (removed)"] == 1
    assert report["negative quantity (kept as returns)"] == 1


def test_revenue_by_region(tmp_path):
    raw = make_raw(tmp_path,
        "SO-1,North,Mouse,2,10.00,1.00,2026-01-01\n"   # 19
        "SO-2,north,Mouse,1,10.00,,2026-01-01\n"       # 10
        "SO-3,South,Mouse,-1,10.00,,2026-01-01\n")     # -10 (return)
    df, _ = clean(raw)
    totals = revenue_by_region(df)
    assert totals.to_dict("records") == [
        {"region": "North", "revenue": 29.0},
        {"region": "South", "revenue": -10.0},
    ]


def test_real_file(tmp_path):
    out = tmp_path / "out.csv"
    totals = main(SALES, str(out))
    assert out.exists()
    assert sorted(totals["region"]) == ["Central", "East", "North", "South", "West"]
    saved = pd.read_csv(out)
    assert saved.equals(totals)


def test_real_file_matches_the_total_row():
    # the TOTAL row in the export counts the duplicates too,
    # so we compare against the data before dropping them
    raw = pd.read_csv(SALES, dtype=str, keep_default_na=False)
    total_row = raw[raw["Order ID"] == "TOTAL"].iloc[0]
    rows = raw[~raw["Order ID"].isin(["TOTAL", "Order ID"])]
    qty = to_number(rows["Quantity "]).sum()
    disc = to_number(rows["Discount"]).sum()
    assert qty == int(total_row["Quantity "])
    assert round(disc, 2) == float(total_row["Discount"])
