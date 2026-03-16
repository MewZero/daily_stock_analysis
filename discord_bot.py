"""
Discord Bot - 接收指令触发股票分析
用法: /opt/homebrew/bin/python3.12 discord_bot.py

Discord 指令:
  !analyze NOW AAPL TSLA     - 分析指定股票
  !analyze                   - 分析 .env 里 STOCK_LIST 的股票
  !help                      - 显示帮助
"""

import asyncio
import os
import sys
import uuid
import logging
import threading
from typing import List

import discord
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

if not BOT_TOKEN:
    print("错误: 未配置 DISCORD_BOT_TOKEN")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 防止同时跑多个分析任务
analysis_lock = threading.Lock()


def run_analysis(stock_codes: List[str]) -> str:
    """在子线程中跑分析，返回摘要文本"""
    try:
        from src.config import get_config
        from src.core.pipeline import StockAnalysisPipeline

        config = get_config()
        config.stock_list = stock_codes

        query_id = uuid.uuid4().hex
        pipeline = StockAnalysisPipeline(
            config=config,
            max_workers=3,
            query_id=query_id,
            query_source="discord",
        )

        results = pipeline.run(
            stock_codes=stock_codes,
            dry_run=False,
            send_notification=True,
            merge_notification=False,
        )

        if not results:
            return "分析完成，但没有返回结果。"

        lines = ["**分析完成** ✅"]
        for r in results:
            code = getattr(r, 'stock_code', '?')
            name = getattr(r, 'stock_name', code)
            suggestion = getattr(r, 'suggestion', '')
            score = getattr(r, 'score', '')
            trend = getattr(r, 'trend', '')
            lines.append(f"• **{name}({code})** — {suggestion} | 评分 {score} | {trend}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("分析出错")
        return f"分析出错: {e}"


@client.event
async def on_ready():
    logger.info(f"Bot 已上线: {client.user}")
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("股票分析 Bot 已上线 ✅\n发送 `!analyze 股票代码` 开始分析，例如: `!analyze NOW AAPL`")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = message.content.strip()

    if content == "!help":
        await message.channel.send(
            "**使用方法:**\n"
            "`!analyze NOW AAPL TSLA` — 分析指定股票\n"
            "`!analyze` — 分析默认股票列表 (STOCK_LIST)\n"
            "`!help` — 显示此帮助"
        )
        return

    if content.startswith("!analyze"):
        if not analysis_lock.acquire(blocking=False):
            await message.channel.send("⏳ 有分析正在进行中，请稍后再试...")
            return

        parts = content.split()
        if len(parts) > 1:
            stock_codes = [s.upper() for s in parts[1:]]
        else:
            default = os.getenv("STOCK_LIST", "")
            stock_codes = [s.strip().upper() for s in default.split(",") if s.strip()]

        if not stock_codes:
            analysis_lock.release()
            await message.channel.send("❌ 请提供股票代码，例如: `!analyze NOW AAPL`")
            return

        await message.channel.send(f"🔍 开始分析: **{', '.join(stock_codes)}**\n大约需要 3-5 分钟，结果会直接发到此频道...")

        loop = asyncio.get_event_loop()

        def run_and_release():
            try:
                result = run_analysis(stock_codes)
                asyncio.run_coroutine_threadsafe(
                    message.channel.send(result), loop
                )
            finally:
                analysis_lock.release()

        thread = threading.Thread(target=run_and_release, daemon=True)
        thread.start()


if __name__ == "__main__":
    logger.info("启动 Discord Bot...")
    client.run(BOT_TOKEN)
