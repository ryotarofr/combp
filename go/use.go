package combp

import "fmt"

// Use は from を実行し、その結果に基づいてセレクタ関数で次のコンビネータを動的に選択する。
//
// 先行パーサーの結果をキーとして、後続のパーサーをディスパッチするパターンに使う。
// セレクタが nil を返した場合、コンビネータは失敗する。
//
// 型パラメータ:
//   - C: コンテキスト型。
//   - M: 先行コンビネータ（from）の結果型。selector の引数に渡される中間型。
//   - T: selector が選択したコンビネータの結果型。最終的な成功値の型。
//
// 引数:
//   - from: 最初に実行するコンビネータ。この結果が selector に渡される。
//   - selector: from の結果を受け取り、次に実行するコンビネータを返す関数。
//     該当するコンビネータがない場合は nil を返す。
//
// 戻り値: selector が選択したコンビネータの結果を返すコンビネータ。
func Use[C any, M any, T any](from Combinator[C, M], selector func(M) Combinator[C, T]) Combinator[C, T] {
	return func(ctx C) Result[C, T] {
		fr := from(ctx)
		if !fr.OK {
			return Err[C, T](fr.Context, fr.Err.Message, fr.Err.By...)
		}
		next := selector(fr.Value)
		if next == nil {
			return Err[C, T](ctx,
				fmt.Sprintf("use: セレクタが %v に対して nil を返しました", fr.Value))
		}
		return next(fr.Context)
	}
}
