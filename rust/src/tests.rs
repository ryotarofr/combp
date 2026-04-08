//! Tests for the combinator library.

use crate::*;
use std::sync::{Arc, Mutex};

// -----------------------------------------------------------------------
// テスト用コンテキスト
// -----------------------------------------------------------------------

/// オフセット追跡付きの基本的な文字列パースコンテキスト。
#[derive(Debug, Clone, PartialEq)]
struct Ctx {
    src: String,
    pos: usize,
}

impl HasOffset for Ctx {
    fn offset(&self) -> usize {
        self.pos
    }
}

impl Ctx {
    fn new(src: &str) -> Self {
        Self {
            src: src.to_string(),
            pos: 0,
        }
    }
}

// -----------------------------------------------------------------------
// プリミティブパーサー（テスト用ヘルパー）
// -----------------------------------------------------------------------

/// 1文字を消費する。
fn any_char() -> Combinator<Ctx, String> {
    comb(|ctx: Ctx| {
        if ctx.pos >= ctx.src.len() {
            return CombinatorResult::err(ctx, "any: 入力の終端です", vec![]);
        }
        let ch = ctx.src[ctx.pos..ctx.pos + 1].to_string();
        CombinatorResult::ok(
            Ctx {
                src: ctx.src.clone(),
                pos: ctx.pos + 1,
            },
            ch,
        )
    })
}

/// 指定した1文字にマッチする。
fn same(expected: &str) -> Combinator<Ctx, String> {
    let expected = expected.to_string();
    comb(move |ctx: Ctx| {
        let r = any_char()(ctx.clone());
        match r.result {
            Err(e) => CombinatorResult::err(r.context, e.message, e.by),
            Ok(v) => {
                if v != expected {
                    CombinatorResult::err(
                        ctx,
                        format!("'{}' が期待されましたが '{}' でした", expected, v),
                        vec![],
                    )
                } else {
                    CombinatorResult::ok(r.context, v)
                }
            }
        }
    })
}

/// 1桁の数字にマッチする。
fn digit() -> Combinator<Ctx, String> {
    comb(|ctx: Ctx| {
        let r = any_char()(ctx.clone());
        match r.result {
            Err(e) => CombinatorResult::err(r.context, e.message, e.by),
            Ok(v) => {
                if v.chars().next().is_some_and(|c| c.is_ascii_digit()) {
                    CombinatorResult::ok(r.context, v)
                } else {
                    CombinatorResult::err(
                        ctx,
                        format!("数字が期待されましたが '{}' でした", v),
                        vec![],
                    )
                }
            }
        }
    })
}

/// 指定した文字列にマッチする。
fn keyword(word: &str) -> Combinator<Ctx, String> {
    let word = word.to_string();
    comb(move |ctx: Ctx| {
        if ctx.src[ctx.pos..].starts_with(&word) {
            CombinatorResult::ok(
                Ctx {
                    src: ctx.src.clone(),
                    pos: ctx.pos + word.len(),
                },
                word.clone(),
            )
        } else {
            CombinatorResult::err(ctx, format!("'{}' が期待されました", word), vec![])
        }
    })
}

/// 入力文字列からコンビネータを実行するヘルパー。
fn parse<T>(c: &Combinator<Ctx, T>, input: &str) -> CombinatorResult<Ctx, T> {
    c(Ctx::new(input))
}

// -----------------------------------------------------------------------
// テスト
// -----------------------------------------------------------------------

