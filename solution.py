import re

import pandas

# a column label = letters and underscores only, nothing else
LABEL = re.compile(r"[A-Za-z_]+")
# what's allowed in a role: labels, + - *, and spaces
TOKEN = re.compile(r"\s*([A-Za-z_]+|[+\-*])\s*")


def _tokenize(role):
    """Split the role into labels and operators. Returns None if something is off."""
    if not isinstance(role, str) or not role.strip():
        return None

    tokens = []
    pos = 0
    while pos < len(role):
        match = TOKEN.match(role, pos)
        if not match:
            return None  # some character we don't support, like & or a digit
        tokens.append(match.group(1))
        pos = match.end()

    # has to go label, op, label, op, label...
    if len(tokens) % 2 == 0:
        return None
    for i, token in enumerate(tokens):
        is_label = bool(LABEL.fullmatch(token))
        if (i % 2 == 0) != is_label:
            return None
    return tokens


def add_virtual_column(df: pandas.DataFrame, role: str, new_column: str) -> pandas.DataFrame:
    if not isinstance(new_column, str) or not LABEL.fullmatch(new_column):
        return pandas.DataFrame([])

    tokens = _tokenize(role)
    if tokens is None:
        return pandas.DataFrame([])

    labels = tokens[0::2]
    if any(label not in df.columns for label in labels):
        return pandas.DataFrame([])

    # do the multiplications first, then add/subtract left to right,
    # so "a + b * c" works like normal math
    terms = []  # list of (sign, value)
    sign = "+"
    current = df[tokens[0]]
    for op, label in zip(tokens[1::2], tokens[2::2]):
        if op == "*":
            current = current * df[label]
        else:
            terms.append((sign, current))
            sign = op
            current = df[label]
    terms.append((sign, current))

    result = None
    for sign, value in terms:
        if result is None:
            result = value
        elif sign == "+":
            result = result + value
        else:
            result = result - value

    out = df.copy()
    out[new_column] = result
    return out
