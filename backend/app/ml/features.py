from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSetDefinition:
    name: str
    description: str


BASELINE_FEATURES = [
    FeatureSetDefinition(name="recent_sales_velocity", description="Rate of sales over the recent observation window."),
    FeatureSetDefinition(name="price_momentum", description="Short-term versus long-term average price delta."),
    FeatureSetDefinition(name="volatility", description="Normalized sale price dispersion across recent transactions."),
]
