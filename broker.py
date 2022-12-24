from constants import *
import logging
import time


class Broker:
    # traders buy assets from and sell assets to the broker
    def __init__(self, exchange):
        self.exchange = exchange
        self.s_session = self.exchange.s_session
        self.f_session = self.exchange.f_session

    def submit_order(self, order):
        if order.market == MarketType.SPOT:
            try:
                order_response = self.s_session.place_active_order(
                    symbol=order.symbol,
                    side=order.side,
                    type=order.type,
                    qty=order.coin_qty if order.side == SIDE_SELL else order.usdt_qty,
                )["result"]
                order.id = order_response["orderId"]
                # order.link_id = order_response["orderLinkId"]
                order.status = OrderStatus.FILLED
                logging.info(
                    f"executed {order.tag} margin order id {order.id} successfully"
                )
            except Exception as e:
                logging.error(f"failed to execute margin order: {e}")
                order.status = OrderStatus.CANCELED
                order.cancel_reason = e

        elif order.market == MarketType.FUTURES:
            try:
                order_response = self.f_session.place_active_order(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.type,
                    qty=order.coin_qty,
                    time_in_force=GOOD_TILL_CANCEL,
                    reduce_only=False,
                    close_on_trigger=False,
                    position_idx=0,
                )["result"]
                order.status = OrderStatus.FILLED
                order.id = order_response["order_id"]
                # order.link_id = order_response["order_link_id"]
                logging.info(
                    f"executed {order.tag} futures order id {order.id} successfully"
                )
            except Exception as e:
                logging.error(f"failed to execute futures order: {e}")
                order.status = OrderStatus.CANCELED
                order.cancel_reason = e
        logging.info(order.__str__())

    def execute_margin_order(self, order, total_liability=None):
        if order.tag == ORDER_TAG_ENTRY and order.side == SIDE_SELL:
            self._borrow_margin_loan(order.symbol[0:-4], order.coin_qty)
        time.sleep(1)
        self.submit_order(order)
        time.sleep(1)
        if order.tag == ORDER_TAG_EXIT and order.side == SIDE_BUY:
            self._repay_margin_loan(order.symbol[0:-4], total_liability)

    def _borrow_margin_loan(self, coin, qty):
        # entering short margin position
        try:
            loan_id = self.s_session.borrow_margin_loan(currency=coin, qty=qty)[
                "result"
            ]
            logging.info(f"borrowed {qty} {coin} successfully with id: {loan_id}")
        except Exception as e:
            logging.error(f"failed to borrow {qty} {coin} with error: {e}")

    def _repay_margin_loan(self, coin, qty):
        # exiting short margin position
        try:
            loan_id = self.s_session.repay_margin_loan(
                currency=coin,
                qty=qty,
            )["result"]
            logging.info(f"repaid {qty} {coin} successfully with id: {loan_id}")
        except Exception as e:
            logging.error(f"failed to repay {qty} {coin} with error: {e}")

    def get_latest_orders_info(self, s_order, f_order):
        try:
            order_info = self.s_session.get_active_order()["result"][0]
            s_order.price = float(order_info["avgPrice"])
            s_order.info = str(order_info)
        except Exception as e:
            logging.error(f"failed to get margin order info: {e}")
        try:
            order_info = self.f_session.get_active_order(symbol=f_order.symbol)[
                "result"
            ]["data"][0]
            f_order.price = float(order_info["last_exec_price"])
            f_order.info = str(order_info)
        except Exception as e:
            logging.error(f"failed to get futures order info: {e}")
