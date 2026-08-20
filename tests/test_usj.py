"""usjパッケージのテスト。

重視しているのは「制限時間を破らない」「必見を落とさない」といった、
壊れても画面上は一見それらしく見えてしまう不変条件です。
"""

from __future__ import annotations

import datetime as dt

import pytest

from usj.attractions import ATTRACTIONS, BY_ID, ENTRANCE, get
from usj.router import (
    EXPRESS_WAIT_FACTOR,
    PlanConfig,
    attraction_value,
    plan_route,
    walk_minutes,
)
from usj.wait_times import (
    MAX_WAIT_MINUTES,
    _match_attraction,
    demand_factor,
    predict_wait,
    simulate,
)

OPEN_AT = dt.datetime(2026, 8, 20, 9, 0)
CLOSE_AT = dt.datetime(2026, 8, 20, 20, 0)
ALL_IDS = tuple(a.id for a in ATTRACTIONS)


def make_config(**overrides) -> PlanConfig:
    params = dict(
        start_at=OPEN_AT,
        end_at=CLOSE_AT,
        candidate_ids=ALL_IDS,
    )
    params.update(overrides)
    return PlanConfig(**params)


# --------------------------------------------------------------------------
# データセット
# --------------------------------------------------------------------------


def test_attraction_ids_are_unique():
    ids = [a.id for a in ATTRACTIONS]
    assert len(ids) == len(set(ids))


def test_entrance_is_resolvable_but_not_a_candidate():
    assert get(ENTRANCE.id) is ENTRANCE
    assert ENTRANCE.id not in BY_ID


# --------------------------------------------------------------------------
# 徒歩時間
# --------------------------------------------------------------------------


def test_walk_time_is_zero_for_same_place():
    assert walk_minutes(BY_ID["jaws"], BY_ID["jaws"]) == 0


def test_walk_time_is_symmetric():
    a, b = BY_ID["mario_kart"], BY_ID["hollywood_dream"]
    assert walk_minutes(a, b) == walk_minutes(b, a)


def test_walk_time_respects_minimum():
    """隣接するアトラクション同士でも下限を割り込まない。"""
    assert walk_minutes(BY_ID["mario_kart"], BY_ID["yoshi_adventure"]) >= 2


def test_walking_faster_never_takes_longer():
    a, b = BY_ID["flying_dinosaur"], BY_ID["elmo_skateboard"]
    assert walk_minutes(a, b, speed_m_per_min=120) <= walk_minutes(a, b, speed_m_per_min=60)


# --------------------------------------------------------------------------
# 待ち時間モデル
# --------------------------------------------------------------------------


def test_simulation_is_deterministic():
    first = simulate(at=OPEN_AT, crowd_level=1.0)
    second = simulate(at=OPEN_AT, crowd_level=1.0)
    assert first.waits == second.waits


def test_simulation_is_flagged_as_estimated():
    assert simulate(at=OPEN_AT).degraded is True


def test_crowd_level_increases_waits():
    quiet = simulate(at=OPEN_AT, crowd_level=0.5)
    busy = simulate(at=OPEN_AT, crowd_level=1.5)
    assert sum(busy.waits.values()) > sum(quiet.waits.values())


def test_waits_stay_within_bounds():
    snapshot = simulate(at=dt.datetime(2026, 8, 20, 13, 0), crowd_level=1.6)
    assert all(0 <= w <= MAX_WAIT_MINUTES for w in snapshot.waits.values())


def test_popular_attractions_wait_longer():
    snapshot = simulate(at=dt.datetime(2026, 8, 20, 13, 0))
    assert snapshot.get("mario_kart") > snapshot.get("flying_snoopy")


def test_demand_peaks_midday_and_falls_at_night():
    assert demand_factor(dt.time(13, 0)) > demand_factor(dt.time(9, 0))
    assert demand_factor(dt.time(13, 0)) > demand_factor(dt.time(20, 0))


def test_prediction_shrinks_toward_closing():
    now = dt.datetime(2026, 8, 20, 13, 0)
    evening = predict_wait(120, now, dt.datetime(2026, 8, 20, 20, 0))
    assert evening < 120


def test_prediction_at_same_time_is_unchanged():
    now = dt.datetime(2026, 8, 20, 13, 0)
    assert predict_wait(90, now, now) == 90


