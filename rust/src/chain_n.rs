//! 複数コンビネータの順次実行（動的型）。

use crate::types::*;

/// 一連のコンビネータを順に実行し、結果を `Vec<Box<dyn Any>>` で返す。
///
/// いずれかが失敗した時点でそのエラーを返す。
/// 動的型のため呼び出し側で `downcast` が必要になる。
///
/// **推奨**: 個数が固定（3〜6個）なら型安全な [`chain3`]〜[`chain6`] を使うこと。
/// `chain_n` はコンビネータ数が実行時に決まる場合に使う。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
///
/// # 引数
/// - `combinators`: 順に実行するコンビネータの Vec。
///   各コンビネータの結果型は `Box<dyn Any + Send + Sync>`。
///
/// # 戻り値
/// 成功時に各コンビネータの結果を格納した `Vec<Box<dyn Any + Send + Sync>>` を返すコンビネータ。
/// Vec のインデックスは `combinators` の順序に対応する。
pub fn chain_n<C>(
    combinators: Vec<Combinator<C, Box<dyn std::any::Any + Send + Sync>>>,
) -> Combinator<C, Vec<Box<dyn std::any::Any + Send + Sync>>>
where
    C: Clone + 'static,
{
    comb(move |ctx: C| {
        let mut results: Vec<Box<dyn std::any::Any + Send + Sync>> = Vec::new();
        let mut current = ctx;
        for c in &combinators {
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
                Ok(v) => {
                    results.push(v);
                    current = r.context;
                }
            }
        }
        CombinatorResult::ok(current, results)
    })
}
