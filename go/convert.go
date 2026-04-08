package combp

// Convert は成功結果を変換関数で別の型に写す。
//
// 内側のコンビネータが成功した場合、その値とコンテキストを f に渡して変換する。
// 失敗した場合はそのままエラーを返す。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - A: 変換前の結果型（内側のコンビネータの成功型）。
//   - B: 変換後の結果型。
//
// 引数:
//   - c: 内側のコンビネータ。
//   - f: 変換関数。func(成功値 A, コンテキスト C) B の形式。
//     コンテキストを参照して変換結果を調整したい場合に有用。
//
// 戻り値: 成功時に B 型の値を返すコンビネータ。
func Convert[C any, A any, B any](c Combinator[C, A], f func(A, C) B) Combinator[C, B] {
	return func(ctx C) Result[C, B] {
		r := c(ctx)
		if !r.OK {
			return Err[C, B](r.Context, r.Err.Message, r.Err.By...)
		}
		return OK(r.Context, f(r.Value, r.Context))
	}
}

// Map は Convert の簡易版。コンテキストを無視して値だけを変換する。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - A: 変換前の結果型。
//   - B: 変換後の結果型。
//
// 引数:
//   - c: 内側のコンビネータ。
//   - f: 変換関数。func(成功値 A) B の形式。
func Map[C any, A any, B any](c Combinator[C, A], f func(A) B) Combinator[C, B] {
	return Convert(c, func(a A, _ C) B { return f(a) })
}
