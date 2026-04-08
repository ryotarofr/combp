//! 型安全なタプル版 chain（3〜6引数）。
//!
//! [`chain`] は2つのコンビネータをタプルで連結するが、3つ以上を連結するには
//! `chain` をネストする必要があり、型が `(A, (B, C))` のように深くなる。
//!
//! このモジュールでは `chain3`〜`chain6` を提供し、
//! `(A, B, C)` のようなフラットなタプルを直接返す。
//!
//! 動的型の [`chain_n`] と異なり、コンパイル時に型が確定するため
//! `downcast` が不要で安全。
//!
//! # 例
//! ```ignore
//! let c = chain3(same('a'), same('b'), same('c'));
//! let r = c(Ctx::new("abcdef"));
//! // r.result == Ok(("a", "b", "c"))
//! ```

use crate::types::*;

/// 型安全な chain 関数をタプルで生成するマクロ。
///
/// 各呼び出し箇所で引数名・型名・値の束縛名を明示的に指定する。
/// コンビネータを順に実行し、すべて成功すればフラットなタプルを返す。
/// いずれかが失敗した時点でそのエラーを伝播する。
macro_rules! define_chain_tuple {
    ($(#[$meta:meta])* $fname:ident => $($c:ident : $T:ident),+) => {
        $(#[$meta])*
        pub fn $fname<Ctx, $($T),+>(
            $($c: Combinator<Ctx, $T>),+
        ) -> Combinator<Ctx, ($($T),+)>
        where
            Ctx: Clone + 'static,
            $($T: Clone + 'static),+
        {
            comb(move |_ctx: Ctx| {
                define_chain_tuple!(@step _ctx; (); $($c : $T),+)
            })
        }
    };

    // 最後のコンビネータ: 蓄積した値とともにタプルを構築して返す
    (@step $ctx:expr; ($($prev_v:ident),*); $c:ident : $T:ident) => {
        {
            let __r = $c($ctx);
            match __r.result {
                Err(e) => propagate_err(__r.context, e),
                Ok(__last) => CombinatorResult::ok(__r.context, ($($prev_v,)* __last)),
            }
        }
    };

    // 中間のコンビネータ: 値を束縛し、次のステップへ進む
    // Ok($c) で引数名を値の束縛名として再利用（ローカルスコープでシャドーイング）
    (@step $ctx:expr; ($($prev_v:ident),*); $c:ident : $T:ident, $($rest:tt)+) => {
        {
            let __r = $c($ctx);
            match __r.result {
                Err(e) => propagate_err(__r.context, e),
                Ok($c) => {
                    define_chain_tuple!(@step __r.context; ($($prev_v,)* $c); $($rest)+)
                }
            }
        }
    };
}

define_chain_tuple!(
    /// 3つのコンビネータを順に実行し、結果を `(A, B, C)` のタプルで返す。
    ///
    /// # 例
    /// ```ignore
    /// let c = chain3(same('a'), same('b'), same('c'));
    /// let r = c(Ctx::new("abc"));
    /// assert_eq!(r.result.unwrap(), ("a", "b", "c"));
    /// ```
    chain3 => c1: A, c2: B, c3: C
);

define_chain_tuple!(
    /// 4つのコンビネータを順に実行し、結果を `(A, B, C, D)` のタプルで返す。
    chain4 => c1: A, c2: B, c3: C, c4: D
);

define_chain_tuple!(
    /// 5つのコンビネータを順に実行し、結果を `(A, B, C, D, E)` のタプルで返す。
    chain5 => c1: A, c2: B, c3: C, c4: D, c5: E
);

define_chain_tuple!(
    /// 6つのコンビネータを順に実行し、結果を `(A, B, C, D, E, F)` のタプルで返す。
    chain6 => c1: A, c2: B, c3: C, c4: D, c5: E, c6: F
);
