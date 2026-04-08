//! コンビネータの繰り返し実行。

use crate::types::*;

/// コンビネータを繰り返し実行し、結果を `Vec` に収集する。
///
/// 正規表現の `{must,max}` に相当する。
/// コンテキストが `HasOffset` を実装している場合、入力が進まない繰り返しを
/// 検知して無限ループを防止する。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。`HasOffset` を実装していれば無限ループ防止が有効になる。
/// - `T`: 内側のコンビネータの結果型。Vec の要素型となる。
///
/// # 引数
/// - `c`: 繰り返し実行するコンビネータ。
/// - `must`: 必要な最低マッチ回数。0 を指定すると、マッチなしでも空 Vec で成功する。
/// - `max`: 最大マッチ回数。`None` で無制限。`Some(n)` の場合、n は 1 以上かつ must 以上。
///
/// # 戻り値
/// 成功時にマッチ結果の `Vec<T>` を返すコンビネータ。
///
/// # パニック
/// `max` が `Some(0)` の場合、または `max < must` の場合。
pub fn repeat<C, T>(c: Combinator<C, T>, must: usize, max: Option<usize>) -> Combinator<C, Vec<T>>
where
    C: Clone + HasOffset + 'static,
    T: Clone + 'static,
{
    if let Some(m) = max {
        assert!(
            m >= 1,
            "combinator::repeat: max ({}) は 1 以上でなければなりません",
            m
        );
        assert!(
            m >= must,
            "combinator::repeat: max ({}) は must ({}) 以上でなければなりません",
            m,
            must
        );
    }
    comb(move |ctx: C| {
        let mut results: Vec<T> = Vec::new();
        let mut current = ctx.clone();
        let mut last_err: Option<OnError<C>> = None;

        loop {
            if let Some(m) = max {
                if results.len() >= m {
                    break;
                }
            }
            let r = c(current.clone());
            match r.result {
                Err(e) => {
                    last_err = Some(e);
                    break;
                }
                Ok(v) => {
                    // 入力が進んでいなければ無限ループを防止して停止する
                    if r.context.offset() == current.offset() {
                        break;
                    }
                    results.push(v);
                    current = r.context;
                }
            }
        }

        if results.len() < must {
            let by = match last_err {
                Some(e) => vec![e],
                None => vec![],
            };
            CombinatorResult::err(
                ctx,
                format!("repeat(): {} 回以上の繰り返しが必要です。", must),
                by,
            )
        } else {
            CombinatorResult::ok(current, results)
        }
    })
}
