"""
ゲーム開発向け最適版: str.split + レジストリ統合 + キャッシュ。

設計方針:
  - パーサーは O(1) の dict ディスパッチ (match 廃止)
  - @lru_cache で同一文字列の再パースを回避
  - マスターデータは id キーの dict に前処理して O(1) 参照
  - dataclass(frozen=True, slots=True) で生成/参照を高速化
  - 可能ならマスターデータロード時に parse_all() で一括プリパース
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable


# ===========================================================================
# データmock
# ===========================================================================

_ENEMY_RAW = [
    {"enemy_id": "12345ACB", "enemy_name": "スライム", "enemy_level": 5},
    {"enemy_id": "67890DEF", "enemy_name": "ゴブリン", "enemy_level": 10},
]

_ITEM_RAW = [
    {"item_id": 1001, "item_name": "こん棒", "item_type": "weapons"},
    {"item_id": 1002, "item_name": "鉄剣", "item_type": "weapons"},
    {"item_id": 2001, "item_name": "皮の盾", "item_type": "shield"},
    {"item_id": 3001, "item_name": "回復薬", "item_type": "consumable"},
]

_SKILL_RAW = [
    {"skill_id": "SK001", "skill_name": "ファイアボール", "element": "fire"},
    {"skill_id": "SK002", "skill_name": "ヒール", "element": "holy"},
]

# id キーの dict に前処理 (O(1) 参照)
ENEMIES: dict[str, dict] = {e["enemy_id"]: e for e in _ENEMY_RAW}
ITEMS: dict[int, dict] = {i["item_id"]: i for i in _ITEM_RAW}
SKILLS: dict[str, dict] = {s["skill_id"]: s for s in _SKILL_RAW}


# ===========================================================================
# コマンド型
# ===========================================================================


@dataclass(frozen=True, slots=True)
class GetItemName:
    enemy_id: str
    item_id: str


@dataclass(frozen=True, slots=True)
class GetItemDetail:
    enemy_id: str
    item_id: str
    field: str


@dataclass(frozen=True, slots=True)
class GetEnemySkill:
    enemy_id: str
    skill_id: str


@dataclass(frozen=True, slots=True)
class GetEnemyStatus:
    enemy_id: str
    field: str


Command = GetItemName | GetItemDetail | GetEnemySkill | GetEnemyStatus


# ===========================================================================
# パーサー: レジストリ1箇所でコマンド追加が完結
# ===========================================================================

# (必要セグメント数, セグメント列 → Command)
_PARSERS: dict[str, tuple[int, Callable[[list[str]], Command]]] = {
    "get_item_name":    (3, lambda s: GetItemName(s[1], s[2])),
    "get_item_detail":  (4, lambda s: GetItemDetail(s[1], s[2], s[3])),
    "get_enemy_skill":  (3, lambda s: GetEnemySkill(s[1], s[2])),
    "get_enemy_status": (3, lambda s: GetEnemyStatus(s[1], s[2])),
}


class ParseError(ValueError):
    """DSL パース失敗。"""


@lru_cache(maxsize=4096)
def parse_command(value: str) -> Command:
    """
    "get_item_name|12345ACB|1001" → GetItemName(...)
    同一文字列の再呼び出しはキャッシュヒットでゼロコストに近い。
    """
    segs = value.split("|")
    entry = _PARSERS.get(segs[0])
    if entry is None:
        raise ParseError(
            f"未知のコマンド '{segs[0]}' "
            f"(有効: {', '.join(_PARSERS)}) 入力: {value!r}"
        )
    arity, build = entry
    if len(segs) != arity:
        raise ParseError(
            f"'{segs[0]}' は {arity} セグメント必要ですが "
            f"{len(segs)} セグメント検出 入力: {value!r}"
        )
    return build(segs)


def parse_all(values: dict[str, str]) -> dict[str, Command]:
    """起動時にまとめてプリパースするための補助。"""
    return {k: parse_command(v) for k, v in values.items()}


# ===========================================================================
# 実行: match で 1 箇所に集約 (データ取得は dict で O(1))
# ===========================================================================


def execute_command(cmd: Command) -> str:
    match cmd:
        case GetItemName(enemy_id=eid, item_id=iid):
            _require_enemy(eid)
            return _require_item(iid)["item_name"]

        case GetItemDetail(enemy_id=eid, item_id=iid, field=fld):
            _require_enemy(eid)
            item = _require_item(iid)
            if fld not in item:
                raise LookupError(f"フィールドが見つかりません: {fld}")
            return str(item[fld])

        case GetEnemySkill(enemy_id=eid, skill_id=sid):
            _require_enemy(eid)
            skill = SKILLS.get(sid)
            if skill is None:
                raise LookupError(f"スキルが見つかりません: skill_id={sid}")
            return skill["skill_name"]

        case GetEnemyStatus(enemy_id=eid, field=fld):
            enemy = _require_enemy(eid)
            if fld not in enemy:
                raise LookupError(f"フィールドが見つかりません: {fld}")
            return str(enemy[fld])


def _require_enemy(eid: str) -> dict:
    enemy = ENEMIES.get(eid)
    if enemy is None:
        raise LookupError(f"敵が見つかりません: enemy_id={eid}")
    return enemy


def _require_item(iid: str) -> dict:
    item = ITEMS.get(int(iid))
    if item is None:
        raise LookupError(f"アイテムが見つかりません: item_id={iid}")
    return item


# ===========================================================================
# 実行
# ===========================================================================


def process_input(data: dict[str, str]) -> dict[str, str]:
    # 起動時・マスタロード時にまとめてパースしておけば、
    # ゲームループ内は execute_command のみ呼べば済む。
    commands = parse_all(data)
    return {k: execute_command(c) for k, c in commands.items()}


if __name__ == "__main__":
    sample_input = {
        "右手アイテム": "get_item_name|12345ACB|1001",
        "左手アイテム": "get_item_name|12345ACB|1002",
        "右手アイテム種別": "get_item_detail|12345ACB|1001|item_type",
        "敵スキル": "get_enemy_skill|67890DEF|SK001",
        "敵レベル": "get_enemy_status|67890DEF|enemy_level",
        "敵名前": "get_enemy_status|67890DEF|enemy_name",
    }

    result = process_input(sample_input)

    expected = {
        "右手アイテム": "こん棒",
        "左手アイテム": "鉄剣",
        "右手アイテム種別": "weapons",
        "敵スキル": "ファイアボール",
        "敵レベル": "10",
        "敵名前": "ゴブリン",
    }
    assert result == expected, f"mismatch: {result} vs {expected}"

    for k, v in result.items():
        print(f"  {k}: {v}")
    print("✓ OK")
    print(f"  parse cache: {parse_command.cache_info()}")
