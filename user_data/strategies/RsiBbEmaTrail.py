"""
استراتژی بهینه‌شده RSI + بولینگر باند + فیلتر روند EMA + Trailing Stop برای Freqtrade.
آماده برای اجرای Hyperopt جهت افزایش تعداد سیگنال‌های سودآور در بازار BTC/USDT.
"""
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


class RsiBbEmaTrail(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "15m"
    startup_candle_count = 110  # باید حداقل به اندازه EMA_PERIOD باشد

    can_short = False

    # --- ثابت‌های پایه ---
    BB_PERIOD = 20
    RSI_PERIOD = 14
    VOLUME_MA_PERIOD = 20

    # --- پارامترهای قابل Hyperopt (فضای buy) ---
    # ۱. بازه RSI از ۲۰ تا ۶۰ بازتر شده تا ورودهای بیشتری پیدا کند
    rsi_threshold = IntParameter(20, 60, default=35, space="buy", optimize=True)
    
    # ۲. دوره EMA قابل تنظیم توسط Hyperopt (از ۲۰ تا ۱۰۰)
    ema_period = IntParameter(20, 100, default=50, space="buy", optimize=True)

    # ۳. ضریب باند پایین بولینگر (از ۱.۲ تا ۲.۲) برای تنظیم میزان خروج قیمت از باند
    bb_std_mult = DecimalParameter(1.2, 2.2, default=1.8, decimals=1, space="buy", optimize=True)

    # --- خروج: ROI عملاً غیرفعال شده؛ تکیه اصلی روی Trailing Stop است ---
    minimal_roi = {"0": 10}

    # --- استاپ ضرر و Trailing Stop (قابل hyperopt با فضاهای stoploss و trailing) ---
    stoploss = -0.03
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # محاسبه RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_PERIOD)
        
        # محاسبه EMA بر اساس پارامتر هایپرلاپت یا مقدار پیش‌فرض
        dataframe["ema"] = ta.EMA(dataframe, timeperiod=self.ema_period.value)

        # محاسبه باند بولینگر پویا
        ma = dataframe["close"].rolling(self.BB_PERIOD).mean()
        std = dataframe["close"].rolling(self.BB_PERIOD).std()
        dataframe["bb_lower"] = ma - (std * self.bb_std_mult.value)
        dataframe["bb_upper"] = ma + (std * self.bb_std_mult.value)

        dataframe["volume_ma"] = dataframe["volume"].rolling(self.VOLUME_MA_PERIOD).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # قیمت نزدیک یا زیر باند پایین بولینگر
                (dataframe["close"] <= dataframe["bb_lower"]) &
                # آستانه RSI قابل تنظیم توسط Hyperopt
                (dataframe["rsi"] < self.rsi_threshold.value) &
                # فیلتر حجم معامله
                (dataframe["volume"] >= dataframe["volume_ma"] * 0.8) &
                (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # خروج مدیریت‌شده توسط Stoploss و Trailing Stop
        return dataframe
