// コンビネータライブラリの型定義。
//
// コンビネータフレームワーク全体で使用されるコア型システムを定義する。
//
// 主要な型パラメータの規約:
//   C: コンテキスト型。パーサーの現在位置や入力ソースを保持するオブジェクト。
//      IHasOffset を実装していれば最遠失敗追跡や無限ループ防止が有効になる。
//   T: パース結果の型。各コンビネータが成功時に返す値の型。

namespace Combp;

// ===========================================================================
// オフセット抽出用インターフェース
// ===========================================================================

/// <summary>
/// Context がオフセット（現在位置）を持つことを示すインターフェース。
/// <para>
/// Or での最遠失敗比較、Repeat / SepBy での無限ループ防止に使用する。
/// コンテキスト型がこのインターフェースを実装していれば、自動的に上記の機能が有効になる。
/// </para>
/// </summary>
public interface IHasOffset
{
    int Offset { get; }
}

// ===========================================================================
// エラー型
// ===========================================================================

/// <summary>
/// コンビネータが失敗したときの構造化エラー情報。
/// </summary>
/// <typeparam name="C">コンテキスト型。失敗地点のコンテキストを保持する。</typeparam>
public sealed class OnError<C>
{
    /// <summary>失敗が発生した時点のコンテキスト。</summary>
    public C On { get; }

    /// <summary>人間が読めるエラーの説明。</summary>
    public string Message { get; }

    /// <summary>
    /// 原因チェーン（子エラー）のリスト。
    /// chain や repeat など、内側のコンビネータの失敗を伝播する際に使用。
    /// </summary>
    public IReadOnlyList<OnError<C>> By { get; }

    /// <summary>
    /// 最も深くまで進んだ失敗。Or / OrN が複数の分岐を試した結果、
    /// 入力を最も先まで消費した失敗を記録する。デバッグ時のエラー特定に有用。
    /// </summary>
    public OnError<C>? Furthest { get; }

    public OnError(C on, string message, IReadOnlyList<OnError<C>>? by = null, OnError<C>? furthest = null)
    {
        On = on;
        Message = message;
        By = by ?? [];
        Furthest = furthest;
    }

    public override string ToString() => Message;
}

// ===========================================================================
// 結果型
// ===========================================================================

/// <summary>
/// コンビネータの実行結果。
/// </summary>
/// <typeparam name="C">コンテキスト型。</typeparam>
/// <typeparam name="T">成功時のパース結果の型。</typeparam>
public sealed class CombinatorResult<C, T>
{
    /// <summary>成功なら true、失敗なら false。</summary>
    public bool Ok { get; }

    /// <summary>
    /// このステップ後の（前に進んだ可能性のある）コンテキスト。
    /// 成功時は消費後の位置、失敗時は失敗発生時点の位置を示す。
    /// </summary>
    public C Context { get; }

    private readonly T? _value;
    private readonly OnError<C>? _error;

    private CombinatorResult(bool ok, C context, T? value, OnError<C>? error)
    {
        Ok = ok;
        Context = context;
        _value = value;
        _error = error;
    }

    /// <summary>成功時の値を返す。失敗時は InvalidOperationException を送出する。</summary>
    public T Value => Ok
        ? _value!
        : throw new InvalidOperationException($"Result is not ok: {_error}");

    /// <summary>失敗時のエラーを返す。成功時は InvalidOperationException を送出する。</summary>
    public OnError<C> Error => !Ok
        ? _error!
        : throw new InvalidOperationException("Result is ok, no error");

    /// <summary>成功した結果を構築する。</summary>
    public static CombinatorResult<C, T> Succeed(C context, T value) =>
        new(true, context, value, null);

    /// <summary>失敗した結果を構築する。</summary>
    public static CombinatorResult<C, T> Fail(C context, OnError<C> error) =>
        new(false, context, default, error);
}

// ===========================================================================
// コンビネータ型
// ===========================================================================

/// <summary>
/// コンビネータの本体。コンテキスト C を受け取り CombinatorResult を返すデリゲート。
/// <para>
/// 小さなコンビネータを Chain, Or, Repeat などで合成し、
/// 複雑なパーサーを宣言的に構築する。
/// </para>
/// </summary>
public delegate CombinatorResult<C, T> Combinator<C, T>(C context);

// ===========================================================================
// 補助型
// ===========================================================================

/// <summary>
/// 2つの値を保持する汎用タプル型。Chain の戻り値で使用する。
/// </summary>
public sealed class Pair<L, R>(L left, R right)
{
    public L Left { get; } = left;
    public R Right { get; } = right;
}

/// <summary>
/// 2つの型のいずれかを保持する直和型。Or の戻り値で使用する。
/// </summary>
public sealed class Either<L, R>
{
    public bool IsLeft { get; }
    public L? LeftValue { get; }
    public R? RightValue { get; }

    private Either(bool isLeft, L? leftValue, R? rightValue)
    {
        IsLeft = isLeft;
        LeftValue = leftValue;
        RightValue = rightValue;
    }

    /// <summary>左の値を構築する。</summary>
    public static Either<L, R> Left(L value) => new(true, value, default);

    /// <summary>右の値を構築する。</summary>
    public static Either<L, R> Right(R value) => new(false, default, value);
}
