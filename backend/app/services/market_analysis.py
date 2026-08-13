from dataclasses import dataclass


@dataclass(frozen=True)
class MarketSignalSummary:
    movers_ready: bool = False
    losers_ready: bool = False
    trending_ready: bool = False
    predictions_ready: bool = False


def get_market_signal_capabilities() -> MarketSignalSummary:
    return MarketSignalSummary()
