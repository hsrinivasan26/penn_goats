# Named constants for the values that must never be typos


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
