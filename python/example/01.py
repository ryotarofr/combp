from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from combp import (
    chain,
    chain_n,
    chain_l,
    chain_r,
    convert,
    label,
    lazy,
    not_,
    option,
    or_,
    or_n,
    peek,
    repeat,
    sep_by,
    use,
)
from combp import Combinator, CombinatorResult, OnError, deeper_error, err, map_, ok


# ===========================================================================
# コンテキスト定義
# ===========================================================================


@dataclass(frozen=True)
class Ctx:
    """オフセット追跡付きの文字列パースコンテキスト。"""

    src: str
    offset: int = 0


# ===========================================================================
# プリミティブパーサー
# ===========================================================================


def any_char(context: Ctx) -> CombinatorResult[Ctx, str]:
    """1文字を消費する。"""
    if context.offset >= len(context.src):
        return err(context, "入力の終端です")
    ch = context.src[context.offset]
    return ok(Ctx(src=context.src, offset=context.offset + 1), ch)


def same(expected: str) -> Combinator[Ctx, str]:
    """指定した1文字にマッチする。"""

    def _same(context: Ctx) -> CombinatorResult[Ctx, str]:
        r = any_char(context)
        if not r.ok:
            return r
        if r.value != expected:
            return err(
                context, f"'{expected}' が期待されましたが '{r.value}' でした"
            )
        return r

    return _same


def keyword(word: str) -> Combinator[Ctx, str]:
    """指定した文字列にマッチする。"""

    def _keyword(context: Ctx) -> CombinatorResult[Ctx, str]:
        remaining = context.src[context.offset :]
        if remaining.startswith(word):
            return ok(
                Ctx(src=context.src, offset=context.offset + len(word)), word
            )
        return err(context, f"'{word}' が期待されました")

    return _keyword


def satisfy(pred, description: str = "条件") -> Combinator[Ctx, str]:
    """条件を満たす1文字にマッチする。"""

    def _satisfy(context: Ctx) -> CombinatorResult[Ctx, str]:
        r = any_char(context)
        if not r.ok:
            return r
        if not pred(r.value):
            return err(
                context,
                f"{description} を満たす文字が期待されましたが '{r.value}' でした",
            )
        return r

    return _satisfy


def parse(c: Combinator[Ctx, Any], input_str: str) -> CombinatorResult[Ctx, Any]:
    """ヘルパー: コンビネータに入力文字列を渡す。"""
    return c(Ctx(src=input_str))


# ===========================================================================
# データmock（RDS などからデータを取得する想定）
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
# データ検索ヘルパー
# ===========================================================================


def find_enemy(enemy_id: str) -> dict | None:
    return next((e for e in enemy_info if e["enemy_id"] == enemy_id), None)


def find_item(item_id: int) -> dict | None:
    return next((i for i in item_info if i["item_id"] == item_id), None)


def find_skill(skill_id: str) -> dict | None:
    return next((s for s in skill_info if s["skill_id"] == skill_id), None)


# ===========================================================================
# コンビネータ: 共通パーツ
# ===========================================================================

pipe = same("|")

segment_char: Combinator[Ctx, str] = satisfy(
    lambda ch: ch != "|",
    "パイプ以外の文字",
)

segment: Combinator[Ctx, str] = label(
    "セグメントが必要です",
    map_(repeat(segment_char, must=1), lambda chars: "".join(chars)),
)


# ===========================================================================
# コマンド型定義
# ===========================================================================


@dataclass
class GetItemName:
    """get_item_name|<enemy_id>|<item_id>"""

    enemy_id: str
    item_id: str


@dataclass
class GetItemDetail:
    """get_item_detail|<enemy_id>|<item_id>|<field>
    field は "type" や "name" など、取得したい属性を指定する。
    """

    enemy_id: str
    item_id: str
    field: str


@dataclass
class GetEnemySkill:
    """get_enemy_skill|<enemy_id>|<skill_id>"""

    enemy_id: str
    skill_id: str


@dataclass
class GetEnemyStatus:
    """get_enemy_status|<enemy_id>|<field>
    field は "name", "enemy_level" など。
    """

    enemy_id: str
    field: str


Command = GetItemName | GetItemDetail | GetEnemySkill | GetEnemyStatus


# ===========================================================================
# コンビネータ: コマンド別パーサー
#
# combp の真価が出るポイント:
#   - or_n でコマンドを分岐
#   - use で先頭キーワードに応じて後続パーサーを切り替え
#   - option でオプショナルフィールドに対応
#   - label でコマンドごとに的確なエラーメッセージ
# ===========================================================================


def _build_get_item_name() -> Combinator[Ctx, GetItemName]:
    """get_item_name|<enemy_id>|<item_id>"""
    return convert(
        chain_n(keyword("get_item_name"), pipe, segment, pipe, segment),
        lambda parts, _: GetItemName(enemy_id=parts[2], item_id=parts[4]),
    )


