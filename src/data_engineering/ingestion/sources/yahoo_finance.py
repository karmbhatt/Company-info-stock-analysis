import yfinance as yf
import pandas as pd


class YahooFinanceSource:
    """Source adapter for retrieving market data from Yahoo Finance."""

    def __init__(self, ticker: str):
        self.ticker = ticker

    def get_historical_prices(
        self,
        period: str = "1mo",
    ) -> pd.DataFrame:
        """Fetch historical OHLCV and corporate-action data."""

        ticker = yf.Ticker(self.ticker)

        data = ticker.history(
            period=period,
            auto_adjust=False,
        )

        return data