"""Enums are (str, Enum): drop-in strings with typo-safety. Plus: the state class rejects bad fields."""

import json
import pytest
from game.enums import GameOver, AssetClass, DebtKind, Housing
from game.state import new_game


def test_members_equal_their_string_value():
    assert AssetClass.INDEX == "index"
    assert GameOver.BANKRUPTCY == "bankruptcy"
    assert Housing.OWN == "own"
    assert DebtKind.CREDIT_CARD == "credit_card"


def test_members_work_as_dict_keys_interchangeably():
    s = new_game("A")
    s.investments[AssetClass.INDEX] = 500        # keyed by an enum member...
    assert s.investments["index"] == 500          # ...but a plain string finds the same slot
    assert "index" in s.investments


def test_serializes_to_plain_json():
    assert json.dumps(GameOver.WIN) == '"win"'


def test_enum_typos_fail_loudly():
    with pytest.raises(AttributeError):
        _ = GameOver.BANKRUPCY   # a typo errors instead of becoming a bad string


def test_state_rejects_misspelled_attributes():
    """The whole reason state is a slotted class: a misspelled field can't silently exist."""
    s = new_game("A")
    with pytest.raises(AttributeError):
        s.cahs = 100             # not 'cash' -> AttributeError, not a silent junk field
