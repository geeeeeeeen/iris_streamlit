"""USJのアトラクション定義（シードデータ）。

座標・所要時間は公開情報をもとにした**概算値**です。園内の実測値ではないため、
歩行時間の見積もりは目安として扱ってください。ラインナップは変更されるので、
このファイルを編集して最新の状態に保つ運用を想定しています。

`aliases` は queue-times.com などの英語名APIとの突き合わせに使います。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Attraction:
    """1つのアトラクション。

    Attributes:
        id: 内部ID（安定させること。設定の保存キーに使う）
        name: 日本語表示名
        area: パーク内エリア名
        lat, lon: 概算座標（歩行時間の推定に使用）
        ride_minutes: 乗車・鑑賞そのものにかかる時間（待ち時間は含まない）
        popularity: 0.0-1.0。混雑予測と優先度のヒントに使う
        kind: "ride"（乗り物） / "show"（ショー）
        express: エクスプレス・パス対象になり得るか
        aliases: 英語名など、外部APIとの名寄せ用の別名
    """

    id: str
    name: str
    area: str
    lat: float
    lon: float
    ride_minutes: int
    popularity: float
    kind: str = "ride"
    express: bool = True
    aliases: tuple[str, ...] = field(default_factory=tuple)


# パーク入口（ルートの起点・終点の既定値）
ENTRANCE = Attraction(
    id="entrance",
    name="パークエントランス",
    area="エントランス",
    lat=34.6636,
    lon=135.4344,
    ride_minutes=0,
    popularity=0.0,
    kind="gate",
    express=False,
)


ATTRACTIONS: tuple[Attraction, ...] = (
    # --- ハリウッド・エリア ---
    Attraction(
        id="hollywood_dream",
        name="ハリウッド・ドリーム・ザ・ライド",
        area="ハリウッド・エリア",
        lat=34.6643,
        lon=135.4338,
        ride_minutes=3,
        popularity=0.80,
        aliases=("Hollywood Dream The Ride",),
    ),
    Attraction(
        id="backdrop",
        name="ハリウッド・ドリーム・ザ・ライド 〜バックドロップ〜",
        area="ハリウッド・エリア",
        lat=34.6645,
        lon=135.4340,
        ride_minutes=3,
        popularity=0.78,
        aliases=("Hollywood Dream The Ride Backdrop", "Backdrop"),
    ),
    Attraction(
        id="space_fantasy",
        name="スペース・ファンタジー・ザ・ライド",
        area="ハリウッド・エリア",
        lat=34.6647,
        lon=135.4334,
        ride_minutes=4,
        popularity=0.70,
        aliases=("Space Fantasy The Ride",),
    ),
    Attraction(
        id="sing_on_tour",
        name="シング・オン・ツアー",
        area="ハリウッド・エリア",
        lat=34.6646,
        lon=135.4342,
        ride_minutes=20,
        popularity=0.45,
        kind="show",
        express=False,
        aliases=("Sing on Tour",),
    ),
    # --- サンフランシスコ・エリア ---
    Attraction(
        id="backdraft",
        name="バックドラフト",
        area="サンフランシスコ・エリア",
        lat=34.6656,
        lon=135.4326,
        ride_minutes=15,
        popularity=0.35,
        kind="show",
        aliases=("Backdraft",),
    ),
    # --- ジュラシック・パーク ---
    Attraction(
        id="jurassic_ride",
        name="ジュラシック・パーク・ザ・ライド",
        area="ジュラシック・パーク",
        lat=34.6660,
        lon=135.4302,
        ride_minutes=8,
        popularity=0.72,
        aliases=("Jurassic Park The Ride",),
    ),
    Attraction(
        id="flying_dinosaur",
        name="ザ・フライング・ダイナソー",
        area="ジュラシック・パーク",
        lat=34.6665,
        lon=135.4296,
        ride_minutes=3,
        popularity=0.92,
        aliases=("The Flying Dinosaur", "Flying Dinosaur"),
    ),
    # --- アミティ・ヴィレッジ ---
    Attraction(
        id="jaws",
        name="ジョーズ",
        area="アミティ・ヴィレッジ",
        lat=34.6669,
        lon=135.4312,
        ride_minutes=7,
        popularity=0.60,
        aliases=("Jaws",),
    ),
    # --- ウォーターワールド ---
    Attraction(
        id="waterworld",
        name="ウォーターワールド",
        area="ウォーターワールド",
        lat=34.6663,
        lon=135.4318,
        ride_minutes=25,
        popularity=0.65,
        kind="show",
        aliases=("WaterWorld", "Water World"),
    ),
    # --- ウィザーディング・ワールド・オブ・ハリー・ポッター ---
    Attraction(
        id="forbidden_journey",
        name="ハリー・ポッター・アンド・ザ・フォービドゥン・ジャーニー",
        area="ウィザーディング・ワールド・オブ・ハリー・ポッター",
        lat=34.6679,
        lon=135.4299,
        ride_minutes=5,
        popularity=0.88,
        aliases=(
            "Harry Potter and the Forbidden Journey",
            "Forbidden Journey",
        ),
    ),
    Attraction(
        id="hippogriff",
        name="フライト・オブ・ザ・ヒッポグリフ",
        area="ウィザーディング・ワールド・オブ・ハリー・ポッター",
        lat=34.6676,
        lon=135.4294,
        ride_minutes=2,
        popularity=0.62,
        aliases=("Flight of the Hippogriff",),
    ),
    # --- ミニオン・パーク ---
    Attraction(
        id="minion_mayhem",
        name="ミニオン・ハチャメチャ・ライド",
        area="ミニオン・パーク",
        lat=34.6668,
        lon=135.4336,
        ride_minutes=5,
        popularity=0.82,
        aliases=("Despicable Me Minion Mayhem", "Minion Mayhem"),
    ),
    Attraction(
        id="freeze_ray",
        name="ミニオン・ハチャメチャ・アイス",
        area="ミニオン・パーク",
        lat=34.6670,
        lon=135.4333,
        ride_minutes=3,
        popularity=0.55,
        aliases=("Freeze Ray Sliders", "Minion Freeze Ray Sliders"),
    ),
    # --- SUPER NINTENDO WORLD ---
    Attraction(
        id="mario_kart",
        name="マリオカート 〜クッパの挑戦状〜",
        area="SUPER NINTENDO WORLD",
        lat=34.6682,
        lon=135.4320,
        ride_minutes=5,
        popularity=0.95,
        aliases=("Mario Kart: Koopa's Challenge", "Mario Kart"),
    ),
    Attraction(
        id="yoshi_adventure",
        name="ヨッシー・アドベンチャー",
        area="SUPER NINTENDO WORLD",
        lat=34.6684,
        lon=135.4316,
        ride_minutes=5,
        popularity=0.68,
        aliases=("Yoshi's Adventure",),
    ),
    # --- ユニバーサル・ワンダーランド ---
    Attraction(
        id="elmo_skateboard",
        name="エルモのゴーゴー・スケートボード",
        area="ユニバーサル・ワンダーランド",
        lat=34.6660,
        lon=135.4342,
        ride_minutes=2,
        popularity=0.40,
        aliases=("Elmo's Go-Go Skateboard",),
    ),
    Attraction(
        id="flying_snoopy",
        name="フライング・スヌーピー",
        area="ユニバーサル・ワンダーランド",
        lat=34.6658,
        lon=135.4345,
        ride_minutes=2,
        popularity=0.38,
        aliases=("Flying Snoopy",),
    ),
)


BY_ID: dict[str, Attraction] = {a.id: a for a in ATTRACTIONS}

AREAS: tuple[str, ...] = tuple(dict.fromkeys(a.area for a in ATTRACTIONS))


def get(attraction_id: str) -> Attraction:
    """IDからアトラクションを引く。エントランスも解決できる。"""
    if attraction_id == ENTRANCE.id:
        return ENTRANCE
    return BY_ID[attraction_id]
