"""
コンビネータライブラリの型定義とヘルパー。

コンビネータフレームワーク全体で使用されるコア型システム、プロトコル、
結果型を定義する。

主要な型パラメータの規約:
    C: コンテキスト型。パーサーの現在位置や入力ソースを保持するオブジェクト。
       offset プロパティを持つ場合（HasOffset 準拠）、最遠失敗追跡や
       無限ループ防止が有効になる。
    T: パース結果の型。各コンビネータが成功時に返す値の型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Protocol,
    runtime_checkable,
)

# ===========================================================================
# オフセット抽出用プロトコル
# ===========================================================================


@runtime_checkable
class HasOffset(Protocol):
    """
    Context がオフセット（現在位置）を持つことを示すプロトコル。

    or_ での最遠失敗比較、repeat / sep_by での無限ループ防止に使用する。
    コンテキスト型がこのプロトコルを実装していれば、自動的に上記の機能が有効になる。

    Example::

        @dataclass(frozen=True)
        class Ctx:
            src: str
            offset: int = 0
    """

    @property
    def offset(self) -> int: ...


# ===========================================================================
# 結果型
# ===========================================================================


@dataclass
class OnError[C]:
    """
    コンビネータが失敗したときの構造化エラー情報。

    型パラメータ:
        C: コンテキスト型。失敗地点のコンテキストを保持する。

    Attributes:
        on: 失敗が発生した時点のコンテキスト。
        message: 人間が読めるエラーの説明。
        by: 原因チェーン（子エラー）のリスト。
            chain や repeat など、内側のコンビネータの失敗を伝播する際に使用。
        furthest: 最も深くまで進んだ失敗。or / or_n が複数の分岐を試した結果、
            入力を最も先まで消費した失敗を記録する。デバッグ時のエラー特定に有用。
    """

    on: C
    message: str
    by: list[OnError[C]] = field(default_factory=list)
    furthest: OnError[C] | None = None

    def __str__(self) -> str:
        return self.message


@dataclass
class CombinatorResult[C, T]:
    """
    コンビネータの実行結果。

    型パラメータ:
        C: コンテキスト型。
        T: 成功時のパース結果の型。

    Attributes:
        ok: 成功なら True、失敗なら False。
        context: このステップ後の（前に進んだ可能性のある）コンテキスト。
            成功時は消費後の位置、失敗時は失敗発生時点の位置を示す。
    """

    ok: bool
    context: C
    _value: T | None = field(default=None, repr=False)
    _error: OnError[C] | None = field(default=None, repr=False)

    @property
    def get(self) -> T | OnError[C]:
        """成功時は値、失敗時はエラー情報を返す。"""
        if self.ok:
            return self._value  # type: ignore[return-value]
        return self._error  # type: ignore[return-value]

    @property
    def value(self) -> T:
        """成功時の値を返す。失敗時は ValueError を送出する。"""
        if not self.ok:
            raise ValueError(f"Result is not ok: {self._error}")
        return self._value  # type: ignore[return-value]

    @property
    def error(self) -> OnError[C]:
        """失敗時のエラーを返す。成功時は ValueError を送出する。"""
        if self.ok:
            raise ValueError("Result is ok, no error")
        return self._error  # type: ignore[return-value]


# ===========================================================================
# コンビネータ型
# ===========================================================================

# コンビネータ: コンテキスト C を受け取り CombinatorResult[C, T] を返す呼び出し可能オブジェクト。
# 小さなコンビネータを chain, or_, repeat などで合成し、複雑なパーサーを宣言的に構築する。
type Combinator[C, T] = Callable[[C], CombinatorResult[C, T]]


# ===========================================================================
# コンストラクタヘルパー
# ===========================================================================


def ok[C, T](context: C, value: T) -> CombinatorResult[C, T]:
    """
    成功した結果を構築する。

    Args:
        context: パース成功後のコンテキスト（消費後の位置）。
        value: パースされた値。

    Returns:
        ok=True の CombinatorResult。
    """
    return CombinatorResult(ok=True, context=context, _value=value)


def err[C](
    context: C,
    message: str,
    by: list[OnError[C]] | None = None,
    furthest: OnError[C] | None = None,
) -> CombinatorResult[C, Any]:
    """
    失敗した結果を構築する。

    Args:
        context: 失敗が発生した時点のコンテキスト。
        message: エラーメッセージ。
        by: 原因となった子エラーのリスト。省略時は空リスト。
        furthest: 最遠到達点のエラー情報。or 系コンビネータで使用。

    Returns:
        ok=False の CombinatorResult。
    """
    return CombinatorResult(
        ok=False,
        context=context,
        _error=OnError(on=context, message=message, by=by or [], furthest=furthest),
    )


# ===========================================================================
# オフセット抽出ヘルパー
# ===========================================================================


def get_offset(ctx: Any) -> int | None:
    """
    Context からオフセット値を安全に取り出す。

    HasOffset プロトコルを実装していれば offset を返し、
    dict で "offset" キーを持つ場合もその値を返す。
    どちらでもなければ None を返す。

    Args:
        ctx: コンテキストオブジェクト。

    Returns:
        オフセット値、または取得できない場合は None。
    """
    if isinstance(ctx, HasOffset):
        return ctx.offset
    if isinstance(ctx, dict) and "offset" in ctx and isinstance(ctx["offset"], int):
        return ctx["offset"]
    return None


def deeper_error[C](lhs: OnError[C], rhs: OnError[C]) -> OnError[C]:
    """
    2つの OnError のうち、入力のより先まで進んだ（offset が大きい）方を返す。

    or / or_n で複数の分岐が失敗した際に、最も有用なエラーを選択するために使用する。
    offset が取得できない場合は lhs を優先する。

    型パラメータ:
        C: コンテキスト型。

    Args:
        lhs: 1つ目のエラー。
        rhs: 2つ目のエラー。

    Returns:
        offset がより大きい方の OnError。
    """
    lhs_offset = get_offset(lhs.on)
    rhs_offset = get_offset(rhs.on)
    if lhs_offset is None or rhs_offset is None:
        return lhs
    return rhs if rhs_offset > lhs_offset else lhs
