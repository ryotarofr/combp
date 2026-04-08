package combp

// Label は内側のコンビネータが失敗したとき、エラーメッセージを上書きする。
//
// 内部エラーの By チェーンは保持されるため、
// デバッグ情報を失わずにユーザー向けのメッセージを改善できる。
// 成功した場合はそのまま結果を返す。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: 内側のコンビネータの結果型。
//
// 引数:
//   - message: 失敗時に使用するエラーメッセージ。
//   - c: ラップ対象のコンビネータ。
//
// 戻り値: 成功時はそのまま、失敗時は message でエラーを上書きしたコンビネータ。
func Label[C any, T any](message string, c Combinator[C, T]) Combinator[C, T] {
	return func(ctx C) Result[C, T] {
		r := c(ctx)
		if r.OK {
			return r
		}
		return Err[C, T](ctx, message, r.Err.By...)
	}
}