@pytest.mark.parametrize(
    ("api_name", "expected_id"),
    [
        ("The Flying Dinosaur", "flying_dinosaur"),
        ("Harry Potter and the Forbidden Journey", "forbidden_journey"),
        ("Mario Kart: Koopa's Challenge", "mario_kart"),
        ("Despicable Me Minion Mayhem", "minion_mayhem"),
    ],
)
def test_english_api_names_match_japanese_attractions(api_name, expected_id):
    matched = _match_attraction(api_name)
    assert matched is not None and matched.id == expected_id


def test_unknown_api_name_does_not_match():
    assert _match_attraction("Space Mountain") is None


# --------------------------------------------------------------------------
# ルート最適化
# --------------------------------------------------------------------------


def test_route_never_exceeds_the_deadline():
    """一番大事な不変条件：閉園時刻を超える行程を返さない。"""
    snapshot = simulate(at=OPEN_AT)
    itinerary = plan_route(make_config(), snapshot, now=OPEN_AT)
    assert itinerary.finish_at <= CLOSE_AT
    for step in itinerary.steps:
        assert step.depart_at <= CLOSE_AT


def test_route_times_are_monotonic():
    snapshot = simulate(at=OPEN_AT)
    itinerary = plan_route(make_config(), snapshot, now=OPEN_AT)
    for step in itinerary.steps:
        assert step.arrive_at <= step.board_at <= step.depart_at
    for previous, following in zip(itinerary.steps, itinerary.steps[1:]):
        assert previous.depart_at <= following.arrive_at


def test_no_attraction_is_visited_twice():
    snapshot = simulate(at=OPEN_AT)
    itinerary = plan_route(make_config(), snapshot, now=OPEN_AT)
    visited = [s.attraction.id for s in itinerary.steps]
    assert len(visited) == len(set(visited))


def test_visited_and_skipped_partition_the_candidates():
    snapshot = simulate(at=OPEN_AT)
    itinerary = plan_route(make_config(), snapshot, now=OPEN_AT)
    visited = {s.attraction.id for s in itinerary.steps}
    skipped = {a.id for a in itinerary.skipped}
    assert visited.isdisjoint(skipped)
    assert visited | skipped == set(ALL_IDS)


def test_must_see_attractions_are_scheduled_when_time_allows():
    snapshot = simulate(at=OPEN_AT)
    must = frozenset({"mario_kart", "flying_dinosaur", "forbidden_journey"})
    itinerary = plan_route(make_config(must_see_ids=must), snapshot, now=OPEN_AT)
    visited = {s.attraction.id for s in itinerary.steps}
    assert must <= visited
    assert itinerary.missed_must_see == ()


def test_short_window_returns_a_short_but_valid_route():
    snapshot = simulate(at=OPEN_AT)
    config = make_config(end_at=OPEN_AT + dt.timedelta(minutes=90))
    itinerary = plan_route(config, snapshot, now=OPEN_AT)
    assert itinerary.finish_at <= config.end_at
    assert len(itinerary.steps) < len(ALL_IDS)


def test_impossible_window_yields_empty_route_without_crashing():
    snapshot = simulate(at=OPEN_AT)
    config = make_config(end_at=OPEN_AT + dt.timedelta(minutes=1))
    itinerary = plan_route(config, snapshot, now=OPEN_AT)
    assert itinerary.steps == ()
    assert len(itinerary.skipped) == len(ALL_IDS)


def test_more_time_never_means_less_value():
    snapshot = simulate(at=OPEN_AT)
    short = plan_route(
        make_config(end_at=OPEN_AT + dt.timedelta(hours=4)), snapshot, now=OPEN_AT
    )
    long = plan_route(
        make_config(end_at=OPEN_AT + dt.timedelta(hours=11)), snapshot, now=OPEN_AT
    )
    assert long.value >= short.value


def test_express_pass_shortens_the_wait():
    """候補を1件に絞り、到着時刻を揃えた上で比較する。

    候補を絞らないと、待ちが短くなった分だけ最適化が別の時間帯に組み替えてしまい、
    待ち時間の絶対値どうしを比べても意味がなくなる。
    """
    snapshot = simulate(at=OPEN_AT)
    single = dict(candidate_ids=("mario_kart",))
    without = plan_route(make_config(**single), snapshot, now=OPEN_AT)
    with_express = plan_route(
        make_config(express_ids=frozenset({"mario_kart"}), **single),
        snapshot,
        now=OPEN_AT,
    )
    plain = without.steps[0]
    express = with_express.steps[0]
    assert plain.arrive_at == express.arrive_at
    assert express.uses_express is True
    assert plain.uses_express is False
    assert express.wait_minutes <= plain.wait_minutes * EXPRESS_WAIT_FACTOR + 1


