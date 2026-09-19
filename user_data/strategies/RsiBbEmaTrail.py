"""
استراتژی بازنویسی شده RSI + بولینگر باند (Mean Reversion) + فیلتر روند EMA برای تایم‌فریم 1h.
طراحی‌شده برای بهبود نسبت سود به زیان (Risk-to-Reward) و حذف سیگنال‌های کاذب.
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    # تغییر تایم‌فریم به ۱ ساعته برای اعتبار بیشتر سیگنال‌ها
    timeframe = "1h"
    startup_candle_count = 210  # حداقل اندازه برای EMA 200

    can_short = False

    # --- تنظیمات اندیکاتورها ---
    EMA_PERIOD = 200  # فیلتر روند اصلی
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14

    # --- پارامتر قابل Hyperopt ---
    rsi_threshold = IntParameter(30, 50, default=42, space="buy", optimize=True)

    # --- ROI مناسب برای تایم‌فریم ۱ ساعته (هدف سودهای بزرگ‌تر) ---
    minimal_roi = {
        "0": 0.06,     # ۶٪ سود
        "120": 0.04,   # بعد از ۲ ساعت: ۴٪ سود
        "360": 0.02    # بعد از ۶ ساعت: ۲٪ سود
    }

    # --- حد زیان ۲.۵ درصدی ---
    stoploss = -0.025

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
                
                # ۲. ورود فقط در روند صعودی کلی (قیمت بالای EMA 200)
                (dataframe["close"] > dataframe["ema200"]) &
                
                # ۳. RSI در محدوده اشباع فروش یا برگشتی
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
