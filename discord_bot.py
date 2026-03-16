"""
Discord Bot - 接收指令触发股票分析 + 每用户定时推送
用法: /opt/homebrew/bin/python3.12 discord_bot.py

Discord 指令:
  !analyze NOW AAPL TSLA     - 立即分析指定股票
  !analyze                   - 立即分析我的关注列表
  !watch add AAPL TSLA       - 添加关注股票
  !watch remove AAPL         - 移除关注股票
  !watch list                - 查看我的关注列表
  !schedule 09:00            - 设置每天定时推送时间（24h格式）
  !schedule off              - 关闭定时推送
  !help                      - 显示帮助
"""

import asyncio
import json
import os
import sys
import uuid
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any

import discord
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
_channel_ids_raw = os.getenv("BOT_CHANNEL_IDS", os.getenv("DISCORD_CHANNEL_ID", "0"))
CHANNEL_IDS = [int(x.strip()) for x in _channel_ids_raw.split(",") if x.strip()]
USER_DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "discord_users.json")

if not BOT_TOKEN:
    print("错误: 未配置 DISCORD_BOT_TOKEN")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 防止同时跑多个分析任务
analysis_lock = threading.Lock()


# ===== 用户数据持久化 =====

def load_user_data() -> Dict[str, Any]:
    os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_user_data(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_user(user_id: str) -> Dict[str, Any]:
    data = load_user_data()
    if user_id not in data:
        data[user_id] = {"watchlist": [], "schedule": None, "channel_id": None}
        save_user_data(data)
    return data[user_id]


def update_user(user_id: str, user_data: Dict[str, Any]):
    data = load_user_data()
    data[user_id] = user_data
    save_user_data(data)


# ===== 分析逻辑 =====

def run_analysis(stock_codes: List[str], discord_user_id: str = "", discord_username: str = "") -> str:
    try:
        from src.config import get_config
        from src.core.pipeline import StockAnalysisPipeline

        config = get_config()
        config.stock_list = stock_codes

        # query_id 格式: discord_{user_id}_{username}_{hex}，方便在数据库里追踪是谁触发的
        suffix = uuid.uuid4().hex[:12]
        if discord_user_id:
            safe_name = discord_username.replace(" ", "_")[:20]
            query_id = f"discord_{discord_user_id}_{safe_name}_{suffix}"
        else:
            query_id = f"discord_{suffix}"

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
            code = getattr(r, 'code', '?')
            name = getattr(r, 'name', code)
            suggestion = getattr(r, 'operation_advice', '')
            score = getattr(r, 'sentiment_score', '')
            trend = getattr(r, 'trend_prediction', '')
            lines.append(f"• **{name}({code})** — {suggestion} | 评分 {score} | {trend}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("分析出错")
        return f"分析出错: {e}"


# ===== 定时任务 =====

async def scheduler_loop():
    """每分钟检查是否有用户需要定时推送"""
    await client.wait_until_ready()
    while not client.is_closed():
        now = datetime.now().strftime("%H:%M")
        data = load_user_data()
        for user_id, user_data in data.items():
            if user_data.get("schedule") == now and user_data.get("watchlist") and user_data.get("channel_id"):
                channel = client.get_channel(int(user_data["channel_id"]))
                if channel:
                    mention = f"<@{user_id}>"
                    stocks = user_data["watchlist"]
                    await channel.send(f"{mention} ⏰ 定时推送开始分析: **{', '.join(stocks)}**\n大约需要 3-5 分钟...")

                    loop = asyncio.get_event_loop()
                    username = user_data.get("username", "")
                    def run_scheduled(s=stocks, c=channel, m=mention, uid=user_id, uname=username):
                        result = run_analysis(s, discord_user_id=uid, discord_username=uname)
                        asyncio.run_coroutine_threadsafe(
                            c.send(f"{m}\n{result}"), loop
                        )
                    threading.Thread(target=run_scheduled, daemon=True).start()

        await asyncio.sleep(60)


# ===== Discord 事件 =====

@client.event
async def on_ready():
    logger.info(f"Bot 已上线: {client.user}")
    client.loop.create_task(scheduler_loop())
    for cid in CHANNEL_IDS:
        channel = client.get_channel(cid)
        if channel:
            await channel.send(
                "股票分析 Bot 已上线 ✅\n"
                "发送 `!help` 查看所有指令"
            )


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id not in CHANNEL_IDS:
        return

    content = message.content.strip()
    user_id = str(message.author.id)
    mention = message.author.mention

    # !help
    if content == "!help":
        await message.channel.send(
            "**📖 使用说明**\n"
            "`!analyze AAPL TSLA` — 立即分析指定股票\n"
            "`!analyze` — 立即分析我的关注列表\n"
            "`!watch add AAPL TSLA` — 添加关注股票\n"
            "`!watch remove AAPL` — 移除关注股票\n"
            "`!watch list` — 查看我的关注列表\n"
            "`!schedule 09:00` — 设置每天定时推送（24h格式）\n"
            "`!schedule off` — 关闭定时推送\n"
        )
        return

    # !watch
    if content.startswith("!watch"):
        parts = content.split()
        user_data = get_user(user_id)
        user_data["channel_id"] = str(message.channel.id)
        user_data["username"] = str(message.author.name)

        if len(parts) >= 3 and parts[1] == "add":
            new_stocks = [s.upper() for s in parts[2:]]
            existing = set(user_data["watchlist"])
            added = [s for s in new_stocks if s not in existing]
            user_data["watchlist"] = list(existing | set(new_stocks))
            update_user(user_id, user_data)
            await message.channel.send(f"{mention} ✅ 已添加: **{', '.join(added)}**\n当前列表: {', '.join(user_data['watchlist'])}")

        elif len(parts) >= 3 and parts[1] == "remove":
            to_remove = [s.upper() for s in parts[2:]]
            user_data["watchlist"] = [s for s in user_data["watchlist"] if s not in to_remove]
            update_user(user_id, user_data)
            await message.channel.send(f"{mention} ✅ 已移除: **{', '.join(to_remove)}**\n当前列表: {', '.join(user_data['watchlist']) or '（空）'}")

        elif len(parts) >= 2 and parts[1] == "list":
            watchlist = user_data.get("watchlist", [])
            schedule = user_data.get("schedule") or "未设置"
            if watchlist:
                await message.channel.send(f"{mention} 📋 你的关注列表: **{', '.join(watchlist)}**\n⏰ 定时推送: {schedule}")
            else:
                await message.channel.send(f"{mention} 📋 关注列表为空，用 `!watch add AAPL` 添加股票")
        else:
            await message.channel.send(f"{mention} 用法: `!watch add AAPL` / `!watch remove AAPL` / `!watch list`")
        return

    # !schedule
    if content.startswith("!schedule"):
        parts = content.split()
        user_data = get_user(user_id)
        user_data["channel_id"] = str(message.channel.id)

        if len(parts) == 2:
            if parts[1] == "off":
                user_data["schedule"] = None
                update_user(user_id, user_data)
                await message.channel.send(f"{mention} ✅ 已关闭定时推送")
            else:
                # 验证时间格式
                try:
                    datetime.strptime(parts[1], "%H:%M")
                    user_data["schedule"] = parts[1]
                    update_user(user_id, user_data)
                    watchlist = user_data.get("watchlist", [])
                    if not watchlist:
                        await message.channel.send(f"{mention} ✅ 定时推送设为 **{parts[1]}**\n⚠️ 关注列表为空，记得用 `!watch add AAPL` 添加股票")
                    else:
                        await message.channel.send(f"{mention} ✅ 定时推送设为 **{parts[1]}**，每天自动分析: {', '.join(watchlist)}")
                except ValueError:
                    await message.channel.send(f"{mention} ❌ 时间格式错误，请用24小时制，例如: `!schedule 09:00`")
        else:
            await message.channel.send(f"{mention} 用法: `!schedule 09:00` 或 `!schedule off`")
        return

    # !analyze
    if content.startswith("!analyze"):
        if not analysis_lock.acquire(blocking=False):
            await message.channel.send(f"{mention} ⏳ 有分析正在进行中，请稍后再试...")
            return

        parts = content.split()
        if len(parts) > 1:
            stock_codes = [s.upper() for s in parts[1:]]
        else:
            user_data = get_user(user_id)
            stock_codes = user_data.get("watchlist", [])
            if not stock_codes:
                analysis_lock.release()
                await message.channel.send(f"{mention} ❌ 关注列表为空，请用 `!watch add AAPL` 添加，或直接指定: `!analyze AAPL`")
                return

        await message.channel.send(f"{mention} 🔍 开始分析: **{', '.join(stock_codes)}**\n大约需要 3-5 分钟，结果会直接发到此频道...")

        loop = asyncio.get_event_loop()

        uid = user_id
        uname = str(message.author.name)

        def run_and_release():
            try:
                result = run_analysis(stock_codes, discord_user_id=uid, discord_username=uname)
                asyncio.run_coroutine_threadsafe(
                    message.channel.send(f"{mention}\n{result}"), loop
                )
            finally:
                analysis_lock.release()

        thread = threading.Thread(target=run_and_release, daemon=True)
        thread.start()


if __name__ == "__main__":
    logger.info("启动 Discord Bot...")
    client.run(BOT_TOKEN)
