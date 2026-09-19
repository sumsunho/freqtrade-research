"""
استراتژی بازنویسی شده RSI + بولینگر باند (Mean Reversion) + ROI سریع برای Freqtrade.
طراحی‌شده برای دریافت سیگنال‌های زیاد و خروج سریع در سود در تایم‌فریم‌های پایین (15m).
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "15m"
    startup_candle_count = 110

    can_short = False

    # --- ثابت‌های اندیکاتورها ---
    EMA_PERIOD = 50
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14
    VOLUME_MA_PERIOD = 20

    # --- پارامتر قابل Hyperopt (فضای buy) ---
    # آستانه RSI قابل تنظیم بین ۳۰ تا ۵۵
    rsi_threshold = IntParameter(30, 55, default=40, space="buy", optimize=True)

    # --- خروج پلکانی سریع (ROI) ---
    minimal_roi = {
        "0": 0.03,    # خروج فوری در ۳٪ سود
        "30": 0.02,   # خروج بعد از ۳۰ دقیقه در ۲٪ سود
        "60": 0.01    # خروج بعد از ۱ ساعت در ۱٪ سود
    }

    # --- حد زیان ثابت و منطقی ---
    stoploss = -0.03  # حد زیان ۳ درصدی

    # --- خاموش کردن Trailing Stop برای جلوگیری از گیر کردن پوزیشن‌ها ---
    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        dataframe["ema"] = ta.EMA(dataframe, timeperiod=self.EMA_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.BB_STD)
        dataframe["bb_upper"] = ma + (std * self.BB_STD)

        dataframe["volume_ma"] = dataframe["volume"].rolling(self.VOLUME_MA_PERIOD).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # ۱. کندل قبلی زیر یا روی باند پایین بوده، ولی کندل فعلی بالای باند بسته شده (شرط برگشت)
                (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1)) &
                (dataframe["close"] > dataframe["bb_lower"]) &
                
                # ۲. RSI زیر آستانه تعیین شده
                (dataframe["rsi"] < self.rsi_threshold.value) &
                
                # ۳. فیلتر حجم معامله
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
