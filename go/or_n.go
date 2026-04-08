package combp

// OrN は各コンビネータを順に試し、最初に成功したものを返す。
//
// 全て失敗した場合、最遠失敗（Furthest）を追跡して返す。
// Go のジェネリクスの制約上、Combinator[C, any] を受け取るため、呼び出し側で型アサーションが必要。
//
// 型パラメータ:
//   - C: コンテキスト型。Offsetter を実装していれば最遠失敗追跡が有効になる。
//
// 引数:
//   - combinators: 試行するコンビネータの可変長引数。先頭から順に試行される。
//
// 戻り値: 最初に成功したコンビネータの結果を返すコンビネータ。
// combinators が空の場合はエラーを返す。
func OrN[C any](combinators ...Combinator[C, any]) Combinator[C, any] {
	return func(ctx C) Result[C, any] {
		var errs []OnError[C]
		for _, c := range combinators {
			r := c(ctx)
			if r.OK {
				return OK(r.Context, r.Value)
			}
			errs = append(errs, r.Err)
		}
		if len(errs) > 0 {
			furthest := errs[0]
			for _, e := range errs[1:] {
				furthest = deeperError(furthest, e)
			}
			return ErrWithFurthest[C, any](ctx, "or", &furthest, errs...)
		}
		return Err[C, any](ctx, "orN: コンビネータが指定されていません")
	}
}
