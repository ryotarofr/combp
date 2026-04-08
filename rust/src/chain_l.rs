//! 順次実行し、最初（左）の結果のみ返すコンビネータ。

use crate::types::*;

/// コンビネータを順に実行し、最初（左端）の結果のみを返す。
///
/// 2番目以降のコンビネータは実行されるが、その結果は捨てられる。
/// トークン後の空白スキップなどに便利。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `T`: 最初のコンビネータ（`first`）の結果型。最終的な戻り値の型。
/// - `R`: 残りのコンビネータの結果型。パースはされるが結果は捨てられる。
///
/// # 引数
/// - `first`: 結果を保持するコンビネータ。
/// - `rest`: `first` 成功後に順に実行するコンビネータの Vec。結果は捨てられる。
///
/// # 戻り値
/// 成功時に `first` の結果を返すコンビネータ。
pub fn chain_l<C, T, R>(first: Combinator<C, T>, rest: Vec<Combinator<C, R>>) -> Combinator<C, T>
where
    C: Clone + 'static,
    T: Clone + 'static,
    R: Clone + 'static,
{
    comb(move |ctx: C| {
        let fr = first(ctx);
        match fr.result {
            Err(e) => propagate_err(fr.context, e),
            Ok(v) => {
                let mut current = fr.context;
                for c in &rest {
                    let r = c(current);
                    match r.result {
                        Err(e) => return propagate_err(r.context, e),
                        Ok(_) => current = r.context,
                    }
                }
                CombinatorResult::ok(current, v)
            }
        }
    })
}

/// `OnError` の `furthest` 情報を保持してエラーを伝播するヘルパー。
fn propagate_err<C: Clone, T>(context: C, e: OnError<C>) -> CombinatorResult<C, T> {
    match e.furthest {
        Some(f) => CombinatorResult::err_with_furthest(context, e.message, e.by, *f),
        None => CombinatorResult::err(context, e.message, e.by),
    }
}
