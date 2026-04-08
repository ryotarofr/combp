//! 選択コンビネータ（or / or_simple）と Either 型。

use crate::types::*;

/// `lhs` を先に試し、失敗したら `rhs` を試す（二者択一）。
///
/// 両方失敗した場合、入力をより先まで消費した分岐のエラーを `furthest` として
/// 記録する。これにより、ユーザーは「どの分岐が最も惜しかったか」を把握できる。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。`HasOffset` を実装していれば最遠失敗追跡が有効になる。
/// - `L`: `lhs` の成功時の結果型。
/// - `R`: `rhs` の成功時の結果型。
///
/// # 引数
/// - `lhs`: 最初に試すコンビネータ。
/// - `rhs`: `lhs` が失敗した場合に試すコンビネータ。
///
/// # 戻り値
/// 成功時に `Either<L, R>` を返すコンビネータ。
/// `lhs` が成功すれば `Either::Left(L)`、`rhs` が成功すれば `Either::Right(R)` を返す。
pub fn or<C, L, R>(lhs: Combinator<C, L>, rhs: Combinator<C, R>) -> Combinator<C, Either<L, R>>
where
    C: Clone + HasOffset + 'static,
    L: Clone + 'static,
    R: Clone + 'static,
{
    comb(move |ctx: C| {
        let lr = lhs(ctx.clone());
        match lr.result {
            Ok(v) => CombinatorResult::ok(lr.context, Either::Left(v)),
            Err(l_err) => {
                let rr = rhs(ctx.clone());
                match rr.result {
                    Ok(v) => CombinatorResult::ok(rr.context, Either::Right(v)),
                    Err(r_err) => {
                        let furthest = deeper_error(&l_err, &r_err);
                        CombinatorResult::err_with_furthest(ctx, "or", vec![l_err, r_err], furthest)
                    }
                }
            }
        }
    })
}

/// `or` で使える Either 型。TypeScript の `L | R` に相当する。
///
/// # 型パラメータ
/// - `L`: 左の値の型（`lhs` の成功結果）。
/// - `R`: 右の値の型（`rhs` の成功結果）。
#[derive(Debug, Clone, PartialEq)]
pub enum Either<L, R> {
    Left(L),
    Right(R),
}

/// `HasOffset` を持たないコンテキスト用の `or`。最遠失敗追跡なし。
///
/// # 型パラメータ
/// - `C`: コンテキスト型（`HasOffset` 不要）。
/// - `L`: `lhs` の成功時の結果型。
/// - `R`: `rhs` の成功時の結果型。
pub fn or_simple<C, L, R>(
    lhs: Combinator<C, L>,
    rhs: Combinator<C, R>,
) -> Combinator<C, Either<L, R>>
where
    C: Clone + 'static,
    L: Clone + 'static,
    R: Clone + 'static,
{
    comb(move |ctx: C| {
        let lr = lhs(ctx.clone());
        match lr.result {
            Ok(v) => CombinatorResult::ok(lr.context, Either::Left(v)),
            Err(l_err) => {
                let rr = rhs(ctx.clone());
                match rr.result {
                    Ok(v) => CombinatorResult::ok(rr.context, Either::Right(v)),
                    Err(r_err) => CombinatorResult::err(ctx, "or", vec![l_err, r_err]),
                }
            }
        }
    })
}

// deeper_error は types.rs で定義されたパブリック関数を使用
