"""
str.split 版: combp を使わずに同等の機能を実装したサンプル。
01.py (combp 版) との比較用。
"""

from __future__ import annotations

from dataclasses import dataclass


# ===========================================================================
# データmock（01.py と同一）
# ===========================================================================

enemy_info = [
    {"enemy_id": "12345ACB", "enemy_name": "スライム", "enemy_level": 5},
    {"enemy_id": "67890DEF", "enemy_name": "ゴブリン", "enemy_level": 10},
]

item_info = [
    {"item_id": 1001, "item_name": "こん棒", "item_type": "weapons"},
    {"item_id": 1002, "item_name": "鉄剣", "item_type": "weapons"},
    {"item_id": 2001, "item_name": "皮の盾", "item_type": "shield"},
    {"item_id": 3001, "item_name": "回復薬", "item_type": "consumable"},
]

skill_info = [
    {"skill_id": "SK001", "skill_name": "ファイアボール", "element": "fire"},
    {"skill_id": "SK002", "skill_name": "ヒール", "element": "holy"},
]


# ===========================================================================
# データ検索ヘルパー（01.py と同一）
# ===========================================================================


def find_enemy(enemy_id: str) -> dict | None:
    return next((e for e in enemy_info if e["enemy_id"] == enemy_id), None)


def find_item(item_id: int) -> dict | None:
    return next((i for i in item_info if i["item_id"] == item_id), None)


def find_skill(skill_id: str) -> dict | None:
    return next((s for s in skill_info if s["skill_id"] == skill_id), None)


# ===========================================================================
# コマンド型定義（01.py と同一）
# ===========================================================================


@dataclass
class GetItemName:
    enemy_id: str
    item_id: str


@dataclass
class GetItemDetail:
    enemy_id: str
    item_id: str
    field: str


@dataclass
class GetEnemySkill:
    enemy_id: str
    skill_id: str


@dataclass
class GetEnemyStatus:
    enemy_id: str
    field: str


Command = GetItemName | GetItemDetail | GetEnemySkill | GetEnemyStatus


# ===========================================================================
# パーサー: str.split ベース
#
#   combp 版との違い:
#     - split 一発でセグメント分割 → コマンド名で辞書引き分岐
#     - セグメント数の検証は手動
#     - エラーメッセージも手動で組み立てる
# ===========================================================================

# コマンド名 → (必要セグメント数, 変換関数) のレジストリ
_COMMAND_REGISTRY: dict[str, tuple[int, type]] = {
    "get_item_name":   (3, GetItemName),
    "get_item_detail": (4, GetItemDetail),
    "get_enemy_skill": (3, GetEnemySkill),
    "get_enemy_status": (3, GetEnemyStatus),
}


def parse_command(value: str) -> Command:
    """
    "get_item_name|12345ACB|1001" → GetItemName(enemy_id="12345ACB", item_id="1001")
    """
    segments = value.split("|")

    if not segments:
        raise ValueError(f"パース失敗: 空の入力")

    cmd_name = segments[0]

    if cmd_name not in _COMMAND_REGISTRY:
        valid = ", ".join(_COMMAND_REGISTRY.keys())
        raise ValueError(
            f"パース失敗: 未知のコマンド '{cmd_name}' "
            f"(有効なコマンド: {valid})"
        )

    expected_count, _ = _COMMAND_REGISTRY[cmd_name]

    if len(segments) != expected_count:
        raise ValueError(
            f"パース失敗: '{cmd_name}' は {expected_count} セグメント必要ですが "
            f"{len(segments)} セグメント検出 (入力: '{value}')"
        )

    # コマンドごとに構造体を生成
    match cmd_name:
        case "get_item_name":
            return GetItemName(enemy_id=segments[1], item_id=segments[2])
        case "get_item_detail":
            return GetItemDetail(enemy_id=segments[1], item_id=segments[2], field=segments[3])
        case "get_enemy_skill":
            return GetEnemySkill(enemy_id=segments[1], skill_id=segments[2])
        case "get_enemy_status":
            return GetEnemyStatus(enemy_id=segments[1], field=segments[2])
        case _:
            raise ValueError(f"パース失敗: 未知のコマンド '{cmd_name}'")


# ===========================================================================
# コマンド実行（01.py と同一）
# ===========================================================================


def execute_command(cmd: Command) -> str:
    match cmd:
        case GetItemName(enemy_id=eid, item_id=iid):
            enemy = find_enemy(eid)
            if enemy is None:
                raise LookupError(f"敵が見つかりません: enemy_id={eid}")
            item = find_item(int(iid))
            if item is None:
                raise LookupError(f"アイテムが見つかりません: item_id={iid}")
            return item["item_name"]

        case GetItemDetail(enemy_id=eid, item_id=iid, field=fld):
            enemy = find_enemy(eid)
            if enemy is None:
                raise LookupError(f"敵が見つかりません: enemy_id={eid}")
            item = find_item(int(iid))
            if item is None:
                raise LookupError(f"アイテムが見つかりません: item_id={iid}")
            if fld not in item:
                raise LookupError(f"フィールドが見つかりません: {fld}")
            return str(item[fld])

        case GetEnemySkill(enemy_id=eid, skill_id=sid):
            enemy = find_enemy(eid)
            if enemy is None:
                raise LookupError(f"敵が見つかりません: enemy_id={eid}")
            skill = find_skill(sid)
            if skill is None:
                raise LookupError(f"スキルが見つかりません: skill_id={sid}")
            return skill["skill_name"]

        case GetEnemyStatus(enemy_id=eid, field=fld):
            enemy = find_enemy(eid)
            if enemy is None:
                raise LookupError(f"敵が見つかりません: enemy_id={eid}")
            if fld not in enemy:
                raise LookupError(f"フィールドが見つかりません: {fld}")
            return str(enemy[fld])

        case _:
            raise ValueError(f"未知のコマンド: {cmd}")


# ===========================================================================
# メイン処理
# ===========================================================================


def process_input(data: dict[str, str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for key, value in data.items():
        cmd = parse_command(value)
        print(f"  [{key}] パース結果: {cmd}")
        output[key] = execute_command(cmd)
    return output


# ===========================================================================
# 実行
# ===========================================================================

if __name__ == "__main__":
    # 01.py と同一のサンプル入力
    sample_input = {
        "右手アイテム": "get_item_name|12345ACB|1001",
        "左手アイテム": "get_item_name|12345ACB|1002",
        "右手アイテム種別": "get_item_detail|12345ACB|1001|item_type",
        "敵スキル": "get_enemy_skill|67890DEF|SK001",
        "敵レベル": "get_enemy_status|67890DEF|enemy_level",
        "敵名前": "get_enemy_status|67890DEF|enemy_name",
    }

    print("=== 入力 ===")
    for k, v in sample_input.items():
        print(f"  {k}: {v}")
    print()

    print("=== パース & 実行 ===")
    result = process_input(sample_input)
    print()

    print("=== 出力 ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print()

    expected = {
        "右手アイテム": "こん棒",
        "左手アイテム": "鉄剣",
        "右手アイテム種別": "weapons",
        "敵スキル": "ファイアボール",
        "敵レベル": "10",
        "敵名前": "ゴブリン",
    }
    assert result == expected, f"期待値と一致しません:\n  結果: {result}\n  期待: {expected}"
    print("✓ 全テスト通過！")
