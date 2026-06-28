from __future__ import annotations

import hashlib
import random
from pathlib import Path

import pandas as pd


SEED = 737921
N_CASES = 3600
POOLS = ["P0", "P1", "P2", "P3", "P4", "P5"]
TIDE_PHASES = ["ebb", "slack", "flood"]
REEF_ZONES = ["lagoon", "crest", "fore_reef"]
MOON_WINDOWS = ["new_moon", "quarter", "full_moon"]
OPS = ["DRIFT", "SPLICE", "SETTLE", "GRAZE", "MUTATE", "PULSE", "BLEACH", "LIMIT"]


def stable_id(text: str) -> str:
    return "rsp_" + hashlib.sha256(text.encode()).hexdigest()[:14]


def empty_pool() -> dict[str, float]:
    return {"mass": 0.0, "branch": 0.0, "plate": 0.0, "free": 0.0}


def add(pool: dict[str, float], mass: float, branch: float, plate: float, free: float) -> None:
    if mass <= 0:
        return
    old = pool["mass"]
    new = old + mass
    pool["branch"] = (pool["branch"] * old + branch * mass) / new
    pool["plate"] = (pool["plate"] * old + plate * mass) / new
    pool["free"] = (pool["free"] * old + free * mass) / new
    pool["mass"] = new


def take(pool: dict[str, float], mass: float) -> dict[str, float]:
    got = min(max(float(mass), 0.0), pool["mass"])
    out = {"mass": got, "branch": pool["branch"], "plate": pool["plate"], "free": pool["free"]}
    pool["mass"] -= got
    if pool["mass"] <= 1e-9:
        pool.update(empty_pool())
    return out


def spore(kind: str) -> tuple[float, float, float]:
    if kind == "BRANCH":
        return 1.0, 0.05, 0.12
    if kind == "PLATE":
        return 0.06, 1.0, 0.10
    if kind == "FREE":
        return 0.08, 0.07, 1.0
    if kind == "SILT":
        return 0.04, 0.06, 0.55
    raise ValueError(kind)


def execute(state: dict[str, dict[str, float]], op: str) -> None:
    p = op.split()
    cmd = p[0]
    if cmd == "SEED":
        _, pool, kind, mass = p
        add(state[pool], float(mass), *spore(kind))
    elif cmd == "DRIFT":
        _, src, dst, mass, loss = p
        payload = take(state[src], float(mass))
        add(state[dst], payload["mass"] * (1.0 - float(loss)), payload["branch"], payload["plate"], payload["free"])
    elif cmd == "SPLICE":
        _, src, a, b, mass, frac, loss = p
        payload = take(state[src], float(mass))
        delivered = payload["mass"] * (1.0 - float(loss))
        frac = float(frac)
        add(state[a], delivered * frac, payload["branch"], payload["plate"], payload["free"])
        add(state[b], delivered * (1.0 - frac), payload["branch"], payload["plate"], payload["free"])
    elif cmd == "SETTLE":
        _, pool, frac = p
        state[pool]["mass"] *= max(0.0, 1.0 - float(frac))
    elif cmd == "GRAZE":
        _, pool, branch_loss, plate_loss = p
        state[pool]["branch"] *= max(0.0, 1.0 - float(branch_loss))
        state[pool]["plate"] *= max(0.0, 1.0 - float(plate_loss))
    elif cmd == "MUTATE":
        _, pool, bp, pf = p
        bp = float(bp)
        pf = float(pf)
        pool_state = state[pool]
        move_bp = pool_state["branch"] * bp
        move_pf = pool_state["plate"] * pf
        pool_state["branch"] -= move_bp
        pool_state["plate"] = max(0.0, pool_state["plate"] + move_bp - move_pf)
        pool_state["free"] = min(1.0, pool_state["free"] + move_pf)
    elif cmd == "PULSE":
        _, pool, kind, mass, retain = p
        payload = take(state[pool], state[pool]["mass"])
        add(state[pool], payload["mass"] * float(retain), payload["branch"], payload["plate"], payload["free"])
        add(state[pool], float(mass), *spore(kind))
    elif cmd == "BLEACH":
        _, pool, free_gain, branch_decay = p
        state[pool]["free"] = min(1.0, state[pool]["free"] + float(free_gain))
        state[pool]["branch"] *= max(0.0, 1.0 - float(branch_decay))
    elif cmd == "LIMIT":
        _, pool, max_mass = p
        state[pool]["mass"] = min(state[pool]["mass"], float(max_mass))


