// 汎用パーサーコンビネータ関数群。
//
// Combinator<C, T> は「コンテキスト C を受け取り、成功（値 T + 次のコンテキスト）
// または失敗（エラー情報）を返す関数」として表現される。
// 小さなコンビネータを Chain, Or, Repeat などで合成し、
// 複雑なパーサーを宣言的に構築できる。

using static Combp.Comb;

namespace Combp;

/// <summary>
/// パーサーコンビネータ関数を提供する静的クラス。
/// <c>using static Combp.Combinators;</c> でインポートして直接呼び出せる。
/// </summary>
public static class Combinators
{
    // ===========================================================================
    // Chain: 順次合成
    // ===========================================================================

    /// <summary>
    /// 2つのコンビネータを順に実行し、結果を <see cref="Pair{L,R}"/> で返す。
    /// <para>lhs が成功した場合、その更新されたコンテキストから rhs を実行する。
    /// どちらかが失敗した時点でそのエラーをそのまま返す。</para>
    /// </summary>
    public static Combinator<C, Pair<L, R>> Chain<C, L, R>(
        Combinator<C, L> lhs, Combinator<C, R> rhs) =>
        ctx =>
        {
            var lr = lhs(ctx);
            if (!lr.Ok)
                return PropagateErr<C, Pair<L, R>>(lr.Context, lr.Error);
            var rr = rhs(lr.Context);
            if (!rr.Ok)
                return PropagateErr<C, Pair<L, R>>(rr.Context, rr.Error);
            return Ok<C, Pair<L, R>>(rr.Context, new Pair<L, R>(lr.Value, rr.Value));
        };

    /// <summary>
    /// 一連のコンビネータを順に実行し、結果を <c>object?[]</c> で返す。
    /// <para>いずれかが失敗した時点でそのエラーを返す。
    /// 型安全に2個を連結するには <see cref="Chain{C,L,R}"/> を使うこと。</para>
    /// </summary>
    public static Combinator<C, object?[]> ChainN<C>(
        params Combinator<C, object?>[] combinators) =>
        ctx =>
        {
            var results = new List<object?>(combinators.Length);
            var current = ctx;
            foreach (var c in combinators)
            {
                var r = c(current);
                if (!r.Ok)
                    return PropagateErr<C, object?[]>(r.Context, r.Error);
                results.Add(r.Value);
                current = r.Context;
            }
            return Ok<C, object?[]>(current, [.. results]);
        };

    /// <summary>
    /// コンビネータを順に実行し、最初（左端）の結果のみを返す。
    /// <para>2番目以降のコンビネータは実行されるが、その結果は捨てられる。
    /// トークン後の空白スキップなどに便利。</para>
    /// </summary>
    public static Combinator<C, T> ChainL<C, T, TRest>(
        Combinator<C, T> first, params Combinator<C, TRest>[] rest) =>
        ctx =>
        {
            var fr = first(ctx);
            if (!fr.Ok)
                return fr;
            var current = fr.Context;
            foreach (var c in rest)
            {
                var r = c(current);
                if (!r.Ok)
                    return PropagateErr<C, T>(r.Context, r.Error);
                current = r.Context;
            }
            return Ok(current, fr.Value);
        };

    /// <summary>
    /// コンビネータを順に実行し、最後（右端）の結果のみを返す。
    /// <para>最後以外のコンビネータは実行されるが、その結果は捨てられる。
    /// プレフィクスやデリミタを読み飛ばしてから本体を取得する場合に便利。</para>
    /// </summary>
    public static Combinator<C, T> ChainR<C, TSkip, T>(
        Combinator<C, TSkip>[] skips, Combinator<C, T> last) =>
        ctx =>
        {
            var current = ctx;
            foreach (var c in skips)
            {
                var r = c(current);
                if (!r.Ok)
                    return PropagateErr<C, T>(r.Context, r.Error);
                current = r.Context;
            }
            var lr = last(current);
            if (!lr.Ok)
                return lr;
            return Ok(lr.Context, lr.Value);
        };

    // ===========================================================================
    // Or: 二者択一・N者択一
    // ===========================================================================

    /// <summary>
    /// lhs を先に試し、失敗したら rhs を試す（二者択一）。
    /// <para>両方失敗した場合、入力をより先まで消費した分岐のエラーを Furthest として
    /// 記録する。これにより「どの分岐が最も惜しかったか」を把握できる。</para>
    /// </summary>
    public static Combinator<C, Either<L, R>> Or<C, L, R>(
        Combinator<C, L> lhs, Combinator<C, R> rhs) =>
        ctx =>
        {
            var lr = lhs(ctx);
            if (lr.Ok)
                return Ok<C, Either<L, R>>(lr.Context, Either<L, R>.Left(lr.Value));
            var rr = rhs(ctx);
            if (rr.Ok)
                return Ok<C, Either<L, R>>(rr.Context, Either<L, R>.Right(rr.Value));
            var furthest = DeeperError(lr.Error, rr.Error);
            return ErrWithFurthest<C, Either<L, R>>(ctx, "or", furthest, lr.Error, rr.Error);
        };

