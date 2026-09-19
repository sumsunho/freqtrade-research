"""
استراتژی RSI + بولینگر باند با فیلتر روند ۴ ساعته (کاهش نویز و حفظ فرکانس معامله)
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


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
        # دریافت داده‌های تایم‌فریم ۴ ساعته برای فیلتر روند کلان
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ۱. اندیکاتورهای تایم‌فریم اصلی (۱ ساعته)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)
        dataframe["bb_middle"] = ma

        # ۲. اندیکاتور تایم‌فریم ۴ ساعته برای فیلتر روند
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        informative["ema200_4h"] = ta.EMA(informative, timeperiod=200)

        # ادغام داده‌های ۴ ساعته با ۱ ساعته
        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # ۱. برگشت قیمت از زیر باند پایین به بالای آن در ۱ ساعته
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. روند کلان صعودی در ۴ ساعته (قیمت بالای EMA 200 ۴ ساعته)
                (dataframe["close"] > dataframe["ema200_4h_4h"]) &
                
                # ۳. آستانه RSI زیر ۴۲
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
