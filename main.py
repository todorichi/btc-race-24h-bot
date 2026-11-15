import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
LOOKBACK = 30
DROP_BPS = 150
TAKE_BPS = 50
STOP_BPS = 150
MAX_HOLD = 120
MAX_SLIPPAGE_BPS = 300

closes = deque(maxlen=LOOKBACK + 1)
entry_seq = None


def on_batch(state, batch):
    global entry_seq
    bar = next((item for item in batch["bars"] if item["symbol"] == SYMBOL), None)
    if bar is None:
        return []
    close = int(bar["c"])
    closes.append(close)
    held = state.positions.get(SYMBOL)
    if state.warming_up or batch["seq"] >= 1439:
        return []
    if held is not None:
        if entry_seq is None:
            entry_seq = batch["seq"]
        marked = state.value(SYMBOL, held.qty)
        if (marked * 10000 >= held.cost * (10000 + TAKE_BPS) or
                marked * 10000 <= held.cost * (10000 - STOP_BPS) or
                batch["seq"] - entry_seq >= MAX_HOLD):
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    entry_seq = None
    if len(closes) == LOOKBACK + 1:
        old = closes[0]
        if close > closes[-2] and close * 10000 <= old * (10000 - DROP_BPS):
            room = state.weight_room(SYMBOL)
            amount = min(state.cash, room)
            if amount >= int(state.hello["fees"]["min_notional_quote_units"]):
                return [{"side": "buy", "symbol": SYMBOL,
                         "notional_quote_units": amount,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
