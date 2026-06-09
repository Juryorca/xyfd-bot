import json
import random
from pathlib import Path

from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent


BASE_DIR = Path(__file__).parent
FOOD_PATH = BASE_DIR / "foods.json"


def load_foods() -> list[str]:
    if not FOOD_PATH.exists():
        return []

    with FOOD_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    foods: list[str] = []

    for item in data:
        food = str(item).strip()
        if food:
            foods.append(food)

    return foods


foods = load_foods()


eat_what = on_message(priority=20, block=False)


@eat_what.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()

    if text != "吃什么":
        return

    if not foods:
        await eat_what.finish("菜单为空，请检查 foods.json。")

    food = random.choice(foods)

    await eat_what.finish(f"吃 {food}")
