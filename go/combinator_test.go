package combp

import (
	"fmt"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// テスト用コンテキスト: シンプルな文字列パーサーコンテキスト
// ---------------------------------------------------------------------------

// Ctx はオフセット追跡付きの基本的な文字列パースコンテキスト。
type Ctx struct {
	Src string
	Pos int
}

// Offset は最遠失敗追跡のために Offsetter インターフェースを実装する。
func (c Ctx) Offset() int { return c.Pos }

// ---------------------------------------------------------------------------
// プリミティブパーサー（テスト用ヘルパー）
// ---------------------------------------------------------------------------

// any_ は1文字を消費する。
func any_() Combinator[Ctx, string] {
	return func(ctx Ctx) Result[Ctx, string] {
		if ctx.Pos >= len(ctx.Src) {
			return Err[Ctx, string](ctx, "any: 入力の終端です")
		}
		ch := string(ctx.Src[ctx.Pos])
		return OK(Ctx{Src: ctx.Src, Pos: ctx.Pos + 1}, ch)
	}
}

// same は指定した1文字にマッチする。
func same(ch string) Combinator[Ctx, string] {
	return func(ctx Ctx) Result[Ctx, string] {
		r := any_()(ctx)
		if !r.OK {
			return r
		}
		if r.Value != ch {
			return Err[Ctx, string](ctx, fmt.Sprintf("'%s' が期待されましたが '%s' でした", ch, r.Value))
		}
		return r
	}
}

// digit は1桁の数字にマッチする。
func digit() Combinator[Ctx, string] {
	return func(ctx Ctx) Result[Ctx, string] {
		r := any_()(ctx)
		if !r.OK {
			return r
		}
		if r.Value[0] < '0' || r.Value[0] > '9' {
			return Err[Ctx, string](ctx, fmt.Sprintf("数字が期待されましたが '%s' でした", r.Value))
		}
		return r
	}
}

// keyword は指定した文字列にマッチする。
func keyword(word string) Combinator[Ctx, string] {
	return func(ctx Ctx) Result[Ctx, string] {
		if !strings.HasPrefix(ctx.Src[ctx.Pos:], word) {
			return Err[Ctx, string](ctx, fmt.Sprintf("'%s' が期待されました", word))
		}
		return OK(Ctx{Src: ctx.Src, Pos: ctx.Pos + len(word)}, word)
	}
}

// parse はコンビネータに入力文字列を渡して実行するヘルパー。
func parse[T any](c Combinator[Ctx, T], input string) Result[Ctx, T] {
	return c(Ctx{Src: input, Pos: 0})
}

// ---------------------------------------------------------------------------
// テスト
// ---------------------------------------------------------------------------

func TestAny(t *testing.T) {
	r := parse(any_(), "abc")
	if !r.OK || r.Value != "a" {
		t.Fatalf("'a' が期待されましたが %v でした", r)
	}
	if r.Context.Pos != 1 {
		t.Fatalf("pos=1 が期待されましたが %d でした", r.Context.Pos)
	}
}

func TestSame(t *testing.T) {
	r := parse(same("a"), "abc")
	if !r.OK || r.Value != "a" {
		t.Fatalf("OK 'a' が期待されましたが %v でした", r)
	}

	r2 := parse(same("x"), "abc")
	if r2.OK {
		t.Fatalf("失敗が期待されましたが OK でした")
	}
}

func TestChain(t *testing.T) {
	c := Chain(same("a"), same("b"))
	r := parse(c, "abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラー: %s", r.Err.Message)
	}
	if r.Value.Left != "a" || r.Value.Right != "b" {
		t.Fatalf("(a, b) が期待されましたが (%s, %s) でした", r.Value.Left, r.Value.Right)
	}
}

func TestOr(t *testing.T) {
	c := Or(same("x"), same("a"))
	r := parse(c, "abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラー: %s", r.Err.Message)
	}
	if r.Value.IsLeft {
		t.Fatalf("Right が期待されましたが Left でした")
	}
	if r.Value.RightV != "a" {
		t.Fatalf("'a' が期待されましたが '%s' でした", r.Value.RightV)
	}
}

func TestOrFurthestFailure(t *testing.T) {
	// "ab" パーサーは pos=2 で失敗、"x" パーサーは pos=0 で失敗
	ab := Chain(same("a"), same("x")) // 'a' にマッチした後 pos=1 で失敗
	xy := same("x")                    // pos=0 で即座に失敗

	c := Or(
		Map(ab, func(p Pair[string, string]) string { return p.Left + p.Right }),
		xy,
	)
	r := parse(c, "abc")
	if r.OK {
		t.Fatalf("失敗が期待されました")
	}
	if r.Err.Furthest == nil {
		t.Fatalf("furthest が設定されているべきです")
	}
	// "ab" 分岐の方が "x" 分岐 (pos=0) より先まで進んだ (pos=1)
	off, ok := getOffset(r.Err.Furthest.On)
	if !ok {
		t.Fatalf("オフセットが取得可能であるべきです")
	}
	if off != 1 {
		t.Fatalf("furthest offset=1 が期待されましたが %d でした", off)
	}
}

