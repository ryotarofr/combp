//! 2つのコンビネータの順次実行。

use crate::types::*;

/// 2つのコンビネータを順に実行し、結果をタプルで返す。
///
/// `lhs` が成功した場合、その更新されたコンテキストから `rhs` を実行する。
/// どちらかが失敗した時点でそのエラーをそのまま返す。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `L`: `lhs` の成功時の結果型。
/// - `R`: `rhs` の成功時の結果型。
///
/// # 引数
/// - `lhs`: 最初に実行するコンビネータ。
/// - `rhs`: `lhs` 成功後に実行するコンビネータ。
///
/// # 戻り値
/// 成功時に `(L, R)` のタプルを返すコンビネータ。
///
/// # 例
/// ```ignore
/// let c = chain(same('a'), same('b'));
/// let r = c(Ctx::new("abc"));
/// // r.result == Ok(('a', 'b'))
/// ```
pub fn chain<C, L, R>(lhs: Combinator<C, L>, rhs: Combinator<C, R>) -> Combinator<C, (L, R)>
where
    C: Clone + 'static,
    L: Clone + 'static,
    R: Clone + 'static,
{
    comb(move |ctx: C| {
        let lr = lhs(ctx);
        match lr.result {
            Err(e) => propagate_err(lr.context, e),
            Ok(lv) => {
                let rr = rhs(lr.context);
                match rr.result {
                    Err(e) => propagate_err(rr.context, e),
                    Ok(rv) => CombinatorResult::ok(rr.context, (lv, rv)),
                }
            }
        }
    })
}
