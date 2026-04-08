//! # combp
//!
//! A generic parser combinator library.
//!
//! `Combinator<C, T>` は「コンテキスト C を受け取り、成功（値 T + 次のコンテキスト）
//! または失敗（エラー情報）を返すクロージャ」として表現される。
//! 小さなコンビネータを `chain`, `or`, `repeat` などで合成し、
//! 複雑なパーサーを宣言的に構築できる。

pub mod chain;
pub mod chain_l;
pub mod chain_n;
pub mod chain_r;
pub mod chain_tuple;
pub mod convert;
pub mod label;
pub mod lazy;
pub mod not_comb;
pub mod option_comb;
pub mod or_comb;
pub mod or_n;
pub mod peek;
pub mod repeat;
pub mod sep_by;
pub mod types;
pub mod use_comb;

#[cfg(test)]
mod tests;

// クレートルートから全モジュールを再エクスポート
pub use chain::*;
pub use chain_l::*;
pub use chain_n::*;
pub use chain_r::*;
pub use chain_tuple::*;
pub use convert::*;
pub use label::*;
pub use lazy::*;
pub use not_comb::*;
pub use option_comb::*;
pub use or_comb::*;
pub use or_n::*;
pub use peek::*;
pub use repeat::*;
pub use sep_by::*;
pub use types::*;
pub use use_comb::*;
