import json
from datetime import datetime
import time
import pandas as pd
import os
import logging

from constants import *
from strategy import Strategy
from exchange import Exchange
from utils import Gdrive


logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format="%(asctime)s: %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %Z",
    filemode="a",
)


class Bot:
    def __init__(self, cash=None):
        self.exchange = Exchange()
        if cash:
            self._cash = cash
        else:
            self._cash = self.exchange.get_wallet_available_balance(
                wallet_type="DERIVATIVES", coin="USDT"
            ) + self.exchange.get_wallet_available_balance(
                wallet_type="SPOT", coin="USDT"
            )
        self.strategy = Strategy(self._cash, self.exchange)
        self.trading_symbols = [
            "ETHUSDT",
            "COMPUSDT",
            "DOGEUSDT",
            "ENSUSDT",
            "SOLUSDT",
            "ETCUSDT",
            "FLOWUSDT",
            "BATUSDT",
            "ALGOUSDT",
            "GRTUSDT",
            "JASMYUSDT",
            "MANAUSDT",
            "GALAUSDT",
            "ICPUSDT",
            "TWTUSDT",
            "BNBUSDT",
            "LINKUSDT",
            "FTMUSDT",
            "XLMUSDT",
            "EOSUSDT",
            "LTCUSDT",
            "ARUSDT",
            "THETAUSDT",
            "TRXUSDT",
            "OPUSDT",
            "AXSUSDT",
            "AAVEUSDT",
            "USDCUSDT",
            "BTCUSDT",
            "FILUSDT",
            "CRVUSDT",
            "NEARUSDT",
            "ZILUSDT",
            "UNIUSDT",
            "DYDXUSDT",
            "MATICUSDT",
            "IMXUSDT",
            "WAVESUSDT",
            "APTUSDT",
            "GMTUSDT",
            "APEUSDT",
            "CHZUSDT",
            "SLPUSDT",
            "BICOUSDT",
            "XRPUSDT",
            "ZRXUSDT",
            "SANDUSDT",
            "BCHUSDT",
            "MASKUSDT",
            "DOTUSDT",
            "EGLDUSDT",
            "ADAUSDT",
            "AVAXUSDT",
            "YFIUSDT",
            "SUSHIUSDT",
            "ATOMUSDT",
        ]  # self.exchange.fetch_trading_symbols()
        self.current_fundings = None
        self.position = None

    def tried_to_exit_if_ordered_success(self):
        self.strategy.position.prepare_exit_orders()
        if self.strategy.position.s_entry_order.status == OrderStatus.FILLED:
            self.strategy.broker.execute_margin_order(
                self.strategy.position.s_exit_order
            )
        if self.strategy.position.f_entry_order.status == OrderStatus.FILLED:
            self.strategy.broker.submit_order(self.strategy.position.f_exit_order)
        if os.path.exists(POSITION_OBJECT_PATH):
            os.remove(POSITION_OBJECT_PATH)

    def run(self, config):
        try:
            if config == "start":
                self.start()
            elif config == "test":
                self.test()
        except Exception as e:
            logging.error(e)
        gdrive = Gdrive()
        gdrive.upload_file_to_gdrive("./logs/bot.log")
        # gdrive.upload_file_to_gdrive("./logs/clogs.log")
        # if self.strategy.position != None:
        #     # todo: close position when if exist and have not tried to close
        #     if self.strategy.position.status == PositionStatus.HOLDING:
        #         # entered successfully, but haven't tried to exit
        #         self.tried_to_exit_if_ordered_success()
        #     elif self.strategy.position.status == PositionStatus.FAILED and (
        #         self.strategy.position.s_exit_order == None
        #         or self.strategy.position.f_exit_order == None
        #     ):
        #         # never tried to exit
        #         self.tried_to_exit_if_ordered_success()

    def run_loop(self):
        logging.info("Bot started")
        self._is_running = True
        while self._is_running:
            dt = datetime.utcnow()
            ts = int(dt.timestamp() * 1000)
            self.current_time = ts
            if dt.hour in SEARCH_HOURS and dt.minute == SEARCH_MINUTE:
                # Todo: Keep track of the currently traded symbols. If a new one is added, make sure to try setting mode to One-Way before trading
                self.current_fundings = pd.DataFrame(
                    data={
                        symbol: self.exchange.fetch_funding_rate(symbol=symbol)
                        for symbol in self.trading_symbols
                    }
                )
                self.strategy.execute(
                    self.current_fundings.loc[["predicted_funding_rate"]],
                    self.current_time,
                )
                if self.strategy.position != None:
                    logging.info(self.strategy.position)
                time.sleep(7.9 * 60 * 60)
        logging.info(f"Bot stopped")

    def start(self):
        logging.info("Bot started")
        dt = datetime.utcnow()
        self.current_time = dt
        print(dt, "Bot started")
        self.current_fundings = pd.DataFrame(
            data={
                symbol: self.exchange.fetch_funding_rate(symbol=symbol)
                for symbol in self.trading_symbols
            }
        )
        self.strategy.execute(
            self.current_fundings.loc[["predicted_funding_rate"]],
            self.current_time,
        )
        if self.strategy.position != None:
            logging.info(self.strategy.position)
        print(dt, "Bot ended")
        logging.info(f"Bot stopped")

    def stop(self):
        logging.info(f"Bot stopping...")
        self._is_running = False

    def test(self):
        print("Start testing...")
        dt = datetime.utcnow()
        ts = int(dt.timestamp() * 1000)
        self.current_time = ts
        self.current_fundings = pd.DataFrame(
            data={
                symbol: self.exchange.fetch_funding_rate(symbol=symbol)
                for symbol in self.trading_symbols
            }
        )
        self.strategy.execute(
            self.current_fundings.loc[["predicted_funding_rate"]], self.current_time
        )
        time.sleep(5)
        self.strategy.execute(
            self.current_fundings.loc[["predicted_funding_rate"]],
            self.current_time,
            is_close_only=True,
        )
        print(f"Test ended")

    def try_setting_position_mode_to_One_Way(self):
        for symbol in self.trading_symbols:
            try:
                self.exchange.f_session.position_mode_switch(
                    symbol=symbol, mode="MergedSingle"
                )
            except Exception as e:
                print(symbol, e)

    def set_leverage_to_one(self):
        for symbol in self.trading_symbols:
            try:
                self.exchange.f_session.set_leverage(
                    symbol=symbol, buy_leverage=1, sell_leverage=1
                )
            except Exception as e:
                print(symbol, e)


