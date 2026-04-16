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
- **Web 数据看板** — Streamlit 可视化面板

## 项目结构

```
QuantShura/
├── quant_shura/           # 主包
│   ├── __init__.py
│   ├── data/              # 数据层
│   │   ├── __init__.py
│   │   ├── data_ingestion.py    # MT5 数据获取
│   │   └── database_manager.py  # SQLite 持久化
│   ├── analysis/          # 分析层
│   │   ├── __init__.py
│   │   ├── price_action_engine.py  # Al Brooks 特征提取
│   │   └── llm_analyzer.py        # 大模型推理
│   ├── visualization/      # 可视化层
│   │   ├── __init__.py
│   │   ├── chart_renderer.py  # K 线图表渲染
│   │   └── dashboard.py       # Streamlit 数据看板
│   ├── trading/           # 交易层
│   │   ├── __init__.py
│   │   ├── backtest_engine.py  # 回测引擎
│   │   └── telegram_notifier.py # Telegram 通知
│   └── daemon/            # 调度层
│       ├── __init__.py
│       └── main_daemon.py    # 定时调度守护进程
├── tests/
├── requirements.txt
└── README.md
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DASHSCOPE_API_KEY='your_dashscope_api_key'
export TELEGRAM_BOT_TOKEN='your_bot_token'
export TELEGRAM_CHAT_ID='your_chat_id'

# 模拟模式运行（无需 MT5）
python -m quant_shura.daemon.main_daemon --mock

# 生产模式运行
python -m quant_shura.daemon.main_daemon --symbol GOLD --timeframe "5分钟"
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API 密钥 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram 聊天 ID |

## 核心模块

### data — 数据层
- `MT5DataFetcher` — MetaTrader 5 历史 K 线获取
- `DatabaseManager` — SQLite 信号持久化

### analysis — 分析层
- `AlBrooksAnalyzer` — 价格行为特征提取（趋势线、Inside Bar、Outside Bar、影线分析）
- `PriceActionLLM` — 基于 Al Brooks 理论的大模型市场分析

### visualization — 可视化层
- `ChartRenderer` — mplfinance K 线图表渲染
- `Dashboard` — Streamlit Web 数据看板

### trading — 交易层
- `BacktestEngine` — 历史信号回测
- `TelegramNotifier` — Telegram 消息推送

### daemon — 调度层
- `QuantShuraDaemon` — 15 分钟整点定时调度

## 免责声明

本项目仅供学习研究之用，不构成投资建议。量化交易存在风险，请谨慎使用。
