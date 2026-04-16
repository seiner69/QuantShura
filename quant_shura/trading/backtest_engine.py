#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantShura 系统 - 胜率回测引擎

从数据库中读取历史交易信号，使用 MT5 数据进行回测，
评估 LLM 交易策略的胜率和盈亏比表现。
"""

import os
import logging
import sqlite3
import pandas as pd
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import MetaTrader5 as mt5

from quant_shura.data.data_ingestion import MT5DataFetcher


class BacktestEngine:
    """胜率回测引擎。"""

    def __init__(
        self,
        db_path: str = "data/quant_shura.db",
        lookback_bars: int = 50,
        timezone: str = 'Asia/Shanghai'
    ):
        self.db_path = db_path
        self.lookback_bars = lookback_bars
        self.timezone = timezone
        self.logger = self._setup_logger()
        self.mt5_fetcher = None
        self.total_signals = 0
        self.parsed_signals = 0
        self.wins = 0
        self.losses = 0
        self.timeouts = 0
        self.max_win_streak = 0
        self.max_loss_streak = 0
        self.logger.info("=== QuantShura 胜率回测引擎初始化完成 ===")

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('BacktestEngine')
        if not logger.handlers:
            log_filename = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO)
        return logger

    def load_signals(self) -> pd.DataFrame:
        try:
            self.logger.info("从数据库加载交易信号...")
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT id, timestamp, symbol, close_price, is_trend_bar, is_inside,
                   is_outside, llm_direction, raw_analysis, created_at
            FROM trade_signals
            WHERE llm_direction IN ('多头占优', '空头占优')
            ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            if df.empty:
                self.logger.warning("数据库中没有有效的交易信号")
                return df
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['created_at'] = pd.to_datetime(df['created_at'])
            self.total_signals = len(df)
            self.logger.info(f"成功加载 {self.total_signals} 条有效交易信号")
            return df
        except Exception as e:
            self.logger.error(f"加载交易信号失败: {e}")
            return pd.DataFrame()

    def _parse_trade_levels(self, raw_analysis: str) -> Optional[Dict[str, float]]:
        try:
            if not raw_analysis:
                return None
            patterns = {
                'entry': [r'入场点位[:：]\s*([+-]?\d+\.?\d*)', r'入场[:：]\s*([+-]?\d+\.?\d*)'],
                'stop_loss': [r'止损位[:：]\s*([+-]?\d+\.?\d*)', r'止损[:：]\s*([+-]?\d+\.?\d*)'],
                'take_profit': [r'目标位[:：]\s*([+-]?\d+\.?\d*)', r'目标[:：]\s*([+-]?\d+\.?\d*)']
            }
            levels = {}
            for key, regex_patterns in patterns.items():
                for pattern in regex_patterns:
                    match = re.search(pattern, raw_analysis, re.IGNORECASE)
                    if match:
                        try:
                            value = float(match.group(1))
                            levels[key] = value
                            break
                        except ValueError:
                            continue
            if len(levels) >= 2:
                self.parsed_signals += 1
                return levels
            return None
        except Exception as e:
            self.logger.error(f"解析交易参数时发生异常: {e}")
            return None

    def _simulate_price_movement(
        self,
        price_data: pd.DataFrame,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str
    ) -> str:
        try:
            for _, row in price_data.iterrows():
                high = row['high']
                low = row['low']
                if direction == '多头占优':
                    if high >= take_profit:
                        return 'Win'
                    elif low <= stop_loss:
                        return 'Loss'
                else:
                    if low <= take_profit:
                        return 'Win'
                    elif high >= stop_loss:
                        return 'Loss'
            return 'Timeout'
        except Exception as e:
            self.logger.error(f"模拟价格走势时发生异常: {e}")
            return 'Timeout'

    def run_backtest(self) -> bool:
        try:
            self.logger.info("开始执行回测...")
            signals_df = self.load_signals()
            if signals_df.empty:
                self.logger.error("没有有效的交易信号，无法执行回测")
                return False
            if self.mt5_fetcher is None:
                self.mt5_fetcher = MT5DataFetcher(timezone=self.timezone)

            for index, signal in signals_df.iterrows():
                try:
                    self.logger.info(f"--- 回测信号 {index + 1}/{len(signals_df)} ---")
                    levels = self._parse_trade_levels(signal['raw_analysis'])
                    if levels is None:
                        self.logger.warning(f"跳过信号 {index + 1}：无法解析交易参数")
                        continue
                    entry_price = levels.get('entry', signal['close_price'])
                    stop_loss = levels.get('stop_loss')
                    take_profit = levels.get('take_profit')
                    if stop_loss is None or take_profit is None:
                        self.logger.warning(f"跳过信号 {index + 1}：缺少止损或止盈位")
                        continue
                    with self.mt5_fetcher as fetcher:
                        historical_data = fetcher.get_historical_data(
                            symbol=signal['symbol'],
                            timeframe=mt5.TIMEFRAME_M5,
                            num_bars=self.lookback_bars
                        )
                    if historical_data is None or historical_data.empty:
                        self.logger.warning(f"无法获取 {signal['symbol']} 的历史数据，跳过")
                        continue
                    signal_time = signal['timestamp']
                    future_data = historical_data[historical_data['time'] > signal_time]
                    if future_data.empty:
                        self.logger.warning(f"信号时间后无数据，跳过")
                        continue
                    result = self._simulate_price_movement(
                        price_data=future_data,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        direction=signal['llm_direction']
                    )
                    if result == 'Win':
                        self.wins += 1
                    elif result == 'Loss':
                        self.losses += 1
                    else:
                        self.timeouts += 1
                    self.logger.info(f"结果: {result}")
                    time.sleep(0.1)
                except Exception as e:
                    self.logger.error(f"处理信号 {index + 1} 时发生异常: {e}")
                    continue
            self.logger.info("回测执行完成")
            return True
        except Exception as e:
            self.logger.error(f"回测执行失败: {e}")
            return False

    def generate_report(self):
        try:
            self.logger.info("\n" + "="*80)
            self.logger.info("回测报告")
            self.logger.info("="*80)
            self.logger.info(f"总交易信号数: {self.total_signals}")
            self.logger.info(f"解析成功数: {self.parsed_signals}")
            self.logger.info(f"有效回测数: {self.wins + self.losses + self.timeouts}")
            total_trades = self.wins + self.losses
            if total_trades > 0:
                win_rate = (self.wins / total_trades) * 100
                self.logger.info(f"胜率 (Win Rate): {win_rate:.2f}% ({self.wins}/{total_trades})")
            self.logger.info(f"最大连胜次数: {self.max_win_streak}")
            self.logger.info(f"最大连败次数: {self.max_loss_streak}")
            self.logger.info(f"盈利交易数: {self.wins}")
            self.logger.info(f"亏损交易数: {self.losses}")
            self.logger.info(f"超时/平局数: {self.timeouts}")
        except Exception as e:
            self.logger.error(f"生成报告时发生异常: {e}")
