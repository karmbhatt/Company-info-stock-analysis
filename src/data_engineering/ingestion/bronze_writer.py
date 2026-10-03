import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


class BronzeWriter:
    """Write source data to the Bronze layer."""

    def __init__(self, base_path: str | Path = "data/bronze"):
        self.base_path = Path(base_path)

    def write_market_data(
        self,
        data: pd.DataFrame,
        source: str,
        ticker: str,
    ) -> Path:
        """Write market data as a raw ingestion snapshot."""

        ingestion_time = datetime.now(timezone.utc)
        ingestion_date = ingestion_time.date().isoformat()

        output_dir = (
            self.base_path
            / "market_data"
            / source
            / f"ticker={ticker}"
            / f"ingestion_date={ingestion_date}"
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "stock_history.json"

        records = []

        for index, row in data.iterrows():
            record = {
                "date": index.isoformat(),
                **row.to_dict(),
            }

            records.append(record)

        payload = {
            "source": source,
            "ticker": ticker,
            "ingested_at": ingestion_time.isoformat(),
            "records": records,
        }

        output_path.write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )

        return output_path
