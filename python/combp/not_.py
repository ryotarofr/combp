"""
否定先読みコンビネータ。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, err, ok


def not_[C, T](combinator: Combinator[C, T]) -> Combinator[C, None]:
    """
    内側のコンビネータが失敗したときに成功し、成功したときに失敗する（否定先読み）。

    入力は消費しない。「この先にマッチしてほしくないもの」を表現するために使う。

    型パラメータ:
        C: コンテキスト型。
        T: 内側のコンビネータの結果型（成功時はエラーメッセージに含まれる）。

    Args:
        combinator: 否定対象のコンビネータ。

    Returns:
        成功時に None を返すコンビネータ。コンテキストは元の位置のまま。

    Example::

        # 改行以外の1文字にマッチ
        not_eol = chain(not_(same("\\n")), any_char)
    """

    def _not(context: C) -> CombinatorResult[C, None]:
        result = combinator(context)
        if result.ok:
            return err(context, f"not: {result.value} にマッチすべきではありません")
        return ok(context, None)

    return _not
