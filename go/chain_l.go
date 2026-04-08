package combp

// ChainL はコンビネータを順に実行し、最初（左端）の結果のみを返す。
//
// 2番目以降のコンビネータは実行されるが、その結果は捨てられる。
// トークン後の空白スキップなどに便利。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: 最初のコンビネータ（first）の結果型。最終的な戻り値の型。
//   - Rest: 残りのコンビネータの結果型。パースはされるが結果は捨てられる。
//
// 引数:
//   - first: 結果を保持するコンビネータ。
//   - rest: first 成功後に順に実行するコンビネータの可変長引数。結果は捨てられる。
//
// 戻り値: 成功時に first の結果を返すコンビネータ。
func ChainL[C any, T any, Rest any](first Combinator[C, T], rest ...Combinator[C, Rest]) Combinator[C, T] {
	return func(ctx C) Result[C, T] {
		fr := first(ctx)
		if !fr.OK {
			return fr
		}
		current := fr.Context
		for _, c := range rest {
			r := c(current)
			if !r.OK {
				return Err[C, T](r.Context, r.Err.Message, r.Err.By...)
			}
			current = r.Context
		}
		return OK(current, fr.Value)
	}
}
