import random

from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.exception import ActionFailed


ban_lottery = on_keyword({"禁言抽奖"}, priority=10, block=True)


@ban_lottery.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id

    # 0 秒到 60 分钟，即 0 ~ 3600 秒
    duration = random.randint(0, 60 * 60)

    try:
        await bot.set_group_ban(
            group_id=group_id,
            user_id=user_id,
            duration=duration,
        )
    except ActionFailed:
        await ban_lottery.finish("禁言失败，可能是我不是管理员，或者你是群主/管理员。")

    if duration == 0:
        await ban_lottery.finish(
            Message(f"[CQ:at,qq={user_id}] 恭喜抽中 0 秒，逃过一劫！")
        )

    minutes = duration // 60
    seconds = duration % 60

    if minutes > 0:
        text = f"[CQ:at,qq={user_id}] 恭喜抽中禁言 {minutes} 分 {seconds} 秒！"
    else:
        text = f"[CQ:at,qq={user_id}] 恭喜抽中禁言 {seconds} 秒！"

    await ban_lottery.finish(Message(text))
