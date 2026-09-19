"""
استراتژی RSI + بولینگر باند + فیلتر روند EMA + Trailing Stop برای Freqtrade.
معادل همون منطقی که روی USDTTMN (والکس) با اسکریپت بک‌تست دستی‌مون اعتبارسنجی کردیم،
این‌بار به فرمت استاندارد Freqtrade برای اجرا روی هر جفت‌ارزی (مثلاً BTC/USDT).

نکته: EMA_PERIOD / BB_PERIOD / BB_STD اینجا ثابت گذاشته شدن (نه hyperopt-پذیر) تا محاسبه
اندیکاتور ساده بمونه — این‌ها رو می‌تونی دستی عوض و دوباره بک‌تست کنی. rsi_threshold و
stoploss/trailing با دستور hyperopt قابل بهینه‌سازی خودکارن (فضاهای استاندارد freqtrade).

نحوه استفاده:
    این فایل رو توی user_data/strategies/RsiBbEmaTrail.py کپی کن، بعد:
        docker compose run --rm freqtrade backtesting --strategy RsiBbEmaTrail ...
        docker compose run --rm freqtrade hyperopt --strategy RsiBbEmaTrail --spaces buy stoploss trailing ...
"""
from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import IStrategy, IntParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "15m"
    startup_candle_count = 110  # باید حداقل به اندازه EMA_PERIOD + بافر کافی باشد

    can_short = False

    # --- ثابت‌های شکل اندیکاتور (پایه؛ می‌تونی دستی عوض و دوباره بک‌تست کنی) ---
    EMA_PERIOD = 100
    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14
    VOLUME_MA_PERIOD = 20

    # --- پارامتر قابل hyperopt (فضای buy) ---
    rsi_threshold = IntParameter(20, 55, default=35, space="buy", optimize=True)

    # --- خروج: ROI عملاً غیرفعال شده؛ تکیه اصلی روی Trailing Stop است ---
    minimal_roi = {"0": 10}  # ۱۰۰۰٪ - در عمل هیچ‌وقت معامله با ROI بسته نمی‌شود

    # --- استاپ ضرر ثابت (قابل hyperopt با فضای پیش‌فرض stoploss) ---
    stoploss = -0.02

    # --- Trailing Stop (قابل hyperopt با فضای پیش‌فرض trailing) ---
    # trailing_stop_positive = فاصله استاپ متحرک از قله
    # trailing_stop_positive_offset = آستانه سودی که باید برسه تا trailing فعال (armed) بشه
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.008
    trailing_stop_positive_offset = 0.01

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        dataframe["ema"] = ta.EMA(dataframe, timeperiod=self.EMA_PERIOD)

        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - std * self.BB_STD
        dataframe["bb_upper"] = ma + std * self.BB_STD

        dataframe["volume_ma"] = dataframe["volume"].rolling(self.VOLUME_MA_PERIOD).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] <= dataframe["bb_lower"]) &
                (dataframe["rsi"] < self.rsi_threshold.value) &
                (dataframe["close"] > dataframe["ema"]) &            # فیلتر روند صعودی
                (dataframe["volume"] >= dataframe["volume_ma"] * 0.8) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # خروج فقط با Stoploss/Trailing Stop انجام می‌شود؛ سیگنال فروش جداگانه‌ای نداریم
        return dataframe
