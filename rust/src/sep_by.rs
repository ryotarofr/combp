//! 区切り文字区切りコンビネータ。

use crate::types::*;

/// 区切り文字で区切られた0個以上の要素をパースする。
///
/// `element (separator element)*` のパターンにマッチし、
/// `separator` の結果は捨てて `element` の結果のみを Vec に収集する。
/// コンテキストが `HasOffset` を実装している場合、入力が進まない繰り返しを
/// 検知して無限ループを防止する。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。`HasOffset` を実装していれば無限ループ防止が有効になる。
/// - `T`: 要素コンビネータの結果型。Vec の要素型となる。
/// - `S`: セパレータコンビネータの結果型。パースはされるが結果は捨てられる。
///
/// # 引数
/// - `element`: 各要素をパースするコンビネータ。
/// - `separator`: 要素間の区切りをパースするコンビネータ。
/// - `min`: 必要な最低要素数。0 の場合、要素がなくても空 Vec で成功する。
///
/// # 戻り値
/// 成功時に要素の `Vec<T>` を返すコンビネータ。
///
/// # 例
/// ```ignore
/// // "1,2,3" -> vec![1, 2, 3]
/// let csv = sep_by(number(), same(','), 1);
/// ```
pub fn sep_by<C, T, S>(
    element: Combinator<C, T>,
    separator: Combinator<C, S>,
    min: usize,
) -> Combinator<C, Vec<T>>
where
    C: Clone + HasOffset + 'static,
    T: Clone + 'static,
    S: Clone + 'static,
{
    comb(move |ctx: C| {
        let mut results: Vec<T> = Vec::new();
        let mut current = ctx.clone();
        let mut last_err: Option<OnError<C>> = None;

        // 最初の要素を試す
        let first = element(current.clone());
        match first.result {
            Err(e) => {
                if min > 0 {
                    return CombinatorResult::err(
                        ctx,
                        format!("sep_by(): 最低 {} 個の要素が必要です。", min),
                        vec![e],
                    );
                }
                return CombinatorResult::ok(ctx, vec![]);
            }
            Ok(v) => {
                results.push(v);
                current = first.context;
            }
        }

        // (separator element)* の繰り返し
        loop {
            // 無限ループ防止: ループ開始時の offset を記録
            let before_offset = current.offset();

            let sr = separator(current.clone());
            match sr.result {
                Err(_) => break,
                Ok(_) => {
                    let er = element(sr.context);
                    match er.result {
                        Err(e) => {
                            last_err = Some(e);
                            break;
                        }
                        Ok(v) => {
                            // 無限ループ防止: separator + element で入力が進まなければ停止
                            if er.context.offset() == before_offset {
                                break;
                            }
                            results.push(v);
                            current = er.context;
                        }
                    }
                }
            }
        }

        if results.len() < min {
            let by = match last_err {
                Some(e) => vec![e],
                None => vec![],
            };
            CombinatorResult::err(
                ctx,
                format!(
                    "sep_by(): 最低 {} 個の要素が必要ですが、{} 個しかありません。",
                    min,
                    results.len()
                ),
                by,
            )
        } else {
            CombinatorResult::ok(current, results)
        }
    })
}
