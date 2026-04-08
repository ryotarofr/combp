package combp

import "fmt"

// SepBy は区切り文字で区切られた0個以上の要素をパースする。
//
// element (separator element)* のパターンにマッチし、
// separator の結果は捨てて element の結果のみをスライスに収集する。
// コンテキストが Offsetter を実装している場合、入力が進まない繰り返しを
// 検知して無限ループを防止する。
//
// 型パラメータ:
//   - C: コンテキスト型。Offsetter を実装していれば無限ループ防止が有効になる。
//   - T: 要素コンビネータの結果型。スライスの要素型となる。
//   - S: セパレータコンビネータの結果型。パースはされるが結果は捨てられる。
//
// 引数:
//   - element: 各要素をパースするコンビネータ。
//   - separator: 要素間の区切りをパースするコンビネータ。
//   - min: 必要な最低要素数。0 の場合、要素がなくても空スライスで成功する。
//
// 戻り値: 成功時に要素の []T を返すコンビネータ。
func SepBy[C any, T any, S any](element Combinator[C, T], separator Combinator[C, S], min int) Combinator[C, []T] {
	return func(ctx C) Result[C, []T] {
		var results []T
		current := ctx
		var lastErr *OnError[C]

		fr := element(current)
		if !fr.OK {
			if min > 0 {
				return Err[C, []T](ctx,
					fmt.Sprintf("sepBy(): 最低 %d 個の要素が必要です。", min),
					fr.Err)
			}
			return OK(ctx, []T{})
		}
		results = append(results, fr.Value)
		current = fr.Context

		for {
			// 無限ループ防止: ループ開始時の offset を記録
			beforeOff, bOK := getOffset(current)

			sr := separator(current)
			if !sr.OK {
				break
			}
			er := element(sr.Context)
			if !er.OK {
				e := er.Err
				lastErr = &e
				break
			}

			// 無限ループ防止: separator + element で入力が進まなければ停止
			afterOff, aOK := getOffset(er.Context)
			if bOK && aOK && beforeOff == afterOff {
				break
			}

			results = append(results, er.Value)
			current = er.Context
		}

		if len(results) < min {
			by := []OnError[C]{}
			if lastErr != nil {
				by = append(by, *lastErr)
			}
			return Err[C, []T](ctx,
				fmt.Sprintf("sepBy(): 最低 %d 個の要素が必要ですが、%d 個しかありません。", min, len(results)),
				by...)
		}
		return OK(current, results)
	}
}
