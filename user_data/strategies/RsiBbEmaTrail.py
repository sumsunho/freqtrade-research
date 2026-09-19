"""
استراتژی نوسان‌گیری بهینه‌شده RSI + بولینگر باند
دارای فیلتر روند میان‌مدت (EMA 50) برای حفظ سودآوری و افزایش تعداد معاملات
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
    EMA_PERIOD = 50   # روند میان‌مدت به جای ۲۰۰ تا معاملات بیشتری تایید شوند
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14

    # --- پارامترهای ورود ---
    rsi_threshold = IntParameter(30, 50, default=42, space="buy", optimize=False)

    # --- جدول ROI پله‌ای ---
    minimal_roi = {
        "0": 0.05,      # ۵٪ سود بلافاصله
        "60": 0.025,    # ۲.۵٪ سود بعد از ۱ ساعت
        "180": 0.012,   # ۱.۲٪ سود بعد از ۳ ساعت
        "360": 0        # خروج روی نقطه بهینه بعد از ۶ ساعت
    }

    # --- حد زیان ---
    stoploss = -0.035   # حد زیان ۳.۵ درصد

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
                # ۱. برگشت قیمت از زیر باند پایین به بالای آن (شکست رو به بالا)
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. فیلتر روند میان‌مدت (قیمت بالای EMA 50 باشد یا EMA 50 شیب صعودی داشته باشد)
                (dataframe["close"] > dataframe["ema50"]) &
                
                # ۳. آستانه RSI (زیر ۴۲)
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # خروج در برخورد به باند بالا یا رسیدن RSI به ۶۸
                (dataframe["close"] >= dataframe["bb_upper"]) |
                (dataframe["rsi"] >= 68)
            ),
            "exit_long",
        ] = 1
        return dataframe
