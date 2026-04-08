//! エラーメッセージ上書きコンビネータ。

use crate::types::*;

/// 内側のコンビネータが失敗したとき、エラーメッセージを上書きする。
///
/// 内部エラーの `by` チェーンと `furthest` 情報は保持されるため、
/// デバッグ情報を失わずにユーザー向けのメッセージを改善できる。
/// 成功した場合はそのまま結果を返す。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `T`: 内側のコンビネータの結果型。
///
/// # 引数
/// - `message`: 失敗時に使用するエラーメッセージ。
/// - `c`: ラップ対象のコンビネータ。
///
/// # 戻り値
/// 成功時はそのまま、失敗時は `message` でエラーを上書きしたコンビネータ。
///
/// # 例
/// ```ignore
/// let c = label("数値が必要です", digit());
/// let r = c(Ctx::new("abc"));
/// // r.result.unwrap_err().message == "数値が必要です"
/// ```
pub fn label<C, T>(
    message: impl Into<String> + Clone + Send + Sync + 'static,
    c: Combinator<C, T>,
) -> Combinator<C, T>
where
    C: Clone + 'static,
    T: Clone + 'static,
{
    comb(move |ctx: C| {
        let r = c(ctx.clone());
        match r.result {
            Ok(_) => r,
            Err(e) => match e.furthest {
                Some(f) => {
                    CombinatorResult::err_with_furthest(ctx, message.clone().into(), e.by, *f)
                }
                None => CombinatorResult::err(ctx, message.clone().into(), e.by),
            },
        }
    })
}
