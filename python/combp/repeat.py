"""
コンビネータの繰り返し実行。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, OnError, err, get_offset, ok


def repeat[C, T](
    combinator: Combinator[C, T],
    must: int = 1,
    to: int | None = None,
) -> Combinator[C, list[T]]:
    """
    コンビネータを繰り返し実行し、結果をリストに収集する。

    正規表現の ``{must,to}`` に相当する。
    コンテキストが HasOffset を実装している場合、入力が進まない繰り返しを
    検知して無限ループを防止する。

    型パラメータ:
        C: コンテキスト型。HasOffset を実装していれば無限ループ防止が有効になる。
        T: 内側のコンビネータの結果型。リストの要素型となる。

    Args:
        combinator: 繰り返し実行するコンビネータ。
        must: 必要な最低マッチ回数（デフォルト: 1）。
            0 を指定すると、マッチなしでも空リストで成功する。
        to: 最大マッチ回数。省略時は無制限。
            指定する場合は 1 以上かつ must 以上でなければならない。

    Returns:
        成功時にマッチ結果の list[T] を返すコンビネータ。

    Raises:
        ValueError: must が負の場合、to が 1 未満の場合、または to < must の場合。

    Example::

        c = repeat(digit, must=1, to=3)
        r = c(Ctx("12345"))
        # r.value == ["1", "2", "3"]（最大3回で停止）
    """
    if must < 0:
        raise ValueError(
            f"repeat() は必ず失敗します: must ({must}) は 0 以上でなければなりません。"
        )
    if to is not None:
        if to < 1:
            raise ValueError(
                f"repeat() は必ず失敗します: to ({to}) は 1 以上でなければなりません。"
            )
        if to < must:
            raise ValueError(
                f"repeat() は必ず失敗します: to ({to}) は must ({must}) 以上でなければなりません。"
            )

    def _repeat(context: C) -> CombinatorResult[C, list[T]]:
        results: list[T] = []
        current = context
        last_error: OnError[C] | None = None

        while to is None or len(results) < to:
            before_offset = get_offset(current)
            result = combinator(current)
            if not result.ok:
                last_error = result.error
                break

            # 入力が進んでいなければ無限ループを防止して停止する
            after_offset = get_offset(result.context)
            if (
                before_offset is not None
                and after_offset is not None
                and before_offset == after_offset
            ):
                break

            results.append(result.value)
            current = result.context

        if len(results) < must:
            return err(
                context,
                f"repeat(): {must} 回以上の繰り返しが必要です。",
                [last_error] if last_error else [],
            )
        return ok(current, results)

    return _repeat