    /// <summary>
    /// 各コンビネータを順に試し、最初に成功したものを返す。
    /// <para>全て失敗した場合、最遠失敗（Furthest）を追跡して返す。</para>
    /// </summary>
    public static Combinator<C, object?> OrN<C>(
        params Combinator<C, object?>[] combinators) =>
        ctx =>
        {
            var errs = new List<OnError<C>>();
            foreach (var c in combinators)
            {
                var r = c(ctx);
                if (r.Ok)
                    return Ok<C, object?>(r.Context, r.Value);
                errs.Add(r.Error);
            }
            if (errs.Count > 0)
            {
                var furthest = errs[0];
                for (var i = 1; i < errs.Count; i++)
                    furthest = DeeperError(furthest, errs[i]);
                return ErrWithFurthest<C, object?>(ctx, "or", furthest, [.. errs]);
            }
            return Err<C, object?>(ctx, "orN: コンビネータが指定されていません");
        };

    // ===========================================================================
    // Repeat: 繰り返し
    // ===========================================================================

    /// <summary>
    /// コンビネータを繰り返し実行し、結果をリストに収集する。
    /// <para>正規表現の {must,to} に相当する。
    /// コンテキストが <see cref="IHasOffset"/> を実装している場合、
    /// 入力が進まない繰り返しを検知して無限ループを防止する。</para>
    /// </summary>
    /// <param name="c">繰り返し実行するコンビネータ。</param>
    /// <param name="must">必要な最低マッチ回数。0 で空リストでも成功。</param>
    /// <param name="to">最大マッチ回数。0 以下で無制限。</param>
    public static Combinator<C, IReadOnlyList<T>> Repeat<C, T>(
        Combinator<C, T> c, int must, int to = 0) =>
        ctx =>
        {
            if (must < 0)
                throw new ArgumentException(
                    $"Repeat: must ({must}) は 0 以上でなければなりません");
            if (to > 0 && to < must)
                throw new ArgumentException(
                    $"Repeat: to ({to}) は must ({must}) 以上でなければなりません");

            var results = new List<T>();
            var current = ctx;
            OnError<C>? lastErr = null;

            while (to <= 0 || results.Count < to)
            {
                var r = c(current);
                if (!r.Ok)
                {
                    lastErr = r.Error;
                    break;
                }
                var before = GetOffset(current);
                var after = GetOffset(r.Context);
                if (before is not null && after is not null && before == after)
                    break;
                results.Add(r.Value);
                current = r.Context;
            }

            if (results.Count < must)
            {
                var by = lastErr is not null ? [lastErr] : Array.Empty<OnError<C>>();
                return Err<C, IReadOnlyList<T>>(ctx,
                    $"repeat(): {must} 回以上の繰り返しが必要です。", by);
            }
            return Ok<C, IReadOnlyList<T>>(current, results);
        };

    // ===========================================================================
    // SepBy: 区切り文字で区切られたリスト
    // ===========================================================================

    /// <summary>
    /// 区切り文字で区切られた0個以上の要素をパースする。
    /// <para>element (separator element)* のパターンにマッチし、
    /// separator の結果は捨てて element の結果のみをリストに収集する。</para>
    /// </summary>
    /// <param name="element">各要素をパースするコンビネータ。</param>
    /// <param name="separator">要素間の区切りをパースするコンビネータ。</param>
    /// <param name="min">必要な最低要素数。0 なら空リストでも成功。</param>
    public static Combinator<C, IReadOnlyList<T>> SepBy<C, T, S>(
        Combinator<C, T> element, Combinator<C, S> separator, int min = 0) =>
        ctx =>
        {
            var results = new List<T>();
            var current = ctx;
            OnError<C>? lastErr = null;

            var fr = element(current);
            if (!fr.Ok)
            {
                if (min > 0)
                    return Err<C, IReadOnlyList<T>>(ctx,
                        $"sepBy(): 最低 {min} 個の要素が必要です。", fr.Error);
                return Ok<C, IReadOnlyList<T>>(ctx, results);
            }
            results.Add(fr.Value);
            current = fr.Context;

            while (true)
            {
                var beforeOff = GetOffset(current);

                var sr = separator(current);
                if (!sr.Ok) break;

                var er = element(sr.Context);
                if (!er.Ok)
                {
                    lastErr = er.Error;
                    break;
                }

                var afterOff = GetOffset(er.Context);
                if (beforeOff is not null && afterOff is not null && beforeOff == afterOff)
                    break;

                results.Add(er.Value);
                current = er.Context;
            }

            if (results.Count < min)
            {
                var by = lastErr is not null ? [lastErr] : Array.Empty<OnError<C>>();
                return Err<C, IReadOnlyList<T>>(ctx,
                    $"sepBy(): 最低 {min} 個の要素が必要ですが、{results.Count} 個しかありません。",
                    by);
            }
            return Ok<C, IReadOnlyList<T>>(current, results);
        };

