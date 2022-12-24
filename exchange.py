from pybit import spot, usdt_perpetual, account_asset
import math
import uuid
from decimal import Decimal
from utils import ceil
import logging
from secret import api_key, api_secret


class Exchange:
    # exchanges match orders from traders -> don't trade on its own
    def __init__(self):
        self.s_session = spot.HTTP(
            endpoint="https://api.bybit.com", api_key=api_key, api_secret=api_secret
        )
        self.f_session = usdt_perpetual.HTTP(
            endpoint="https://api.bybit.com", api_key=api_key, api_secret=api_secret
        )
        self.a_session = account_asset.HTTP(
            endpoint="https://api.bybit.com", api_key=api_key, api_secret=api_secret
        )

    def fetch_funding_rate(self, symbol):
        return self.f_session.predicted_funding_rate(symbol=symbol)["result"]

    def fetch_trading_symbols(self):
        spot_symbols = [x["name"] for x in self.query_spot_symbols()]
        futures_symbols = [x["name"] for x in self.query_futures_symbols()]
        symbols = list(set(spot_symbols) & set(futures_symbols))
        arb_pairs = []
        for symbol in symbols:
            res = self.get_1h_margin_interest(symbol[0:-4])
            if res:
                arb_pairs.append(symbol)
        return arb_pairs

    def get_1h_margin_interest(self, coin):
        try:
            res = self.s_session.query_interest_quota(currency=coin)
            return float(res["result"]["interestRate"]) / 24 / 2
        except Exception:
            return None

    def get_spot_price(self, symbol):
        return float(self.s_session.last_traded_price(symbol=symbol)["result"]["price"])

    def get_futures_price(self, symbol):
        return float(
            self.f_session.latest_information_for_symbol(symbol=symbol)["result"][0][
                "last_price"
            ]
        )

    def query_spot_symbols(self):
        return self.s_session.query_symbol()["result"]

    def query_futures_symbols(self):
        return self.f_session.query_symbol()["result"]

    def get_margin_loan_info(self, coin):
        assets = self.s_session.query_account_info()["result"]["loanAccountList"]
        for e in assets:
            if e["tokenId"] == coin:
                return float(e["loan"]), float(
                    e["interest"]
                )  # total loan, total interest

    def get_margin_precision(self, symbol):
        infos = self.query_spot_symbols()
        for info in infos:
            if info["name"] == symbol:
                return {
                    "base_precision": int(
                        round(-math.log(float(info["basePrecision"]), 10), 0)
                    ),
                    "quote_precision": int(
                        round(-math.log(float(info["quotePrecision"]), 10), 0)
                    ),
                }

    def get_futures_precision(self, symbol):
        infos = self.query_futures_symbols()
        for info in infos:
            if info["name"] == symbol:
                return int(round(-math.log(info["lot_size_filter"]["qty_step"], 10), 0))

    def get_wallet_available_balance(self, wallet_type, coin):
        balance = None
        if wallet_type == "DERIVATIVES":
            wallet = self.f_session.get_wallet_balance()["result"][coin]
            balance = wallet["available_balance"]
        elif wallet_type == "SPOT":
            balances = self.s_session.get_wallet_balance()["result"]["balances"]
            for e in balances:
                if e["coin"] == coin:
                    balance = float(e["total"])
        return balance

    def transfer(self, coin, amount, from_account_type, to_account_type):
        self.a_session.create_internal_transfer(
            transfer_id=str(uuid.uuid4()),
            coin=coin,
            amount=amount,
            from_account_type=from_account_type,
            to_account_type=to_account_type,
        )
        logging.info(
            f"transferred {amount} {coin} from {from_account_type} to {to_account_type} successfully"
        )

    def usdt_to_coin_qty_margin(self, usdt, symbol):
        coin_price = self.get_spot_price(symbol=symbol)
        precision = self.get_margin_precision(symbol)["base_precision"]
        return float(round(usdt / coin_price, precision))

    def usdt_to_coin_qty_futures(self, usdt, symbol):
        coin_price = self.get_futures_price(symbol=symbol)
        precision = self.get_futures_precision(symbol)
        return float(round(usdt / coin_price, precision))
        # mark price = fair price of a perpetual contract (Spot Liquidity Mid Price x 75% + BTSE Impact Mid Price x 25%)
        # index price = Average Spot Liquidity Mid Price of Major Exchanges

    def coin_qty_to_usdt_margin(self, qty, symbol):
        coin_price = self.get_spot_price(symbol=symbol)
        precision = 1
        return ceil(coin_price * qty, precision)

    def coin_qty_to_usdt_futures(self, qty, symbol):
        coin_price = self.get_futures_price(symbol=symbol)
        precision = 3
        return ceil(coin_price * qty, precision)

    def get_my_total_liability(self, symbol):
        loan, interest = self.get_margin_loan_info(coin=symbol[0:-4])
        precision = self.get_margin_precision(symbol)["base_precision"]
        coin_qty = round(
            math.ceil((loan + interest) * (10**precision)) * (0.1**precision),
            precision,
        )  # round up to make sure when convert to usdt, will buy cover liability
        interest_precision = abs(Decimal(str(interest)).as_tuple().exponent)
        total_liability = round(loan + interest, interest_precision)
        return coin_qty, total_liability, loan, interest

    def cal_usdt_for_buying_spot(self, qty_to_buy, symbol):
        asks = self.s_session.orderbook(symbol=symbol)["result"]["asks"]
        usdt_required = 0
        for ask in asks:
            price, qty = float(ask[0]), float(ask[1])
            usdt_required += min(qty, qty_to_buy) * price
            qty_to_buy -= qty
            if qty_to_buy <= 0:
                break
        return usdt_required