def _build_get_item_detail() -> Combinator[Ctx, GetItemDetail]:
    """get_item_detail|<enemy_id>|<item_id>|<field>"""
    return convert(
        chain_n(
            keyword("get_item_detail"), pipe, segment, pipe, segment, pipe, segment
        ),
        lambda parts, _: GetItemDetail(
            enemy_id=parts[2], item_id=parts[4], field=parts[6]
        ),
    )


def _build_get_enemy_skill() -> Combinator[Ctx, GetEnemySkill]:
    """get_enemy_skill|<enemy_id>|<skill_id>"""
    return convert(
        chain_n(keyword("get_enemy_skill"), pipe, segment, pipe, segment),
        lambda parts, _: GetEnemySkill(enemy_id=parts[2], skill_id=parts[4]),
    )


def _build_get_enemy_status() -> Combinator[Ctx, GetEnemyStatus]:
    """get_enemy_status|<enemy_id>|<field>"""
    return convert(
        chain_n(keyword("get_enemy_status"), pipe, segment, pipe, segment),
        lambda parts, _: GetEnemyStatus(enemy_id=parts[2], field=parts[4]),
    )


# ---------------------------------------------------------------------------
# 方式A: or_n（シンプルだがバックトラックあり）
#   各分岐を先頭から順に試す。失敗したら巻き戻して次を試す。
#   コマンド数 N に対して最悪 O(N) 回キーワード部分を読み直す。
# ---------------------------------------------------------------------------

command_parser_or_n: Combinator[Ctx, Command] = label(
    "有効なコマンドが期待されます "
    "(get_item_name, get_item_detail, get_enemy_skill, get_enemy_status)",
    or_n(
        _build_get_item_detail(),  # 4セグメント（先にマッチさせる）
        _build_get_item_name(),  # 3セグメント
        _build_get_enemy_skill(),  # 3セグメント
        _build_get_enemy_status(),  # 3セグメント
    ),
)


# ---------------------------------------------------------------------------
# 方式B: use + peek（キーワードを1度だけ読んで O(1) 分岐）
#   peek(segment) で先頭キーワードを先読みし、その値で後続パーサーを選択。
#   キーワード部分の再読み込みが発生しないため、コマンド数が増えても
#   分岐コストは辞書引き O(1)。
# ---------------------------------------------------------------------------


# [指摘5 修正] dispatch 辞書をモジュールレベルでキャッシュし、
# _select_command が呼ばれるたびに再生成されるのを防ぐ。
_COMMAND_DISPATCH: dict[str, Combinator[Ctx, Command]] = {
    "get_item_name": _build_get_item_name(),
    "get_item_detail": _build_get_item_detail(),
    "get_enemy_skill": _build_get_enemy_skill(),
    "get_enemy_status": _build_get_enemy_status(),
}


def _select_command(cmd_keyword: str):
    """先頭キーワードに対応するパーサーを返す。None を返すと use が失敗扱い。"""
    return _COMMAND_DISPATCH.get(cmd_keyword)  # 見つからなければ None → 失敗


command_parser_use: Combinator[Ctx, Command] = label(
    "有効なコマンドが期待されます "
    "(get_item_name, get_item_detail, get_enemy_skill, get_enemy_status)",
    use(peek(segment), _select_command),
)


# ---------------------------------------------------------------------------
# デフォルト: use 版を採用
# ---------------------------------------------------------------------------

command_parser = command_parser_use


def parse_command(value: str) -> Command:
    """文字列をパースして Command に変換する。"""
    result = parse(command_parser, value)
    if not result.ok:
        raise ValueError(f"パース失敗: {result.error.message} (入力: '{value}')")
    return result.value


# ===========================================================================
# コマンド実行（パース結果に応じたデータ取得）
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
    # -----------------------------------------------------------------------
    # シナリオ: ユーザ_A から見える敵の情報を一括取得
    #
    #   コマンド体系が複数あり、フォーマットもセグメント数も異なる。
    #   combp の or_n が先頭キーワードで自動分岐し、
    #   セグメント数の違いもパーサー側で吸収する。
    # -----------------------------------------------------------------------

    sample_input = {
        # get_item_name: 3セグメント
        "右手アイテム": "get_item_name|12345ACB|1001",
        "左手アイテム": "get_item_name|12345ACB|1002",
        # get_item_detail: 4セグメント（フィールド指定）
        "右手アイテム種別": "get_item_detail|12345ACB|1001|item_type",
        # get_enemy_skill: 3セグメント
        "敵スキル": "get_enemy_skill|67890DEF|SK001",
        # get_enemy_status: 3セグメント
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