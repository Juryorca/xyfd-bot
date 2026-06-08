import json
import re
from pathlib import Path


RAW_PATH = Path("cards_raw.json")
OUT_PATH = Path("cards.json")


SPECIAL_ICON_MAP = {
    "coin": "金币",
    "essence_token": "精华代币",
    "removal_token": "移除代币",
    "reroll_token": "重置代币",
    # 骰子状态，没有独立中文 name，手动补
    "d3_1": "1点",
    "d3_2": "2点",
    "d3_3": "3点",
    "dice1": "1点",
    "dice2": "2点",
    "dice3": "3点",
    "dice4": "4点",
    "dice5": "5点",
}


SKIP_IDS = {
    "missing",
    "item_missing",
    "d3_1",
    "d3_2",
    "d3_3",
    "dice1",
    "dice2",
    "dice3",
    "dice4",
    "dice5",
}


RARITY_ZH = {
    "common": "普通",
    "uncommon": "非凡",
    "rare": "稀有",
    "very_rare": "非常稀有",
    "essence": "精华",
    None: "",
    "": "",
}


TYPE_ZH = {
    "symbol": "符号",
    "item": "物品",
    "essence": "精华",
}


def load_cards() -> list[dict]:
    return json.loads(RAW_PATH.read_text(encoding="utf-8"))


def build_name_by_id(cards: list[dict]) -> dict[str, str]:
    result = {}

    for card in cards:
        card_id = card.get("id", "")
        name = card.get("name", "")

        if card_id and name:
            result[card_id] = name

    return result


def build_group_members(cards: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}

    for card in cards:
        card_id = card.get("id", "")
        name = card.get("name", "")

        if not name:
            continue

        if card_id in SKIP_IDS:
            continue

        for group in card.get("meta", {}).get("groups", []):
            groups.setdefault(group, []).append(name)

    # 特殊组：描述里有，但 meta.groups 里没有
    groups["item_pepper"] = [
        card["name"]
        for card in cards
        if card.get("type") == "item"
        and card.get("id", "").endswith("_pepper")
        and not card.get("id", "").endswith("_essence")
        and card.get("name")
    ]

    groups["passed"] = ["本局曾出现但未添加的符号"]

    # 去重，保留顺序
    for group, names in groups.items():
        seen = set()
        deduped = []

        for name in names:
            if name in seen:
                continue
            seen.add(name)
            deduped.append(name)

        groups[group] = deduped

    return groups


def format_name_list(names: list[str], connector: str) -> str:
    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    if len(names) == 2:
        return f"{names[0]}{connector}{names[1]}"

    return "、".join(names[:-1]) + connector + names[-1]


def replace_values(text: str, values: list) -> str:
    def repl(match: re.Match) -> str:
        index = int(match.group(1)) - 1

        if 0 <= index < len(values):
            return str(values[index])

        return match.group(0)

    return re.sub(r"<value_(\d+)>", repl, text)


def replace_icons(text: str, name_by_id: dict[str, str]) -> str:
    def repl(match: re.Match) -> str:
        key = match.group(1)

        if key in SPECIAL_ICON_MAP:
            return SPECIAL_ICON_MAP[key]

        return name_by_id.get(key, key)

    return re.sub(r"<icon_([a-zA-Z0-9_]+)>", repl, text)


def replace_group_pairs(text: str, group_members: dict[str, list[str]]) -> str:
    # 注意顺序：先处理“或者”，再处理“或”
    def repl_or_long(match: re.Match) -> str:
        group = match.group(1)
        names = group_members.get(group, [])
        return format_name_list(names, "或") if names else match.group(0)

    text = re.sub(
        r"<group_([a-zA-Z0-9_]+)>或者<last_\1>",
        repl_or_long,
        text,
    )

    def repl_and(match: re.Match) -> str:
        group = match.group(1)
        names = group_members.get(group, [])
        return format_name_list(names, "和") if names else match.group(0)

    text = re.sub(
        r"<group_([a-zA-Z0-9_]+)>和<last_\1>",
        repl_and,
        text,
    )

    def repl_or(match: re.Match) -> str:
        group = match.group(1)
        names = group_members.get(group, [])
        return format_name_list(names, "或") if names else match.group(0)

    text = re.sub(
        r"<group_([a-zA-Z0-9_]+)>或<last_\1>",
        repl_or,
        text,
    )

    return text


