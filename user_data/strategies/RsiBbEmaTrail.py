"""
استراتژی RSI + بولینگر باند با فیلتر روند ۴ ساعته
کد اصلاح‌شده - بدون خطای NameError
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    merge_informative_pair
)


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    informative_timeframe = "4h"
    startup_candle_count = 200

    can_short = False

    # --- تنظیمات اندیکاتورها ---
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14

    # --- پارامترهای ورود ---
    rsi_threshold = IntParameter(30, 48, default=42, space="buy", optimize=False)

    # --- جدول ROI ---
    minimal_roi = {
        "0": 0.04,      # ۴٪ سود
        "120": 0.02,    # ۲٪ سود بعد از ۲ ساعت
        "360": 0.01,    # ۱٪ سود بعد از ۶ ساعت
        "720": 0
    }

    # --- حد زیان منطقی ---
    stoploss = -0.035   # ۳.۵ درصد حد زیان

    trailing_stop = False

    def informative_pairs(self):
        # دریافت داده‌های ۴ ساعته برای فیلتر روند
        pairs = self.dp.current_whitelist()
        return [(pair, self.informative_timeframe) for pair in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ۱. اندیکاتورهای تایم‌فریم اصلی
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)
        dataframe["bb_middle"] = ma

        # ۲. دریافت داده ۴ ساعته و محاسبه EMA 200
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        informative["ema200"] = ta.EMA(informative, timeperiod=200)

        # ادغام ایمن داده‌های ۴ ساعته در تایم‌فریم اصلی
        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # نام ستون ادغام‌شده ۴ ساعته
        ema_4h_col = f"ema200_{self.informative_timeframe}"

        dataframe.loc[
            (
                # ۱. برگشت قیمت از زیر/روی باند پایین به بالای آن
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. فیلتر روند صعودی ۴ ساعته (قیمت بالای EMA 200 ۴ ساعته)
                (dataframe["close"] > dataframe[ema_4h_col]) &
                
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
