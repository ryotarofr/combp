package combp

// ChainN は一連のコンビネータを順に実行し、結果を []any で返す。
//
// いずれかが失敗した時点でそのエラーを返す。
// Go のジェネリクスの制約上、型安全性は失われるため、呼び出し側で型アサーションが必要。
// 型安全に2〜4個を連結するには Chain を入れ子にすること。
//
// 型パラメータ:
//   - C: コンテキスト型。
//
// 引数:
//   - combinators: 順に実行するコンビネータの可変長引数。
//     各コンビネータの結果型は any。
//
// 戻り値: 成功時に各コンビネータの結果を格納した []any を返すコンビネータ。
// スライスのインデックスは combinators の順序に対応する。
func ChainN[C any](combinators ...Combinator[C, any]) Combinator[C, []any] {
	return func(ctx C) Result[C, []any] {
		results := make([]any, 0, len(combinators))
		current := ctx
		for _, c := range combinators {
			r := c(current)
			if !r.OK {
				return Err[C, []any](r.Context, r.Err.Message, r.Err.By...)
			}
			results = append(results, r.Value)
			current = r.Context
		}
		return OK(current, results)
	}
}
