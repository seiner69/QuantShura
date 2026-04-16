#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantShura 系统 - Telegram 通知模块

通过 Telegram Bot API 发送图文消息，将市场分析结果推送到指定群组或频道。
"""

import os
import logging
import requests
from typing import Optional
from datetime import datetime


class TelegramNotifier:
    """Telegram 通知发送器。"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = self._setup_logger()
        self._validate_config()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _validate_config(self):
        if not self.bot_token or not self.chat_id:
            raise ValueError("Bot Token 和 Chat ID 都是必需的")
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    self.logger.info(f"Telegram Bot 验证成功: @{bot_info.get('username', 'Unknown')}")
                else:
                    raise ValueError("Bot Token 无效")
            else:
                raise ValueError(f"Bot Token 验证失败，状态码: {response.status_code}")
        except Exception as e:
            self.logger.warning(f"无法验证 Bot Token: {e}")

    def send_text_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    self.logger.info("文本消息发送成功")
                    return True
                else:
                    self.logger.error(f"消息发送失败: {data.get('description', 'Unknown error')}")
                    return False
            else:
                self.logger.error(f"HTTP 错误: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"发送消息时发生异常: {e}")
            return False

    def send_photo(self, photo_path: str, caption: Optional[str] = None, parse_mode: str = "Markdown") -> bool:
        try:
            if not os.path.exists(photo_path):
                self.logger.error(f"图片文件不存在: {photo_path}")
                return False
            url = f"{self.base_url}/sendPhoto"
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {"chat_id": self.chat_id, "parse_mode": parse_mode}
                if caption:
                    data["caption"] = caption
                response = requests.post(url, data=data, files=files, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    self.logger.info("图片消息发送成功")
                    return True
                else:
                    self.logger.error(f"图片发送失败: {data.get('description', 'Unknown error')}")
                    return False
            else:
                self.logger.error(f"HTTP 错误: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"发送图片时发生异常: {e}")
            return False

    def send_analysis_report(
        self,
        analysis_text: str,
        chart_path: Optional[str] = None,
        symbol: str = "XAUUSD",
        timeframe: str = "5分钟"
    ) -> bool:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            title = f"📊 {symbol} {timeframe} 市场分析报告"
            subtitle = f"⏰ 分析时间: {timestamp}"
            full_message = f"{title}\n\n{subtitle}\n\n{analysis_text}"
            if chart_path and os.path.exists(chart_path):
                success = self.send_photo(photo_path=chart_path, caption=f"{symbol} {timeframe} K 线图")
                if not success:
                    return False
                import time
                time.sleep(1)
            success = self.send_text_message(text=full_message, parse_mode="Markdown")
            return success
        except Exception as e:
            self.logger.error(f"发送分析报告时发生异常: {e}")
            return False

    def test_connection(self) -> bool:
        try:
            return self.send_text_message("🧪 Telegram 通知模块连接测试")
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False
