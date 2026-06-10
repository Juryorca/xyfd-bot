from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

yzlm = on_message(priority=10, block=False)


@yzlm.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()

    if "宇宙冷漠" not in text:
        return

    await yzlm.finish(
        MessageSegment.record("file:///app/napcat/musics/宇宙冷漠.mp3")
    )
