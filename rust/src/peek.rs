//! 先読みコンビネータ（入力を消費しない）。

use crate::types::*;

/// コンビネータを実行するが、成功時にコンテキストを元に戻す（先読み）。
///
/// 入力を消費せずに「次に何が来るか」を確認したい場合に使う。
/// 失敗した場合はそのままエラーを返す。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `T`: 内側のコンビネータの結果型。
///
/// # 引数
/// - `c`: 先読み対象のコンビネータ。
///
/// # 戻り値
/// 成功時にコンテキストを元の位置に戻した上で `T` 型の値を返すコンビネータ。
///
/// # 例
/// ```ignore
/// let c = peek(same('a'));
/// let r = c(Ctx::new("abc"));
/// // r.result == Ok('a'), r.context.offset == 0（位置は進まない）
/// ```
pub fn peek<C, T>(c: Combinator<C, T>) -> Combinator<C, T>
where
    C: Clone + 'static,
    T: Clone + 'static,
{
    comb(move |ctx: C| {
        let r = c(ctx.clone());
        match r.result {
            Err(e) => CombinatorResult::err(r.context, e.message, e.by),
            Ok(v) => CombinatorResult::ok(ctx, v),
        }
    })
}
