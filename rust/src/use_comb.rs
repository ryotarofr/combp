//! 条件分岐コンビネータ（動的コンビネータ選択）。

use crate::types::*;
use std::fmt;

/// `from` を実行し、その結果に基づいて次のコンビネータを動的に選択する。
///
/// 先行パーサーの結果をキーとして、後続のパーサーをディスパッチするパターンに使う。
/// セレクタが `None` を返した場合、コンビネータは失敗する。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `M`: 先行コンビネータ（`from`）の結果型。`selector` の引数に渡される中間型。
///   `Debug` 必須（`None` 返却時のエラーメッセージに使用）。
/// - `T`: `selector` が選択したコンビネータの結果型。最終的な成功値の型。
///
/// # 引数
/// - `from`: 最初に実行するコンビネータ。この結果が `selector` に渡される。
/// - `selector`: `from` の結果を受け取り、次に実行するコンビネータを返す関数。
///   該当するコンビネータがない場合は `None` を返す。
///
/// # 戻り値
/// `selector` が選択したコンビネータの結果を返すコンビネータ。
///
/// # 例
/// ```ignore
/// // 先頭文字を peek して対応するキーワードパーサーを選択
/// let c = use_combinator(peek(any_char()), |ch| match ch {
///     'i' => Some(keyword("if")),
///     'w' => Some(keyword("while")),
///     _ => None,
/// });
/// ```
pub fn use_combinator<C, M, T>(
    from: Combinator<C, M>,
    selector: impl Fn(M) -> Option<Combinator<C, T>> + Send + Sync + 'static,
) -> Combinator<C, T>
where
    C: Clone + 'static,
    M: Clone + fmt::Debug + 'static,
    T: Clone + 'static,
{
    comb(move |ctx: C| {
        let fr = from(ctx.clone());
        match fr.result {
            Err(e) => CombinatorResult::err(fr.context, e.message, e.by),
            Ok(v) => match selector(v.clone()) {
                None => CombinatorResult::err(
                    ctx,
                    format!("use: セレクタが {:?} に対して None を返しました", v),
                    vec![],
                ),
                Some(next) => next(fr.context),
            },
        }
    })
}
