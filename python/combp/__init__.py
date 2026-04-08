"""
汎用パーサーコンビネータライブラリ。

Combinator[C, T] は「コンテキスト C を受け取り、成功（値 T + 次のコンテキスト）
または失敗（エラー情報）を返す関数」として表現される。
chain, or_, repeat などを使って小さなコンビネータを合成し、
複雑なパーサーを宣言的に構築できる。
"""

from .combinator_types import (
    HasOffset,
    OnError,
    CombinatorResult,
    Combinator,
    ok,
    err,
    get_offset,
    deeper_error,
)
from .chain import chain
from .chain_n import chain_n
from .chain_l import chain_l
from .chain_r import chain_r
from .convert import convert, map_
from .or_ import or_
from .or_n import or_n
from .not_ import not_
from .option import option
from .repeat import repeat
from .sep_by import sep_by
from .lazy import lazy
from .use import use
from .peek import peek
from .label import label

__all__ = [
    "HasOffset",
    "OnError",
    "CombinatorResult",
    "Combinator",
    "ok",
    "err",
    "get_offset",
    "deeper_error",
    "chain",
    "chain_n",
    "chain_l",
    "chain_r",
    "convert",
    "map_",
    "or_",
    "or_n",
    "not_",
    "option",
    "repeat",
    "sep_by",
    "lazy",
    "use",
    "peek",
    "label",
]
