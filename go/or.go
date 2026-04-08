package combp

// Or は lhs を先に試し、失敗したら rhs を試す（二者択一）。
//
// 両方失敗した場合、入力をより先まで消費した分岐のエラーを Furthest として
// 記録する。これにより、ユーザーは「どの分岐が最も惜しかったか」を把握できる。
//
// 型パラメータ:
//   - C: コンテキスト型。Offsetter を実装していれば最遠失敗追跡が有効になる。
//   - L: lhs の成功時の結果型。Either.LeftV に格納される。
//   - R: rhs の成功時の結果型。Either.RightV に格納される。
//
// 引数:
//   - lhs: 最初に試すコンビネータ。
//   - rhs: lhs が失敗した場合に試すコンビネータ。
//
// 戻り値: 成功時に Either[L, R] を返すコンビネータ。
// lhs が成功すれば Left、rhs が成功すれば Right を返す。
func Or[C any, L any, R any](lhs Combinator[C, L], rhs Combinator[C, R]) Combinator[C, Either[L, R]] {
	return func(ctx C) Result[C, Either[L, R]] {
		lr := lhs(ctx)
		if lr.OK {
			return OK(lr.Context, Left[L, R](lr.Value))
		}
		rr := rhs(ctx)
		if rr.OK {
			return OK(rr.Context, Right[L, R](rr.Value))
		}
		furthest := deeperError(lr.Err, rr.Err)
		return ErrWithFurthest[C, Either[L, R]](ctx, "or", &furthest, lr.Err, rr.Err)
	}
}
