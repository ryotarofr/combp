"""
区切り文字区切りコンビネータ。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, OnError, err, get_offset, ok


def sep_by[C, T, S](
    element: Combinator[C, T],
    separator: Combinator[C, S],
    min_count: int = 0,
) -> Combinator[C, list[T]]:
    """
    区切り文字で区切られた0個以上の要素をパースする。

    ``element (separator element)*`` のパターンにマッチし、
    separator の結果は捨てて element の結果のみをリストに収集する。
    コンテキストが HasOffset を実装している場合、入力が進まない繰り返しを
    検知して無限ループを防止する。

    型パラメータ:
        C: コンテキスト型。HasOffset を実装していれば無限ループ防止が有効になる。
        T: 要素コンビネータの結果型。リストの要素型となる。
        S: セパレータコンビネータの結果型。パースはされるが結果は捨てられる。

    Args:
        element: 各要素をパースするコンビネータ。
        separator: 要素間の区切りをパースするコンビネータ。
        min_count: 必要な最低要素数（デフォルト: 0）。
            0 の場合、要素がなくても空リストで成功する。

    Returns:
        成功時に要素の list[T] を返すコンビネータ。

    Example::

        # "1,2,3" -> [1, 2, 3]
        csv = sep_by(number, same(","), min_count=1)
        r = csv(Ctx("1,2,3"))
        # r.value == [1, 2, 3]
    """

    def _sep_by(context: C) -> CombinatorResult[C, list[T]]:
        results: list[T] = []
        current = context
        last_error: OnError[C] | None = None

        # 最初の要素を試す
        first = element(current)
        if not first.ok:
            if min_count > 0:
                return err(
                    context,
                    f"sepBy(): 最低 {min_count} 個の要素が必要です。",
                    [first.error],
                )
            return ok(context, [])

        results.append(first.value)
        current = first.context

        # (separator element)* の繰り返し
        while True:
            # 無限ループ防止: ループ開始時の offset を記録
            before_offset = get_offset(current)

            sep = separator(current)
            if not sep.ok:
                break
            next_elem = element(sep.context)
            if not next_elem.ok:
                last_error = next_elem.error
                break

            # 無限ループ防止: separator + element で入力が進まなければ停止
            after_offset = get_offset(next_elem.context)
            if (
                before_offset is not None
                and after_offset is not None
                and before_offset == after_offset
            ):
                break

            results.append(next_elem.value)
            current = next_elem.context

        if len(results) < min_count:
            return err(
                context,
                f"sepBy(): 最低 {min_count} 個の要素が必要ですが、{len(results)} 個しかありません。",
                [last_error] if last_error else [],
            )
        return ok(current, results)

    return _sep_by
