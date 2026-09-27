from app.models.common import SignalBadge, SignalKind

MOVER_ABS_CHANGE = 0.05
FIFTY_TWO_WEEK_HIGH_TOLERANCE = 0.02
FOREIGN_ACCUMULATION_MIN_RATIO = 0.15
FOREIGN_ACCUMULATION_MIN_NET = 1_000_000_000  # Rp 1 billion


def badges_for_stock(
    *,
    symbol: str,
    daily_close_change: float | None,
    last_close_price: float | None,
    is_sectors_52w_high: bool,
    high_52w: float | None,
    net_foreign_inflow: float | None,
    foreign_buy_value: float | None,
    foreign_sell_value: float | None,
    insider_buy: dict | None,
) -> list[SignalBadge]:
    badges: list[SignalBadge] = []
    mover = _mover_badge(daily_close_change)
    if mover is not None:
        badges.append(mover)
    week_high = _fifty_two_week_high_badge(
        last_close_price=last_close_price,
        is_sectors_52w_high=is_sectors_52w_high,
        high_52w=high_52w,
    )
    if week_high is not None:
        badges.append(week_high)
    accumulation = _foreign_accumulation_badge(
        net_foreign_inflow=net_foreign_inflow,
        foreign_buy_value=foreign_buy_value,
        foreign_sell_value=foreign_sell_value,
    )
    if accumulation is not None:
        badges.append(accumulation)
    insider = _insider_buying_badge(insider_buy)
    if insider is not None:
        badges.append(insider)
    del symbol
    return badges


def _mover_badge(daily_close_change: float | None) -> SignalBadge | None:
    if daily_close_change is None:
        return None
    if abs(daily_close_change) < MOVER_ABS_CHANGE:
        return None
    percent = daily_close_change * 100
    direction = "Up" if daily_close_change > 0 else "Down"
    return SignalBadge(
        signal_kind=SignalKind.mover,
        label="Mover",
        reason=(
            f"{direction} {abs(percent):.1f}% today "
            "(Sectors daily_close_change)."
        ),
    )


def _fifty_two_week_high_badge(
    *,
    last_close_price: float | None,
    is_sectors_52w_high: bool,
    high_52w: float | None,
) -> SignalBadge | None:
    if is_sectors_52w_high:
        return SignalBadge(
            signal_kind=SignalKind.fifty_two_week_high,
            label="52-week high",
            reason="Sectors screener tag 52-w-high.",
        )
    if last_close_price is None or high_52w in (None, 0):
        return None
    if last_close_price + 1e-9 < high_52w * (1 - FIFTY_TWO_WEEK_HIGH_TOLERANCE):
        return None
    return SignalBadge(
        signal_kind=SignalKind.fifty_two_week_high,
        label="52-week high",
        reason=(
            f"Close {last_close_price:.0f} is within "
            f"{FIFTY_TWO_WEEK_HIGH_TOLERANCE * 100:.0f}% of 52-week high "
            f"{high_52w:.0f} (Yahoo OHLCV overlay; Sectors tag not in cache)."
        ),
    )


def _foreign_accumulation_badge(
    *,
    net_foreign_inflow: float | None,
    foreign_buy_value: float | None,
    foreign_sell_value: float | None,
) -> SignalBadge | None:
    if net_foreign_inflow is None or net_foreign_inflow <= 0:
        return None
    if net_foreign_inflow < FOREIGN_ACCUMULATION_MIN_NET:
        return None
    if foreign_buy_value is None or foreign_sell_value is None:
        return None
    turnover = foreign_buy_value + foreign_sell_value
    if turnover <= 0:
        return None
    net_ratio = net_foreign_inflow / turnover
    if net_ratio < FOREIGN_ACCUMULATION_MIN_RATIO:
        return None
    return SignalBadge(
        signal_kind=SignalKind.foreign_accumulation,
        label="Foreign accumulation",
        reason=(
            f"Net foreign inflow Rp {net_foreign_inflow:,.0f} "
            f"({net_ratio * 100:.1f}% of foreign turnover) "
            "on the latest cached Sectors foreign-flow day."
        ),
    )


def _insider_buying_badge(insider_buy: dict | None) -> SignalBadge | None:
    if not insider_buy:
        return None
    holder = insider_buy.get("holder_name") or "An insider"
    filed_at = insider_buy.get("filed_at") or "recently"
    amount_text = _share_amount_text(insider_buy.get("amount_transaction"))
    return SignalBadge(
        signal_kind=SignalKind.insider_buying,
        label="Insider buying",
        reason=(
            f"{holder} bought {amount_text} "
            f"(Sectors filings, {str(filed_at)[:10]})."
        ),
    )


def _share_amount_text(amount) -> str:
    if isinstance(amount, bool) or amount is None:
        return "shares"
    try:
        number = float(amount)
    except (TypeError, ValueError):
        return "shares"
    if number != number:
        return "shares"
    return f"{int(number):,} shares"
