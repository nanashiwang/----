from typing import Iterable, Optional

import pandas as pd

from ..data.db.sqlite_client import SQLiteClient
from .feature_builder import FeatureBuilder
from .label_builder import LabelBuilder


class DatasetBuilder:
    """把特征与标签拼成可直接训练和回测的数据集。"""

    def __init__(self, sqlite_client: SQLiteClient):
        self.feature_builder = FeatureBuilder(sqlite_client)
        self.label_builder = LabelBuilder()

    def build_dataset(
        self,
        symbols: Optional[Iterable[str]] = None,
        query_start_date: str = "",
        query_end_date: str = "",
        signal_start_date: str = "",
        signal_end_date: str = "",
        hold_days: int = 5,
    ) -> pd.DataFrame:
        frame = self.feature_builder.load_market_frame(
            symbols=symbols,
            start_date=query_start_date,
            end_date=query_end_date,
        )
        if frame.empty:
            return frame

        labeled = self.label_builder.build_labels(frame, hold_days=hold_days)
        if signal_start_date:
            labeled = labeled[labeled["trade_date"] >= pd.Timestamp(signal_start_date)]
        if signal_end_date:
            labeled = labeled[labeled["trade_date"] <= pd.Timestamp(signal_end_date)]
        return labeled.reset_index(drop=True)
