//! 結果変換コンビネータ（convert / map）。

use crate::types::*;

/// 成功結果を変換関数で別の型に写す。
///
/// 内側のコンビネータが成功した場合、その値とコンテキストの参照を `f` に渡して変換する。
/// 失敗した場合はそのままエラーを返す。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `A`: 変換前の結果型（内側のコンビネータの成功型）。
/// - `B`: 変換後の結果型。
///
/// # 引数
/// - `c`: 内側のコンビネータ。
/// - `f`: 変換関数。`(成功値: A, コンテキスト参照: &C) -> B` の形式。
///   コンテキストを参照して変換結果を調整したい場合に有用。
///
/// # 戻り値
/// 成功時に `B` 型の値を返すコンビネータ。
///
/// # 例
/// ```ignore
/// let c = convert(digit(), |s, _| s.parse::<i32>().unwrap());
/// ```
pub fn convert<C, A, B>(
    c: Combinator<C, A>,
    f: impl Fn(A, &C) -> B + Send + Sync + 'static,
) -> Combinator<C, B>
where
    C: Clone + 'static,
    A: Clone + 'static,
    B: Clone + 'static,
{
    comb(move |ctx: C| {
        let r = c(ctx);
        match r.result {
            Err(e) => CombinatorResult::err(r.context, e.message, e.by),
            Ok(v) => {
                let mapped = f(v, &r.context);
                CombinatorResult::ok(r.context, mapped)
            }
        }
    })
}

/// [`convert`] の簡易版。コンテキストを無視して値だけを変換する。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `A`: 変換前の結果型。
/// - `B`: 変換後の結果型。
///
/// # 引数
/// - `c`: 内側のコンビネータ。
/// - `f`: 変換関数。`(成功値: A) -> B` の形式。
pub fn map<C, A, B>(
    c: Combinator<C, A>,
    f: impl Fn(A) -> B + Send + Sync + 'static,
) -> Combinator<C, B>
where
    C: Clone + 'static,
    A: Clone + 'static,
    B: Clone + 'static,
{
    convert(c, move |a, _| f(a))
}
