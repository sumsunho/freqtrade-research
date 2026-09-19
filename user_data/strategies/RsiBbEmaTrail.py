"""
استراتژی نهایی بهینه‌شده RSI + بولینگر باند (Mean Reversion)
بر اساس نتایج موفق Hyperopt (برآیند سودآور).
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    startup_candle_count = 210

    can_short = False

    # --- تنظیمات اندیکاتورها ---
    EMA_PERIOD = 200
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14

    # --- پارامترهای بهینه‌شده Buy از Hyperopt ---
    buy_params = {
        "rsi_threshold": 37,
    }

    rsi_threshold = IntParameter(30, 50, default=37, space="buy", optimize=False)

    # --- جدول ROI بهینه‌شده از Hyperopt ---
    minimal_roi = {
        "0": 0.118,
        "90": 0.101,
        "180": 0.042,
        "393": 0
    }

    # --- حد زیان (Stoploss) کنترل‌شده ---
    # برای جلوگیری از ریسک ۳۳ درصدی، استاپ‌لاوس روی ۴.۵٪ تنظیم شد
    stoploss = -0.045

    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=self.EMA_PERIOD)

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
                # ۲. ورود فقط در روند صعودی کلی (بالای EMA 200)
                (dataframe["close"] > dataframe["ema200"]) &
                # ۳. آستانه RSI بهینه‌شده (زیر ۳۷)
                (dataframe["rsi"] < self.rsi_threshold.value) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # سیگنال خروج: برخورد قیمت به باند بالای بولینگر یا رسیدن RSI به ۷۰
                (dataframe["close"] >= dataframe["bb_upper"]) |
                (dataframe["rsi"] >= 70)
            ),
            "exit_long",
        ] = 1
        return dataframe
