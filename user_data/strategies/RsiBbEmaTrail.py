"""
استراتژی بهینه‌شده RSI + بولینگر باند
حل مشکل شرط متناقض EMA و فعال‌سازی مجدد سیگنال‌های ورود
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    startup_candle_count = 60

    can_short = False

    # --- تنظیمات اندیکاتورها ---
    EMA_PERIOD = 50
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14

    # --- پارامترهای ورود ---
    rsi_threshold = IntParameter(30, 50, default=45, space="buy", optimize=False)

    # --- جدول ROI ---
    minimal_roi = {
        "0": 0.04,
        "120": 0.02,
        "360": 0.01,
        "720": 0
    }

    # --- حد زیان ---
    stoploss = -0.035  # ۳.۵ درصد حد زیان

    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=self.EMA_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # ۱. برگشت قیمت از زیر باند پایین به بالای آن
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. فیلتر روند اصلاح‌شده: شیب مثبت EMA 50 (روند صعودی) یا قیمت بالای EMA 50
                (
                    (dataframe["ema50"] >= dataframe["ema50"].shift(3)) |
                    (dataframe["close"] > dataframe["ema50"])
                ) &
                
                # ۳. آستانه RSI مناسب
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # خروج در برخورد به باند بالا یا RSI بالای ۶۵
                (dataframe["close"] >= dataframe["bb_upper"]) |
                (dataframe["rsi"] >= 65)
            ),
            "exit_long",
        ] = 1
        return dataframe
