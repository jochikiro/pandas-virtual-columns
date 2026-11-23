# Virtual columns

Solution for the recruitment task. `solution.py` has the `add_virtual_column` function and `pipeline.py` uses it to calculate revenue per region from `sales.csv`.

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## How to run

Pipeline:

```
python pipeline.py
```

It reads `sales.csv`, cleans it, and saves the totals to `revenue_by_region.csv`. It also prints how many rows each fix touched, which helped me while working on it.

Tests (the sample ones plus mine):

```
pytest
```

## add_virtual_column

The function checks the input first and returns an empty DataFrame if something is wrong. Otherwise it returns a copy of the df with the new column, the original one stays untouched. I didn't want to use `eval` on a string from the user, so the role is split into column names and operators and calculated with regular pandas operations.

Assumptions I made:

- The new column gets the name passed in `new_column`. The example in the task shows `price_total` but passes `"total"`. I think that's a typo, and the sample tests also expect the passed name.
- `*` is calculated before `+` and `-`, same as in normal math.
- The role can only contain column names, `+`, `-`, `*` and spaces. No numbers or brackets, since the task only mentions these three operations.
- I validate the labels used in the role and in `new_column`. Other columns in the df aren't checked because they're not used.
- If `new_column` already exists, it gets overwritten.

## Problems in sales.csv

The file has 1507 rows (not counting the first header). After cleaning there are 1500 orders. The numbers below are counted on the raw file.

- `Quantity ` header has a trailing space. I strip all column names and rename them to snake_case.
- The header is repeated in the middle of the file (1 row). Removed.
- There's a `TOTAL` row at the end (1 row). Removed, it's not an order.
- Region names with extra spaces or wrong case, like `" South"`, `EAST`, `west  ` (15 rows). Stripped and changed to title case.
- Quantity with a space as a thousands separator, like `1 762` (4 rows). Removed the space.
- Unit price with a comma instead of a dot, like `"59,00"` (7 rows). Replaced the comma.
- Empty discount (963 rows). Set to 0, since the task says empty means no discount.
- Missing unit price (4 rows). Filled with the price of the same product. Each product has exactly one price in the whole file, so there's no guessing here.
- Exact duplicates, same order ID and all values (5 rows). Kept one copy.
- Negative quantity (6 rows). Kept as returns.
- Quantity over 1000, while all other rows are between 1 and 40 (4 rows). Kept.

The last few needed a decision, so here's my reasoning:

- **Negative quantities** look like returns to me, so they lower the revenue. Dropping them or flipping the sign would be guessing.
- **The 1000+ quantities** look suspicious, but the `TOTAL` row at the end of the file only adds up if you read `1 762` as 1762 and count the negative rows as they are. So I think that's how the source system sees them. I added a test that checks this. These rows make up a big part of North's revenue though, so in a real project I'd ask someone about them.
- **Duplicates** I treated as an export bug, because order IDs are unique everywhere else.

Revenue is `quantity * unit_price - discount`, rounded to 2 decimals at the end.