def context(program: list[str], target_pool: str) -> dict[str, int]:
    counts = {f"count_{op.lower()}": 0 for op in OPS}
    for op in program:
        cmd = op.split()[0]
        if f"count_{cmd.lower()}" in counts:
            counts[f"count_{cmd.lower()}"] += 1
    idx = POOLS.index(target_pool)
    return {
        **counts,
        "target_pool_idx": idx,
        "edge_pool": int(idx in {0, 5}),
        "pulse_heavy": int(counts["count_pulse"] >= 3),
        "bleach_heavy": int(counts["count_bleach"] >= 3),
        "splice_heavy": int(counts["count_splice"] >= 3),
        "graze_heavy": int(counts["count_graze"] >= 3),
    }


def build_case(rng: random.Random, idx: int) -> dict[str, object]:
    tide_phase = rng.choice(TIDE_PHASES)
    reef_zone = rng.choice(REEF_ZONES)
    moon_window = rng.choice(MOON_WINDOWS)
    state = {pool: empty_pool() for pool in POOLS}
    program: list[str] = []
    for pool in rng.sample(POOLS, rng.choice([2, 3, 4])):
        op = f"SEED {pool} {rng.choice(['BRANCH', 'PLATE', 'FREE'])} {rng.choice([7, 11, 15, 22, 30])}"
        program.append(op)
        execute(state, op)
    for _ in range(rng.randint(20, 38)):
        occupied = [pool for pool in POOLS if state[pool]["mass"] > 0.35]
        cmd = rng.choices(OPS, weights=[6, 4, 3, 3, 3, 3, 2, 1])[0]
        if cmd == "DRIFT" and occupied:
            op = f"DRIFT {rng.choice(occupied)} {rng.choice(POOLS)} {rng.choice([3, 5, 8, 12, 16])} {rng.choice([0.00, 0.04, 0.09, 0.14]):.2f}"
        elif cmd == "SPLICE" and occupied:
            a, b = rng.sample(POOLS, 2)
            op = f"SPLICE {rng.choice(occupied)} {a} {b} {rng.choice([6, 10, 14, 20])} {rng.choice([0.25, 0.40, 0.60, 0.75]):.2f} {rng.choice([0.00, 0.05, 0.10]):.2f}"
        elif cmd == "SETTLE" and occupied:
            op = f"SETTLE {rng.choice(occupied)} {rng.choice([0.04, 0.10, 0.18, 0.30]):.2f}"
        elif cmd == "GRAZE":
            op = f"GRAZE {rng.choice(POOLS)} {rng.choice([0.00, 0.05, 0.12, 0.22]):.2f} {rng.choice([0.00, 0.04, 0.10, 0.18]):.2f}"
        elif cmd == "MUTATE":
            op = f"MUTATE {rng.choice(POOLS)} {rng.choice([0.03, 0.07, 0.13, 0.20]):.2f} {rng.choice([0.02, 0.06, 0.11, 0.17]):.2f}"
        elif cmd == "PULSE":
            op = f"PULSE {rng.choice(POOLS)} {rng.choice(['BRANCH', 'PLATE', 'FREE', 'SILT'])} {rng.choice([4, 7, 10, 14])} {rng.choice([0.02, 0.06, 0.12, 0.20]):.2f}"
        elif cmd == "BLEACH":
            op = f"BLEACH {rng.choice(POOLS)} {rng.choice([0.00, 0.04, 0.09, 0.16]):.2f} {rng.choice([0.00, 0.06, 0.13, 0.24]):.2f}"
        else:
            op = f"LIMIT {rng.choice(POOLS)} {rng.choice([18, 26, 36, 52])}"
        program.append(op)
        execute(state, op)

    target_pool = rng.choice(POOLS)
    final = state[target_pool]
    mass = max(0.0, final["mass"])
    denom = max(final["branch"] + final["plate"] + final["free"], 1e-9)
    branch_pct = 100.0 * final["branch"] / denom
    plate_pct = 100.0 * final["plate"] / denom
    free_pct = 100.0 * final["free"] / denom
    feat = context(program, target_pool)

    tide_scale = {"ebb": 0.82, "slack": 1.08, "flood": 1.22}[tide_phase]
    zone_scale = {"lagoon": 1.16, "crest": 0.86, "fore_reef": 0.94}[reef_zone]
    moon_offset = {"new_moon": -2.6, "quarter": 1.1, "full_moon": 3.4}[moon_window]
    mass = max(0.0, mass * tide_scale * zone_scale + moon_offset)
    if feat["pulse_heavy"]:
        mass *= 1.20
    if feat["splice_heavy"]:
        mass *= 0.80
    if feat["edge_pool"] and tide_phase == "ebb":
        mass *= 0.74
    if feat["target_pool_idx"] >= 4 and moon_window == "full_moon":
        mass += 3.2

    tide_comp = {
        "ebb": (1.18, 0.86, 0.96),
        "slack": (0.96, 1.10, 0.96),
        "flood": (0.82, 0.98, 1.28),
    }[tide_phase]
    zone_comp = {
        "lagoon": (0.94, 1.16, 0.96),
        "crest": (1.22, 0.82, 1.02),
        "fore_reef": (0.88, 0.92, 1.30),
    }[reef_zone]
    branch = branch_pct * tide_comp[0] * zone_comp[0]
    plate = plate_pct * tide_comp[1] * zone_comp[1]
    free = free_pct * tide_comp[2] * zone_comp[2]
    if feat["bleach_heavy"]:
        free *= 1.32
        branch *= 0.78
    if feat["graze_heavy"]:
        branch *= 0.84
        plate *= 0.80
        free *= 1.18
    if feat["pulse_heavy"]:
        plate *= 1.12
    if feat["target_pool_idx"] <= 1:
        branch *= 1.15
    if feat["target_pool_idx"] >= 4:
        free *= 1.16
    total = max(branch + plate + free, 1e-9)

    row = {
        "case_id": stable_id(f"{idx}-{'|'.join(program)}-{target_pool}"),
        "target_pool": target_pool,
        "program_text": "; ".join(program),
        "operation_count": len(program),
        "tide_phase": tide_phase,
        "reef_zone": reef_zone,
        "moon_window": moon_window,
        "spore_mass": round(mass, 6),
        "branch_pct": round(100.0 * branch / total, 6),
        "plate_pct": round(100.0 * plate / total, 6),
        "free_pct": round(100.0 * free / total, 6),
    }
    row.update({k: v for k, v in feat.items() if k.startswith("count_")})
    row["operation_bin_private"] = "short" if len(program) < 27 else "medium" if len(program) < 36 else "long"
    row["mass_bin_private"] = "empty" if mass < 1 else "low" if mass < 12 else "mid" if mass < 34 else "high"
    row["structure_private"] = (
        "pulse" if feat["pulse_heavy"] else "bleach" if feat["bleach_heavy"] else "splice" if feat["splice_heavy"] else "ordinary"
    )
    return row


def main() -> None:
    rng = random.Random(SEED)
    df = pd.DataFrame([build_case(rng, i) for i in range(N_CASES)])
    Path("raw").mkdir(exist_ok=True)
    df.to_csv("raw/data.csv", index=False)
    df.to_csv("data.csv", index=False)
    print(f"Wrote {len(df)} rows")


if __name__ == "__main__":
    main()
