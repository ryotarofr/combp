package combp

// Option はコンビネータを試し、失敗した場合はエラーなしで nil を返す。
//
// 成功した場合は *T（値へのポインタ）を返す。正規表現の ? に相当する。
// 失敗時にコンテキストは進まない。いずれの場合も結果は成功となる。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: 内側のコンビネータの結果型。
//
// 引数:
//   - c: 省略可能な対象のコンビネータ。
//
// 戻り値: 成功時に *T、失敗時に (*T)(nil) を返すコンビネータ。
func Option[C any, T any](c Combinator[C, T]) Combinator[C, *T] {
	return func(ctx C) Result[C, *T] {
		r := c(ctx)
		if r.OK {
			v := r.Value
			return OK(r.Context, &v)
		}
		return OK(ctx, (*T)(nil))
	}
}
