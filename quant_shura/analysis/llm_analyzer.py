#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantShura 系统 - 大模型推理模块

基于 Al Brooks 价格行为学理论，利用大语言模型对市场进行深度分析，
提供专业的交易信号和策略建议。
"""

import os
import logging
import pandas as pd
from typing import Optional, Any
import time


class PriceActionLLM:
    """价格行为学大模型分析器。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model_name: str = "qwen-vl-max",
        timeout: int = 60,
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = self._setup_logger()
        self.client = self._initialize_client()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _initialize_client(self):
        try:
            from openai import OpenAI
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            raise ImportError("请安装 openai 库: pip install openai")

    def _format_market_context(self, df: pd.DataFrame, num_bars: int = 5) -> str:
        if df.empty:
            raise ValueError("DataFrame 为空，无法格式化市场上下文")
        recent_bars = df.tail(num_bars).copy().reset_index(drop=True)
        context_lines = ["# 市场上下文分析", "", "## K 线特征摘要", ""]
        for i, row in recent_bars.iterrows():
            time_str = row['time'].strftime('%Y-%m-%d %H:%M:%S')
            context_lines.append(f"### K 线 {i+1}: {time_str}")
            context_lines.append(f"- **价格**: 开盘 {row['open']:.2f}, 最高 {row['high']:.2f}, 最低 {row['low']:.2f}, 收盘 {row['close']:.2f}")
            context_lines.append(f"- **EMA 20**: {row['ema_20']:.2f}")
            context_lines.append(f"- **K 线形态**: {'多头' if row['is_bullish'] else '空头' if row['is_bearish'] else '十字星'}")
            context_lines.append(f"- **趋势线**: {'是' if row['is_trend_bar'] else '否'}")
            context_lines.append(f"- **Inside Bar**: {'是' if row['is_inside'] else '否'}")
            context_lines.append(f"- **Outside Bar**: {'是' if row['is_outside'] else '否'}")
            context_lines.append(f"- **下影线**: {row['bottom_tail_pct']:.1f}%")
            context_lines.append(f"- **上影线**: {row['top_tail_pct']:.1f}%")
            context_lines.append("")
        context_lines.append("## 整体市场特征")
        bullish_count = recent_bars['is_bullish'].sum()
        bearish_count = recent_bars['is_bearish'].sum()
        trend_bar_count = recent_bars['is_trend_bar'].sum()
        context_lines.append(f"- **多头 K 线**: {bullish_count}/{num_bars}")
        context_lines.append(f"- **空头 K 线**: {bearish_count}/{num_bars}")
        context_lines.append(f"- **趋势线**: {trend_bar_count}/{num_bars}")
        context_lines.append(f"- **Inside Bar**: {recent_bars['is_inside'].sum()} 根")
        context_lines.append(f"- **Outside Bar**: {recent_bars['is_outside'].sum()} 根")
        latest_close = recent_bars.iloc[-1]['close']
        latest_ema = recent_bars.iloc[-1]['ema_20']
        price_position = "上方" if latest_close > latest_ema else "下方"
        context_lines.append(f"- **价格位置**: 收盘价 {latest_close:.2f} 位于 EMA 20 ({latest_ema:.2f}) {price_position}")
        return "\n".join(context_lines)

    def _build_system_prompt(self) -> str:
        return """
# Al Brooks 价格行为学专家角色设定

你是一位专业的 Al Brooks 价格行为学交易专家。你的分析必须基于以下核心原则：

## 分析框架
- **趋势线识别**: 实体长度 > K 线总长度 50% 的为趋势线
- **Inside Bar (孕线)**: 当前 K 线完全包含在前一根 K 线范围内
- **Outside Bar (吞没线)**: 当前 K 线完全包含前一根 K 线
- **影线分析**: 长影线代表价格拒绝，是重要的支撑/阻力信号

## 输出要求
必须输出明确结论：
- **多头占优**: 明确看涨，给出入场点和目标
- **空头占优**: 明确看跌，给出入室点和目标
- **震荡平衡**: 明确区间震荡，给出支撑阻力位

禁止使用"可能"、"或许"、"大概"等模棱两可的词汇。

## 交易建议格式
```
## 市场结论: [多头占优/空头占优/震荡平衡]

### 交易策略:
- **入场点位**: [具体价格]
- **止损位**: [具体价格]
- **目标位**: [具体价格]
- **风险回报比**: [具体数值]
```
""".strip()

    def analyze_market(self, df: pd.DataFrame) -> str:
        try:
            market_context = self._format_market_context(df, num_bars=5)
            system_prompt = self._build_system_prompt()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": market_context}
            ]
            response = self._call_api_with_retry(messages)
            if hasattr(response, 'choices') and len(response.choices) > 0:
                analysis = response.choices[0].message.content
                self.logger.info("成功获取 LLM 分析结果")
                return analysis
            else:
                raise Exception("API 响应格式异常")
        except Exception as e:
            self.logger.error(f"市场分析失败: {e}")
            return f"分析失败: {str(e)}"

    def _call_api_with_retry(self, messages: list) -> Any:
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1500,
                    timeout=self.timeout
                )
                return response
            except Exception as e:
                self.logger.warning(f"API 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"API 调用失败，已达到最大重试次数: {e}")
                wait_time = 2 ** attempt
                time.sleep(wait_time)
