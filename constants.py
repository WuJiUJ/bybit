from enum import Enum

SEARCH_HOURS = [23, 7, 15]
SEARCH_MINUTE = 58

FUTURES_TAKER_FEE = 0.0006
SPOT_TAKER_FEE = 0.0

POSITION_SIDE_LONG = "LONG"
POSITION_SIDE_SHORT = "SHORT"

ORDER_TAG_ENTRY = "ENTRY"
ORDER_TAG_EXIT = "EXIT"

POSITION_OBJECT_PATH = "/home/wuji/bot/bybit/position.pkl"
LOG_FILE_PATH = "/home/wuji/bot/bybit/logs/bot.log"


class OrderStatus(Enum):
    PENDING = "PENDING"
    CANCELED = "CANCELED"
    FILLED = "FILLED"


class MarketType(Enum):
    FUTURES = "FUTURES"
    SPOT = "SPOT"


class PositionStatus(Enum):
    PENDING = "PENDING"
    HOLDING = "HOLDING"
    FAILED = "FAILED"
    EXITED = "EXITED"


class ExitReason(Enum):
    FCD = "Funding Changed Direction"
    FBO = "Found Better Opportunity"
    FC = "FORCED CLOSE"


# bybit enums
SIDE_BUY = "Buy"
SIDE_SELL = "Sell"

ORDER_TYPE_MARKET = "MARKET"
FUTURES_ORDER_TYPE_MARKET = "Market"

GOOD_TILL_CANCEL = "GoodTillCancel"
IMMEDIATE_OR_CANCEL = "ImmediateOrCancel"
FILL_OR_KILL = "FillOrKill"
POST_ONLY = "PostOnly"

ONE_WAY_MODE = "MergedSingle"
HEDGE_MODE = "BothSide"

ACCOUNT_TYPE_SPOT = "SPOT"
ACCOUNT_TYPE_DERIVATIVE = "CONTRACT"
