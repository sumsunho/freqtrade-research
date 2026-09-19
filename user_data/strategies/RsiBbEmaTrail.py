"""
استراتژی RSI + بولینگر باند (نسخه فرکانس بالا با مدیریت ریسک هوشمند)
designed for higher trade frequency with strict mean reversion logic
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

    # --- پارامترهای قابل بهینه‌سازی ---
    rsi_threshold = IntParameter(30, 52, default=48, space="buy", optimize=False)

    # --- جدول ROI ساطع‌کننده سود سریع ---
    minimal_roi = {
        "0": 0.035,     # ۳.۵٪ سود بلافاصله
        "60": 0.018,    # ۱.۸٪ سود بعد از ۱ ساعت
        "180": 0.008,   # ۰.۸٪ سود بعد از ۳ ساعت
        "360": 0        # خروج روی نقطه بزنگاه بعد از ۶ ساعت
    }

    # --- حد زیان کنترل‌شده ---
    stoploss = -0.025   # ۲.۵ درصد حد زیان برای خروج سریع در ریزش‌های شدید

    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)
        dataframe["bb_middle"] = ma

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # ۱. برگشت قیمت: کندل قبلی زیر/روی باند پایین و کندل فعلی بالاتر از باند پایین
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. آستانه RSI مناسب (زیر ۴۸)
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                # ۳. وجود حجم معاملات
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # خروج در برخورد به باند وسط/بالا یا RSI بالای ۶۲
                (dataframe["close"] >= dataframe["bb_middle"]) |
                (dataframe["rsi"] >= 62)
            ),
            "exit_long",
        ] = 1
        return dataframe
