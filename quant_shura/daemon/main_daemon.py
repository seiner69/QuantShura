#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantShura 系统 - 自动化调度守护进程

整合核心模块，实现基于绝对时间的精确调度，
确保在每个 5 分钟整点触发一次完整的分析流程。
"""

import os
import sys
import time
import logging
import traceback
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from quant_shura.data.data_ingestion import MT5DataFetcher
from quant_shura.data.database_manager import DatabaseManager
from quant_shura.analysis.price_action_engine import AlBrooksAnalyzer, create_sample_data
from quant_shura.analysis.llm_analyzer import PriceActionLLM
from quant_shura.visualization.chart_renderer import ChartRenderer
from quant_shura.trading.telegram_notifier import TelegramNotifier


class QuantShuraDaemon:
    """QuantShura 自动化调度守护进程。"""

    def __init__(
        self,
        symbol: str = "GOLD",
        timeframe: str = "15分钟",
        timezone: str = 'Asia/Shanghai',
        is_mock: bool = False,
        log_level: str = "INFO"
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.timezone = timezone
        self.is_mock = is_mock
        self.last_analyzed_timestamp: Optional[datetime] = None
        self.logger = self._setup_logger(log_level)

        self.price_analyzer = AlBrooksAnalyzer()
        self.chart_renderer = ChartRenderer(output_dir="output")
        self.llm_analyzer = None
        self.telegram_notifier = None
        self.db_manager = DatabaseManager()

        self.logger.info("=== QuantShura 守护进程初始化完成 ===")
        self.logger.info(f"交易品种: {self.symbol}")
        self.logger.info(f"时间周期: {self.timeframe}")
        self.logger.info(f"模拟模式: {'是' if self.is_mock else '否'}")

    def _setup_logger(self, log_level: str) -> logging.Logger:
        logger = logging.getLogger('QuantShuraDaemon')
        logger.setLevel(getattr(logging, log_level.upper()))
        if not logger.handlers:
            log_filename = f"quant_shura_daemon_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        return logger

    def _calculate_next_wakeup_time(self) -> datetime:
        now = datetime.now()
        minutes = (now.minute // 15 + 1) * 15
        if minutes >= 60:
            next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            next_time = now.replace(minute=minutes, second=0, microsecond=0)
        next_time += timedelta(seconds=2)
        self.logger.info(f"下一个唤醒时间: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return next_time

    def _calculate_sleep_duration(self, next_wakeup: datetime) -> float:
        now = datetime.now()
        duration = (next_wakeup - now).total_seconds()
        return max(duration, 1)

    def _initialize_llm_analyzer(self) -> bool:
        try:
            if self.llm_analyzer is not None:
                return True
            api_key = os.getenv('DASHSCOPE_API_KEY')
            if not api_key:
                self.logger.warning("未找到 DASHSCOPE_API_KEY，跳过 LLM 分析")
                return False
            self.llm_analyzer = PriceActionLLM(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model_name="qwen-vl-max",
                timeout=60,
                max_retries=3
            )
            self.logger.info("LLM 分析器初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"LLM 分析器初始化失败: {e}")
            return False

    def _initialize_telegram_notifier(self) -> bool:
        try:
            if self.telegram_notifier is not None:
                return True
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if not bot_token or not chat_id:
                self.logger.warning("未配置 Telegram，跳过通知发送")
                return False
            self.telegram_notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
            if self.telegram_notifier.test_connection():
                self.logger.info("Telegram 通知器初始化成功")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Telegram 通知器初始化失败: {e}")
            return False

    def _get_market_data(self) -> Optional[Dict[str, Any]]:
        try:
            if self.is_mock:
                self.logger.info("使用模拟数据模式")
                raw_data = create_sample_data()
            else:
                self.logger.info("从 MT5 获取实时数据")
                with MT5DataFetcher(timezone=self.timezone) as fetcher:
                    raw_data = fetcher.get_historical_data(
                        symbol=self.symbol,
                        timeframe=5,
                        num_bars=100
                    )
            if raw_data is None or raw_data.empty:
                self.logger.error("获取市场数据失败")
                return None
            feature_data = self.price_analyzer.add_price_action_features(raw_data)
            self.logger.info(f"成功获取 {len(feature_data)} 根 K 线数据")
            return {'raw_data': raw_data, 'feature_data': feature_data}
        except Exception as e:
            self.logger.error(f"获取市场数据时发生异常: {e}")
            return None

    def _perform_analysis(self, feature_data) -> Optional[str]:
        try:
            if not self._initialize_llm_analyzer():
                self.logger.warning("LLM 分析器未就绪，跳过分析")
                return None
            analysis = self.llm_analyzer.analyze_market(feature_data)
            if analysis and len(analysis) > 10:
                self.logger.info("LLM 市场分析完成")
                return analysis
            return None
        except Exception as e:
            self.logger.error(f"执行市场分析时发生异常: {e}")
            return None

    def _render_chart(self, feature_data) -> Optional[str]:
        try:
            chart_filename = f"{self.symbol}_{self.timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            chart_path = self.chart_renderer.render_chart(
                df=feature_data,
                symbol=self.symbol,
                timeframe=self.timeframe,
                save_filename=chart_filename
            )
            self.logger.info(f"图表渲染完成: {chart_path}")
            return chart_path
        except Exception as e:
            self.logger.error(f"渲染图表时发生异常: {e}")
            return None

    def _send_notification(self, analysis_text: str, chart_path: Optional[str]) -> bool:
        try:
            if self.telegram_notifier is None:
                self.logger.warning("Telegram 通知器未就绪，跳过通知")
                return True
            success = self.telegram_notifier.send_analysis_report(
                analysis_text=analysis_text,
                chart_path=chart_path,
                symbol=self.symbol,
                timeframe=self.timeframe
            )
            if success:
                self.logger.info("Telegram 通知发送成功")
            return success
        except Exception as e:
            self.logger.error(f"发送通知时发生异常: {e}")
            return False

    def _check_state_lock(self, latest_timestamp: datetime) -> bool:
        if self.last_analyzed_timestamp is None:
            return True
        if latest_timestamp <= self.last_analyzed_timestamp:
            self.logger.info(f"K 线未更新，跳过本次执行")
            return False
        return True

    def _update_state_lock(self, latest_timestamp: datetime):
        self.last_analyzed_timestamp = latest_timestamp

    def _persist_signal(self, feature_data, analysis_result: str) -> bool:
        try:
            latest_row = feature_data.iloc[-1]
            llm_direction = self.db_manager.extract_llm_direction(analysis_result)
            timestamp = latest_row['time'].strftime('%Y-%m-%d %H:%M:%S')
            close_price = float(latest_row['close'])
            is_trend_bar = bool(latest_row['is_trend_bar'])
            is_inside = bool(latest_row['is_inside'])
            is_outside = bool(latest_row['is_outside'])
            success = self.db_manager.insert_signal(
                timestamp=timestamp,
                symbol=self.symbol,
                close_price=close_price,
                is_trend_bar=is_trend_bar,
                is_inside=is_inside,
                is_outside=is_outside,
                llm_direction=llm_direction,
                raw_analysis=analysis_result
            )
            if success:
                self.logger.info(f"交易信号已持久化: {llm_direction}")
            return success
        except Exception as e:
            self.logger.error(f"持久化交易信号时发生异常: {e}")
            return False

    def _execute_single_cycle(self) -> bool:
        try:
            self.logger.info("="*80)
            self.logger.info("开始执行分析周期")
            market_data = self._get_market_data()
            if market_data is None:
                return False
            feature_data = market_data['feature_data']
            latest_timestamp = feature_data['time'].iloc[-1]
            if not self._check_state_lock(latest_timestamp):
                return True
            analysis_result = self._perform_analysis(feature_data)
            if analysis_result:
                self._persist_signal(feature_data, analysis_result)
            chart_path = self._render_chart(feature_data)
            if analysis_result:
                if self.telegram_notifier is None:
                    self._initialize_telegram_notifier()
                if self.telegram_notifier is not None:
                    self._send_notification(analysis_result, chart_path)
            self._update_state_lock(latest_timestamp)
            self.logger.info("分析周期执行完成")
            return True
        except Exception as e:
            self.logger.error(f"执行分析周期时发生异常: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def run(self):
        self.logger.info("QuantShura 守护进程启动")
        try:
            while True:
                try:
                    self._execute_single_cycle()
                    next_wakeup = self._calculate_next_wakeup_time()
                    sleep_duration = self._calculate_sleep_duration(next_wakeup)
                    self.logger.info(f"睡眠 {sleep_duration:.1f} 秒，等待下次唤醒")
                    time.sleep(sleep_duration)
                except KeyboardInterrupt:
                    self.logger.info("收到中断信号，准备退出...")
                    break
                except Exception as e:
                    self.logger.error(f"主循环异常: {e}")
                    time.sleep(60)
                    continue
        except Exception as e:
            self.logger.critical(f"守护进程严重错误: {e}")
        finally:
            self.logger.info("QuantShura 守护进程已停止")


def main():
    print("QuantShura 系统 - 自动化调度守护进程")
    print("="*80)

    parser = argparse.ArgumentParser(description='QuantShura 守护进程')
    parser.add_argument('--symbol', default='GOLD', help='交易品种 (默认: GOLD)')
    parser.add_argument('--timeframe', default='5分钟', help='时间周期 (默认: 5分钟)')
    parser.add_argument('--timezone', default='Asia/Shanghai', help='时区 (默认: Asia/Shanghai)')
    parser.add_argument('--mock', action='store_true', help='启用模拟模式')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    args = parser.parse_args()

    try:
        import pandas as pd
        import numpy as np
        import mplfinance as mpf
        print("所有依赖库检查通过")
    except ImportError as e:
        print(f"缺少依赖库: {e}")
        print("请安装: pip install pandas numpy mplfinance matplotlib openai requests MetaTrader5")
        return

    daemon = QuantShuraDaemon(
        symbol=args.symbol,
        timeframe=args.timeframe,
        timezone=args.timezone,
        is_mock=args.mock,
        log_level=args.log_level
    )

    try:
        daemon.run()
    except KeyboardInterrupt:
        print("\n守护进程已安全退出")
    except Exception as e:
        print(f"\n守护进程异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
