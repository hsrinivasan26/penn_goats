"""Named constants for the values that must never be typos.

Each inherits from `str`, so members ARE real strings: they work as dict keys,
serialize to JSON, and compare equal to their text ("index" == AssetClass.INDEX).
That makes them a drop-in over the plain strings we used before, while a typo
like GameOver.BANKRUPCY now fails loudly instead of silently.
"""

from enum import Enum


class GameOver(str, Enum):
    BANKRUPTCY = "bankruptcy"
    BURNOUT = "burnout"
    TIMEOUT = "timeout"
    WIN = "win"


class AssetClass(str, Enum):
    RISKFREE = "riskfree"
    INDEX = "index"
    GROWTH = "growth"
    CRYPTO = "crypto"
    HOME = "home"


class DebtKind(str, Enum):
    STUDENT = "student"
    MORTGAGE = "mortgage"
    CREDIT_CARD = "credit_card"
    AUTO = "auto"


class Housing(str, Enum):
    RENT = "rent"
    OWN = "own"