def replace_remaining_groups(text: str, group_members: dict[str, list[str]]) -> str:
    def repl_group(match: re.Match) -> str:
        group = match.group(1)
        names = group_members.get(group, [])

        if not names:
            return match.group(0)

        return "、".join(names)

    def repl_last(match: re.Match) -> str:
        group = match.group(1)
        names = group_members.get(group, [])

        if not names:
            return match.group(0)

        return names[-1]

    text = re.sub(r"<group_([a-zA-Z0-9_]+)>", repl_group, text)
    text = re.sub(r"<last_([a-zA-Z0-9_]+)>", repl_last, text)

    return text


def strip_style_tags(text: str) -> str:
    text = re.sub(r"<color_[A-Fa-f0-9]+>", "", text)
    text = re.sub(r"<text_color_[a-zA-Z0-9_]+>", "", text)
    text = text.replace("<end>", "")

    return text


def normalize_desc(
    raw_desc: str,
    values: list,
    name_by_id: dict[str, str],
    group_members: dict[str, list[str]],
) -> str:
    text = raw_desc

    text = replace_values(text, values)
    text = replace_icons(text, name_by_id)
    text = replace_group_pairs(text, group_members)
    text = replace_remaining_groups(text, group_members)
    text = strip_style_tags(text)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def parse_value(meta: dict):
    raw = meta.get("value", None)

    if raw is None:
        return None

    try:
        if "." in str(raw):
            value = float(raw)
        else:
            value = int(raw)
    except ValueError:
        return raw

    if value == 0:
        return None

    return value


def main():
    raw_cards = load_cards()
    name_by_id = build_name_by_id(raw_cards)
    group_members = build_group_members(raw_cards)

    cards = []

    for raw in raw_cards:
        card_id = raw.get("id", "")
        name = raw.get("name", "")
        card_type = raw.get("type", "")
        meta = raw.get("meta", {})
        raw_desc = raw.get("desc", "")

        if card_id in SKIP_IDS:
            continue

        if not name:
            continue

        values = meta.get("values", [])
        desc = (
            normalize_desc(raw_desc, values, name_by_id, group_members)
            if raw_desc
            else ""
        )

        item = {
            "id": card_id,
            "name": name,
            "type": card_type,
            "type_zh": TYPE_ZH.get(card_type, card_type),
            "rarity": meta.get("rarity", ""),
            "rarity_zh": RARITY_ZH.get(meta.get("rarity", ""), meta.get("rarity", "")),
            "text": desc,
        }

        value = parse_value(meta)
        if value is not None:
            item["value"] = value

        cards.append(item)

    OUT_PATH.write_text(
        json.dumps(cards, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"wrote {OUT_PATH}")
    print(f"cards = {len(cards)}")

    leftovers = {}
    for card in cards:
        for tag in re.findall(r"<[^>]+>", card.get("text", "")):
            leftovers[tag] = leftovers.get(tag, 0) + 1

    if leftovers:
        print("\nleftover tags:")
        for tag, count in sorted(leftovers.items()):
            print(count, tag)
    else:
        print("leftover tags = 0")

    print("\npreview:")
    for key in [
        "miner",
        "jellyfish",
        "pufferfish",
        "essence_capsule",
        "removal_capsule",
        "chili_powder",
        "symbol_bomb_quantum",
    ]:
        for card in cards:
            if card["id"] == key:
                print("----")
                print(card["id"], card["name"])
                if "value" in card:
                    print("value:", card["value"])
                print(card["text"])
                break


if __name__ == "__main__":
    main()