if __name__ == "__main__":
    bot = Bot(60)
    bot.run("test")

# def start(self):
#     def on_message(ws, message):
#         # message received always delay by 1 sec
#         msg = json.loads(message)
#         self._current_frates["time"] = int(msg[0]["E"]) // 1000
#         for e in msg:
#             if e["s"] in self._current_frates["rates"]:
#                 self._current_frates["rates"][e["s"]] = float(e["r"])
#         dt = datetime.fromtimestamp(self._current_frates["time"])
#         # if dt.hour in SEARCH_HOURS and dt.minute == SEARCH_MINUTE:
#         is_signal, target_symbol, target_rate, is_long_spot = find_arb_opp(
#             self._current_frates["rates"]
#         )
#         print(is_signal, target_symbol, target_rate, is_long_spot)
#         if (
#             self.position != None
#             and self.position.status == PositionStatus.HOLDING
#             and dt.minute == 41
#         ):
#             position_funding_rate = self._current_frates["rates"][self.position.symbol]
#             fixed_cost = get_fixed_cost(target_symbol)
#             if self.position.is_long_spot == (position_funding_rate < 0):
#                 self._exit_position(ExitReason.FCD)
#             elif (
#                 fixed_cost
#                 and (abs(target_rate) / 2 - fixed_cost) > abs(position_funding_rate) / 2
#             ):
#                 self._exit_position(ExitReason.FBO)
#             else:
#                 self._exit_position("test")
#         if self.position == None and dt.minute == 40:  # and is_signal:
#             self._enter_position(
#                 "BTCUSDT",  # target_symbol,
#                 target_rate,
#                 is_long_spot,
#             )

#     ws = CustomSocket(FUNDING_RATE_SOCKET, on_message).ws
#     ws.run_forever()
