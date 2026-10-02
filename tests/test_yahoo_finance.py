from data_engineering.ingestion.sources.yahoo_finance import YahooFinanceSource


def test_get_historical_prices():
    source = YahooFinanceSource("TCS.NS")

    data = source.get_historical_prices(period="5d")

    assert not data.empty
    assert "Open" in data.columns
    assert "High" in data.columns
    assert "Low" in data.columns
    assert "Close" in data.columns
    assert "Volume" in data.columns