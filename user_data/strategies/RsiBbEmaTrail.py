"""
استراتژی RSI + بولینگر باند (بهینه‌شده برای تعداد معامله بالا و ورودهای دقیق)
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
    rsi_threshold = IntParameter(35, 55, default=48, space="buy", optimize=False)

    # --- جدول ROI ساطع‌کننده سود سریع ---
    minimal_roi = {
        "0": 0.035,     # ۳.۵٪ سود سریع
        "60": 0.02,     # ۲٪ سود بعد از ۱ ساعت
        "180": 0.01,    # ۱٪ سود بعد از ۳ ساعت
        "360": 0
    }

    # --- حد زیان ---
    stoploss = -0.03  # ۳ درصد حد زیان

    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ۱. RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        
        # ۲. EMA برای سنجش شیب روند
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)

        # ۳. بولینگر باند
        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)
        dataframe["bb_middle"] = ma

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # ۱. قیمت فعلی یا کندل قبل، باند پایین را لمس/شکسته باشد
                (
                    (dataframe["close"] <= dataframe["bb_lower"]) |
                    (dataframe["low"] <= dataframe["bb_lower"]) |
                    (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1))
                ) &
                
                # ۲. RSI در منطقه اشباع فروش یا پایین
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                # ۳. جلوگیری از خرید در ریزش‌های کندل‌های بدون حجم
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # خروج در برخورد به باند وسط/بالا یا RSI بالای ۶۰
                (dataframe["close"] >= dataframe["bb_middle"]) |
                (dataframe["rsi"] >= 60)
            ),
            "exit_long",
        ] = 1
        return dataframe
