"""散策ルートの最適化。

解いている問題は「時間依存の orienteering problem（選択的巡回路問題）」です。
制限時間内に全部は回れない前提で、**回る対象と順番の両方**を選びます。

- コスト = 移動時間 + 到着時刻における予測待ち時間 + 体験時間
- 価値   = 優先度（必見指定は大きな加点）
- 目的   = 制限時間を守りつつ価値の合計を最大化する

厳密解は現実的でないので、貪欲法で初期解を作り、局所探索（移動・反転・挿入）で
改善します。ヒューリスティックなので最適解の保証はありません。
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field

from .attractions import ENTRANCE, Attraction, get
from .wait_times import WaitSnapshot, predict_wait

WALK_SPEED_M_PER_MIN = 75.0
# 直線距離に対する実際の園路の遠回り係数
PATH_DETOUR_FACTOR = 1.35
MIN_WALK_MINUTES = 2
MUST_SEE_VALUE = 1000.0
EXPRESS_WAIT_FACTOR = 0.15
# 人気度に対する価値の凸性。大きいほど「目玉優先」、1.0に近いほど「数を稼ぐ」
DEFAULT_POPULARITY_BIAS = 2.0


def attraction_value(
    attraction: Attraction,
    must_see_ids: frozenset[str] = frozenset(),
    popularity_bias: float = DEFAULT_POPULARITY_BIAS,
) -> float:
    """アトラクションを1つ回ることの価値。

    人気度を累乗するのは、待ち時間あたりの価値で比べたときに、
    待ち時間の短い小型アトラクションばかりが選ばれるのを防ぐため。
    指数を上げるほど目玉アトラクションが優先される。
    """
    base = (attraction.popularity**popularity_bias) * 25.0 + 1.0
    if attraction.id in must_see_ids:
        return MUST_SEE_VALUE + base
    return base


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """2点間の大円距離（メートル）。"""
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def walk_minutes(
    origin: Attraction,
    destination: Attraction,
    speed_m_per_min: float = WALK_SPEED_M_PER_MIN,
) -> int:
    """園内の徒歩移動時間（分）。座標が概算なので目安。"""
    if origin.id == destination.id:
        return 0
    meters = haversine_meters(origin.lat, origin.lon, destination.lat, destination.lon)
    minutes = (meters * PATH_DETOUR_FACTOR) / max(speed_m_per_min, 1.0)
    return max(MIN_WALK_MINUTES, int(round(minutes)))


@dataclass
class PlanConfig:
    """ルート探索の入力条件。"""

    start_at: dt.datetime
    end_at: dt.datetime
    candidate_ids: tuple[str, ...]
    must_see_ids: frozenset[str] = frozenset()
    express_ids: frozenset[str] = frozenset()
    walk_speed: float = WALK_SPEED_M_PER_MIN
    buffer_minutes: int = 0
    lunch_minutes: int = 0
    lunch_from: dt.time | None = None
    return_to_entrance: bool = True
    start_id: str = ENTRANCE.id
    popularity_bias: float = DEFAULT_POPULARITY_BIAS

    def value_of(self, attraction: Attraction) -> float:
        """このアトラクションを回る価値。"""
        return attraction_value(attraction, self.must_see_ids, self.popularity_bias)


@dataclass
class ItineraryStep:
    """行程の1ステップ。"""

    attraction: Attraction
    walk_from_previous: int
    arrive_at: dt.datetime
    wait_minutes: int
    board_at: dt.datetime
    depart_at: dt.datetime
    uses_express: bool = False
    is_must_see: bool = False
    value: float = 0.0


@dataclass
class Itinerary:
    """探索結果のルート。"""

    steps: tuple[ItineraryStep, ...]
    skipped: tuple[Attraction, ...]
    finish_at: dt.datetime
    lunch_at: dt.datetime | None = None
    lunch_minutes: int = 0
    return_walk_minutes: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def total_wait(self) -> int:
        return sum(s.wait_minutes for s in self.steps)

    @property
    def total_walk(self) -> int:
        return sum(s.walk_from_previous for s in self.steps) + self.return_walk_minutes

    @property
    def total_ride(self) -> int:
        return sum(s.attraction.ride_minutes for s in self.steps)

    must_see_ids: frozenset[str] = frozenset()

    @property
    def value(self) -> float:
        return sum(s.value for s in self.steps)

    @property
    def missed_must_see(self) -> tuple[Attraction, ...]:
        return tuple(a for a in self.skipped if a.id in self.must_see_ids)


def _simulate(
    order: list[str],
    cfg: PlanConfig,
    snapshot: WaitSnapshot,
    now: dt.datetime,
) -> tuple[list[ItineraryStep], dt.datetime, dt.datetime | None, int, bool]:
    """並び順どおりに回ったときの時刻を積み上げる。

    Returns:
        (steps, finish_at, lunch_at, return_walk, feasible)
    """
    deadline = cfg.end_at
    current = get(cfg.start_id)
    clock = cfg.start_at
    steps: list[ItineraryStep] = []
    lunch_at: dt.datetime | None = None
    lunch_taken = cfg.lunch_minutes <= 0 or cfg.lunch_from is None

    for attraction_id in order:
        attraction = get(attraction_id)
        walk = walk_minutes(current, attraction, cfg.walk_speed)
        arrive = clock + dt.timedelta(minutes=walk)

        # 昼食の時間帯に入っていたら、乗る前に休憩を挟む
        if not lunch_taken and cfg.lunch_from is not None:
            lunch_threshold = dt.datetime.combine(cfg.start_at.date(), cfg.lunch_from)
            if arrive >= lunch_threshold:
                lunch_at = arrive
                arrive += dt.timedelta(minutes=cfg.lunch_minutes)
                lunch_taken = True

        raw_wait = snapshot.get(attraction.id, 0)
        wait = predict_wait(raw_wait, now, arrive)
        uses_express = attraction.id in cfg.express_ids and attraction.express
        if uses_express:
            wait = int(round(wait * EXPRESS_WAIT_FACTOR))

        board = arrive + dt.timedelta(minutes=wait)
        depart = board + dt.timedelta(
            minutes=attraction.ride_minutes + cfg.buffer_minutes
        )

        steps.append(
            ItineraryStep(
                attraction=attraction,
                walk_from_previous=walk,
                arrive_at=arrive,
                wait_minutes=wait,
                board_at=board,
                depart_at=depart,
                uses_express=uses_express,
                is_must_see=attraction.id in cfg.must_see_ids,
                value=cfg.value_of(attraction),
            )
        )
        clock = depart
        current = attraction

    return_walk = 0
    if cfg.return_to_entrance and steps:
        return_walk = walk_minutes(current, get(cfg.start_id), cfg.walk_speed)
        clock += dt.timedelta(minutes=return_walk)

    return steps, clock, lunch_at, return_walk, clock <= deadline


def _order_value(order: list[str], cfg: PlanConfig) -> float:
    return sum(cfg.value_of(get(i)) for i in order)


def plan_route(
    cfg: PlanConfig,
    snapshot: WaitSnapshot,
    now: dt.datetime | None = None,
    max_passes: int = 6,
) -> Itinerary:
    """制限時間内で価値が最大になるルートを組み立てる。"""
    now = now or snapshot.fetched_at
    candidates = [i for i in cfg.candidate_ids if i != cfg.start_id]

    # --- 1. 貪欲法で初期ルートを作る ---
    order: list[str] = []
    remaining = list(candidates)

    while remaining:
        best_id = None
        best_score = -1.0
        for attraction_id in remaining:
            trial = order + [attraction_id]
            steps, finish, _, _, feasible = _simulate(trial, cfg, snapshot, now)
            if not feasible:
                continue
            last = steps[-1]
            cost = (
                last.walk_from_previous
                + last.wait_minutes
                + last.attraction.ride_minutes
                + cfg.buffer_minutes
            )
            score = cfg.value_of(get(attraction_id)) / max(cost, 1)
            if score > best_score:
                best_score, best_id = score, attraction_id
        if best_id is None:
            break
        order.append(best_id)
        remaining.remove(best_id)

    # --- 2. 局所探索で並び順を改善する ---
    def evaluate(seq: list[str]) -> tuple[bool, float, dt.datetime]:
        _, finish, _, _, feasible = _simulate(seq, cfg, snapshot, now)
        return feasible, _order_value(seq, cfg), finish

    improved = True
    passes = 0
    while improved and passes < max_passes:
        improved = False
        passes += 1
        base_ok, base_value, base_finish = evaluate(order)

        # 2-opt: 区間を反転して交差した経路をほどく
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                trial = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
                ok, value, finish = evaluate(trial)
                if ok and (value > base_value or (value == base_value and finish < base_finish)):
                    order, base_value, base_finish, base_ok = trial, value, finish, ok
                    improved = True

        # Or-opt: 1つ抜き出して別の位置に差し込む
        for i in range(len(order)):
            for j in range(len(order)):
                if i == j:
                    continue
                trial = order[:i] + order[i + 1 :]
                trial.insert(j, order[i])
                ok, value, finish = evaluate(trial)
                if ok and (value > base_value or (value == base_value and finish < base_finish)):
                    order, base_value, base_finish, base_ok = trial, value, finish, ok
                    improved = True

        # 余った時間に未訪問を差し込めないか試す
        for attraction_id in list(remaining):
            inserted = False
            for pos in range(len(order) + 1):
                trial = order[:pos] + [attraction_id] + order[pos:]
                ok, value, finish = evaluate(trial)
                if ok and value > base_value:
                    order, base_value, base_finish = trial, value, finish
                    remaining.remove(attraction_id)
                    improved = inserted = True
                    break
            if inserted:
                continue

    steps, finish, lunch_at, return_walk, feasible = _simulate(order, cfg, snapshot, now)
    skipped = tuple(get(i) for i in candidates if i not in order)

    notes: list[str] = []
    if snapshot.degraded:
        notes.append("待ち時間は推定値です。実際の運営状況とは異なります。")
    missed = [a for a in skipped if a.id in cfg.must_see_ids]
    if missed:
        names = "、".join(a.name for a in missed)
        notes.append(f"時間内に収まらず、必見指定を外したものがあります: {names}")
    if not feasible and steps:
        notes.append("終了予定時刻を超過しています。条件を緩めてください。")

    itinerary = Itinerary(
        steps=tuple(steps),
        skipped=skipped,
        finish_at=finish,
        lunch_at=lunch_at,
        lunch_minutes=cfg.lunch_minutes if lunch_at else 0,
        return_walk_minutes=return_walk,
        notes=tuple(notes),
        must_see_ids=cfg.must_see_ids,
    )
    return itinerary