    // ===========================================================================
    // Convert / Map: 結果の変換
    // ===========================================================================

    /// <summary>
    /// 成功結果を変換関数で別の型に写す。
    /// <para>内側のコンビネータが成功した場合、その値とコンテキストを f に渡して変換する。</para>
    /// </summary>
    public static Combinator<C, B> Convert<C, A, B>(
        Combinator<C, A> c, Func<A, C, B> f) =>
        ctx =>
        {
            var r = c(ctx);
            if (!r.Ok)
                return PropagateErr<C, B>(r.Context, r.Error);
            return Ok(r.Context, f(r.Value, r.Context));
        };

    /// <summary>
    /// Convert の簡易版。コンテキストを無視して値だけを変換する。
    /// </summary>
    public static Combinator<C, B> Map<C, A, B>(
        Combinator<C, A> c, Func<A, B> f) =>
        Convert(c, (a, _) => f(a));

    // ===========================================================================
    // Lazy: 遅延構築
    // ===========================================================================

    /// <summary>
    /// コンビネータの構築を遅延させ、循環参照を回避する。
    /// <para>ファクトリ関数は最初の呼び出し時に1回だけ実行され、以降はキャッシュを使用する。
    /// スレッドセーフ（<see cref="System.Lazy{T}"/> を内部で使用）。</para>
    /// </summary>
    public static Combinator<C, T> Lazy<C, T>(Func<Combinator<C, T>> factory)
    {
        var lazy = new Lazy<Combinator<C, T>>(factory);
        return ctx => lazy.Value(ctx);
    }

    // ===========================================================================
    // Option: 省略可能
    // ===========================================================================

    /// <summary>
    /// コンビネータを試し、失敗した場合はエラーなしで default を返す。
    /// <para>正規表現の ? に相当する。失敗時にコンテキストは進まない。</para>
    /// </summary>
    public static Combinator<C, T?> Option<C, T>(Combinator<C, T> c) =>
        ctx =>
        {
            var r = c(ctx);
            if (r.Ok)
                return Ok<C, T?>(r.Context, r.Value);
            return Ok<C, T?>(ctx, default);
        };

    // ===========================================================================
    // Not: 否定先読み
    // ===========================================================================

    /// <summary>
    /// 否定先読み。内側のコンビネータが失敗したら成功、成功したら失敗する。
    /// <para>入力は消費しない。</para>
    /// </summary>
    public static Combinator<C, bool> Not<C, T>(Combinator<C, T> c) =>
        ctx =>
        {
            var r = c(ctx);
            if (r.Ok)
                return Err<C, bool>(ctx, $"not: {r.Value} にマッチすべきではありません");
            return Ok(ctx, true);
        };

    // ===========================================================================
    // Peek: 先読み
    // ===========================================================================

    /// <summary>
    /// 先読み。コンビネータを実行するが入力を消費しない。
    /// <para>成功時はコンテキストを元に戻し、失敗した場合はそのままエラーを返す。</para>
    /// </summary>
    public static Combinator<C, T> Peek<C, T>(Combinator<C, T> c) =>
        ctx =>
        {
            var r = c(ctx);
            if (!r.Ok) return r;
            return Ok(ctx, r.Value);
        };

    // ===========================================================================
    // Use: 動的ディスパッチ
    // ===========================================================================

    /// <summary>
    /// from を実行し、その結果に基づいてセレクタ関数で次のコンビネータを動的に選択する。
    /// <para>セレクタが null を返した場合、コンビネータは失敗する。</para>
    /// </summary>
    public static Combinator<C, T> Use<C, M, T>(
        Combinator<C, M> from, Func<M, Combinator<C, T>?> selector) =>
        ctx =>
        {
            var fr = from(ctx);
            if (!fr.Ok)
                return PropagateErr<C, T>(fr.Context, fr.Error);
            var next = selector(fr.Value);
            if (next is null)
                return Err<C, T>(ctx,
                    $"use: セレクタが {fr.Value} に対して null を返しました");
            return next(fr.Context);
        };

    // ===========================================================================
    // Label: エラーメッセージ上書き
    // ===========================================================================

    /// <summary>
    /// 内側のコンビネータが失敗したとき、エラーメッセージを上書きする。
    /// <para>内部エラーの By チェーンは保持されるため、
    /// デバッグ情報を失わずにユーザー向けのメッセージを改善できる。</para>
    /// </summary>
    public static Combinator<C, T> Label<C, T>(string message, Combinator<C, T> c) =>
        ctx =>
        {
            var r = c(ctx);
            if (r.Ok) return r;
            return Err<C, T>(ctx, message, [.. r.Error.By]);
        };
}
