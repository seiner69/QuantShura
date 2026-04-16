# QuantShura

现货黄金（XAU/USD）价格行为学量化分析系统，基于 Al Brooks 价格行为理论。

## 功能特性

- **价格行为分析** — 提取 K 线形态特征（Inside Bar、Outside Bar、影线百分比等）
- **EMA 指标计算** — 多周期指数移动平均线
- **LLM 市场分析** — 支持 DeepSeek / OpenAI 等兼容 API，基于 Al Brooks 理论生成交易信号
- **自动图表渲染** — 生成带标注的技术分析图表
- **Telegram 通知** — 实时推送交易信号至 Telegram
- **回测引擎** — 基于历史数据验证策略表现
- **数据库管理** — 持久化存储行情与分析数据
- **定时调度** — 5 分钟整点自动化运行

## 核心模块

| 模块 | 说明 |
|------|------|
| `data_ingestion.py` | MT5 数据接入 |
| `price_action_engine.py` | Al Brooks 价格行为特征提取 |
| `llm_analyzer.py` | 大模型推理与交易信号生成 |
| `chart_renderer.py` | 图表渲染与标注 |
| `dashboard.py` | 可视化面板 |
| `telegram_notifier.py` | Telegram 消息推送 |
| `database_manager.py` | 数据库管理 |
| `backtest_engine.py` | 回测引擎 |
| `main_daemon.py` | 定时调度守护进程 |

## 快速开始

```bash
# 安装依赖
pip install pandas numpy MetaTrader5 pyqtgraph python-telegram-bot

# 配置 MT5 和 Telegram（修改 main_daemon.py 中的配置）
# 运行
python main_daemon.py
```

## 免责声明

本项目仅供学习研究之用，不构成投资建议。量化交易存在风险，请谨慎使用。
