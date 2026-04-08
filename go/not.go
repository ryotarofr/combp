package combp

import "fmt"

// Not は否定先読み。内側のコンビネータが失敗したら成功、成功したら失敗する。
//
// 入力は消費しない。「この先にマッチしてほしくないもの」を表現するために使う。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: 内側のコンビネータの結果型（成功時はエラーメッセージに含まれる）。
//
// 引数:
//   - c: 否定対象のコンビネータ。
//
// 戻り値: 成功時に struct{} を返すコンビネータ。コンテキストは元の位置のまま。
func Not[C any, T any](c Combinator[C, T]) Combinator[C, struct{}] {
	return func(ctx C) Result[C, struct{}] {
		r := c(ctx)
		if r.OK {
			return Err[C, struct{}](ctx, fmt.Sprintf("not: %v にマッチすべきではありません", r.Value))
		}
		return OK(ctx, struct{}{})
	}
}
