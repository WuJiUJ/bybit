from constants import *
from order import Order
from position import Position
from broker import Broker
from statistic import Statistic
from utils import to_skl, read_skl

import logging
import time
import pickle
import os


class Strategy:
    def __init__(self, total_cash, exchange):
        self.total_cash = total_cash
        self.exchange = exchange
        self.broker = Broker(self.exchange)
        if os.path.exists(POSITION_OBJECT_PATH):
            self.position = read_skl(POSITION_OBJECT_PATH)
        else:
            self.position = None
        self.usdt_per_trade = (self.total_cash * 0.95) / 2

    def execute(self, funding_rates, exec_time, is_close_only=None):
        self.exec_time = exec_time

        data = self.find_signal(funding_rates)
        # data["symbol"] = "ALGOUSDT"
        # data["is_signal"] = True
        # data["is_long_spot"] = True

        if self.position != None:
            position_funding_rate = funding_rates.loc[
                "predicted_funding_rate", self.position.symbol
            ]
            self._funding_rate_paid(position_funding_rate)
            if self.position.is_long_spot == (position_funding_rate < 0):
                self._exit_position(ExitReason.FCD)
            elif data["initial_fixed_profit_loss"] > abs(position_funding_rate) / 2:
                self._exit_position(ExitReason.FBO)
            elif is_close_only:
                self._exit_position(ExitReason.FC)

        if (
            self.position == None
            and not data.empty
            and data["is_signal"]
            and not is_close_only
        ):
            self.balance_fund()
            time.sleep(1)
            self._enter_position(
                data["symbol"],
                data["predicted_funding_rate"],
                data["is_long_spot"],
                data["max_loanable"],
            )

    def find_signal(self, df):
        df = df.loc["predicted_funding_rate"].to_frame()
        df["abs_predicted_funding_rate"] = abs(df["predicted_funding_rate"])
        df = df[
            (df["abs_predicted_funding_rate"] / 2) > SPOT_TAKER_FEE + FUTURES_TAKER_FEE
        ].reset_index(names=["symbol"])
        if df.empty:
            return df
        for i in range(df.shape[0]):
            symbol = df.loc[i, "symbol"]
            res = self.exchange.s_session.query_interest_quota(currency=symbol[0:-4])[
                "result"
            ]
            df.loc[i, "1h_interest_rate"] = float(res["interestRate"]) / 24 / 2
            df.loc[i, "loanable"] = float(res["loanAbleAmount"])
            df.loc[i, "max_loanable"] = float(res["maxLoanAmount"])
            df.loc[i, "tradeable_usdt"] = min(
                self.exchange.coin_qty_to_usdt_futures(
                    df.loc[i, "max_loanable"], symbol
                ),
                self.usdt_per_trade,
            )
            df.loc[i, "initial_fixed_profit_loss"] = (
                df.loc[i, "abs_predicted_funding_rate"] / 2
                - df.loc[i, "1h_interest_rate"] * 8 / 2
                - SPOT_TAKER_FEE
                - FUTURES_TAKER_FEE
            )
            df.loc[i, "expected_usdt_profit"] = (
                df.loc[i, "tradeable_usdt"] * 2 * df.loc[i, "initial_fixed_profit_loss"]
            )
            df.loc[i, "is_signal"] = df.loc[i, "expected_usdt_profit"] > 0
            df.loc[i, "is_long_spot"] = df.loc[i, "predicted_funding_rate"] > 0
        df = df[df["tradeable_usdt"] >= 15]
        df = df.sort_values(
            by=["expected_usdt_profit"],
            ascending=False,
        ).reset_index(drop=True)
        logging.info(str(df.to_dict("index")))
        if df.empty:
            return df
        else:
            return df.iloc[0]

    def _add_features(self, df):
        df["max_symbol"] = abs(df).idxmax(axis=1)
        df["max_funding_rate"] = df.apply(lambda x: x[x["max_symbol"]], axis=1)
        df["target_returns"] = abs(df["max_funding_rate"]) / 2
        df["margin_interest_1h"] = df["max_symbol"].apply(
            lambda x: self.exchange.get_1h_margin_interest(x[0:-4])
        )
        return df

    def _add_trading_signal(self, df):
        df["initial_fixed_profit_loss"] = (
            df["target_returns"]
            - SPOT_TAKER_FEE
            - FUTURES_TAKER_FEE
            - (df["margin_interest_1h"] * 8)
        )
        df["is_signal"] = df["initial_fixed_profit_loss"] > 0
        df["is_long_spot"] = df["max_funding_rate"] > 0
        return df

    def _funding_rate_paid(self, funding_rate):
        res = self.exchange.f_session.my_last_funding_fee(symbol=self.position.symbol)[
            "result"
        ]
        if res:
            funding_rate = res["funding_rate"]
            funding_fee = res["exec_fee"]
            payout_time = res["exec_time"]
            self.position.fundings.append((funding_rate, funding_fee, payout_time))
            self.position.funding_profit_loss += -funding_fee
            to_skl(POSITION_OBJECT_PATH, self.position)

    def _position_fail(self, action, source):
        self.position.status = PositionStatus.FAILED
        logging.error(
            f"failed to {action} position id {self.position.id} due to {source}"
        )
        logging.info(self.position.__str__())

    def _enter_position(self, target_symbol, target_rate, is_long_spot, max_loanable):
        self.position = Position(
            open_time=self.exec_time,
            symbol=target_symbol,
            total_usdt=self.usdt_per_trade * 2,
            is_long_spot=is_long_spot,
            entry_funding_rate=target_rate,
            exchange=self.exchange,
        )
        self.position.prepare_entry_orders(max_loanable)
        logging.info(f"entering position {self.position.id}...")
        self.broker.execute_margin_order(self.position.s_entry_order)
        if self.position.s_entry_order.status == OrderStatus.FILLED:
            self.broker.submit_order(self.position.f_entry_order)
            if self.position.f_entry_order.status == OrderStatus.FILLED:
                self.position.status = PositionStatus.HOLDING
                logging.info(f"entered position id {self.position.id} successfully")
                time.sleep(1)
                self.broker.get_latest_orders_info(
                    self.position.s_entry_order, self.position.f_entry_order
                )
                to_skl(POSITION_OBJECT_PATH, self.position)
            else:
                # execute spot order successfully but fail futures, i.e. reverse spot
                self.position.prepare_exit_orders()
                self.broker.execute_margin_order(
                    self.position.s_exit_order,
                    self.position.total_liability
                    if hasattr(self.position, "total_liability")
                    else None,
                )
                self._position_fail("enter", "futures fail")
        else:
            self._position_fail("enter", "margin fail")

    def _exit_position(self, reason):
        self.position.close_time = self.exec_time
        self.position.prepare_exit_orders()
        logging.info(f"exiting position {self.position.id}...")
        self.broker.execute_margin_order(
            self.position.s_exit_order,
            self.position.total_liability
            if hasattr(self.position, "total_liability")
            else None,
        )
        self.broker.submit_order(self.position.f_exit_order)
        if (
            self.position.s_exit_order.status == OrderStatus.FILLED
            and self.position.f_exit_order.status == OrderStatus.FILLED
        ):
            self.position.closing_reason = reason
            self.position.status = PositionStatus.EXITED
            logging.info(f"exited position {self.position.id} successfully")
            time.sleep(1)
            self.broker.get_latest_orders_info(
                self.position.s_exit_order, self.position.f_exit_order
            )
            self.position.calculate_position(self.exec_time)
            logging.info(self.position.__str__())
            POSITION_RECORD_PATH
            os.remove(POSITION_OBJECT_PATH)
        elif (
            self.position.s_exit_order.status != OrderStatus.FILLED
            and self.position.f_exit_order.status != OrderStatus.FILLED
        ):
            self._position_fail("exit", "both fail")
        elif self.position.s_exit_order.status != OrderStatus.FILLED:
            self._position_fail("exit", "margin fail")
        else:
            self._position_fail("exit", "futures fail")

    def balance_fund(self):
        # make 2 accounts have equal funds
        f_fund = self.exchange.get_wallet_available_balance(
            wallet_type="DERIVATIVES", coin="USDT"
        )
        s_fund = self.exchange.get_wallet_available_balance(
            wallet_type="SPOT", coin="USDT"
        )
        total_fund = s_fund + f_fund
        logging.info(Statistic(total_fund).__str__())
        each_fund = total_fund / 2
        if f_fund > s_fund:
            fund_to_transfer = str(round(f_fund - each_fund, 4))
            if fund_to_transfer != "0.0":
                self.exchange.transfer(
                    coin="USDT",
                    amount=fund_to_transfer,
                    from_account_type=ACCOUNT_TYPE_DERIVATIVE,
                    to_account_type=ACCOUNT_TYPE_SPOT,
                )
        else:
            fund_to_transfer = str(round(s_fund - each_fund, 4))
            if fund_to_transfer != "0.0":
                self.exchange.transfer(
                    coin="USDT",
                    amount=fund_to_transfer,
                    from_account_type=ACCOUNT_TYPE_SPOT,
                    to_account_type=ACCOUNT_TYPE_DERIVATIVE,
                )
