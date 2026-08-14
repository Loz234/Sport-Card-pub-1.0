from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSetDefinition:
    name: str
    description: str


MARKET_PREDICTION_FEATURES = [
    FeatureSetDefinition(name="recent_median_price", description="Median sale price over the recent 14-day window."),
    FeatureSetDefinition(name="price_7d", description="Median sale price over the recent 7-day window."),
    FeatureSetDefinition(name="price_30d", description="Median sale price over the recent 30-day window."),
    FeatureSetDefinition(name="price_90d", description="Median sale price over the recent 90-day window."),
    FeatureSetDefinition(name="price_momentum", description="Relative 7-day versus 30-day price movement."),
    FeatureSetDefinition(name="sales_velocity", description="Sales per day over the recent 30-day window."),
    FeatureSetDefinition(name="sales_volume", description="Number of sales over the recent 30-day window."),
    FeatureSetDefinition(name="price_volatility", description="Normalized sale-price dispersion over 90 days."),
    FeatureSetDefinition(name="active_listings", description="Number of active listings as of the analysis timestamp."),
    FeatureSetDefinition(name="listing_to_sales_ratio", description="Active listings divided by recent 30-day sales volume."),
    FeatureSetDefinition(name="historical_price_trend", description="Normalized linear trend of 90-day sale prices."),
]


BASELINE_FEATURES = MARKET_PREDICTION_FEATURES
