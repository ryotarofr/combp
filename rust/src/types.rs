//! コンビネータライブラリの型定義とヘルパー。
//!
//! コンビネータフレームワーク全体で使用されるコア型システムを定義する。
//!
//! 主要な型パラメータの規約:
//!   - `C`: コンテキスト型。パーサーの現在位置や入力ソースを保持するオブジェクト。
//!     `HasOffset` を実装していれば最遠失敗追跡や無限ループ防止が有効になる。
//!   - `T`: パース結果の型。各コンビネータが成功時に返す値の型。

use std::fmt;
use std::sync::Arc;

/// コンビネータが失敗したときの構造化エラー情報。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。失敗地点のコンテキストを保持する。
///
/// # フィールド
/// - `on`: 失敗が発生した時点のコンテキスト。
/// - `message`: 人間が読めるエラーの説明。
/// - `by`: 原因チェーン（子エラー）のリスト。
///   chain や repeat など、内側のコンビネータの失敗を伝播する際に使用。
/// - `furthest`: 最も深くまで進んだ失敗。or / or_n が複数の分岐を試した結果、
///   入力を最も先まで消費した失敗を記録する。デバッグ時のエラー特定に有用。
#[derive(Debug, Clone)]
pub struct OnError<C: Clone> {
    pub on: C,
    pub message: String,
    pub by: Vec<OnError<C>>,
    pub furthest: Option<Box<OnError<C>>>,
}

impl<C: Clone> fmt::Display for OnError<C> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}

/// コンビネータの実行結果。
///
/// # 型パラメータ
/// - `C`: コンテキスト型。
/// - `T`: 成功時のパース結果の型。
///
/// # フィールド
/// - `result`: 成功なら `Ok(値)`、失敗なら `Err(エラー情報)`。
/// - `context`: このステップ後の（前に進んだ可能性のある）コンテキスト。
///   成功時は消費後の位置、失敗時は失敗発生時点の位置を示す。
///
/// T に Clone 制約を課さないことで、`Box<dyn Any>` など Clone 不可な型も扱える。
pub struct CombinatorResult<C: Clone, T> {
    pub result: Result<T, OnError<C>>,
    pub context: C,
}

// T: Clone の場合のみ Clone を提供する
impl<C: Clone, T: Clone> Clone for CombinatorResult<C, T> {
    fn clone(&self) -> Self {
        Self {
            result: self.result.clone(),
            context: self.context.clone(),
        }
    }
}

impl<C: Clone + fmt::Debug, T: fmt::Debug> fmt::Debug for CombinatorResult<C, T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("CombinatorResult")
            .field("result", &self.result)
            .field("context", &self.context)
            .finish()
    }
}

impl<C: Clone, T> CombinatorResult<C, T> {
    /// 成功した結果を構築する。
    ///
    /// # 引数
    /// - `context`: パース成功後のコンテキスト（消費後の位置）。
    /// - `value`: パースされた値。
    pub fn ok(context: C, value: T) -> Self {
        Self {
            result: Ok(value),
            context,
        }
    }

    /// 失敗した結果を構築する。
    ///
    /// # 引数
    /// - `context`: 失敗が発生した時点のコンテキスト。
    /// - `message`: エラーメッセージ。
    /// - `by`: 原因となった子エラーのリスト。
    pub fn err(context: C, message: impl Into<String>, by: Vec<OnError<C>>) -> Self {
        let ctx = context.clone();
        Self {
            result: Err(OnError {
                on: context,
                message: message.into(),
                by,
                furthest: None,
            }),
            context: ctx,
        }
    }

    /// 最遠到達点の情報付きで失敗した結果を構築する。
    ///
    /// # 引数
    /// - `context`: 失敗が発生した時点のコンテキスト。
    /// - `message`: エラーメッセージ。
    /// - `by`: 原因となった子エラーのリスト。
    /// - `furthest`: 最遠到達点のエラー情報。or 系コンビネータで使用。
    pub fn err_with_furthest(
        context: C,
        message: impl Into<String>,
        by: Vec<OnError<C>>,
        furthest: OnError<C>,
    ) -> Self {
        let ctx = context.clone();
        Self {
            result: Err(OnError {
                on: context,
                message: message.into(),
                by,
                furthest: Some(Box::new(furthest)),
            }),
            context: ctx,
        }
    }

    /// 成功かどうかを返す。
    pub fn is_ok(&self) -> bool {
        self.result.is_ok()
    }
}

/// コンビネータの本体。コンテキスト `C` を受け取り `CombinatorResult` を返すクロージャ。
///
/// `Arc` で包むことで Clone 可能にし、合成可能にしている。
/// 小さなコンビネータを `chain`, `or`, `repeat` などで合成し、複雑なパーサーを宣言的に構築する。
pub type Combinator<C, T> = Arc<dyn Fn(C) -> CombinatorResult<C, T> + Send + Sync>;

/// コンビネータを簡単に作るヘルパー。クロージャを `Arc` で包んで `Combinator` 型にする。
pub fn comb<C: Clone + 'static, T: 'static>(
    f: impl Fn(C) -> CombinatorResult<C, T> + Send + Sync + 'static,
) -> Combinator<C, T> {
    Arc::new(f)
}

/// Context がオフセット（現在位置）を持つことを示すトレイト。
///
/// `or` での最遠失敗比較、`repeat` / `sep_by` での無限ループ防止に使用する。
/// コンテキスト型がこのトレイトを実装していれば、自動的に上記の機能が有効になる。
///
/// # 例
/// ```ignore
/// struct Ctx { src: String, offset: usize }
/// impl HasOffset for Ctx {
///     fn offset(&self) -> usize { self.offset }
/// }
/// ```
pub trait HasOffset {
    fn offset(&self) -> usize;
}

/// 2つの `OnError` のうち、入力のより先まで進んだ（offset が大きい）方を返す。
///
/// `or` / `or_n` で複数の分岐が失敗した際に、最も有用なエラーを選択するために使用する。
///
/// # 型パラメータ
/// - `C`: `HasOffset` を実装したコンテキスト型。
///
/// # 引数
/// - `a`: 1つ目のエラー。
/// - `b`: 2つ目のエラー。
pub fn deeper_error<C: Clone + HasOffset>(a: &OnError<C>, b: &OnError<C>) -> OnError<C> {
    if b.on.offset() > a.on.offset() {
        b.clone()
    } else {
        a.clone()
    }
}
