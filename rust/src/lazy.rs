//! 遅延構築コンビネータ（循環参照の回避用）。

use crate::types::*;
use std::sync::{Arc, Mutex};

/// コンビネータの構築を遅延させ、循環参照を回避する。
///
/// ファクトリ関数は最初の呼び出し時に1回だけ実行され、以降は `Mutex` で
/// キャッシュされた結果を使用する。再帰的なパーサー（括弧のネストなど）を
/// 定義する際に必須となる。スレッドセーフ。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `T`: 内側のコンビネータの結果型。
///
/// # 引数
/// - `factory`: コンビネータを生成するファクトリ関数。引数なしで呼び出され、
///   `Combinator<C, T>` を返す。この関数内で `lazy` の戻り値自身を
///   参照することで循環参照を実現できる。
///
/// # 戻り値
/// ファクトリが生成するコンビネータと同じ振る舞いをするコンビネータ。
///
/// # 例
/// ```ignore
/// // 再帰パーサー: "a", "(a)", "((a))", ...
/// let expr = lazy(|| or(
///     convert(chain_n(vec![same('('), expr.clone(), same(')')]),
///             |p, _| format!("({})", p[1])),
///     same('a'),
/// ));
/// ```
pub fn lazy<C, T>(
    factory: impl Fn() -> Combinator<C, T> + Send + Sync + 'static,
) -> Combinator<C, T>
where
    C: Clone + 'static,
    T: Clone + 'static,
{
    let cached: Arc<Mutex<Option<Combinator<C, T>>>> = Arc::new(Mutex::new(None));
    comb(move |ctx: C| {
        let mut guard = cached.lock().expect("lazy: Mutex が poisoned されています");
        if guard.is_none() {
            *guard = Some(factory());
        }
        let c = guard
            .as_ref()
            .expect("lazy: キャッシュの初期化に失敗")
            .clone();
        drop(guard); // ロックを解放してからコンビネータを実行
        c(ctx)
    })
}
