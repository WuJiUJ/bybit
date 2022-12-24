from constants import *
import math
from decimal import Decimal


class Order:
    def __init__(
        self,
        symbol,
        market,
        order_type,
        side,
        order_tag,
        exchange,
        coin_qty,
        usdt_qty=None,  # only useful for spot market order
    ):
        self.id = None
        self.symbol = symbol
        self.market = market
        self.type = order_type
        self.side = side
        self.tag = order_tag
        self.exchange = exchange
        self.coin_qty = coin_qty
        self.exec_coin_qty = None
        self.usdt_qty = usdt_qty
        self.status = OrderStatus.PENDING
        self.loan_id = None
        self.price = None
        self.cancel_reason = None

    def __str__(self):
        return "Order: " + str(self.__dict__)

    def _cal_margin_usdt(self, qty):
        coin_price = self.exchange.get_spot_price(symbol=self.symbol)
        precision = 3
        return round(
            math.ceil((coin_price * qty) * (10**precision)) * (0.1**precision),
            precision,
        )

    def _cal_margin_qty(self, usdt):
        coin_price = self.exchange.get_spot_price(symbol=self.symbol)
        precision = self.exchange.get_margin_precision(self.symbol)["base_precision"]
        return float(round(usdt / coin_price, precision))

    def _cal_futures_qty(self, usdt):
        coin_price = self.exchange.get_futures_price(symbol=self.symbol)
        precision = self.exchange.get_futures_precision(self.symbol)
        return float(round(usdt / coin_price, precision))
        # mark price = fair price of a perpetual contract (Spot Liquidity Mid Price x 75% + BTSE Impact Mid Price x 25%)
        # index price = Average Spot Liquidity Mid Price of Major Exchanges

    def _get_my_margin_interest_amount(self):
        margin_interest = self.exchange.get_my_margin_interest_amount(
            coin=self.symbol[0:-4]
        )
        precision = self.exchange.get_margin_precision(self.symbol)["base_precision"]
        return round(
            math.ceil(margin_interest * (10**precision)) * (0.1**precision),
            precision,
        )

    def _get_my_liability(self):
        loan, interest = self.exchange.get_margin_loan_info(coin=self.symbol[0:-4])
        precision = self.exchange.get_margin_precision(self.symbol)["base_precision"]
        coin_qty = round(
            math.ceil((loan + interest) * (10**precision)) * (0.1**precision),
            precision,
        )  # round up to make sure when convert to usdt, will buy cover liability
        interest_precision = abs(Decimal(str(interest)).as_tuple().exponent)
        total_liability = round(loan + interest, interest_precision)
        return coin_qty, total_liability, loan, interest
