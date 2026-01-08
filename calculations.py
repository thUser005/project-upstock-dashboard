def calculate_breakout(open_price, y_high, y_low):
    """
    Excel:
    =MROUND((Open + ((High - Low) * 0.55)), 0.05)
    """
    return round(open_price + ((y_high - y_low) * 0.55), 2)


def trade_levels(breakout):
    """
    Your custom logic:
    Entry  = Breakout - 50
    Target = Entry + 100
    SL     = Entry - 70
    """
    entry = breakout - 50
    target = entry + 100
    stoploss = entry - 70

    return entry, target, stoploss
