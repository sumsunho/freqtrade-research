"""
استراتژی RSI + بولینگر باند (بالانس‌شده برای فرکانس معامله بیشتر)
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
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14
    EMA_PERIOD = 50

    # --- پارامترهای ورود ---
    rsi_threshold = IntParameter(30, 52, default=50, space="buy", optimize=False)

    # --- جدول ROI ساطع‌کننده سود ---
    minimal_roi = {
        "0": 0.03,      # ۳٪ سود سریع
        "120": 0.015,   # ۱.۵٪ سود بعد از ۲ ساعت
        "360": 0.008,   # ۰.۸٪ سود بعد از ۶ ساعت
        "720": 0
    }

    # --- حد زیان ---
    stoploss = -0.03    # ۳ درصد حد زیان

    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=self.EMA_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)
        dataframe["bb_middle"] = ma

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # ۱. نفوذ به زیر یا برخورد با باند پایین و برگشت
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. فیلتر روند انعطاف‌پذیر: EMA50 صعودی یا شیب مثبت آن
                (dataframe["ema50"] >= dataframe["ema50"].shift(2)) &
                
                # ۳. RSI مناسب برای خرید در اصلاح
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # خروج در برخورد به باند بالا یا RSI بالای ۶۳
                (dataframe["close"] >= dataframe["bb_upper"]) |
                (dataframe["rsi"] >= 63)
            ),
            "exit_long",
        ] = 1
        return dataframe
