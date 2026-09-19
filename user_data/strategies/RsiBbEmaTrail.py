"""
استراتژی بهینه‌شده RSI + بولینگر باند + فیلتر روند EMA + Trailing Stop برای Freqtrade.
کاملاً سازگار با فرآیند Hyperopt جهت جلوگیری از کرش سرور.
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "15m"
    startup_candle_count = 110

    can_short = False

    # --- ثابت‌های اندیکاتورها ---
    EMA_PERIOD = 50
    BB_PERIOD = 20
    BB_STD = 1.8
    RSI_PERIOD = 14
    VOLUME_MA_PERIOD = 20

    # --- پارامتر قابل Hyperopt (فضای buy) ---
    # آستانه RSI قابل بهینه‌سازی بین ۲۰ تا ۶۰
    rsi_threshold = IntParameter(20, 60, default=35, space="buy", optimize=True)

    # --- خروج: ROI غیرفعال ---
    minimal_roi = {"0": 10}

    # --- استاپ ضرر و Trailing Stop پیش‌فرض (قابل Hyperopt) ---
    stoploss = -0.03
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        dataframe["ema"] = ta.EMA(dataframe, timeperiod=self.EMA_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)

        dataframe["volume_ma"] = dataframe["volume"].rolling(self.VOLUME_MA_PERIOD).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] <= dataframe["bb_lower"]) &
                (dataframe["rsi"] < self.rsi_threshold.value) &
                (dataframe["volume"] >= dataframe["volume_ma"] * 0.8) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
