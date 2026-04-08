package combp

// Peek は先読み。コンビネータを実行するが入力を消費しない。
//
// 入力を消費せずに「次に何が来るか」を確認したい場合に使う。
// 成功時はコンテキストを元に戻し、失敗した場合はそのままエラーを返す。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: 内側のコンビネータの結果型。
//
// 引数:
//   - c: 先読み対象のコンビネータ。
//
// 戻り値: 成功時にコンテキストを元の位置に戻した上で T 型の値を返すコンビネータ。
func Peek[C any, T any](c Combinator[C, T]) Combinator[C, T] {
	return func(ctx C) Result[C, T] {
		r := c(ctx)
		if !r.OK {
			return r
		}
		return OK(ctx, r.Value)
	}
}
