"""01.py (combp) vs 02_split.py (str.split) のパフォーマンス比較。"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import importlib.util


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # __main__ ブロックを走らせたくないので書き換え
    spec.loader.exec_module(mod)
    return mod


HERE = Path(__file__).parent


def _load_without_main(name: str, path: Path):
    src = path.read_text(encoding="utf-8")
    src = src.replace('if __name__ == "__main__":', "if False:")
    spec = importlib.util.spec_from_loader(name, loader=None)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


combp_mod = _load_without_main("ex01", HERE / "01.py")
split_mod = _load_without_main("ex02", HERE / "02_split.py")
game_mod  = _load_without_main("ex03", HERE / "03_game.py")


def gen_inputs(n: int) -> list[str]:
    templates = [
        "get_item_name|12345ACB|1001",
        "get_item_name|12345ACB|1002",
        "get_item_detail|12345ACB|1001|item_type",
        "get_enemy_skill|67890DEF|SK001",
        "get_enemy_status|67890DEF|enemy_level",
        "get_enemy_status|67890DEF|enemy_name",
    ]
    rng = random.Random(42)
    return [rng.choice(templates) for _ in range(n)]


def bench(label: str, fn, inputs: list[str], repeat: int = 3) -> float:
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        for s in inputs:
            fn(s)
        dt = time.perf_counter() - t0
        if dt < best:
            best = dt
    print(f"  {label:20s}  {best*1000:10.2f} ms   ({len(inputs)/best:>12,.0f} ops/s)")
    return best


def main():
    # 正当性確認
    sample = "get_item_detail|12345ACB|1001|item_type"
    a = combp_mod.parse_command(sample)
    b = split_mod.parse_command(sample)
    assert (a.enemy_id, a.item_id, a.field) == (b.enemy_id, b.item_id, b.field)
    print("✓ 正当性OK\n")

    for n in (100, 1_000, 100_000, 1_000_000):
        inputs = gen_inputs(n)
        print(f"[N={n:,}]")
        t_combp = bench("combp (use+peek)", combp_mod.parse_command, inputs)
        t_split = bench("str.split",        split_mod.parse_command, inputs)
        # 03 はキャッシュを毎回クリアして純粋なパース性能を測る
        def _game_nocache(s, _fn=game_mod.parse_command):
            _fn.cache_clear()
            return _fn(s)
        t_game  = bench("03 game (no cache)", game_mod.parse_command, inputs)
        game_mod.parse_command.cache_clear()
        print(f"  ratio combp/split = {t_combp/t_split:.1f}x"
              f"   03/split = {t_game/t_split:.2f}x\n")


if __name__ == "__main__":
    main()
