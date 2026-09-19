"""
استراتژی RSI + بولینگر باند با فرکانس معامله بالاتر (تعداد معاملات بیشتر در ماه)
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    startup_candle_count = 50

    can_short = False

    # --- تنظیمات اندیکاتورها ---
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14

    # --- پارامترهای ورود ---
    # آستانه RSI آزادتر برای افزایش تعداد معاملات
    rsi_threshold = IntParameter(30, 50, default=45, space="buy", optimize=True)

    # --- جدول ROI ---
    minimal_roi = {
        "0": 0.04,     # ۴٪ سود
        "120": 0.02,   # ۲٪ سود بعد از ۲ ساعت
        "360": 0.01    # ۱٪ سود بعد از ۶ ساعت
    }

    # --- حد زیان منطقی ---
    stoploss = -0.03  # ۳ درصد حد زیان

    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # ۱. برگشت قیمت از زیر یا روی باند پایین به بالای آن
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. آستانه RSI مناسب
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # خروج در باند بالا یا RSI بالای ۶۸
                (dataframe["close"] >= dataframe["bb_upper"]) |
                (dataframe["rsi"] >= 68)
            ),
            "exit_long",
        ] = 1
        return dataframe
