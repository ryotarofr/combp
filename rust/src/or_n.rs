//! 複数候補からの選択コンビネータ。

use crate::types::*;

/// 各コンビネータを順に試し、最初に成功したものを返す。
///
/// 全て失敗した場合、最遠失敗（furthest）を追跡して返す。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。`HasOffset` を実装していれば最遠失敗追跡が有効になる。
/// - `T`: 各コンビネータの結果型（全て同一型）。
///
/// # 引数
/// - `combinators`: 試行するコンビネータの Vec。先頭から順に試行される。
///
/// # 戻り値
/// 最初に成功したコンビネータの結果を返すコンビネータ。
/// `combinators` が空の場合はエラーを返す。
pub fn or_n<C, T>(combinators: Vec<Combinator<C, T>>) -> Combinator<C, T>
where
    C: Clone + HasOffset + 'static,
    T: Clone + 'static,
{
    comb(move |ctx: C| {
        let mut errs: Vec<OnError<C>> = Vec::new();
        for c in &combinators {
            let r = c(ctx.clone());
            match r.result {
                Ok(v) => return CombinatorResult::ok(r.context, v),
                Err(e) => errs.push(e),
            }
        }
        if !errs.is_empty() {
            let mut furthest = errs[0].clone();
            for e in &errs[1..] {
                furthest = deeper_error(&furthest, e);
            }
            CombinatorResult::err_with_furthest(ctx, "or", errs, furthest)
        } else {
            CombinatorResult::err(ctx, "or_n: コンビネータが指定されていません", vec![])
        }
    })
}

// deeper_error は types.rs で定義されたパブリック関数を使用
