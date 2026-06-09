import random
from pathlib import Path
import gc

from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

# 插件目录
BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "images"

# 触发词
TRIGGERS = {"菜农", "农猪", "农农"}

matcher = on_message(priority=20, block=False)

@matcher.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text not in TRIGGERS:
        return

    # 获取所有图片文件（jpg/png/gif/webp）
    images = [
        p for p in IMAGE_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ]
    if not images:
        await matcher.finish("图片目录为空。")

    # 随机选一张
    chosen_image = random.choice(images)

    # 读取为 bytes，发送完马上释放
    img_bytes = chosen_image.read_bytes()
    try:
        await matcher.finish(MessageSegment.image(img_bytes))
    finally:
        # 删除引用，触发垃圾回收
        del img_bytes
        gc.collect()