#[test]
fn test_any() {
    let r = parse(&any_char(), "abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), "a");
    assert_eq!(r.context.pos, 1);
}

#[test]
fn test_same() {
    let r = parse(&same("a"), "abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), "a");

    let r2 = parse(&same("x"), "abc");
    assert!(!r2.is_ok());
}

#[test]
fn test_chain() {
    let c = chain(same("a"), same("b"));
    let r = parse(&c, "abc");
    assert!(r.is_ok());
    let (l, ri) = r.result.unwrap();
    assert_eq!(l, "a");
    assert_eq!(ri, "b");
}

#[test]
fn test_or() {
    let c = or(same("x"), same("a"));
    let r = parse(&c, "abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), Either::Right("a".to_string()));
}

#[test]
fn test_or_furthest_failure() {
    // "ab" パーサーは pos=1 で失敗、"x" パーサーは pos=0 で失敗
    let ab = chain(same("a"), same("x"));
    let ab_mapped = map(ab, |p| format!("{}{}", p.0, p.1));
    let xy = same("x");

    let c = or(ab_mapped, xy);
    let r = parse(&c, "abc");
    assert!(!r.is_ok());
    let err = r.result.unwrap_err();
    assert!(err.furthest.is_some());
    // "ab" 分岐の方が先まで進んだ (pos=1)
    assert_eq!(err.furthest.unwrap().on.offset(), 1);
}

#[test]
fn test_convert() {
    let c = map(digit(), |s| s.parse::<i32>().unwrap());
    let r = parse(&c, "7abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), 7);
}

#[test]
fn test_not() {
    let c = not(same("x"));
    let r = parse(&c, "abc");
    assert!(r.is_ok());
    // コンテキストは進まない
    assert_eq!(r.context.pos, 0);
}

#[test]
fn test_option() {
    let c = option(same("x"));
    let r = parse(&c, "abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), None);

    let r2 = parse(&c, "xyz");
    assert!(r2.is_ok());
    assert_eq!(r2.result.unwrap(), Some("x".to_string()));
}

#[test]
fn test_repeat() {
    let c = repeat(digit(), 1, None);
    let r = parse(&c, "123abc");
    assert!(r.is_ok());
    let v = r.result.unwrap();
    assert_eq!(v, vec!["1", "2", "3"]);
}

#[test]
fn test_repeat_with_bounds() {
    let c = repeat(digit(), 1, Some(2)); // 最低1回、最大2回
    let r = parse(&c, "123abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap().len(), 2);
}

#[test]
fn test_repeat_min_fail() {
    let c = repeat(digit(), 3, None);
    let r = parse(&c, "12abc");
    assert!(!r.is_ok());
}

#[test]
fn test_sep_by() {
    let comma = same(",");
    let c = sep_by(digit(), comma, 0);

    // 複数要素
    let r = parse(&c, "1,2,3abc");
    assert!(r.is_ok());
    let v = r.result.unwrap();
    assert_eq!(v, vec!["1", "2", "3"]);

    // 空入力
    let r2 = parse(&c, "abc");
    assert!(r2.is_ok());
    assert_eq!(r2.result.unwrap().len(), 0);

    // 要素1つ
    let r3 = parse(&c, "5abc");
    assert!(r3.is_ok());
    assert_eq!(r3.result.unwrap(), vec!["5"]);
}

#[test]
fn test_sep_by_min() {
    let c = sep_by(digit(), same(","), 2);
    let r = parse(&c, "1abc");
    assert!(!r.is_ok());
}

#[test]
fn test_lazy() {
    let call_count = Arc::new(Mutex::new(0));
    let cc = call_count.clone();
    let c = lazy(move || {
        *cc.lock().unwrap() += 1;
        same("a")
    });

    // 初回呼び出しでファクトリが実行される
    let r = parse(&c, "abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), "a");
    assert_eq!(*call_count.lock().unwrap(), 1);

    // 2回目はキャッシュを使う
    let r2 = parse(&c, "abc");
    assert!(r2.is_ok());
    assert_eq!(*call_count.lock().unwrap(), 1);
}

#[test]
fn test_peek() {
    let c = peek(same("a"));
    let r = parse(&c, "abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), "a");
    // Peek は位置を進めない
    assert_eq!(r.context.pos, 0);
}

#[test]
fn test_use() {
    // 先頭1文字を先読みしてディスパッチする
    let c = use_combinator(
        peek(any_char()),
        |ch: String| -> Option<Combinator<Ctx, String>> {
            match ch.as_str() {
                "a" => Some(keyword("abc")),
                "x" => Some(keyword("xyz")),
                _ => None,
            }
        },
    );

    let r = parse(&c, "abcdef");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), "abc");

    let r2 = parse(&c, "xyzabc");
    assert!(r2.is_ok());
    assert_eq!(r2.result.unwrap(), "xyz");

    let r3 = parse(&c, "qqq");
    assert!(!r3.is_ok());
}

#[test]
fn test_label() {
    let c = label("数値が必要です", digit());
    let r = parse(&c, "abc");
    assert!(!r.is_ok());
    assert_eq!(r.result.unwrap_err().message, "数値が必要です");
}

#[test]
fn test_or_n() {
    let c = or_n(vec![same("x"), same("y"), same("a")]);
    let r = parse(&c, "abc");
    assert!(r.is_ok());
    assert_eq!(r.result.unwrap(), "a");
}

// -----------------------------------------------------------------------
// 統合テスト: シンプルな行パーサー（README の例に相当）
// -----------------------------------------------------------------------

#[test]
fn test_line_parser() {
    let eol = same("\n");
    let not_eol = map(chain(not(eol.clone()), any_char()), |p| p.1);
    let line = map(chain(repeat(not_eol, 1, None), option(eol)), |p| {
        p.0.join("")
    });
    let lines = repeat(line, 0, None);

    let r = parse(&lines, "hello\nworld\n");
    assert!(r.is_ok());
    let v = r.result.unwrap();
    assert_eq!(v, vec!["hello", "world"]);
}
