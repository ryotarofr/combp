using Xunit;
using Combp;
using static Combp.Comb;
using static Combp.Combinators;

namespace Combp.Tests;

// ---------------------------------------------------------------------------
// テスト用コンテキスト: シンプルな文字列パーサーコンテキスト
// ---------------------------------------------------------------------------

/// <summary>
/// オフセット追跡付きの基本的な文字列パースコンテキスト。
/// </summary>
public sealed class Ctx(string src, int pos) : IHasOffset
{
    public string Src { get; } = src;
    public int Pos { get; } = pos;
    public int Offset => Pos;
}

// ---------------------------------------------------------------------------
// プリミティブパーサー（テスト用ヘルパー）
// ---------------------------------------------------------------------------

public static class Primitives
{
    /// <summary>1文字を消費する。</summary>
    public static Combinator<Ctx, string> Any() =>
        ctx =>
        {
            if (ctx.Pos >= ctx.Src.Length)
                return Err<Ctx, string>(ctx, "any: 入力の終端です");
            var ch = ctx.Src[ctx.Pos].ToString();
            return Ok(new Ctx(ctx.Src, ctx.Pos + 1), ch);
        };

    /// <summary>指定した1文字にマッチする。</summary>
    public static Combinator<Ctx, string> Same(string ch) =>
        ctx =>
        {
            var r = Any()(ctx);
            if (!r.Ok) return r;
            if (r.Value != ch)
                return Err<Ctx, string>(ctx, $"'{ch}' が期待されましたが '{r.Value}' でした");
            return r;
        };

    /// <summary>1桁の数字にマッチする。</summary>
    public static Combinator<Ctx, string> Digit() =>
        ctx =>
        {
            var r = Any()(ctx);
            if (!r.Ok) return r;
            if (r.Value[0] < '0' || r.Value[0] > '9')
                return Err<Ctx, string>(ctx, $"数字が期待されましたが '{r.Value}' でした");
            return r;
        };

    /// <summary>指定した文字列にマッチする。</summary>
    public static Combinator<Ctx, string> Keyword(string word) =>
        ctx =>
        {
            if (ctx.Pos + word.Length > ctx.Src.Length ||
                ctx.Src.Substring(ctx.Pos, word.Length) != word)
                return Err<Ctx, string>(ctx, $"'{word}' が期待されました");
            return Ok(new Ctx(ctx.Src, ctx.Pos + word.Length), word);
        };

    /// <summary>コンビネータに入力文字列を渡して実行する。</summary>
    public static CombinatorResult<Ctx, T> Parse<T>(
        Combinator<Ctx, T> c, string input) =>
        c(new Ctx(input, 0));
}

// ---------------------------------------------------------------------------
// テスト
// ---------------------------------------------------------------------------

public class CombinatorTests
{
    [Fact]
    public void TestAny()
    {
        var r = Primitives.Parse(Primitives.Any(), "abc");
        Assert.True(r.Ok);
        Assert.Equal("a", r.Value);
        Assert.Equal(1, r.Context.Pos);
    }

    [Fact]
    public void TestSame()
    {
        var r = Primitives.Parse(Primitives.Same("a"), "abc");
        Assert.True(r.Ok);
        Assert.Equal("a", r.Value);

        var r2 = Primitives.Parse(Primitives.Same("x"), "abc");
        Assert.False(r2.Ok);
    }

    [Fact]
    public void TestChain()
    {
        var c = Chain(Primitives.Same("a"), Primitives.Same("b"));
        var r = Primitives.Parse(c, "abc");
        Assert.True(r.Ok);
        Assert.Equal("a", r.Value.Left);
        Assert.Equal("b", r.Value.Right);
    }

    [Fact]
    public void TestOr()
    {
        var c = Or(Primitives.Same("x"), Primitives.Same("a"));
        var r = Primitives.Parse(c, "abc");
        Assert.True(r.Ok);
        Assert.False(r.Value.IsLeft);
        Assert.Equal("a", r.Value.RightValue);
    }

