//! 順次実行し、最後（右）の結果のみ返すコンビネータ。

use crate::types::*;

/// コンビネータを順に実行し、最後（右端）の結果のみを返す。
///
/// 最後以外のコンビネータは実行されるが、その結果は捨てられる。
/// プレフィクスやデリミタを読み飛ばしてから本体を取得する場合に便利。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `S`: 読み飛ばすコンビネータ（`skips`）の結果型。パースはされるが結果は捨てられる。
/// - `T`: 最後のコンビネータ（`last`）の結果型。最終的な戻り値の型。
///
/// # 引数
/// - `skips`: 先に実行して結果を捨てるコンビネータの Vec。
/// - `last`: 最後に実行し、結果を保持するコンビネータ。
///
/// # 戻り値
/// 成功時に `last` の結果を返すコンビネータ。
pub fn chain_r<C, S, T>(skips: Vec<Combinator<C, S>>, last: Combinator<C, T>) -> Combinator<C, T>
where
    C: Clone + 'static,
    S: Clone + 'static,
    T: Clone + 'static,
{
    comb(move |ctx: C| {
        let mut current = ctx;
        for c in &skips {
            let r = c(current);
            match r.result {
                Err(e) => {
                    return match e.furthest {
                        Some(f) => {
                            CombinatorResult::err_with_furthest(r.context, e.message, e.by, *f)
                        }
                        None => CombinatorResult::err(r.context, e.message, e.by),
                    };
                }
                Ok(_) => current = r.context,
            }
        }
        last(current)
    })
}
