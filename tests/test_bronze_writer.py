import json

import pandas as pd

from data_engineering.ingestion.bronze_writer import BronzeWriter


def test_write_market_data(tmp_path):
    data = pd.DataFrame(
        {
            "Open": [2100.0],
            "High": [2110.0],
            "Low": [2090.0],
            "Close": [2105.0],
            "Volume": [1000000],
        },
        index=pd.DatetimeIndex(
            ["2026-10-01"],
            name="Date",
        ),
    )

    writer = BronzeWriter(tmp_path)

    output_path = writer.write_market_data(
        data=data,
        source="yahoo_finance",
        ticker="TCS.NS",
    )

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["source"] == "yahoo_finance"
    assert payload["ticker"] == "TCS.NS"
    assert "ingested_at" in payload

    assert len(payload["records"]) == 1
    assert payload["records"][0]["Open"] == 2100.0
    assert payload["records"][0]["Close"] == 2105.0
    assert payload["records"][0]["Volume"] == 1000000
