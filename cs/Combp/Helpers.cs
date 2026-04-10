// コンビネータの結果構築・オフセット抽出ヘルパー。

namespace Combp;

/// <summary>
/// CombinatorResult の構築やオフセット操作のためのヘルパー関数群。
/// </summary>
public static class Comb
{
    // ===========================================================================
    // 結果コンストラクタ
    // ===========================================================================

    /// <summary>
    /// 成功した結果を構築する。
    /// </summary>
    /// <param name="context">パース成功後のコンテキスト（消費後の位置）。</param>
    /// <param name="value">パースされた値。</param>
    public static CombinatorResult<C, T> Ok<C, T>(C context, T value) =>
        CombinatorResult<C, T>.Succeed(context, value);

    /// <summary>
    /// 失敗した結果を構築する。
    /// </summary>
    /// <param name="context">失敗が発生した時点のコンテキスト。</param>
    /// <param name="message">エラーメッセージ。</param>
    /// <param name="by">原因となった子エラーのリスト。</param>
    public static CombinatorResult<C, T> Err<C, T>(
        C context, string message, params OnError<C>[] by) =>
        CombinatorResult<C, T>.Fail(context,
            new OnError<C>(context, message, by.Length > 0 ? by : null));

    /// <summary>
    /// 最遠到達点の情報付きで失敗した結果を構築する。
    /// </summary>
    /// <param name="context">失敗が発生した時点のコンテキスト。</param>
    /// <param name="message">エラーメッセージ。</param>
    /// <param name="furthest">最遠到達点のエラー情報。Or 系コンビネータで使用。</param>
    /// <param name="by">原因となった子エラーのリスト。</param>
    public static CombinatorResult<C, T> ErrWithFurthest<C, T>(
        C context, string message, OnError<C> furthest, params OnError<C>[] by) =>
        CombinatorResult<C, T>.Fail(context,
            new OnError<C>(context, message, by.Length > 0 ? by : null, furthest));

    // ===========================================================================
    // オフセット抽出
    // ===========================================================================

    /// <summary>
    /// Context からオフセット値を安全に取り出す。
    /// IHasOffset を実装していれば offset を返し、なければ null を返す。
    /// </summary>
    public static int? GetOffset<C>(C ctx) =>
        ctx is IHasOffset o ? o.Offset : null;

    /// <summary>
    /// 2つの OnError のうち、入力のより先まで進んだ（offset が大きい）方を返す。
    /// <para>
    /// Or / OrN で複数の分岐が失敗した際に、最も有用なエラーを選択するために使用する。
    /// offset が取得できない場合は lhs を優先する。
    /// </para>
    /// </summary>
    public static OnError<C> DeeperError<C>(OnError<C> lhs, OnError<C> rhs)
    {
        var lo = GetOffset(lhs.On);
        var ro = GetOffset(rhs.On);
        if (lo is null || ro is null) return lhs;
        return ro > lo ? rhs : lhs;
    }

    /// <summary>
    /// OnError の furthest 情報を保持してエラーを伝播するヘルパー。
    /// chain 系コンビネータで内側の失敗をそのまま返す際に使用する。
    /// </summary>
    internal static CombinatorResult<C, T> PropagateErr<C, T>(C context, OnError<C> e) =>
        e.Furthest is not null
            ? ErrWithFurthest<C, T>(context, e.Message, e.Furthest, [.. e.By])
            : CombinatorResult<C, T>.Fail(context,
                new OnError<C>(context, e.Message, e.By));
}