func TestConvert(t *testing.T) {
	c := Map(digit(), func(s string) int { return int(s[0] - '0') })
	r := parse(c, "7abc")
	if !r.OK || r.Value != 7 {
		t.Fatalf("7 が期待されましたが %v でした", r)
	}
}

func TestNot(t *testing.T) {
	c := Not[Ctx, string](same("x"))
	r := parse(c, "abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラーでした")
	}
	// コンテキストは進まないはず
	if r.Context.Pos != 0 {
		t.Fatalf("pos=0 が期待されましたが %d でした", r.Context.Pos)
	}
}

func TestOption(t *testing.T) {
	c := Option(same("x"))
	r := parse(c, "abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラーでした")
	}
	if r.Value != nil {
		t.Fatalf("nil が期待されましたが %v でした", *r.Value)
	}

	r2 := parse(c, "xyz")
	if !r2.OK || r2.Value == nil || *r2.Value != "x" {
		t.Fatalf("'x' が期待されましたが %v でした", r2)
	}
}

func TestRepeat(t *testing.T) {
	c := Repeat(digit(), 1, 0)
	r := parse(c, "123abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラー: %s", r.Err.Message)
	}
	if len(r.Value) != 3 {
		t.Fatalf("3桁が期待されましたが %d 桁でした", len(r.Value))
	}
	if r.Value[0] != "1" || r.Value[1] != "2" || r.Value[2] != "3" {
		t.Fatalf("[1,2,3] が期待されましたが %v でした", r.Value)
	}
}

func TestRepeatWithBounds(t *testing.T) {
	c := Repeat(digit(), 1, 2) // 最低1回、最大2回
	r := parse(c, "123abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラーでした")
	}
	if len(r.Value) != 2 {
		t.Fatalf("2 が期待されましたが %d でした", len(r.Value))
	}
}

func TestRepeatMinFail(t *testing.T) {
	c := Repeat(digit(), 3, 0)
	r := parse(c, "12abc")
	if r.OK {
		t.Fatalf("失敗が期待されました（2桁しかないが3桁必要）")
	}
}

func TestSepBy(t *testing.T) {
	comma := same(",")
	c := SepBy(digit(), comma, 0)

	// 複数要素
	r := parse(c, "1,2,3abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラー: %s", r.Err.Message)
	}
	if len(r.Value) != 3 || r.Value[0] != "1" || r.Value[2] != "3" {
		t.Fatalf("[1,2,3] が期待されましたが %v でした", r.Value)
	}

	// 空入力
	r2 := parse(c, "abc")
	if !r2.OK {
		t.Fatalf("空でも OK が期待されましたがエラーでした")
	}
	if len(r2.Value) != 0 {
		t.Fatalf("[] が期待されましたが %v でした", r2.Value)
	}

	// 要素1つ
	r3 := parse(c, "5abc")
	if !r3.OK || len(r3.Value) != 1 || r3.Value[0] != "5" {
		t.Fatalf("[5] が期待されましたが %v でした", r3)
	}
}

func TestSepByMin(t *testing.T) {
	c := SepBy(digit(), same(","), 2)
	r := parse(c, "1abc")
	if r.OK {
		t.Fatalf("失敗が期待されました（1要素しかないが2要素必要）")
	}
}

func TestLazy(t *testing.T) {
	callCount := 0
	c := Lazy(func() Combinator[Ctx, string] {
		callCount++
		return same("a")
	})

	// 初回呼び出しでファクトリが実行される
	r := parse(c, "abc")
	if !r.OK || r.Value != "a" {
		t.Fatalf("'a' が期待されましたが %v でした", r)
	}
	if callCount != 1 {
		t.Fatalf("ファクトリが1回呼ばれるべきですが %d 回でした", callCount)
	}

	// 2回目はキャッシュを使う
	r2 := parse(c, "abc")
	if !r2.OK {
		t.Fatalf("2回目も OK が期待されました")
	}
	if callCount != 1 {
		t.Fatalf("ファクトリはまだ1回のはずですが %d 回でした", callCount)
	}
}

