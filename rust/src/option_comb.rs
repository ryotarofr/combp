//! 省略可能マッチコンビネータ。

use crate::types::*;

/// コンビネータを試し、失敗した場合はエラーなしで `None` を返す。
///
/// 成功した場合は `Some(値)` を返す。正規表現の `?` に相当する。
/// 失敗時にコンテキストは進まない。いずれの場合も結果は成功となる。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `T`: 内側のコンビネータの結果型。
///
/// # 引数
/// - `c`: 省略可能な対象のコンビネータ。
///
/// # 戻り値
/// 成功時に `Some(T)`、失敗時に `None` を返すコンビネータ。
pub fn option<C, T>(c: Combinator<C, T>) -> Combinator<C, Option<T>>
where
    C: Clone + 'static,
    T: Clone + 'static,
{
    comb(move |ctx: C| {
        let r = c(ctx.clone());
        match r.result {
            Ok(v) => CombinatorResult::ok(r.context, Some(v)),
            Err(_) => CombinatorResult::ok(ctx, None),
        }
    })
}
