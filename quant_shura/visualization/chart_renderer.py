#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantShura 系统 - 图表渲染模块

将包含价格行为特征的 DataFrame 渲染为专业的 K 线图表。
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import mplfinance as mpf
    import pandas as pd
    import matplotlib.pyplot as plt
except ImportError:
    raise ImportError("请安装必要的依赖库: pip install mplfinance pandas numpy matplotlib")


class ChartRenderer:
    """K 线图表渲染器。"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.logger = self._setup_logger()
        self._ensure_output_dir()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _ensure_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"创建输出目录: {self.output_dir}")

    def render_chart(
        self,
        df: pd.DataFrame,
        symbol: str = "XAUUSD",
        timeframe: str = "5分钟",
        save_filename: Optional[str] = None,
        style_config: Optional[Dict[str, Any]] = None
    ) -> str:
        if df.empty:
            raise ValueError("DataFrame 为空，无法渲染图表")
        required_columns = ['time', 'open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"数据中缺少必要列: {col}")

        if 'volume' not in df.columns and 'tick_volume' in df.columns:
            df = df.copy()
            df['volume'] = df['tick_volume']
        elif 'volume' not in df.columns:
            df = df.copy()
            df['volume'] = 0

        df_plot = df.copy()
        df_plot.set_index('time', inplace=True)

        if save_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_filename = f"{symbol}_{timeframe}_{timestamp}.png"
        save_path = os.path.join(self.output_dir, save_filename)
        plot_style = self._get_plot_style(style_config)

        try:
            fig, axes = mpf.plot(
                df_plot,
                type='candle',
                style=plot_style,
                title=f'{symbol} {timeframe} K 线图\nEMA 20 趋势分析',
                ylabel='价格 (USD)',
                volume=True,
                mav=(20,),
                figsize=(12, 8),
                tight_layout=True,
                returnfig=True
            )
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            self.logger.info(f"图表已保存至: {save_path}")
            return save_path
        except Exception as e:
            self.logger.error(f"渲染图表时发生异常: {e}")
            raise

    def _get_plot_style(self, style_config: Optional[Dict[str, Any]] = None):
        if style_config is None:
            return mpf.make_mpf_style(
                base_mpf_style='yahoo',
                marketcolors=mpf.make_marketcolors(
                    up='red',
                    down='green',
                    wick='i',
                    edge='i',
                    volume='in'
                ),
                gridstyle='-.',
                gridcolor='gray'
            )
        else:
            return mpf.make_mpf_style(**style_config)