func TestPeek(t *testing.T) {
	c := Peek(same("a"))
	r := parse(c, "abc")
	if !r.OK || r.Value != "a" {
		t.Fatalf("'a' が期待されましたが %v でした", r)
	}
	// Peek は位置を進めないはず
	if r.Context.Pos != 0 {
		t.Fatalf("pos=0（消費なし）が期待されましたが %d でした", r.Context.Pos)
	}
}

func TestUse(t *testing.T) {
	// 先頭1文字を先読みしてディスパッチする
	c := Use(Peek(any_()), func(ch string) Combinator[Ctx, string] {
		switch ch {
		case "a":
			return keyword("abc")
		case "x":
			return keyword("xyz")
		default:
			return nil
		}
	})

	r := parse(c, "abcdef")
	if !r.OK || r.Value != "abc" {
		t.Fatalf("'abc' が期待されましたが %v でした", r)
	}

	r2 := parse(c, "xyzabc")
	if !r2.OK || r2.Value != "xyz" {
		t.Fatalf("'xyz' が期待されましたが %v でした", r2)
	}

	r3 := parse(c, "qqq")
	if r3.OK {
		t.Fatalf("'qqq' に対して失敗が期待されました")
	}
}

func TestLabel(t *testing.T) {
	c := Label[Ctx, string]("数値が必要です", digit())
	r := parse(c, "abc")
	if r.OK {
		t.Fatalf("失敗が期待されました")
	}
	if r.Err.Message != "数値が必要です" {
		t.Fatalf("カスタムメッセージが期待されましたが '%s' でした", r.Err.Message)
	}
}

func TestChainN(t *testing.T) {
	// same() を Combinator[Ctx, any] にラップする
	a := func(ctx Ctx) Result[Ctx, any] { r := same("a")(ctx); return Result[Ctx, any]{OK: r.OK, Value: r.Value, Err: r.Err, Context: r.Context} }
	b := func(ctx Ctx) Result[Ctx, any] { r := same("b")(ctx); return Result[Ctx, any]{OK: r.OK, Value: r.Value, Err: r.Err, Context: r.Context} }
	c := func(ctx Ctx) Result[Ctx, any] { r := same("c")(ctx); return Result[Ctx, any]{OK: r.OK, Value: r.Value, Err: r.Err, Context: r.Context} }

	p := ChainN[Ctx](a, b, c)
	r := parse(p, "abcde")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラー: %s", r.Err.Message)
	}
	if len(r.Value) != 3 {
		t.Fatalf("3件の結果が期待されましたが %d 件でした", len(r.Value))
	}
	if r.Value[0] != "a" || r.Value[1] != "b" || r.Value[2] != "c" {
		t.Fatalf("[a,b,c] が期待されましたが %v でした", r.Value)
	}
}

func TestOrN(t *testing.T) {
	x := func(ctx Ctx) Result[Ctx, any] { r := same("x")(ctx); return Result[Ctx, any]{OK: r.OK, Value: r.Value, Err: r.Err, Context: r.Context} }
	y := func(ctx Ctx) Result[Ctx, any] { r := same("y")(ctx); return Result[Ctx, any]{OK: r.OK, Value: r.Value, Err: r.Err, Context: r.Context} }
	a := func(ctx Ctx) Result[Ctx, any] { r := same("a")(ctx); return Result[Ctx, any]{OK: r.OK, Value: r.Value, Err: r.Err, Context: r.Context} }

	p := OrN[Ctx](x, y, a)
	r := parse(p, "abc")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラー: %s", r.Err.Message)
	}
	if r.Value != "a" {
		t.Fatalf("'a' が期待されましたが %v でした", r.Value)
	}
}

// ---------------------------------------------------------------------------
// 統合テスト: シンプルな行パーサー（README の例に相当）
// ---------------------------------------------------------------------------

func TestLineParser(t *testing.T) {
	eol := same("\n")
	notEol := Map(
		Chain(Not[Ctx, string](eol), any_()),
		func(p Pair[struct{}, string]) string { return p.Right },
	)
	line := Map(
		Chain(Repeat(notEol, 1, 0), Option(eol)),
		func(p Pair[[]string, *string]) string {
			return strings.Join(p.Left, "")
		},
	)
	lines := Repeat(line, 0, 0)

	r := parse(lines, "line1\nline2\nline3")
	if !r.OK {
		t.Fatalf("OK が期待されましたがエラー: %s", r.Err.Message)
	}
	if len(r.Value) != 3 {
		t.Fatalf("3行が期待されましたが %d 行でした: %v", len(r.Value), r.Value)
	}
	if r.Value[0] != "line1" || r.Value[1] != "line2" || r.Value[2] != "line3" {
		t.Fatalf("[line1, line2, line3] が期待されましたが %v でした", r.Value)
	}
}
