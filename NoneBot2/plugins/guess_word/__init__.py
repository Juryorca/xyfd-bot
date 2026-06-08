import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import GroupMessageEvent


BASE_DIR = Path(__file__).parent
CARD_PATH = BASE_DIR / "cards.json"
CONFIG_PATH = BASE_DIR / "config.json"

VISIBLE_CHARS = set(" \n\r\t，。、：:；;！!？?（）()[]【】+-*/%=0123456789")

games: dict[int, dict] = {}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {
            "allowed_groups": [],
            "timeout_minutes": 30,
        }

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "allowed_groups": data.get("allowed_groups", []),
        "timeout_minutes": data.get("timeout_minutes", 30),
    }


config = load_config()


def is_group_allowed(group_id: int) -> bool:
    allowed_groups = config.get("allowed_groups", [])

    # 空白名单时默认禁用，避免被随便拉群使用
    if not allowed_groups:
        return False

    return group_id in allowed_groups


def get_timeout() -> timedelta:
    minutes = int(config.get("timeout_minutes", 30))
    return timedelta(minutes=minutes)


def is_game_expired(game: dict) -> bool:
    started_at = game.get("started_at")

    if not isinstance(started_at, datetime):
        return False

    return datetime.now() - started_at >= get_timeout()


def cleanup_expired_game(group_id: int) -> bool:
    game = games.get(group_id)

    if not game:
        return False

    if is_game_expired(game):
        del games[group_id]
        return True

    return False


def load_cards() -> list[dict]:
    with CARD_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cards: list[dict] = []

    for item in data:
        name = str(item.get("name", "")).strip()
        text = str(item.get("text", "")).strip()

        if not name:
            continue

        # 没有效果描述的卡牌不进入猜字卡池
        if not text:
            continue

        card = {
            "name": name,
            "text": text,
        }

        if "value" in item:
            card["value"] = item["value"]

        cards.append(card)

    return cards


cards = load_cards()


def normalize(text: str) -> str:
    return text.strip().replace(" ", "").lower()


def build_hint_text(card: dict) -> tuple[str, str]:
    header = ""

    if "value" in card:
        header = f"价值：{card['value']}"

    body = card.get("text", "")

    return header, body


def render_hint(hint: str, revealed: set[str]) -> str:
    return "".join(ch if ch in revealed or ch in VISIBLE_CHARS else "□" for ch in hint)


def render_game_hint(game: dict) -> str:
    header = game.get("hint_header", "")
    body = game.get("hint_body", "")
    masked_body = render_hint(body, game["revealed"])

    if header:
        return f"{header}\n{masked_body}"

    return masked_body


def full_game_hint(game: dict) -> str:
    header = game.get("hint_header", "")
    body = game.get("hint_body", "")

    if header:
        return f"{header}\n{body}"

    return body


def is_hint_fully_revealed(hint: str, revealed: set[str]) -> bool:
    return all(ch in revealed or ch in VISIBLE_CHARS for ch in hint)


# 指令必须 @机器人 才触发
ping = on_command("ping", priority=5)


@ping.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    if not is_group_allowed(group_id):
        return

    await ping.finish("pong")
# 指令必须 @机器人 才触发
start_guess = on_command("猜字", rule=to_me(), priority=5)


@start_guess.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id

    if not is_group_allowed(group_id):
        await start_guess.finish("本群未启用猜字功能。")

    if cleanup_expired_game(group_id):
        await start_guess.finish("上一局猜字已超时结束，请重新发送 /猜字 开始。")

    if group_id in games:
        await start_guess.finish(
            "本群已经有猜字游戏在进行了。\n发送 /猜字状态 查看当前提示。"
        )

    if not cards:
        await start_guess.finish("卡牌库为空，请检查 cards.json。")

    card = random.choice(cards)
    hint_header, hint_body = build_hint_text(card)

    games[group_id] = {
        "name": card["name"],
        "hint_header": hint_header,
        "hint_body": hint_body,
        "card": card,
        "revealed": set(),
        "started_at": datetime.now(),
    }

    await start_guess.finish(
        "猜字开始！\n"
        "根据逐步揭示的效果描述，猜出物品名字。\n\n"
        "相关指令：\n"
        "@机器人 /猜字：开始一局新游戏\n"
        "@机器人 /猜字状态：查看当前提示\n"
        "@机器人 /结束猜字：结束本局并公布答案\n\n"
        "玩法说明：\n"
        "发送任意消息，消息里的字如果出现在效果描述中，就会被揭示。\n"
        "游戏进行中的消息检测不需要 @机器人。\n"
	"精华请在最后带上精华二字\n"
        "如果消息里包含正确的物品名字，就算猜对。\n\n"
        "当前提示：\n"
        f"{render_game_hint(games[group_id])}"
    )


# 指令必须 @机器人 才触发
status_guess = on_command("猜字状态", rule=to_me(), priority=5)


@status_guess.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id

    if not is_group_allowed(group_id):
        await status_guess.finish("本群未启用猜字功能。")

    if cleanup_expired_game(group_id):
        await status_guess.finish("本局猜字已超时结束。")

    if group_id not in games:
        await status_guess.finish("本群没有正在进行的猜字游戏。")

    game = games[group_id]

    await status_guess.finish(f"当前提示：\n{render_game_hint(game)}")


# 指令必须 @机器人 才触发
stop_guess = on_command("结束猜字", rule=to_me(), priority=5)


@stop_guess.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id

    if not is_group_allowed(group_id):
        await stop_guess.finish("本群未启用猜字功能。")

    if cleanup_expired_game(group_id):
        await stop_guess.finish("本局猜字已超时结束。")

    if group_id not in games:
        await stop_guess.finish("本群没有正在进行的猜字游戏。")

    game = games[group_id]
    del games[group_id]

    await stop_guess.finish(
        f"猜字已结束。\n答案是：{game['name']}\n{full_game_hint(game)}"
    )


# 游戏中的普通消息检测不需要 @机器人
guess_listener = on_message(priority=20, block=False)


@guess_listener.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id

    if not is_group_allowed(group_id):
        return

    if group_id not in games:
        return

    if cleanup_expired_game(group_id):
        await guess_listener.finish(f"本局猜字已超时结束。\n答案是: {name}\n{full_game_hint(game)}")

    text = event.get_plaintext().strip()

    if not text:
        return

    # 普通消息里如果是命令，不参与揭示
    if text.startswith("/"):
        return

    game = games[group_id]
    name = game["name"]
    hint_body = game["hint_body"]

    # 1. 先判断是否猜中物品名字
    if normalize(name) in normalize(text):
        del games[group_id]
        await guess_listener.finish(f"猜对了！\n答案是：{name}\n{full_game_hint(game)}")

    # 2. 没猜中，再用消息里的字揭示效果描述
    old_revealed = set(game["revealed"])

    for ch in text:
        if ch in hint_body and ch not in VISIBLE_CHARS:
            game["revealed"].add(ch)

    if game["revealed"] == old_revealed:
        return

    masked = render_game_hint(game)

    if is_hint_fully_revealed(hint_body, game["revealed"]):
        await guess_listener.finish(f"当前提示已全部揭示！\n请猜物品名字。\n\n{masked}")

    await guess_listener.finish(f"当前提示：\n{masked}")
