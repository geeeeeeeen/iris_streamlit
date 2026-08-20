"""待ち時間の取得。

データソースは2系統あります。

1. **ライブ取得** (`fetch_live`): queue-times.com の公開APIから実際の待ち時間を取る。
2. **シミュレーション** (`simulate`): ネットワークが使えない場合の代替。
   混雑度と時間帯カーブからもっともらしい待ち時間を生成する。

`load_wait_times()` はライブを試し、失敗したらシミュレーションに落ちます。
どちらを使ったかは `WaitSnapshot.source` と `degraded` で必ず判別できるので、
UIは「本物の値か推定値か」を利用者に隠さないこと。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from .attractions import ATTRACTIONS, Attraction

QUEUE_TIMES_PARKS_URL = "https://queue-times.com/parks.json"
QUEUE_TIMES_QUEUE_URL = "https://queue-times.com/parks/{park_id}/queue_times.json"

SOURCE_LIVE = "live"
SOURCE_SIMULATED = "simulated"

# 時間帯ごとの相対的な混み方。1.0 = その日の平均的な水準。
_DEMAND_CURVE: tuple[tuple[float, float], ...] = (
    (8.0, 0.35),
    (9.0, 0.55),
    (10.0, 0.85),
    (11.0, 1.00),
    (12.0, 1.05),
    (13.0, 1.10),
    (14.0, 1.05),
    (15.0, 1.00),
    (16.0, 0.90),
    (17.0, 0.80),
    (18.0, 0.70),
    (19.0, 0.60),
    (20.0, 0.50),
    (21.0, 0.40),
    (22.0, 0.30),
)

MAX_WAIT_MINUTES = 240


@dataclass
class WaitSnapshot:
    """ある時刻の待ち時間スナップショット。"""

    waits: dict[str, int]
    source: str
    fetched_at: dt.datetime
    note: str = ""
    detail: str = ""
    unmatched: tuple[str, ...] = field(default_factory=tuple)

    @property
    def degraded(self) -> bool:
        """実データではなく推定値かどうか。"""
        return self.source != SOURCE_LIVE

    def get(self, attraction_id: str, default: int = 0) -> int:
        return self.waits.get(attraction_id, default)


def demand_factor(when: dt.time | dt.datetime) -> float:
    """時間帯による混雑係数を線形補間で返す。"""
    if isinstance(when, dt.datetime):
        when = when.time()
    hour = when.hour + when.minute / 60.0
    points = _DEMAND_CURVE
    if hour <= points[0][0]:
        return points[0][1]
    if hour >= points[-1][0]:
        return points[-1][1]
    for (h0, v0), (h1, v1) in zip(points, points[1:]):
        if h0 <= hour <= h1:
            ratio = (hour - h0) / (h1 - h0)
            return v0 + (v1 - v0) * ratio
    return 1.0


def _normalize(name: str) -> str:
    """名寄せ用にゆるく正規化する。"""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _match_attraction(api_name: str) -> Attraction | None:
    """APIが返した名前を内部のアトラクションに突き合わせる。"""
    target = _normalize(api_name)
    if not target:
        return None
    for attraction in ATTRACTIONS:
        candidates = (attraction.name, *attraction.aliases)
        for candidate in candidates:
            norm = _normalize(candidate)
            if not norm:
                continue
            if norm == target or norm in target or target in norm:
                return attraction
    return None


def fetch_live(timeout: float = 10.0) -> WaitSnapshot:
    """queue-times.com から実際の待ち時間を取得する。

    ネットワークやAPI形式の問題は例外として送出する。呼び出し側で
    `load_wait_times` のようにフォールバックすること。
    """
    import requests  # 遅延インポート：オフラインでもモジュールを読めるように

    parks = requests.get(QUEUE_TIMES_PARKS_URL, timeout=timeout)
    parks.raise_for_status()

    park_id = None
    for group in parks.json():
        for park in group.get("parks", []):
            if "universal studios japan" in park.get("name", "").lower():
                park_id = park["id"]
                break
        if park_id is not None:
            break
    if park_id is None:
        raise LookupError("queue-times.com のパーク一覧にUSJが見つかりません")

    response = requests.get(
        QUEUE_TIMES_QUEUE_URL.format(park_id=park_id), timeout=timeout
    )
    response.raise_for_status()
    payload = response.json()

    rides: list[dict] = list(payload.get("rides", []))
    for land in payload.get("lands", []):
        rides.extend(land.get("rides", []))

    waits: dict[str, int] = {}
    unmatched: list[str] = []
    for ride in rides:
        attraction = _match_attraction(ride.get("name", ""))
        if attraction is None:
            unmatched.append(ride.get("name", ""))
            continue
        # 閉鎖中は待ち時間0で返ってくるので、運営状況を見て除外する
        if not ride.get("is_open", True):
            continue
        waits[attraction.id] = int(ride.get("wait_time", 0) or 0)

    if not waits:
        raise LookupError("APIの応答を既知のアトラクションに紐付けられませんでした")

    return WaitSnapshot(
        waits=waits,
        source=SOURCE_LIVE,
        fetched_at=dt.datetime.now(),
        note=f"queue-times.com（park_id={park_id}）から取得",
        unmatched=tuple(unmatched),
    )


def simulate(
    at: dt.datetime | None = None,
    crowd_level: float = 1.0,
    seed_note: str = "",
    detail: str = "",
) -> WaitSnapshot:
    """混雑度と時間帯から待ち時間を推定する（オフライン用）。

    Args:
        at: 基準時刻。省略時は現在時刻。
        crowd_level: 0.4（閑散）〜1.6（激混み）程度を想定した倍率。
        seed_note: 生成メモに添える説明。

    同じ日・同じ時刻・同じ混雑度なら同じ値になります（再実行でぶれない）。
    """
    at = at or dt.datetime.now()
    factor = demand_factor(at)
    waits: dict[str, int] = {}

    for attraction in ATTRACTIONS:
        # 人気度を強調しつつ、時間帯と混雑度でスケールする
        base = (attraction.popularity**1.6) * 130.0
        value = base * factor * crowd_level
        if attraction.kind == "show":
            # ショーは上演時刻待ちなので、行列そのものは短めに扱う
            value *= 0.5
        # 日付とIDから決まる小さなゆらぎ（±12%）を足して均質さを崩す
        jitter_seed = hash((attraction.id, at.date().isoformat(), int(crowd_level * 10)))
        jitter = ((jitter_seed % 25) - 12) / 100.0
        value *= 1.0 + jitter
        waits[attraction.id] = max(0, min(MAX_WAIT_MINUTES, int(round(value / 5.0) * 5)))

    note = seed_note or "混雑度と時間帯から推定した値です。"
    return WaitSnapshot(
        waits=waits,
        source=SOURCE_SIMULATED,
        fetched_at=at,
        note=note,
        detail=detail,
    )


def load_wait_times(
    prefer_live: bool = True,
    crowd_level: float = 1.0,
    at: dt.datetime | None = None,
) -> WaitSnapshot:
    """ライブ取得を試し、だめならシミュレーションに切り替える。

    どちらに転んでも必ず `WaitSnapshot` が返るので、UI側は分岐せずに描画でき、
    `degraded` を見て注意書きを出せばよい。
    """
    if prefer_live:
        try:
            return fetch_live()
        except Exception as exc:  # ネットワーク・API形式のあらゆる失敗を含む
            # 技術的な理由は detail に隔離する。画面の主文はあくまで
            # 「実測ではなく推定である」ことを伝えるためのもの。
            return simulate(
                at=at,
                crowd_level=crowd_level,
                seed_note="待ち時間を取得できなかったため、推定値を表示しています。",
                detail=f"{type(exc).__name__}: {exc}",
            )
    return simulate(at=at, crowd_level=crowd_level)


def predict_wait(
    current_wait: int,
    now: dt.datetime,
    arrival: dt.datetime,
) -> int:
    """現在の待ち時間から、到着時刻の待ち時間を予測する。

    時間帯カーブの比で伸縮させるだけの素朴なモデル。個別の運営状況までは
    織り込まないので、あくまで並び順を決めるためのシグナルとして使う。
    """
    now_factor = demand_factor(now)
    if now_factor <= 0:
        return current_wait
    scaled = current_wait * (demand_factor(arrival) / now_factor)
    return max(0, min(MAX_WAIT_MINUTES, int(round(scaled))))