def test_express_pass_is_ignored_for_non_express_attractions():
    """エクスプレス対象外のアトラクションに指定しても割り引かれない。"""
    snapshot = simulate(at=OPEN_AT)
    itinerary = plan_route(
        make_config(
            candidate_ids=("sing_on_tour",),
            express_ids=frozenset({"sing_on_tour"}),
        ),
        snapshot,
        now=OPEN_AT,
    )
    assert itinerary.steps[0].uses_express is False


def test_lunch_break_is_inserted_once():
    snapshot = simulate(at=OPEN_AT)
    config = make_config(lunch_minutes=60, lunch_from=dt.time(12, 0))
    itinerary = plan_route(config, snapshot, now=OPEN_AT)
    assert itinerary.lunch_at is not None
    assert itinerary.lunch_minutes == 60
    assert itinerary.lunch_at.hour >= 12


def test_returning_to_the_entrance_costs_walking_time():
    snapshot = simulate(at=OPEN_AT)
    itinerary = plan_route(make_config(return_to_entrance=True), snapshot, now=OPEN_AT)
    assert itinerary.return_walk_minutes > 0
    one_way = plan_route(make_config(return_to_entrance=False), snapshot, now=OPEN_AT)
    assert one_way.return_walk_minutes == 0


def test_estimated_data_is_called_out_in_the_notes():
    itinerary = plan_route(make_config(), simulate(at=OPEN_AT), now=OPEN_AT)
    assert any("推定値" in note for note in itinerary.notes)


# --------------------------------------------------------------------------
# 価値関数
# --------------------------------------------------------------------------


def test_must_see_dominates_ordinary_value():
    ride = BY_ID["flying_snoopy"]
    assert attraction_value(ride, frozenset({ride.id})) > attraction_value(
        BY_ID["mario_kart"], frozenset()
    )


def test_higher_bias_favours_headliners():
    """人気度の指数を上げるほど、目玉と小型の価値差が開く。"""
    headliner, small = BY_ID["mario_kart"], BY_ID["flying_snoopy"]
    low = attraction_value(headliner, popularity_bias=1.0) / attraction_value(
        small, popularity_bias=1.0
    )
    high = attraction_value(headliner, popularity_bias=3.0) / attraction_value(
        small, popularity_bias=3.0
    )
    assert high > low


# --------------------------------------------------------------------------
# データソースの切り替え
# --------------------------------------------------------------------------


def test_offline_mode_never_touches_the_network(monkeypatch):
    """prefer_live=False ならライブ取得を呼ばない。"""
    import usj.wait_times as wt

    def explode(*args, **kwargs):  # pragma: no cover - 呼ばれたら失敗
        raise AssertionError("fetch_live が呼ばれてはいけない")

    monkeypatch.setattr(wt, "fetch_live", explode)
    snapshot = wt.load_wait_times(prefer_live=False, at=OPEN_AT)
    assert snapshot.source == "simulated"


def test_live_failure_falls_back_to_estimates(monkeypatch):
    """APIが落ちていてもアプリが止まらず、推定値で継続する。"""
    import usj.wait_times as wt

    def boom(*args, **kwargs):
        raise ConnectionError("network unreachable")

    monkeypatch.setattr(wt, "fetch_live", boom)
    snapshot = wt.load_wait_times(prefer_live=True, at=OPEN_AT)
    assert snapshot.degraded is True
    assert snapshot.waits, "フォールバックしても待ち時間は埋まっているべき"


def test_failure_detail_is_kept_out_of_the_headline_message(monkeypatch):
    """例外の文字列を利用者向けの主文に混ぜない（detailに隔離する）。"""
    import usj.wait_times as wt

    def boom(*args, **kwargs):
        raise ConnectionError("network unreachable")

    monkeypatch.setattr(wt, "fetch_live", boom)
    snapshot = wt.load_wait_times(prefer_live=True, at=OPEN_AT)
    assert "ConnectionError" not in snapshot.note
    assert "ConnectionError" in snapshot.detail
