#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantShura 系统 - Al Brooks 价格行为特征提取模块

基于 Al Brooks 的价格行为学理论，从 K 线数据中提取关键的价格行为特征，
为后续的交易信号识别和策略开发提供基础特征数据。
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging


class AlBrooksAnalyzer:
    """Al Brooks 价格行为特征分析器。"""

    def __init__(self):
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def add_price_action_features(self, df: pd.DataFrame) -> pd.DataFrame:
        result_df = df.copy()
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in result_df.columns:
                raise ValueError(f"数据中缺少必要列: {col}")

        result_df['ema_20'] = self._calculate_ema(result_df['close'], period=20)
        result_df['bar_range'] = result_df['high'] - result_df['low']
        result_df['body_size'] = np.abs(result_df['close'] - result_df['open'])
        result_df['is_trend_bar'] = result_df['body_size'] > (result_df['bar_range'] * 0.5)
        result_df['is_bullish'] = result_df['close'] > result_df['open']
        result_df['is_bearish'] = result_df['close'] < result_df['open']
        result_df['is_inside'] = (
            (result_df['high'] < result_df['high'].shift(1)) &
            (result_df['low'] > result_df['low'].shift(1))
        )
        result_df['is_outside'] = (
            (result_df['high'] > result_df['high'].shift(1)) &
            (result_df['low'] < result_df['low'].shift(1))
        )
        result_df['bottom_tail'] = np.minimum(result_df['open'], result_df['close']) - result_df['low']
        result_df['top_tail'] = result_df['high'] - np.maximum(result_df['open'], result_df['close'])
        result_df['bottom_tail_pct'] = np.where(
            result_df['bar_range'] > 0,
            (result_df['bottom_tail'] / result_df['bar_range']) * 100,
            0.0
        )
        result_df['top_tail_pct'] = np.where(
            result_df['bar_range'] > 0,
            (result_df['top_tail'] / result_df['bar_range']) * 100,
            0.0
        )
        result_df = self._handle_nan_values(result_df)
        self.logger.info(f"成功添加价格行为特征，处理了 {len(result_df)} 根 K 线")
        return result_df

    def _calculate_ema(self, series: pd.Series, period: int = 20) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def _handle_nan_values(self, df: pd.DataFrame) -> pd.DataFrame:
        bool_columns = ['is_trend_bar', 'is_bullish', 'is_bearish', 'is_inside', 'is_outside']
        for col in bool_columns:
            if col in df.columns:
                df[col] = df[col].fillna(False)
        numeric_columns = ['ema_20', 'bar_range', 'body_size', 'bottom_tail', 'top_tail',
                          'bottom_tail_pct', 'top_tail_pct']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].fillna(method='ffill')
        df = df.fillna(0)
        return df


def create_sample_data() -> pd.DataFrame:
    """创建包含典型 K 线形态的模拟数据。"""
    base_time = pd.Timestamp('2024-01-01 09:30:00')
    times = [base_time + pd.Timedelta(minutes=5*i) for i in range(10)]
    sample_data = [
        [times[0], 1900.0, 1905.0, 1898.0, 1903.0, 1000],
        [times[1], 1903.0, 1908.0, 1902.0, 1907.0, 1200],
        [times[2], 1907.0, 1909.0, 1906.0, 1906.5, 800],
        [times[3], 1906.5, 1907.0, 1905.0, 1905.5, 900],
        [times[4], 1905.5, 1910.0, 1904.0, 1909.0, 1500],
        [times[5], 1909.0, 1912.0, 1908.0, 1911.0, 1100],
        [times[6], 1911.0, 1911.5, 1909.0, 1909.5, 700],
        [times[7], 1909.5, 1910.0, 1908.5, 1909.0, 600],
        [times[8], 1909.0, 1913.0, 1907.0, 1912.0, 1400],
        [times[9], 1912.0, 1915.0, 1911.0, 1914.0, 1300],
    ]
    df = pd.DataFrame(sample_data, columns=['time', 'open', 'high', 'low', 'close', 'tick_volume'])
    return df
