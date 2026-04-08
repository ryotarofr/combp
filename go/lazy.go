package combp

import "sync"

// Lazy はコンビネータの構築を遅延させ、循環参照を回避する。
//
// ファクトリ関数は最初の呼び出し時に1回だけ実行され、以降はキャッシュを使用する。
// sync.Once によりゴルーチン安全。
// 再帰的なパーサー（括弧のネストなど）を定義する際に必須となる。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - T: 内側のコンビネータの結果型。
//
// 引数:
//   - factory: コンビネータを生成するファクトリ関数。引数なしで呼び出され、
//     Combinator[C, T] を返す。この関数内で Lazy の戻り値自身を参照することで
//     循環参照を実現できる。
//
// 戻り値: factory が生成するコンビネータと同じ振る舞いをするコンビネータ。
func Lazy[C any, T any](factory func() Combinator[C, T]) Combinator[C, T] {
	var (
		once   sync.Once
		cached Combinator[C, T]
	)
	return func(ctx C) Result[C, T] {
		once.Do(func() {
			cached = factory()
		})
		return cached(ctx)
	}
}
