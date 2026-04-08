"""
エラーメッセージ上書きコンビネータ。
"""

from __future__ import annotations

from .combinator_types import Combinator, CombinatorResult, err


def label[C, T](message: str, combinator: Combinator[C, T]) -> Combinator[C, T]:
    """
    内側のコンビネータが失敗したとき、エラーメッセージを上書きする。

    内部エラーの by チェーンと furthest 情報は保持されるため、
    デバッグ情報を失わずにユーザー向けのメッセージを改善できる。
    成功した場合はそのまま結果を返す。

    型パラメータ:
        C: コンテキスト型。
        T: 内側のコンビネータの結果型。

    Args:
        message: 失敗時に使用するエラーメッセージ。
        combinator: ラップ対象のコンビネータ。

    Returns:
        成功時はそのまま、失敗時は message でエラーを上書きしたコンビネータ。

    Example::

        c = label("数値が必要です", digit)
        r = c(Ctx("abc"))
        # r.error.message == "数値が必要です"
    """

    def _label(context: C) -> CombinatorResult[C, T]:
        result = combinator(context)
        if result.ok:
            return result
        return err(context, message, result.error.by, result.error.furthest)

    return _label
