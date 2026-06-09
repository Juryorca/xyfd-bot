import random
from pathlib import Path

from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message

BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "image"

# 触发词列表
TRIGGERS = ["菜农", "农猪", "农农"]

eat_what = on_message(priority=20, block=False)


@eat_what.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()

    if text not in TRIGGERS:
        return

    # 获取所有图片文件
    images = list(IMAGE_DIR.glob("*.*"))  # 可以匹配 jpg/png/gif 等
    if not images:
        await eat_what.finish("图片目录为空，请检查 ./image。")

    chosen_image = random.choice(images)

    # 发送图片
    msg = MessageSegment.image(str(chosen_image))
    await eat_what.finish(msg)
