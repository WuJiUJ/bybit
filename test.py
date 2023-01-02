from exchange import Exchange
from utils import read_skl

# exchange = Exchange()
# data = exchange.s_session.user_trade_records(symbol="APEUSDT")

# print(data)

position = read_skl("./records/position_49640151-91b2-4c1b-9d0d-1265608dd81a.skl")
print(position.s_entry_order)