    [Fact]
    public void TestOrFurthestFailure()
    {
        // "ab" パーサーは pos=2 で失敗、"x" パーサーは pos=0 で失敗
        var ab = Chain(Primitives.Same("a"), Primitives.Same("x"));
        var xy = Primitives.Same("x");

        var c = Or(
            Map(ab, p => p.Left + p.Right),
            xy);
        var r = Primitives.Parse(c, "abc");
        Assert.False(r.Ok);
        Assert.NotNull(r.Error.Furthest);
        // "ab" 分岐の方が "x" 分岐 (pos=0) より先まで進んだ (pos=1)
        var off = Comb.GetOffset(r.Error.Furthest.On);
        Assert.NotNull(off);
        Assert.Equal(1, off.Value);
    }

    [Fact]
    public void TestConvert()
    {
        var c = Map<Ctx, string, int>(Primitives.Digit(), s => s[0] - '0');
        var r = Primitives.Parse(c, "7abc");
        Assert.True(r.Ok);
        Assert.Equal(7, r.Value);
    }

    [Fact]
    public void TestNot()
    {
        var c = Not<Ctx, string>(Primitives.Same("x"));
        var r = Primitives.Parse(c, "abc");
        Assert.True(r.Ok);
        // コンテキストは進まないはず
        Assert.Equal(0, r.Context.Pos);
    }

    [Fact]
    public void TestOption()
    {
        var c = Option(Primitives.Same("x"));
        var r = Primitives.Parse(c, "abc");
        Assert.True(r.Ok);
        Assert.Null(r.Value);

        var r2 = Primitives.Parse(c, "xyz");
        Assert.True(r2.Ok);
        Assert.Equal("x", r2.Value);
    }

    [Fact]
    public void TestRepeat()
    {
        var c = Repeat(Primitives.Digit(), 1);
        var r = Primitives.Parse(c, "123abc");
        Assert.True(r.Ok);
        Assert.Equal(3, r.Value.Count);
        Assert.Equal("1", r.Value[0]);
        Assert.Equal("2", r.Value[1]);
        Assert.Equal("3", r.Value[2]);
    }

    [Fact]
    public void TestRepeatWithBounds()
    {
        var c = Repeat(Primitives.Digit(), 1, 2); // 最低1回、最大2回
        var r = Primitives.Parse(c, "123abc");
        Assert.True(r.Ok);
        Assert.Equal(2, r.Value.Count);
    }

    [Fact]
    public void TestRepeatMinFail()
    {
        var c = Repeat(Primitives.Digit(), 3);
        var r = Primitives.Parse(c, "12abc");
        Assert.False(r.Ok); // 2桁しかないが3桁必要
    }

    [Fact]
    public void TestSepBy()
    {
        var comma = Primitives.Same(",");
        var c = SepBy(Primitives.Digit(), comma);

        // 複数要素
        var r = Primitives.Parse(c, "1,2,3abc");
        Assert.True(r.Ok);
        Assert.Equal(3, r.Value.Count);
        Assert.Equal("1", r.Value[0]);
        Assert.Equal("3", r.Value[2]);

        // 空入力
        var r2 = Primitives.Parse(c, "abc");
        Assert.True(r2.Ok);
        Assert.Empty(r2.Value);

        // 要素1つ
        var r3 = Primitives.Parse(c, "5abc");
        Assert.True(r3.Ok);
        Assert.Single(r3.Value);
        Assert.Equal("5", r3.Value[0]);
    }

    [Fact]
    public void TestSepByMin()
    {
        var c = SepBy(Primitives.Digit(), Primitives.Same(","), 2);
        var r = Primitives.Parse(c, "1abc");
        Assert.False(r.Ok); // 1要素しかないが2要素必要
    }

    [Fact]
    public void TestLazy()
    {
        var callCount = 0;
        var c = Lazy<Ctx, string>(() =>
        {
            callCount++;
            return Primitives.Same("a");
        });

        // 初回呼び出しでファクトリが実行される
        var r = Primitives.Parse(c, "abc");
        Assert.True(r.Ok);
        Assert.Equal("a", r.Value);
        Assert.Equal(1, callCount);

        // 2回目はキャッシュを使う
        var r2 = Primitives.Parse(c, "abc");
        Assert.True(r2.Ok);
        Assert.Equal(1, callCount);
    }

