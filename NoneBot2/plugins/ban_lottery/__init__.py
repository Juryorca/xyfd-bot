import random
import asyncio

from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.exception import ActionFailed


lottery_sessions: dict[int, set[int]] = {}
lottery_tasks: dict[int, asyncio.Task] = {}


def draw_duration() -> int:
    max_seconds = 60 * 60

    # 10% 概率 0 秒
    if random.random() < 0.10:
        return 0

    # 短时间多，长时间少；平均约 8 分钟
    avg_seconds = 5 * 60
    duration = int(random.expovariate(1 / avg_seconds))

    return max(1, min(duration, max_seconds))


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0 秒"

    minutes = seconds // 60
    rest_seconds = seconds % 60

    if minutes > 0:
        return f"{minutes} 分 {rest_seconds} 秒"

    return f"{rest_seconds} 秒"


ban_lottery = on_keyword({"禁言抽奖"}, priority=10, block=True)


@ban_lottery.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    user_id = event.user_id

    if group_id not in lottery_sessions:
        lottery_sessions[group_id] = set()
        lottery_tasks[group_id] = asyncio.create_task(finish_lottery(bot, group_id))

        await ban_lottery.send(
            Message(
                f"禁言抽奖开始！\n"
                f"[CQ:at,qq={user_id}] 已加入奖池。\n"
                f"其他人发送“禁言抽奖”加入。\n"
                f"30 秒后随机抽一位幸运群友。"
            )
        )
    else:
        if user_id in lottery_sessions[group_id]:
            await ban_lottery.finish(
                Message(f"[CQ:at,qq={user_id}] 你已经在奖池里了。")
            )

        await ban_lottery.send(
            Message(
                f"[CQ:at,qq={user_id}] 加入成功！当前奖池人数：{len(lottery_sessions[group_id]) + 1}"
            )
        )

    lottery_sessions[group_id].add(user_id)


async def finish_lottery(bot: Bot, group_id: int):
    await asyncio.sleep(30)

    players = list(lottery_sessions.pop(group_id, set()))
    lottery_tasks.pop(group_id, None)

    if not players:
        return

    target_id = random.choice(players)
    duration = draw_duration()

    if duration <= 0:
        await bot.send_group_msg(
            group_id=group_id,
            message=Message(f"开奖！[CQ:at,qq={target_id}] 抽中 0 秒，逃过一劫！"),
        )
        return

    try:
        await bot.set_group_ban(
            group_id=group_id,
            user_id=target_id,
            duration=duration,
        )
    except ActionFailed:
        await bot.send_group_msg(
            group_id=group_id,
            message=Message(
                f"开奖！抽中了 [CQ:at,qq={target_id}]，但是禁言失败，可能对方权限太高。"
            ),
        )
        return

    await bot.send_group_msg(
        group_id=group_id,
        message=Message(
            f"开奖！幸运群友是 [CQ:at,qq={target_id}]！\n"
            f"禁言时长：{format_duration(duration)}"
        ),
    )
