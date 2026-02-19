"""
Strict enum definitions for trading rule classification
"""
from enum import Enum

class DrawdownType(Enum):
    TRAILING = "TRAILING"
    STATIC = "STATIC"
    EOD = "EOD"
    HYBRID = "HYBRID"

class PayoutFrequency(Enum):
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    ON_DEMAND = "ON_DEMAND"

class Status(Enum):
    OK = "OK"
    MISSING_DATA = "MISSING_DATA"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    FAILED = "FAILED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

class Platform(Enum):
    MT4 = "MT4"
    MT5 = "MT5"
    CTRADER = "CTRADER"
    NINJA_TRADER = "NINJA_TRADER"
    TRADING_VIEW = "TRADING_VIEW"
    PROPRIETARY = "PROPRIETARY"
    MULTIPLE = "MULTIPLE"
    UNKNOWN = "UNKNOWN"

class Broker(Enum):
    PURPLE_TRADING = "PURPLE_TRADING"
    EIGHTCAP = "EIGHTCAP"
    MATCH_TRADER = "MATCH_TRADER"
    TOPSTEP = "TOPSTEP"
    RITHMIC = "RITHMIC"
    CQG = "CQG"
    UNKNOWN = "UNKNOWN"
    MULTIPLE = "MULTIPLE"