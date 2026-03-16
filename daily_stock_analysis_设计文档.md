# Daily Stock Analysis 系统 — 详尽设计文档

> 项目地址：`/Users/sssccc/git/daily_stock_analysis`
> 文档生成日期：2026-03-15

---

## 目录

1. [系统概述](#1-系统概述)
2. [目录结构](#2-目录结构)
3. [核心模块详解](#3-核心模块详解)
4. [数据流：从输入到输出](#4-数据流从输入到输出)
5. [模块交互关系图](#5-模块交互关系图)
6. [数据提供层（data_provider）](#6-数据提供层data_provider)
7. [AI 分析层（analyzer + LiteLLM）](#7-ai-分析层analyzer--litellm)
8. [多智能体策略系统（Agent）](#8-多智能体策略系统agent)
9. [通知系统（Notification）](#9-通知系统notification)
10. [Web API 与前端](#10-web-api-与前端)
11. [持久化与回测](#11-持久化与回测)
12. [配置参考](#12-配置参考)
13. [部署方式](#13-部署方式)
14. [使用方法（快速上手）](#14-使用方法快速上手)
15. [测试体系](#15-测试体系)
16. [架构设计模式总结](#16-架构设计模式总结)

---

## 1. 系统概述

`daily_stock_analysis` 是一套面向个人投资者和量化研究者的 **AI 驱动股票分析系统**，支持：

- **市场覆盖**：A 股、港股、美股
- **AI 引擎**：通过 LiteLLM 统一调用 Gemini / Claude / GPT / DeepSeek
- **数据来源**：5 个数据源自动降级（东财、AkShare、Tushare、通达信、Yahoo）
- **新闻搜索**：6 种搜索引擎聚合（Tavily、博查、SerpAPI、Brave、MiniMax、SearXNG）
- **通知渠道**：10+ 渠道（企业微信、飞书、Telegram、邮件、Discord 等）
- **交互方式**：CLI、Web UI、REST API、Discord/飞书/钉钉 Bot
- **扩展能力**：多智能体对话、YAML 策略配置、回测准确率追踪

---

## 2. 目录结构

```
daily_stock_analysis/
│
├── main.py                    # CLI 入口：调度、参数解析
├── server.py                  # FastAPI 应用入口（仅 API 模式）
├── webui.py                   # Web UI 启动包装器
├── analyzer_service.py        # 服务层：暴露 analyze_stock() 等方法
├── discord_bot.py             # Discord 独立 Bot
│
├── api/                       # REST API 层（FastAPI）
│   ├── app.py                 # 应用工厂、CORS
│   ├── deps.py                # 依赖注入
│   ├── middlewares/           # 认证 & 错误处理中间件
│   └── v1/
│       ├── router.py          # 路由聚合
│       ├── endpoints/         # 各功能端点
│       └── schemas/           # Pydantic 请求/响应模型
│
├── src/                       # 核心业务逻辑
│   ├── config.py              # 配置单例（读取 .env）
│   ├── analyzer.py            # LLM 调用层
│   ├── notification.py        # 通知聚合与路由
│   ├── search_service.py      # 多引擎新闻搜索
│   ├── storage.py             # SQLAlchemy ORM & 数据库操作
│   ├── stock_analyzer.py      # 技术趋势分析（MA5/10/20）
│   ├── market_analyzer.py     # 大盘分析
│   ├── formatters.py          # 报告格式化
│   ├── enums.py               # 枚举定义
│   ├── auth.py                # Web 认证（JWT）
│   │
│   ├── core/                  # 核心流程
│   │   ├── pipeline.py        # ★ 主分析工作流编排器
│   │   ├── market_review.py   # 市场综述
│   │   ├── market_strategy.py # 市场策略规则
│   │   ├── backtest_engine.py # 回测准确率引擎
│   │   ├── config_manager.py  # 配置 CRUD
│   │   ├── config_registry.py # 配置 Schema & 注册表
│   │   ├── trading_calendar.py # 交易日历（A/港/美）
│   │   └── market_profile.py  # 市场画像工具
│   │
│   ├── services/              # 业务服务层
│   │   ├── task_queue.py      # 异步任务队列
│   │   ├── task_service.py    # 任务执行与状态跟踪
│   │   ├── history_service.py # 分析历史 CRUD
│   │   ├── backtest_service.py
│   │   ├── portfolio_service.py
│   │   ├── portfolio_risk_service.py
│   │   ├── system_config_service.py
│   │   ├── image_stock_extractor.py # 图片识别提取股票代码
│   │   ├── import_parser.py         # CSV/Excel 导入解析
│   │   ├── name_to_code_resolver.py # 股票名称转代码
│   │   └── report_renderer.py       # Jinja2 模板渲染
│   │
│   ├── agent/                 # 多智能体系统
│   │   ├── runner.py          # 智能体执行引擎
│   │   ├── protocols.py       # 协议定义
│   │   ├── conversation.py    # 多轮对话管理
│   │   ├── memory.py          # 对话记忆持久化
│   │   ├── tools/             # 工具实现（分析、搜索、数据、回测等）
│   │   └── strategies/        # 策略加载与路由
│   │
│   ├── notification_sender/   # 通知渠道实现
│   │   ├── wechat_sender.py
│   │   ├── feishu_sender.py
│   │   ├── telegram_sender.py
│   │   ├── email_sender.py
│   │   ├── discord_sender.py
│   │   ├── pushover_sender.py
│   │   ├── pushplus_sender.py
│   │   ├── serverchan3_sender.py
│   │   ├── custom_webhook_sender.py
│   │   └── astrbot_sender.py
│   │
│   ├── repositories/          # 数据访问层
│   ├── utils/                 # 工具函数
│   ├── data/                  # 股票映射数据
│   └── schemas/               # 共享 Schema
│
├── data_provider/             # 多数据源抓取（策略模式）
│   ├── base.py                # 基础抓取器 & DataFetcherManager
│   ├── akshare_fetcher.py     # AkShare（东财爬虫）
│   ├── efinance_fetcher.py    # EFinance（东财官方）
│   ├── tushare_fetcher.py     # Tushare Pro
│   ├── pytdx_fetcher.py       # Pytdx（通达信）
│   ├── baostock_fetcher.py    # Baostock（证券宝）
│   ├── yfinance_fetcher.py    # Yahoo Finance（美股）
│   ├── fundamental_adapter.py # 基本面数据聚合
│   └── realtime_types.py      # 实时数据结构
│
├── bot/                       # Bot 集成
│   ├── dispatcher.py          # 命令分发器
│   ├── handler.py             # 消息处理器
│   ├── platforms/             # Discord / 飞书 / 钉钉
│   └── commands/              # 命令实现（ask, analyze, chat, market 等）
│
├── strategies/                # 内置交易策略（YAML）
│   ├── bull_trend.yaml        # 多头趋势（默认）
│   ├── ma_golden_cross.yaml   # 均线金叉
│   ├── volume_breakout.yaml   # 量能突破
│   ├── shrink_pullback.yaml   # 缩量回调低吸
│   ├── bottom_volume.yaml     # 底部放量反转
│   ├── dragon_head.yaml       # 龙头动量
│   ├── one_yang_three_yin.yaml # 一阳三阴
│   ├── box_oscillation.yaml   # 箱体震荡区间
│   ├── chan_theory.yaml       # 缠中说禅
│   ├── wave_theory.yaml       # 艾略特波浪
│   └── emotion_cycle.yaml     # 市场情绪周期
│
├── templates/                 # Jinja2 报告模板
├── apps/dsa-web/              # React 前端（独立 npm 项目）
├── docker/                    # Docker & Compose 配置
├── tests/                     # 测试套件
├── docs/                      # 文档
├── .env.example               # 环境变量模板
└── requirements.txt           # Python 依赖
```

---

## 3. 核心模块详解

### 3.1 入口层

| 文件 | 职责 |
|------|------|
| `main.py` | CLI 总入口；解析参数（`--stocks`、`--schedule`、`--webui`、`--dry-run` 等）；初始化调度器 |
| `server.py` | FastAPI 应用初始化，适合纯 API 模式部署 |
| `webui.py` | 轻量包装，启动 FastAPI + 前端静态文件 |
| `analyzer_service.py` | 暴露 `analyze_stock()` / `analyze_stocks()` / `perform_market_review()` 服务接口 |
| `discord_bot.py` | 独立 Discord Bot，支持用户自定义观察列表与定时分析 |

### 3.2 核心流程 `src/core/pipeline.py`

这是整个系统的**总编排器**，`StockAnalysisPipeline` 类负责：

1. 调用 `DataFetcherManager` 获取行情、基本面数据
2. 调用 `StockTrendAnalyzer` 计算技术指标
3. 调用 `SearchService` 抓取相关新闻
4. 调用 `GeminiAnalyzer`（LLM）生成分析报告
5. 调用 `Storage` 持久化结果
6. 调用 `NotificationService` 分发通知

### 3.3 技术分析 `src/stock_analyzer.py`

`StockTrendAnalyzer` 计算以下指标：

| 指标 | 说明 |
|------|------|
| MA5 / MA10 / MA20 | 5/10/20 日均线 |
| 趋势判断 | 多头排列 / 震荡 / 空头排列 |
| 乖离率（Bias） | 价格与均线的偏离百分比 |
| 价格位置 | 在均线体系中的相对位置 |
| 成交量分析 | 量比、换手率 |
| 筹码分布（可选） | 需 `ENABLE_CHIP_DISTRIBUTION=true` |

### 3.4 LLM 调用 `src/analyzer.py`

- 通过 **LiteLLM** 统一调用多个 LLM 提供商
- 输入：股票代码 + 技术数据 + 新闻摘要 + 配置
- 输出：结构化 JSON（`core_conclusion`、`intelligence`、`battle_plan`、`sentiment_score`、`operation_advice` 等）
- 支持 **Report Integrity Check**（`REPORT_INTEGRITY_ENABLED=true`）：验证并补全缺失字段，自动重试

### 3.5 新闻搜索 `src/search_service.py`

多引擎搜索，按顺序降级：

```
Bocha → Tavily → SerpAPI → Brave → MiniMax → SearXNG
```

- 支持 AI 摘要（部分引擎）
- 过滤 `NEWS_MAX_AGE_DAYS` 天以外的旧新闻
- 多 API Key 轮转，避免限速

---

## 4. 数据流：从输入到输出

### 4.1 单股分析完整流程

```
用户输入（CLI / Web API / Bot 命令）
        │
        ▼
StockAnalysisPipeline.process_single_stock()
        │
        ├──► DataFetcherManager
        │       ├── 历史 OHLCV 数据（6 个月回溯）
        │       ├── 实时行情（量比、PE、换手率）
        │       └── 基本面数据（PE/PB、龙虎榜、机构持仓、板块信息）
        │
        ├──► StockTrendAnalyzer
        │       ├── 计算 MA5/MA10/MA20
        │       ├── 判断趋势状态（多头/震荡/空头）
        │       └── 乖离率、价格位置、成交量分析
        │
        ├──► SearchService
        │       ├── 查询：情绪分析、催化剂、风险预警
        │       └── 多引擎：Bocha → Tavily → SerpAPI → Brave → SearXNG
        │
        ├──► GeminiAnalyzer (via LiteLLM)
        │       ├── 输入：结构化技术数据 + 新闻摘要
        │       ├── LLM Prompt：要求 JSON 格式输出
        │       └── 解析响应 → AnalysisResult 对象
        │
        ├──► NotificationService
        │       ├── 格式化报告（Markdown / Jinja2 模板）
        │       ├── 乖离率阈值检查、交易清单
        │       └── 生成 simple/full/brief 三种报告类型
        │
        ├──► Report Integrity Check
        │       ├── 验证必填字段（sentiment_score, operation_advice 等）
        │       └── 自动补全缺失项（最多重试 N 次）
        │
        ├──► Storage (SQLAlchemy → SQLite)
        │       ├── 保存分析记录
        │       ├── 存储 dashboard JSON、原始文本
        │       └── 记录时间戳（用于历史查询）
        │
        └──► Notification Routing
                ├── 检测已启用的渠道
                ├── Markdown → HTML/图片（按需转换）
                └── 发送至：企业微信 / 飞书 / Telegram / 邮件 / Discord / ...
```

### 4.2 大盘综述流程

```
market_review_enabled=true 或 CLI: --market-review
        │
        ▼
MarketReview.run_market_review()
        ├── 抓取板块涨跌榜（领涨/领跌板块）
        ├── 抓取主要指数（上证、深证、创业板、纳斯达克等）
        ├── 生成市场概览：涨跌家数、涨停/跌停数、热点板块
        └── LLM 汇总市场情绪
        │
        ▼
格式化并发送通知
```

### 4.3 多智能体策略流程（可选）

```
/chat 页面 或 /ask 命令
        │
        ▼
Agent.run(strategy_name, stock_code, context)
        ├── 加载策略 YAML（规则、指令、必需工具）
        ├── 初始化工具注册表（get_daily_history, analyze_trend, search_news 等）
        └── 多轮 LLM 循环
                1. LLM 调用（指令 + 工具列表）
                2. LLM 输出：推理 + tool_calls
                3. 执行工具（抓取数据、执行分析、搜索新闻）
                4. 将结果反馈给 LLM
                5. 重复，直到：完成 / 达到 max_steps / 出错
        │
        ▼
格式化结果 → 返回给用户/API
```

### 4.4 回测流程

```
数据库中已有 AnalysisReport（若干天前生成）
        │
        ▼ （等待 BACKTEST_MIN_AGE_DAYS 天后）
BacktestEngine.evaluate()
        ├── 读取历史报告（decision_type, sniper_points）
        ├── 读取实际价格走势（±BACKTEST_EVAL_WINDOW_DAYS 交易日）
        ├── 评估：
        │   ├── 方向正确率（看多/看空 vs 实际涨跌）
        │   ├── 买点命中率（止盈/止损点位命中）
        │   ├── 胜率 %
        │   └── 评级：A/B/C/D
        └── 保存 BacktestResult 到数据库
```

---

## 5. 模块交互关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户接入层                               │
│  CLI (main.py)  │  Web UI  │  REST API  │  Discord/飞书/钉钉 Bot │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      服务编排层                                   │
│              StockAnalysisPipeline (core/pipeline.py)           │
│              AnalyzerService (analyzer_service.py)              │
└───┬────────────┬────────────┬────────────┬────────────┬─────────┘
    │            │            │            │            │
    ▼            ▼            ▼            ▼            ▼
┌───────┐  ┌─────────┐  ┌────────┐  ┌──────────┐  ┌────────────┐
│数据层 │  │技术分析 │  │新闻搜索│  │  LLM 层  │  │  通知层    │
│data_  │  │stock_   │  │search_ │  │analyzer.py│  │notification│
│provid.│  │analyzer │  │service │  │(LiteLLM)  │  │.py + sender│
└───────┘  └─────────┘  └────────┘  └──────────┘  └────────────┘
    │                                    │
    │ 5 个数据源（优先级降级）           │ 多 LLM 提供商
    ├── EFinance  (P0)                   ├── Google Gemini
    ├── AkShare   (P1)                   ├── Anthropic Claude
    ├── Tushare   (P2)                   ├── OpenAI / DeepSeek
    ├── Pytdx     (P2)                   └── AIHubMix（聚合）
    ├── Baostock  (P3)
    └── YFinance  (P4, 美股)
                                ┌──────────────────────┐
                                │      持久化层         │
                                │   SQLite (storage.py) │
                                │   SQLAlchemy ORM      │
                                └──────────────────────┘
```

---

## 6. 数据提供层（data_provider）

### 架构：策略模式 + 优先级降级

`DataFetcherManager` 管理所有数据源，根据股票类型（A 股/港股/美股）和配置优先级自动选择最优数据源，失败时自动降级。

### 各数据源对比

| 数据源 | 优先级 | 市场覆盖 | 需要认证 | 特点 |
|--------|--------|---------|---------|------|
| EFinance（东财官方） | 0（最高） | A 股 | 无 | 最稳定，东方财富官方接口 |
| AkShare（东财爬虫） | 1 | A 股、港股 | 无 | 数据丰富，爬虫方式 |
| Tushare Pro | 2 | A 股 | Token（付费） | 数据质量高，有频率限制 |
| Pytdx（通达信） | 2 | A 股 | 服务器地址 | 速度快，需要服务器 |
| Baostock（证券宝） | 3 | A 股 | 无 | 数据较全，速度慢 |
| YFinance（Yahoo） | 4（最低） | 全球 | 无 | 美股/港股主力 |

### 数据类型

- **历史 OHLCV**：开高低收量（6 个月回溯）
- **实时行情**：当前价、量比、换手率、PE、涨跌幅
- **基本面**（`ENABLE_FUNDAMENTAL_PIPELINE=true`）：PE/PB、营收增长、机构持仓、龙虎榜、板块信息

---

## 7. AI 分析层（analyzer + LiteLLM）

### LiteLLM 统一接口

系统通过 `litellm` 库统一调用多个 LLM，配置方式（优先级由高到低）：

1. **YAML 配置**（`LITELLM_CONFIG` 指定路径）：支持 Router 负载均衡、多模型 fallback
2. **多渠道配置**（`LLM_CHANNELS`）：指定多个 LLM 渠道
3. **单一 Key 配置**（`GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`）

### LLM 提供商

| 提供商 | 模型示例 | 费用 | 推荐场景 |
|--------|---------|------|---------|
| Google Gemini | gemini-2.5-flash | 免费（1500 次/天） | 日常使用首选 |
| Anthropic Claude | claude-3-5-sonnet | 付费 | 高质量分析 |
| OpenAI | gpt-4o, gpt-4o-mini | 付费 | 通用场景 |
| DeepSeek | deepseek-chat, deepseek-r1 | 极低成本 | 性价比最高 |
| AIHubMix | 以上所有 | 按 token 计费 | 一个 Key 访问全部 |

### 分析输出结构（JSON）

LLM 返回的分析结果包含以下字段：

| 字段 | 说明 |
|------|------|
| `core_conclusion` | 核心结论（一句话） |
| `intelligence` | 情报分析（新闻/消息面） |
| `battle_plan` | 操作计划（买点/止盈/止损） |
| `sentiment_score` | 情绪评分（-100 到 +100） |
| `operation_advice` | 操作建议（买入/持有/观望/卖出） |
| `decision_type` | 决策类型（看多/看空/中性） |
| `sniper_points` | 狙击点位（精确买点位） |

---

## 8. 多智能体策略系统（Agent）

### 架构

```
用户问题/命令
    │
    ▼
AgentRunner (src/agent/runner.py)
    ├── 加载策略 YAML
    ├── 初始化工具注册表
    └── 多轮对话循环（LLM ↔ 工具）
```

### 11 种内置策略

| 策略文件 | 名称 | 适用场景 |
|---------|------|---------|
| `bull_trend.yaml` | 多头趋势 | 均线多头排列，趋势跟随 |
| `ma_golden_cross.yaml` | 均线金叉 | MA5/MA10 金叉信号 |
| `volume_breakout.yaml` | 量能突破 | 放量突破压力位 |
| `shrink_pullback.yaml` | 缩量回调低吸 | 强势股缩量调整买点 |
| `bottom_volume.yaml` | 底部放量反转 | 底部放量见底信号 |
| `dragon_head.yaml` | 龙头动量 | 板块龙头强势追踪 |
| `one_yang_three_yin.yaml` | 一阳三阴 | 经典 K 线形态 |
| `box_oscillation.yaml` | 箱体震荡 | 区间震荡区间交易 |
| `chan_theory.yaml` | 缠中说禅 | 缠论笔段分析 |
| `wave_theory.yaml` | 艾略特波浪 | 波浪理论计数 |
| `emotion_cycle.yaml` | 情绪周期 | 市场情绪极端识别 |

### YAML 策略格式示例

```yaml
name: bull_trend
description: 多头趋势策略
rules:
  - MA5 > MA10 > MA20（多头排列）
  - 价格在 MA5 上方
  - 成交量温和放大
instructions: |
  分析该股票是否符合多头趋势特征，给出买点建议...
required_tools:
  - get_daily_history
  - analyze_trend
  - search_news
```

### 工具列表

Agent 可调用的工具：

| 工具 | 功能 |
|------|------|
| `get_daily_history` | 获取历史 K 线数据 |
| `analyze_trend` | 执行技术趋势分析 |
| `search_news` | 搜索相关新闻 |
| `run_backtest` | 执行策略回测 |
| `get_market_overview` | 获取大盘数据 |
| `get_fundamental_data` | 获取基本面数据 |

### 多智能体模式（`AGENT_ARCH=multi`）

```
用户输入
    │
    ▼
Orchestrator Agent（编排器）
    ├── Market Agent（大盘分析）
    ├── Technical Agent（技术分析）
    ├── News Agent（新闻情报）
    └── Risk Agent（风险控制，可 veto 买入信号）
    │
    ▼
汇总输出
```

---

## 9. 通知系统（Notification）

### 架构：Hub-Spoke 模式

```
NotificationService（notification.py）
    ├── 检测所有已配置的渠道
    ├── 报告格式转换（Markdown → HTML / 图片）
    └── 并发发送到所有启用的渠道
```

### 支持的通知渠道

| 渠道 | 配置 Key | 说明 |
|------|---------|------|
| 企业微信 Webhook | `WECHAT_WEBHOOK_URL` | 群机器人 |
| 飞书 Webhook | `FEISHU_WEBHOOK_URL` | 群机器人 |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Bot 消息 |
| 邮件（SMTP） | `EMAIL_SENDER` + `EMAIL_PASSWORD` + `EMAIL_RECEIVERS` | 支持 HTML 格式 |
| Discord Webhook | `DISCORD_WEBHOOK_URL` | 频道 Webhook |
| Discord Bot | `DISCORD_BOT_TOKEN` + `DISCORD_MAIN_CHANNEL_ID` | Bot 发消息 |
| Pushover | `PUSHOVER_TOKEN` | 手机/桌面推送 |
| PushPlus | `PUSHPLUS_TOKEN` | 微信公众号推送 |
| Server 酱 3 | `SERVERCHAN3_SENDKEY` | 微信通知 |
| 自定义 Webhook | `CUSTOM_WEBHOOK_URLS` | 钉钉等 |
| AstrBot | `ASTRBOT_*` | 机器人集成 |

### 报告格式

| 类型 | 配置 | 说明 |
|------|------|------|
| `simple` | `REPORT_TYPE=simple` | 简洁版（默认） |
| `full` | `REPORT_TYPE=full` | 完整版（含所有指标） |
| `brief` | `REPORT_TYPE=brief` | 极简摘要 |
| 自定义模板 | `REPORT_RENDERER_ENABLED=true` | Jinja2 模板自定义 |

### Markdown 转图片

部分渠道不支持 Markdown，可自动转换：

```ini
MARKDOWN_TO_IMAGE_CHANNELS=telegram,email
MARKDOWN_TO_IMAGE_MAX_CHARS=3000    # 超过字数转图片
MD2IMG_ENGINE=wkhtmltoimage         # 或 markdown-to-file
```

---

## 10. Web API 与前端

### API 端点（`/api/v1/`）

| 端点 | 方法 | 功能 |
|------|------|------|
| `/analysis/analyze` | POST | 触发股票分析（同步/异步） |
| `/analysis/status/{task_id}` | GET | 查询任务状态 |
| `/analysis/tasks` | GET | 列出活跃任务 |
| `/analysis/tasks/stream` | GET | SSE 实时更新 |
| `/stocks/info/{code}` | GET | 股票元数据 |
| `/stocks/extract-from-image` | POST | 视觉 API 从图片提取股票代码 |
| `/stocks/parse-import` | POST | 解析 CSV/Excel/剪贴板 |
| `/history/reports` | GET | 列出分析历史 |
| `/history/reports/{id}` | GET | 获取报告详情 |
| `/backtest/results` | GET | 回测准确率统计 |
| `/portfolio/*` | GET/POST/PUT | 持仓管理 |
| `/system_config/*` | GET/POST | 系统设置 |
| `/usage/summary` | GET | LLM Token 用量统计 |
| `/auth/*` | POST | 登录/退出 |
| `/agent/chat` | POST | 智能体多轮对话 |
| `/agent/strategies` | GET | 可用策略列表 |

### Web 界面页面

1. **主仪表盘**（`/`）
   - 分析历史记录与详情查看
   - 快捷编辑、批量删除
   - 状态指示器（信号类型、情绪评分）

2. **系统设置**（`/settings`）
   - 基础配置：股票列表、通知渠道
   - LLM 配置：模型选择、API Key
   - 高级配置：数据源优先级、回测参数
   - 智能导入：图片/CSV/粘贴（含视觉识别）

3. **对话页面**（`/chat`）
   - 11 种策略选择
   - 自然语言问答
   - 工具调用轨迹实时展示
   - 导出/发送结果

4. **API 文档**（`/docs`）：Swagger UI 自动生成

### 任务队列机制

```
POST /analyze （async_mode=true）
    │
    ▼
TaskQueue（src/services/task_queue.py）
    ├── 去重：同一股票已在队列中则拒绝
    ├── FIFO 执行（线程池）
    └── 存储任务元数据 & 结果
    │
    ▼
任务 ID 返回给客户端（202 Accepted）
    │
    ▼ 客户端轮询或 SSE 订阅
GET /status/{task_id}  或  GET /tasks/stream（SSE）
```

---

## 11. 持久化与回测

### 数据库（SQLite via SQLAlchemy）

默认路径：`./data/stock_analysis.db`

#### 主要数据表

| 表名 | 字段 | 说明 |
|------|------|------|
| `StockDaily` | code, date, open, high, low, close, volume, ma5, ma10, ma20 | 历史 K 线 + 技术指标 |
| `AnalysisReport` | code, date, decision_type, sentiment_score, dashboard_json, raw_text | 完整分析报告 |
| `BacktestResult` | report_id, grade, direction_correct, win_rate, hit_rate | 回测结果 |
| `PortfolioEntry` | code, name, cost_price, quantity, notes | 持仓记录 |
| `TaskInfo` | task_id, status, created_at, result_json | 异步任务状态 |

### 回测评估逻辑

```
分析报告生成后，等待 BACKTEST_MIN_AGE_DAYS 天

评估维度：
1. 方向准确率：看多 → 实际上涨？看空 → 实际下跌？
2. 买点命中率：止盈/止损价位是否被触及？
3. 胜率 %：综合正确率

评级标准：
A：方向准确 + 买点命中
B：方向准确，买点偏差 ±5%
C：方向偏差，但未触止损
D：方向错误 + 触及止损
```

---

## 12. 配置参考

### 最小配置（.env 最少需要填写）

```ini
# 股票列表（A股用代码，港股加 hk 前缀，美股用 TICKER）
STOCK_LIST=600519,000001,hk00700,AAPL

# LLM（至少配置一个，Gemini 免费额度最高）
GEMINI_API_KEY=your_key_here

# 通知（至少配置一个）
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 完整配置分类

#### LLM 配置

```ini
# Google Gemini（推荐，免费 1500 次/天）
GEMINI_API_KEY=

# Anthropic Claude
ANTHROPIC_API_KEY=

# OpenAI 或兼容接口（DeepSeek 等）
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com  # DeepSeek
OPENAI_MODEL=deepseek-chat

# AIHubMix（一个 Key 访问多个模型）
AIHUBMIX_KEY=

# LiteLLM YAML 路由配置（高级）
LITELLM_CONFIG=./litellm_config.yaml

# 多渠道配置
LLM_CHANNELS=deepseek,gemini
LLM_DEEPSEEK_PROTOCOL=openai
LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_DEEPSEEK_API_KEY=
LLM_DEEPSEEK_MODELS=deepseek-chat

LLM_TEMPERATURE=0.7
```

#### 数据源配置

```ini
# 数据源优先级（数字越小优先级越高）
EFINANCE_PRIORITY=0
AKSHARE_PRIORITY=1
TUSHARE_PRIORITY=2
PYTDX_PRIORITY=2
BAOSTOCK_PRIORITY=3
YFINANCE_PRIORITY=4

# Tushare Pro Token（可选，提升 A 股数据质量）
TUSHARE_TOKEN=

# 实时行情
ENABLE_REALTIME_QUOTE=true
REALTIME_SOURCE_PRIORITY=tencent,akshare_sina,efinance

# 基本面数据
ENABLE_FUNDAMENTAL_PIPELINE=true
FUNDAMENTAL_STAGE_TIMEOUT_SECONDS=8.0
FUNDAMENTAL_FETCH_TIMEOUT_SECONDS=3.0
FUNDAMENTAL_CACHE_TTL_SECONDS=3600
```

#### 新闻搜索配置

```ini
# 博查（中文搜索效果好，推荐）
BOCHA_API_KEYS=key1,key2

# Tavily（免费 1000 次/月）
TAVILY_API_KEYS=key1,key2

# SerpAPI（免费 100 次/月）
SERPAPI_API_KEYS=

# Brave Search
BRAVE_API_KEYS=

# SearXNG（自建，无限额）
SEARXNG_BASE_URLS=http://your-searxng.com

NEWS_MAX_AGE_DAYS=3           # 只看最近 3 天的新闻
```

#### 分析配置

```ini
BIAS_THRESHOLD=5.0             # 乖离率阈值（%）
ENABLE_CHIP_DISTRIBUTION=false # 筹码分布（可能不稳定）
TRADING_DAY_CHECK_ENABLED=true # 非交易日跳过
ANALYSIS_DELAY=2               # 每股分析间隔（秒，避免 API 限速）
MAX_WORKERS=3                  # 并发线程数
```

#### 通知配置

```ini
# 企业微信
WECHAT_WEBHOOK_URL=

# 飞书
FEISHU_WEBHOOK_URL=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_MESSAGE_THREAD_ID=    # 话题 ID（可选）

# 邮件
EMAIL_SENDER=xxx@gmail.com
EMAIL_PASSWORD=app_specific_password
EMAIL_RECEIVERS=a@x.com,b@x.com
EMAIL_SENDER_NAME=股票分析助手

# Discord
DISCORD_WEBHOOK_URL=
DISCORD_BOT_TOKEN=
DISCORD_MAIN_CHANNEL_ID=

# 其他
PUSHOVER_TOKEN=
PUSHPLUS_TOKEN=
SERVERCHAN3_SENDKEY=
CUSTOM_WEBHOOK_URLS=

# 报告设置
REPORT_TYPE=simple             # simple / full / brief
SINGLE_STOCK_NOTIFY=false      # 每股立即通知（vs 批量）
REPORT_SUMMARY_ONLY=false      # 仅发送汇总

# Markdown 转图片
MARKDOWN_TO_IMAGE_CHANNELS=telegram
MARKDOWN_TO_IMAGE_MAX_CHARS=3000
MD2IMG_ENGINE=wkhtmltoimage
```

#### 调度配置

```ini
SCHEDULE_ENABLED=false         # 启用定时调度
SCHEDULE_TIME=18:00            # 每天执行时间（北京时间）
RUN_IMMEDIATELY=true           # 启动时立即运行一次
MARKET_REVIEW_ENABLED=true     # 启用大盘综述
MARKET_REVIEW_REGION=cn        # cn / us / both
MERGE_EMAIL_NOTIFICATION=true  # 合并邮件通知
```

#### Web UI 配置

```ini
WEBUI_ENABLED=false            # 是否自动启动 Web UI
WEBUI_HOST=127.0.0.1           # 绑定地址（Docker 用 0.0.0.0）
WEBUI_PORT=8000
WEBUI_AUTO_BUILD=false         # 自动构建前端
ADMIN_AUTH_ENABLED=false       # 启用密码保护
ADMIN_SESSION_MAX_AGE_HOURS=24
REPORT_RENDERER_ENABLED=false  # 使用 Jinja2 模板
```

#### 智能体配置

```ini
AGENT_MODE=false               # 启用 /chat 智能体（LLM 配置后自动启用）
AGENT_SKILLS=bull_trend,ma_golden_cross,volume_breakout,bottom_volume
# 或 AGENT_SKILLS=all 启用全部 11 种策略
AGENT_MAX_STEPS=10
AGENT_ARCH=single              # single 或 multi（多智能体编排）
AGENT_ORCHESTRATOR_MODE=standard  # quick / standard / full / strategy
AGENT_RISK_OVERRIDE=false      # Risk Agent 是否可 veto 买入信号
AGENT_MEMORY_ENABLED=false     # 追踪历史准确率
AGENT_STRATEGY_AUTOWEIGHT=false # 按回测结果自动加权策略
```

#### 回测配置

```ini
BACKTEST_ENABLED=false
BACKTEST_EVAL_WINDOW_DAYS=5    # 评估窗口（交易日）
BACKTEST_MIN_AGE_DAYS=3        # 最小等待天数
BACKTEST_NEUTRAL_BAND_PCT=2.0  # 中性判断阈值（%）
```

#### 系统配置

```ini
DATABASE_PATH=./data/stock_analysis.db
LOG_DIR=./logs
LOG_LEVEL=INFO                 # DEBUG / INFO / WARNING / ERROR
TZ=Asia/Shanghai

# 代理（本地开发用）
USE_PROXY=false
PROXY_HOST=127.0.0.1
PROXY_PORT=10809
```

---

## 13. 部署方式

### 方式一：GitHub Actions（推荐新手，完全免费）

1. Fork 仓库
2. 进入 Settings → Secrets and Variables → Actions → 添加 Secrets：
   ```
   STOCK_LIST=600519,000001,AAPL
   GEMINI_API_KEY=...
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```
3. 进入 Actions → Enable workflows
4. 工作流按计划运行（默认：工作日北京时间 18:00）
5. 也可手动触发：Actions → 每日股票分析 → Run workflow

### 方式二：本地运行

```bash
# 克隆仓库
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis

# 安装依赖
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env，填入 API Key 和股票列表

# 一次性分析运行
python main.py

# 启用 Web UI
python main.py --webui

# 定时调度模式（持续运行）
python main.py --schedule

# 仅 Web UI，不调度
python main.py --webui-only
```

### 方式三：Docker

```bash
# 构建镜像
docker build -f docker/Dockerfile -t daily-stock-analysis .

# 运行调度模式
docker run --env-file .env \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  daily-stock-analysis

# 运行 API Server
docker run --env-file .env \
  -p 8000:8000 \
  -v ./data:/app/data \
  daily-stock-analysis python main.py --serve-only

# Docker Compose（推荐）
cd docker
docker-compose up -d            # 调度器
docker-compose up -d server     # API 服务器
```

### 方式四：VPS / 云服务器（长期运行）

```bash
# 使用 systemd 或 supervisor 管理进程
python main.py --schedule --webui

# 或使用 nohup
nohup python main.py --schedule > logs/run.log 2>&1 &
```

---

## 14. 使用方法（快速上手）

### CLI 常用命令

```bash
# 分析默认股票列表
python main.py

# 调试模式（详细日志）
python main.py --debug

# 只抓数据，不调用 LLM（测试数据连接）
python main.py --dry-run

# 指定股票
python main.py --stocks 600519,000001,hk00700,AAPL

# 不发送通知
python main.py --no-notify

# 每股分析完立即通知（而非批量完成后通知）
python main.py --single-notify

# 只做大盘综述
python main.py --market-review

# 启动 Web UI（含调度器）
python main.py --webui

# 只启动 Web UI
python main.py --webui-only

# 只运行 API Server
python main.py --serve-only

# 启用定时调度
python main.py --schedule
```

### 股票代码格式

| 市场 | 格式 | 示例 |
|------|------|------|
| A 股上交所 | 6 位数字 | `600519`（贵州茅台） |
| A 股深交所 | 6 位数字 | `000001`（平安银行） |
| A 股创业板 | 6 位数字 | `300750`（宁德时代） |
| 港股 | `hk` + 5 位数字 | `hk00700`（腾讯） |
| 美股 | Ticker 符号 | `AAPL`、`TSLA`、`NVDA` |

### Web UI 使用流程

1. 启动：`python main.py --webui`
2. 访问：`http://localhost:8000`
3. 进入 **Settings** 配置 API Key、股票列表、通知渠道
4. 回到主页，点击 **分析** 触发分析
5. 进入 **/chat** 页面进行智能体对话

### Bot 命令（Discord / 飞书 / 钉钉）

| 命令 | 功能 |
|------|------|
| `/analyze 600519` | 分析指定股票 |
| `/ask 贵州茅台最近怎么样？` | 自然语言查询 |
| `/market` | 获取大盘综述 |
| `/chat` | 开启多轮对话模式 |
| `/watchlist add 600519` | 添加到观察列表 |
| `/watchlist remove 600519` | 从观察列表移除 |
| `/watchlist show` | 查看观察列表 |

---

## 15. 测试体系

测试位于 `/tests/` 目录，覆盖率约 80%：

```bash
# 运行全部测试
pytest tests/

# 运行特定测试文件
pytest tests/test_config_manager.py
pytest tests/test_pipeline.py
pytest tests/test_notification.py

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

主要测试类别：
- 单元测试：配置、认证、存储、格式化
- 集成测试：数据抓取器、通知发送、API 端点
- Mock 测试：LiteLLM stub、搜索服务模拟
- Agent 测试：策略加载、工具调用

---

## 16. 架构设计模式总结

| 模式 | 应用位置 | 说明 |
|------|---------|------|
| **单例模式** | `Config`、`Database`、`FetcherManager` | 全局唯一实例，避免重复初始化 |
| **策略模式** | `DataFetcherManager` + 各 Fetcher | 动态切换数据源，支持优先级降级 |
| **工厂模式** | FastAPI App、通知发送器 | 根据配置创建具体实现 |
| **仓储模式** | `analysis_repo`、`stock_repo` | 数据访问层抽象，隔离 ORM 细节 |
| **模板方法** | 通知发送器基类 | 定义发送流程骨架，子类实现具体渠道 |
| **依赖注入** | FastAPI `deps.py` | 解耦服务依赖，便于测试 |
| **中间件模式** | Auth、Error Handler | 横切关注点（认证、错误处理）统一处理 |
| **Agent/Tool** | `src/agent/` | LLM 多步推理 + 工具调用（ReAct 风格） |
| **Hub-Spoke** | `NotificationService` | 中心分发，多渠道并发推送 |
| **管道/链** | `StockAnalysisPipeline` | 数据→技术→新闻→LLM→通知，顺序编排 |

---

## 附录：外部服务依赖汇总

### LLM 服务

| 服务 | 免费额度 | 注册地址 |
|------|---------|---------|
| Google Gemini | 1500 次/天 | aistudio.google.com |
| Anthropic Claude | 无（付费） | console.anthropic.com |
| OpenAI | 无（付费） | platform.openai.com |
| DeepSeek | 极低成本 | platform.deepseek.com |
| AIHubMix | 按用量 | aihubmix.com |

### 新闻搜索服务

| 服务 | 免费额度 | 特点 |
|------|---------|------|
| Tavily | 1000 次/月 | AI 摘要，适合英文 |
| 博查（Bocha） | 按量 | 中文优化 |
| SerpAPI | 100 次/月 | 支持百度/Google |
| Brave Search | 2000 次/月 | 隐私保护 |
| SearXNG | 无限 | 需自建 |

### Python 核心依赖

```
fastapi, uvicorn        # Web 框架
sqlalchemy              # ORM
litellm                 # LLM 统一接口
efinance, akshare       # A 股数据
yfinance                # 美股数据
tushare                 # Tushare Pro
pandas, numpy           # 数据处理
tavily-python           # 新闻搜索
lark-oapi               # 飞书 SDK
discord.py              # Discord Bot
jinja2                  # 报告模板
schedule                # 任务调度
tenacity                # 重试逻辑
```

---

*文档由 Claude Code 自动生成，基于对源代码的全面分析。如需进一步了解特定模块，请参考对应源文件或查阅 `/docs/` 目录。*
