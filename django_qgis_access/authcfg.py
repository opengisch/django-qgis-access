"""The id of the QGIS authentication configuration of a user.

QGIS takes exactly seven alphanumeric characters for such an id: the three of the prefix
(`QGIS_ACCESS_AUTHCFG_PREFIX`) and four for the user id.

User ids below 10000 are written in decimal, zero-padded: user 42 gets `qgs0042`. Larger ids,
counted from 10000, are a lowercase letter followed by three base-36 digits: user 10000 gets
`qgsa000`, user 10036 `qgsa010`, user 56656 `qgsb000`. A letter never starts a decimal id, so
two users never share an id, and the ids of existing users never change as more users come.
This makes room for 1 223 056 users (ids up to 1 223 055); a larger id raises a ValueError.
"""

import re

from .conf import get_setting

DECIMAL_IDS = 10_000
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
LETTERS = DIGITS[10:]
MAX_USER_ID = DECIMAL_IDS + len(LETTERS) * len(DIGITS) ** 3 - 1

PREFIX_PATTERN = re.compile(r"[A-Za-z0-9]{3}")


def authcfg_id(user) -> str:
    """The id of the QGIS authentication configuration of `user`, e.g. `qgs0042`."""
    return get_setting("AUTHCFG_PREFIX") + encode_user_id(user.pk)


def encode_user_id(user_id: int) -> str:
    """Four alphanumeric characters that stand for `user_id` and no other."""
    if not 0 <= user_id <= MAX_USER_ID:
        raise ValueError(f"no QGIS authentication configuration id for user id {user_id} (0 to {MAX_USER_ID})")
    if user_id < DECIMAL_IDS:
        return f"{user_id:04d}"
    number = user_id - DECIMAL_IDS
    letter, rest = divmod(number, len(DIGITS) ** 3)
    digits = ""
    for _ in range(3):
        rest, digit = divmod(rest, len(DIGITS))
        digits = DIGITS[digit] + digits
    return LETTERS[letter] + digits


def is_valid_prefix(prefix) -> bool:
    return isinstance(prefix, str) and PREFIX_PATTERN.fullmatch(prefix) is not None
