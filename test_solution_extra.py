import pandas as pd
import pytest

from solution import add_virtual_column


@pytest.fixture
def fruits():
    return pd.DataFrame({"name": ["banana", "apple"], "quantity": [10, 3], "price": [10, 1]})


def test_example_from_task(fruits):
    result = add_virtual_column(fruits, "quantity * price", "total")
    assert result["total"].tolist() == [100, 3]
    assert list(result.columns) == ["name", "quantity", "price", "total"]


def test_does_not_touch_the_input(fruits):
    add_virtual_column(fruits, "quantity * price", "total")
    assert "total" not in fruits.columns


def test_multiplication_goes_before_plus_and_minus():
    df = pd.DataFrame({"a": [2], "b": [3], "c": [4]})
    assert add_virtual_column(df, "a + b * c", "x")["x"].tolist() == [14]
    assert add_virtual_column(df, "a * b - c", "x")["x"].tolist() == [2]


def test_minus_goes_left_to_right():
    df = pd.DataFrame({"a": [10], "b": [3], "c": [2]})
    assert add_virtual_column(df, "a - b - c", "x")["x"].tolist() == [5]


def test_single_column_is_just_a_copy():
    df = pd.DataFrame({"a": [1, 2]})
    assert add_virtual_column(df, "a", "b")["b"].tolist() == [1, 2]


def test_same_column_twice():
    df = pd.DataFrame({"a": [3]})
    assert add_virtual_column(df, "a*a", "sq")["sq"].tolist() == [9]


def test_floats():
    df = pd.DataFrame({"qty": [2], "price": [1.5], "disc": [0.5]})
    assert add_virtual_column(df, "qty * price - disc", "rev")["rev"].tolist() == [2.5]


def test_existing_column_gets_overwritten():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = add_virtual_column(df, "a + a", "b")
    assert result["b"].tolist() == [2]
    assert list(result.columns) == ["a", "b"]


def test_empty_df_with_columns_still_works():
    df = pd.DataFrame({"a": pd.Series([], dtype=int), "b": pd.Series([], dtype=int)})
    result = add_virtual_column(df, "a + b", "c")
    assert list(result.columns) == ["a", "b", "c"]


@pytest.mark.parametrize("role", [
    "",
    "   ",
    "a +",
    "+ a",
    "a b",
    "a + + b",
    "a / b",
    "a + 2",
    "a ** b",
    "(a + b)",
    "a & b",
    "a+b;",
    "missing + a",
    None,
])
def test_bad_role_gives_empty_df(role):
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert add_virtual_column(df, role, "c").empty


@pytest.mark.parametrize("new_column", ["c3", "new column", "", "c-d", "żółw", None])
def test_bad_new_column_gives_empty_df(new_column):
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert add_virtual_column(df, "a + b", new_column).empty


def test_column_label_with_digit_in_df_cant_be_used():
    df = pd.DataFrame({"a1": [1], "b": [2]})
    assert add_virtual_column(df, "a1 + b", "c").empty
