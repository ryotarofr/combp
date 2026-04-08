//! 否定先読みコンビネータ。

use crate::types::*;
use std::fmt;

/// 内側のコンビネータが失敗したときに成功し、成功したときに失敗する（否定先読み）。
///
/// 入力は消費しない。「この先にマッチしてほしくないもの」を表現するために使う。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `T`: 内側のコンビネータの結果型（成功時はエラーメッセージに含まれる。`Debug` 必須）。
///
/// # 引数
/// - `c`: 否定対象のコンビネータ。
///
/// # 戻り値
/// 成功時に `()` を返すコンビネータ。コンテキストは元の位置のまま。
///
/// # 例
/// ```ignore
/// // 改行以外の1文字にマッチ
/// let not_eol = chain(not(same('\n')), any_char());
/// ```
pub fn not<C, T>(c: Combinator<C, T>) -> Combinator<C, ()>
where
    C: Clone + 'static,
    T: Clone + fmt::Debug + 'static,
{
    comb(move |ctx: C| {
        let r = c(ctx.clone());
        match r.result {
            Ok(v) => CombinatorResult::err(
                ctx,
                format!("not: {:?} にマッチすべきではありません", v),
                vec![],
            ),
            Err(_) => CombinatorResult::ok(ctx, ()),
        }
    })
}
