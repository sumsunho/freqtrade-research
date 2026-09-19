"""
استراتژی بهینه‌شده RSI + بولینگر باند (Mean Reversion) + خروج هوشمند در باند بالا برای تایم‌فریم 1h.
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

    # --- پارامتر ورودی ---
    rsi_threshold = IntParameter(30, 50, default=42, space="buy", optimize=True)

    # --- ROI انعطاف‌پذیر ---
    minimal_roi = {
        "0": 0.05,     # ۵٪ سود در صورت جهش ناگهانی
        "180": 0.02,   # ۲٪ سود بعد از ۳ ساعت
        "360": 0.01    # ۱٪ سود بعد از ۶ ساعت
    }

    # --- حد زیان ---
    stoploss = -0.025  # ۲.۵ درصد

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
                # برگشت قیمت از زیر باند پایین به بالای آن
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                # فیلتر روند صعودی
                (dataframe["close"] > dataframe["ema200"]) &
                # آستانه RSI
                (dataframe["rsi"] < self.rsi_threshold.value) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # سیگنال خروج: برخورد قیمت به باند بالای بولینگر یا رسیدن RSI به اشباع خرید (۷۰)
                (dataframe["close"] >= dataframe["bb_upper"]) |
                (dataframe["rsi"] >= 70)
            ),
            "exit_long",
        ] = 1
        return dataframe
