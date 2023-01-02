from constants import *
from order import Order
from utils import floor, ceil

import uuid
import json
import logging


class Position:
    def __init__(
        self,
        open_time,
        symbol,
        total_usdt,
        is_long_spot,
        entry_funding_rate,
        exchange,
    ):
        self.id = str(uuid.uuid4())
        self.open_time = open_time
        self.symbol = symbol
        self.total_usdt = total_usdt
        self.usdt_per_trade = total_usdt / 2
        self.exchange = exchange
        self.is_long_spot = is_long_spot
        self.entry_funding_rate = entry_funding_rate
        self.s_entry_order = None
        self.f_entry_order = None
        self.status = PositionStatus.PENDING
        self.funding_profit_loss = 0
        self.profit_loss = 0
        self.s_exit_order = None
        self.f_exit_order = None
        self.closing_reason = None
        self.fundings = []

    def __str__(self):
        return "Position: " + str(self.__dict__)

    def prepare_entry_orders(self, max_loanable):
        s_coin_qty = self.exchange.usdt_to_coin_qty_margin(
            self.usdt_per_trade, self.symbol
        )
        if not self.is_long_spot:
            s_coin_qty = min(s_coin_qty, max_loanable)
        actual_s_entry_usdt = self.exchange.coin_qty_to_usdt_margin(
            s_coin_qty, self.symbol
        )
        if not self.is_long_spot:
            f_coin_qty = self.exchange.usdt_to_coin_qty_futures(
                actual_s_entry_usdt, self.symbol
            )
        else:
            f_coin_qty = self.exchange.usdt_to_coin_qty_futures(
                self.usdt_per_trade, self.symbol
            )
        self.s_entry_order = Order(
            symbol=self.symbol,
            market=MarketType.SPOT,
            order_type=ORDER_TYPE_MARKET,
            side=SIDE_BUY if self.is_long_spot else SIDE_SELL,
            order_tag=ORDER_TAG_ENTRY,
            exchange=self.exchange,
            coin_qty=s_coin_qty,
            usdt_qty=actual_s_entry_usdt,
        )
        self.f_entry_order = Order(
            symbol=self.symbol,
            market=MarketType.FUTURES,
            order_type=FUTURES_ORDER_TYPE_MARKET,
            side=SIDE_SELL if self.is_long_spot else SIDE_BUY,
            order_tag=ORDER_TAG_ENTRY,
            exchange=self.exchange,
            coin_qty=f_coin_qty,
        )

    def prepare_exit_orders(self):
        if not self.is_long_spot:
            (
                self.coin_qty_to_buy_back,
                self.total_liability,
                self.loan,
                self.coin_margin_interest,
            ) = self.exchange.get_my_total_liability(self.symbol)
            self.usdt_margin_interest = self.exchange.coin_qty_to_usdt_margin(
                self.coin_margin_interest, self.symbol
            )
            actual_s_exit_usdt = self.exchange.cal_usdt_for_buying_spot(
                self.coin_qty_to_buy_back, self.symbol
            )
            # logging.info(f"{self.coin_qty_to_buy_back}, {actual_s_exit_usdt}")
        else:
            actual_s_exit_usdt = self.exchange.coin_qty_to_usdt_margin(
                self.s_entry_order.coin_qty, self.symbol
            )
        self.s_exit_order = Order(
            symbol=self.symbol,
            market=MarketType.SPOT,
            order_type=ORDER_TYPE_MARKET,
            side=SIDE_SELL if self.is_long_spot else SIDE_BUY,
            order_tag=ORDER_TAG_EXIT,
            exchange=self.exchange,
            coin_qty=floor(
                self.exchange.get_wallet_available_balance("SPOT", self.symbol[0:-4]),
                self.exchange.get_margin_precision(self.symbol)["base_precision"],
            )
            if self.is_long_spot
            else self.coin_qty_to_buy_back,
            usdt_qty=ceil(actual_s_exit_usdt, 1),
        )
        self.f_exit_order = Order(
            symbol=self.symbol,
            market=MarketType.FUTURES,
            order_type=FUTURES_ORDER_TYPE_MARKET,
            side=SIDE_BUY if self.is_long_spot else SIDE_SELL,
            order_tag=ORDER_TAG_EXIT,
            exchange=self.exchange,
            coin_qty=self.f_entry_order.coin_qty,
        )

    def calculate_position(self, time):
        self.fundings = json.dumps(self.fundings)
        self.spot_entry = self.s_entry_order.price
        self.futures_entry = self.f_entry_order.price
        self.spot_exit = self.s_exit_order.price
        self.futures_exit = self.f_exit_order.price

        # cal closing profit -> Todo: use value from exchange
        self.futures_closing_returns = 0
        data = self.exchange.f_session.closed_profit_and_loss(symbol="APEUSDT")["result"]["data"][0]
        if data["order_id"] == self.f_exit_order.id:
            self.futures_closing_returns = data["closed_pnl"]
            self.futures_entry = data["avg_exit_price"]
            self.futures_exit = data["avg_entry_price"]
        else:
            logging.info("closed_profit_and_loss for the futures position is not available yet")
        

        # cal spot commission
        # Todo: convert the commission to usdt as it's currently in the transacting coin (e.g. APE)
        s_trade_records = self.exchange.s_session.user_trade_records(
            symbol=self.symbol
        )["result"]
        self.spot_entry_commission = 0.0
        self.spot_exit_commission = 0.0        
        self.spot_closing_returns = 0
        entry_usdt_amount = 0
        exit_usdt_amount = 0
        for trade in s_trade_records:
            if trade["orderId"][0:-4] == self.s_entry_order.id[0:-4]:
                self.spot_entry_commission += float(trade["feeAmount"])
                entry_usdt_amount = float(trade["price"])*float(trade["qty"])
            elif trade["orderId"][0:-4] == self.s_exit_order.id[0:-4]:
                self.spot_exit_commission += float(trade["feeAmount"])
                exit_usdt_amount = float(trade["price"])*float(trade["qty"])
        if exit_usdt_amount and entry_usdt_amount:
            saf = 1 if self.is_long_spot else -1
            self.spot_closing_returns = saf * (exit_usdt_amount - entry_usdt_amount)

        # calculate futures commission
        f_trade_records = self.exchange.f_session.user_trade_records(
            symbol=self.symbol, exec_type="Trade"
        )["result"]["data"]
        self.futures_entry_commission = 0.0
        self.futures_exit_commission = 0.0
        for trade in f_trade_records:
            if trade["order_id"] == self.f_entry_order.id:
                self.futures_entry_commission += trade["exec_fee"]
            elif trade["order_id"] == self.f_exit_order.id:
                self.futures_exit_commission += trade["exec_fee"]

        self.closing_profit_loss = (
            self.futures_closing_returns + self.spot_closing_returns
        )
        self.holding_duration = time - self.open_time  # in msec
        self.margin_interest = (
            self.usdt_margin_interest if hasattr(self, "usdt_margin_interest") else 0.0
        )
        self.costs = (
            -self.futures_entry_commission
            - self.futures_exit_commission
            - self.spot_entry_commission
            - self.spot_exit_commission
            - self.margin_interest
        )
        self.profit_loss = (
            self.closing_profit_loss + self.costs + self.funding_profit_loss
        )
        self.close_time = time
        return self

    def cal_closing_profit_loss_manually(self):
        saf = 1 if self.is_long_spot else -1
        self.spot_closing_returns = (
            saf * ((self.spot_exit - self.spot_entry) / self.spot_entry) / 2
        ) * self.total_usdt
        faf = 1 if not self.is_long_spot else -1
        self.futures_closing_returns = (
            faf
            * ((1 / self.futures_entry - 1 / self.futures_exit) * self.futures_exit)
            / 2
        ) * self.total_usdt
