package combp

import "fmt"

// Repeat はコンビネータを繰り返し実行し、結果をスライスに収集する。
//
// 正規表現の {must,to} に相当する。
// コンテキストが Offsetter を実装している場合、入力が進まない繰り返しを
// 検知して無限ループを防止する。
//
// 型パラメータ:
//   - C: コンテキスト型。Offsetter を実装していれば無限ループ防止が有効になる。
//   - T: 内側のコンビネータの結果型。スライスの要素型となる。
//
// 引数:
//   - c: 繰り返し実行するコンビネータ。
//   - must: 必要な最低マッチ回数。0 を指定すると、マッチなしでも空スライスで成功する。
//   - to: 最大マッチ回数。0 以下で無制限。正の値の場合、must 以上でなければならない。
//
// 戻り値: 成功時にマッチ結果の []T を返すコンビネータ。
//
// パニック: must が負の場合、または to > 0 かつ to < must の場合。
func Repeat[C any, T any](c Combinator[C, T], must int, to int) Combinator[C, []T] {
	if must < 0 {
		panic(fmt.Sprintf("combinator.Repeat: must (%d) は 0 以上でなければなりません", must))
	}
	if to > 0 && to < must {
		panic(fmt.Sprintf("combinator.Repeat: to (%d) は must (%d) 以上でなければなりません", to, must))
	}
	return func(ctx C) Result[C, []T] {
		var results []T
		current := ctx
		var lastErr *OnError[C]
		for to <= 0 || len(results) < to {
			r := c(current)
			if !r.OK {
				e := r.Err
				lastErr = &e
				break
			}
			before, bOK := getOffset(current)
			after, aOK := getOffset(r.Context)
			if bOK && aOK && before == after {
				break
			}
			results = append(results, r.Value)
			current = r.Context
		}
		if len(results) < must {
			by := []OnError[C]{}
			if lastErr != nil {
				by = append(by, *lastErr)
			}
			return Err[C, []T](ctx,
				fmt.Sprintf("repeat(): %d 回以上の繰り返しが必要です。", must),
				by...)
		}
		return OK(current, results)
	}
}