    [Fact]
    public void TestPeek()
    {
        var c = Peek(Primitives.Same("a"));
        var r = Primitives.Parse(c, "abc");
        Assert.True(r.Ok);
        Assert.Equal("a", r.Value);
        // Peek は位置を進めないはず
        Assert.Equal(0, r.Context.Pos);
    }

    [Fact]
    public void TestUse()
    {
        // 先頭1文字を先読みしてディスパッチする
        var c = Use(Peek(Primitives.Any()), ch => ch switch
        {
            "a" => Primitives.Keyword("abc"),
            "x" => Primitives.Keyword("xyz"),
            _ => null
        });

        var r = Primitives.Parse(c, "abcdef");
        Assert.True(r.Ok);
        Assert.Equal("abc", r.Value);

        var r2 = Primitives.Parse(c, "xyzabc");
        Assert.True(r2.Ok);
        Assert.Equal("xyz", r2.Value);

        var r3 = Primitives.Parse(c, "qqq");
        Assert.False(r3.Ok);
    }

    [Fact]
    public void TestLabel()
    {
        var c = Label<Ctx, string>("数値が必要です", Primitives.Digit());
        var r = Primitives.Parse(c, "abc");
        Assert.False(r.Ok);
        Assert.Equal("数値が必要です", r.Error.Message);
    }

    [Fact]
    public void TestChainN()
    {
        // Same() を Combinator<Ctx, object?> にラップする
        Combinator<Ctx, object?> a = ctx => { var r = Primitives.Same("a")(ctx); return r.Ok ? Ok<Ctx, object?>(r.Context, r.Value) : Err<Ctx, object?>(r.Context, r.Error.Message); };
        Combinator<Ctx, object?> b = ctx => { var r = Primitives.Same("b")(ctx); return r.Ok ? Ok<Ctx, object?>(r.Context, r.Value) : Err<Ctx, object?>(r.Context, r.Error.Message); };
        Combinator<Ctx, object?> c = ctx => { var r = Primitives.Same("c")(ctx); return r.Ok ? Ok<Ctx, object?>(r.Context, r.Value) : Err<Ctx, object?>(r.Context, r.Error.Message); };

        var p = ChainN(a, b, c);
        var r2 = Primitives.Parse(p, "abcde");
        Assert.True(r2.Ok);
        Assert.Equal(3, r2.Value.Length);
        Assert.Equal("a", r2.Value[0]);
        Assert.Equal("b", r2.Value[1]);
        Assert.Equal("c", r2.Value[2]);
    }

    [Fact]
    public void TestOrN()
    {
        Combinator<Ctx, object?> x = ctx => { var r = Primitives.Same("x")(ctx); return r.Ok ? Ok<Ctx, object?>(r.Context, r.Value) : Err<Ctx, object?>(r.Context, r.Error.Message); };
        Combinator<Ctx, object?> y = ctx => { var r = Primitives.Same("y")(ctx); return r.Ok ? Ok<Ctx, object?>(r.Context, r.Value) : Err<Ctx, object?>(r.Context, r.Error.Message); };
        Combinator<Ctx, object?> a = ctx => { var r = Primitives.Same("a")(ctx); return r.Ok ? Ok<Ctx, object?>(r.Context, r.Value) : Err<Ctx, object?>(r.Context, r.Error.Message); };

        var p = OrN(x, y, a);
        var r2 = Primitives.Parse(p, "abc");
        Assert.True(r2.Ok);
        Assert.Equal("a", r2.Value);
    }

    // ---------------------------------------------------------------------------
    // 統合テスト: シンプルな行パーサー（README の例に相当）
    // ---------------------------------------------------------------------------

    [Fact]
    public void TestLineParser()
    {
        var eol = Primitives.Same("\n");
        var notEol = Map(
            Chain(Not<Ctx, string>(eol), Primitives.Any()),
            p => p.Right);
        var line = Map(
            Chain(
                Repeat(notEol, 1),
                Option(eol)),
            p => string.Join("", p.Left));
        var lines = Repeat(line, 0);

        var r = Primitives.Parse(lines, "line1\nline2\nline3");
        Assert.True(r.Ok);
        Assert.Equal(3, r.Value.Count);
        Assert.Equal("line1", r.Value[0]);
        Assert.Equal("line2", r.Value[1]);
        Assert.Equal("line3", r.Value[2]);
    }
}
