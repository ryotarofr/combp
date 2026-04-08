package combp

// Chain は2つのコンビネータを順に実行し、結果を Pair で返す。
//
// lhs が成功した場合、その更新されたコンテキストから rhs を実行する。
// どちらかが失敗した時点でそのエラーをそのまま返す。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - L: lhs の成功時の結果型。Pair.Left に格納される。
//   - R: rhs の成功時の結果型。Pair.Right に格納される。
//
// 引数:
//   - lhs: 最初に実行するコンビネータ。
//   - rhs: lhs 成功後に実行するコンビネータ。
//
// 戻り値: 成功時に Pair[L, R] を返すコンビネータ。
func Chain[C any, L any, R any](lhs Combinator[C, L], rhs Combinator[C, R]) Combinator[C, Pair[L, R]] {
	return func(ctx C) Result[C, Pair[L, R]] {
		lr := lhs(ctx)
		if !lr.OK {
			return Err[C, Pair[L, R]](lr.Context, lr.Err.Message, lr.Err.By...)
		}
		rr := rhs(lr.Context)
		if !rr.OK {
			return Err[C, Pair[L, R]](rr.Context, rr.Err.Message, rr.Err.By...)
		}
		return OK(rr.Context, Pair[L, R]{Left: lr.Value, Right: rr.Value})
	}
}
