package combp

// ChainR はコンビネータを順に実行し、最後（右端）の結果のみを返す。
//
// 最後以外のコンビネータは実行されるが、その結果は捨てられる。
// プレフィクスやデリミタを読み飛ばしてから本体を取得する場合に便利。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - Skip: 読み飛ばすコンビネータ（skips）の結果型。パースはされるが結果は捨てられる。
//   - T: 最後のコンビネータ（last）の結果型。最終的な戻り値の型。
//
// 引数:
//   - skips: 先に実行して結果を捨てるコンビネータのスライス。
//   - last: 最後に実行し、結果を保持するコンビネータ。
//
// 戻り値: 成功時に last の結果を返すコンビネータ。
func ChainR[C any, Skip any, T any](skips []Combinator[C, Skip], last Combinator[C, T]) Combinator[C, T] {
	return func(ctx C) Result[C, T] {
		current := ctx
		for _, c := range skips {
			r := c(current)
			if !r.OK {
				return Err[C, T](r.Context, r.Err.Message, r.Err.By...)
			}
			current = r.Context
		}
		lr := last(current)
		if !lr.OK {
			return lr
		}
		return OK(lr.Context, lr.Value)
	}
}
