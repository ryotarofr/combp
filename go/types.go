// Package combinator は汎用パーサーコンビネータ関数を提供する。
//
// Combinator[C, T] は「コンテキスト C を受け取り、成功（値 T + 次のコンテキスト）
// または失敗（エラー情報）を返す関数」として表現される。
// 小さなコンビネータを Chain, Or, Repeat などで合成し、
// 複雑なパーサーを宣言的に構築できる。
//
// 主要な型パラメータの規約:
//   - C: コンテキスト型。パーサーの現在位置や入力ソースを保持するオブジェクト。
//     Offsetter インターフェースを実装していれば最遠失敗追跡や無限ループ防止が有効になる。
//   - T: パース結果の型。各コンビネータが成功時に返す値の型。
package combp

// OnError はコンビネータが失敗したときの構造化エラー情報を保持する。
//
// 型パラメータ:
//   - C: コンテキスト型。失敗地点のコンテキストを保持する。
//
// フィールド:
//   - On: 失敗が発生した時点のコンテキスト。
//   - Message: 人間が読めるエラーの説明。
//   - By: 原因チェーン（子エラー）のリスト。
//     chain や repeat など、内側のコンビネータの失敗を伝播する際に使用。
//   - Furthest: 最も深くまで進んだ失敗。Or / OrN が複数の分岐を試した結果、
//     入力を最も先まで消費した失敗を記録する。デバッグ時のエラー特定に有用。
type OnError[C any] struct {
	On       C
	Message  string
	By       []OnError[C]
	Furthest *OnError[C]
}
func (e OnError[C]) Error() string { return e.Message }

// Result はコンビネータの実行結果を保持する。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: 成功時のパース結果の型。
//
// フィールド:
//   - OK: 成功なら true、失敗なら false。
//   - Value: 成功時のパースされた値。
//   - Err: 失敗時のエラー情報。
//   - Context: このステップ後の（前に進んだ可能性のある）コンテキスト。
type Result[C any, T any] struct {
	OK      bool
	Value   T
	Err     OnError[C]
	Context C
}

// OK は成功した結果を構築する。
//
//   - ctx: パース成功後のコンテキスト（消費後の位置）。
//   - value: パースされた値。
func OK[C any, T any](ctx C, value T) Result[C, T] {
	return Result[C, T]{OK: true, Value: value, Context: ctx}
}

// Err は失敗した結果を構築する。
//
//   - ctx: 失敗が発生した時点のコンテキスト。
//   - message: エラーメッセージ。
//   - by: 原因となった子エラーのリスト（可変長）。
func Err[C any, T any](ctx C, message string, by ...OnError[C]) Result[C, T] {
	return Result[C, T]{
		OK:      false,
		Err:     OnError[C]{On: ctx, Message: message, By: by},
		Context: ctx,
	}
}

// ErrWithFurthest は最遠到達点の情報付きで失敗した結果を構築する。
//
//   - ctx: 失敗が発生した時点のコンテキスト。
//   - message: エラーメッセージ。
//   - furthest: 最遠到達点のエラー情報。Or 系コンビネータで使用。
//   - by: 原因となった子エラーのリスト（可変長）。
func ErrWithFurthest[C any, T any](ctx C, message string, furthest *OnError[C], by ...OnError[C]) Result[C, T] {
	return Result[C, T]{
		OK:      false,
		Err:     OnError[C]{On: ctx, Message: message, By: by, Furthest: furthest},
		Context: ctx,
	}
}

// Combinator はコンビネータの本体。コンテキスト C を受け取り Result を返す関数。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: パース結果の型。
type Combinator[C any, T any] func(ctx C) Result[C, T]

// Offsetter はコンテキストがオフセット（現在位置）を持つことを示すインターフェース。
//
// Or での最遠失敗比較、Repeat / SepBy での無限ループ防止に使用する。
// コンテキスト型がこのインターフェースを実装していれば、自動的に上記の機能が有効になる。
type Offsetter interface {
	Offset() int
}

// getOffset はコンテキストから Offset 値を安全に取り出す。
// Offsetter を実装していれば値と true を返し、なければ 0 と false を返す。
func getOffset[C any](ctx C) (int, bool) {
	if o, ok := any(ctx).(Offsetter); ok {
		return o.Offset(), true
	}
	return 0, false
}

// deeperError は2つの OnError のうち、入力のより先まで進んだ（offset が大きい）方を返す。
//
// Or / OrN で複数の分岐が失敗した際に、最も有用なエラーを選択するために使用する。
// offset が取得できない場合は a を優先する。
func deeperError[C any](a, b OnError[C]) OnError[C] {
	ao, aok := getOffset(a.On)
	bo, bok := getOffset(b.On)
	if !aok || !bok {
		return a
	}
	if bo > ao {
		return b
	}
	return a
}

// Pair は2つの値を保持する汎用タプル型。Chain の戻り値で使用する。
//
// 型パラメータ:
//   - L: 左（最初）の値の型。
//   - R: 右（2番目）の値の型。
type Pair[L any, R any] struct {
	Left  L
	Right R
}

// Either は2つの型のいずれかを保持する直和型。Or の戻り値で使用する。
//
// 型パラメータ:
//   - L: 左の値の型（lhs の成功結果）。
//   - R: 右の値の型（rhs の成功結果）。
type Either[L any, R any] struct {
	IsLeft bool
	LeftV  L
	RightV R
}

// Left は Either の左の値を構築する。
func Left[L any, R any](v L) Either[L, R] { return Either[L, R]{IsLeft: true, LeftV: v} }

// Right は Either の右の値を構築する。
func Right[L any, R any](v R) Either[L, R] { return Either[L, R]{IsLeft: false, RightV: v} }
