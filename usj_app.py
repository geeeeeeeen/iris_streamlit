"""USJ 待ち時間 × 最適散策ルート提案アプリ。

起動:
    streamlit run usj_app.py

待ち時間は queue-times.com の公開APIから取得し、取れない場合は推定値に切り替えます。
どちらを表示しているかは画面上で必ず明示します（推定値を実測のように見せない）。

これはファンメイドの非公式ツールです。USJ公式とは関係ありません。
"""

from __future__ import annotations

import datetime as dt
import html

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from usj.attractions import AREAS, ATTRACTIONS, BY_ID, ENTRANCE
from usj.router import PlanConfig, plan_route
from usj.wait_times import SOURCE_LIVE, load_wait_times, simulate

st.set_page_config(
    page_title="USJ 最適散策ルート",
    page_icon="🎢",
    layout="wide",
)

st.markdown(
    """
    <style>
        :root {
            --usj-ink: #12203a;
            --usj-blue: #1f4f8f;
            --usj-sky: #2f8fd0;
            --usj-coral: #e4572e;
            --usj-sun: #f0a202;
            --usj-line: #dfe7f2;
            --usj-soft: #f5f8fc;
        }

        .stApp {
            background: linear-gradient(180deg, #eef4fb 0%, #ffffff 38%, #f7fbff 100%);
        }

        .usj-hero {
            border-radius: 20px;
            padding: 34px 38px;
            margin-bottom: 18px;
            color: #fff;
            background:
                radial-gradient(circle at 86% 18%, rgba(240, 162, 2, .38), transparent 30%),
                radial-gradient(circle at 12% 82%, rgba(228, 87, 46, .34), transparent 32%),
                linear-gradient(135deg, #10233f 0%, #1c4a86 48%, #2f8fd0 100%);
            box-shadow: 0 14px 30px rgba(16, 35, 63, .24);
        }

        .usj-hero h1 { margin: 0; font-size: 1.95rem; font-weight: 700; }
        .usj-hero p  { margin: 10px 0 0; opacity: .93; line-height: 1.75; max-width: 70ch; }

        .usj-chip {
            display: inline-block;
            margin: 14px 8px 0 0;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: .8rem;
            background: rgba(255,255,255,.18);
            border: 1px solid rgba(255,255,255,.26);
        }

        .usj-section {
            margin: 6px 0 12px;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--usj-ink);
        }

        .usj-step {
            display: flex;
            gap: 16px;
            align-items: stretch;
            background: #fff;
            border: 1px solid var(--usj-line);
            border-left: 5px solid var(--usj-sky);
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 10px;
            box-shadow: 0 5px 14px rgba(14, 40, 75, .07);
        }

        .usj-step.must  { border-left-color: var(--usj-coral); }
        .usj-step.lunch { border-left-color: var(--usj-sun); background: #fffdf5; }

        .usj-time {
            min-width: 92px;
            font-weight: 700;
            color: var(--usj-blue);
            font-size: 1.02rem;
            line-height: 1.5;
        }

        .usj-time small { display: block; font-weight: 500; color: #78859b; font-size: .74rem; }
        .usj-body { flex: 1; }
        .usj-name { font-weight: 700; color: var(--usj-ink); font-size: 1.02rem; }
        .usj-meta { margin-top: 4px; color: #5d6981; font-size: .84rem; }

        .usj-badge {
            display: inline-block;
            margin-left: 8px;
            padding: 2px 9px;
            border-radius: 999px;
            font-size: .72rem;
            font-weight: 700;
            vertical-align: middle;
        }

        .usj-badge.must    { background: #fdece7; color: var(--usj-coral); }
        .usj-badge.express { background: #e8f3fb; color: var(--usj-blue); }
        .usj-badge.show    { background: #f0ecfb; color: #5b46a8; }

        .usj-note {
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 10px;
            font-size: .88rem;
            background: var(--usj-soft);
            border: 1px solid var(--usj-line);
            color: #44506a;
        }

        .usj-foot { margin-top: 26px; color: #6b7689; font-size: .8rem; }

        /* 既定では非表示。スマートフォン幅でのみ出す操作ヒント */
        .usj-hint {
            display: none;
            margin: 0 0 12px;
            padding: 10px 14px;
            border-radius: 12px;
            background: #eef4fb;
            border: 1px solid var(--usj-line);
            color: #3f4c66;
            font-size: .82rem;
        }

        /* ------------------------------------------------------------------
           スマートフォン（iPhone想定）。ヒーローと余白を詰め、
           指標を2×2に折り返して、行程が早く画面に出るようにする。
           ------------------------------------------------------------------ */
        @media (max-width: 640px) {
            section[data-testid="stMain"] .block-container {
                padding: .8rem .7rem 3rem !important;
            }

            .usj-hint { display: block; }

            .usj-hero { padding: 20px 18px; border-radius: 16px; margin-bottom: 12px; }
            .usj-hero h1 { font-size: 1.3rem; line-height: 1.4; }
            .usj-hero p { font-size: .84rem; line-height: 1.65; margin-top: 8px; }
            .usj-chip {
                font-size: .68rem;
                padding: 4px 9px;
                margin: 8px 5px 0 0;
            }

            /* 4つの指標を縦積みではなく2×2にする */
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: .5rem !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                flex: 0 0 calc(50% - .25rem) !important;
                width: calc(50% - .25rem) !important;
                min-width: calc(50% - .25rem) !important;
            }
            div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
            div[data-testid="stMetric"] { padding: 2px 0; }

            /* 行程カードを詰める */
            .usj-step { gap: 10px; padding: 11px 12px; border-radius: 12px; }
            .usj-time { min-width: 58px; font-size: .9rem; }
            .usj-time small { font-size: .67rem; }
            .usj-name { font-size: .92rem; line-height: 1.5; }
            .usj-meta { font-size: .75rem; line-height: 1.65; }
            .usj-section { font-size: 1.06rem; }
            .usj-badge { font-size: .66rem; padding: 2px 7px; margin-left: 6px; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300, show_spinner=False)
def get_wait_times(prefer_live: bool, crowd_level: float, cache_key: int):
    """待ち時間を取得する（5分キャッシュ）。

    `cache_key` は「更新」ボタンでキャッシュを意図的に外すためのダミー引数。
    """
    return load_wait_times(prefer_live=prefer_live, crowd_level=crowd_level)


def format_minutes(total: int) -> str:
    hours, minutes = divmod(int(total), 60)
    return f"{hours}時間{minutes}分" if hours else f"{minutes}分"


# ---------------------------------------------------------------------------
# サイドバー（入力条件）
# ---------------------------------------------------------------------------

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0

with st.sidebar:
    st.header("条件設定")

    st.subheader("データソース")
    prefer_live = st.toggle(
        "実際の待ち時間を取得する",
        value=True,
        help="queue-times.com の公開APIを使います。取得できない環境では自動的に推定値へ切り替わります。",
    )
    crowd_level = st.slider(
        "混雑度（推定時に使用）",
        min_value=0.4,
        max_value=1.6,
        value=1.0,
        step=0.1,
        help="0.4=閑散期、1.0=平常、1.6=繁忙期。推定値を使うときのスケールです。",
    )
    if st.button("最新の待ち時間に更新", width="stretch"):
        st.session_state.refresh_token += 1

    st.divider()
    st.subheader("滞在プラン")
    plan_date = st.date_input("来園日", value=dt.date.today())
    col_a, col_b = st.columns(2)
    with col_a:
        start_time = st.time_input("入園", value=dt.time(9, 0), step=900)
    with col_b:
        end_time = st.time_input("退園", value=dt.time(20, 0), step=900)

    walk_speed = st.slider(
        "歩く速さ（m/分）",
        min_value=50,
        max_value=110,
        value=75,
        step=5,
        help="小さな子ども連れなら遅め、健脚なら速めに。",
    )
    buffer_minutes = st.slider(
        "1件あたりの余裕（分）",
        min_value=0,
        max_value=20,
        value=5,
        help="写真撮影やトイレなど、行程に含めない細かい時間の吸収枠です。",
    )

    st.divider()
    st.subheader("休憩")
    lunch_minutes = st.slider("昼食・休憩（分）", 0, 120, 45, step=15)
    lunch_from = st.time_input("休憩を入れ始める時刻", value=dt.time(12, 0), step=900)

    st.divider()
    st.subheader("優先度")
    popularity_bias = st.slider(
        "方針",
        min_value=1.0,
        max_value=3.0,
        value=2.0,
        step=0.25,
        help="小さいほど「件数を稼ぐ」、大きいほど「目玉アトラクション優先」。",
    )
    st.caption("← たくさん回る　　目玉を優先 →")

    selected_areas = st.multiselect(
        "対象エリア",
        options=list(AREAS),
        default=list(AREAS),
        placeholder="エリアを選択",
    )

    area_filtered = [a for a in ATTRACTIONS if a.area in selected_areas]
    must_see_ids = st.multiselect(
        "必ず乗りたい（最優先）",
        options=[a.id for a in area_filtered],
        format_func=lambda i: BY_ID[i].name,
        placeholder="アトラクションを選択",
        help="ここで選んだものは、多少時間がかかっても優先的に組み込みます。",
    )
    express_ids = st.multiselect(
        "エクスプレス・パスを使う",
        options=[a.id for a in area_filtered if a.express],
        format_func=lambda i: BY_ID[i].name,
        placeholder="アトラクションを選択",
        help="対象アトラクションの待ち時間を大幅に短縮して計算します。",
    )

    return_to_entrance = st.checkbox("最後にエントランスへ戻る", value=True)


# ---------------------------------------------------------------------------
# ヘッダー
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="usj-hero">
        <h1>🎢 USJ 最適散策ルート</h1>
        <p>
            アトラクションの待ち時間を取得し、移動時間・体験時間・時間帯ごとの混み方を
            まとめて考えて、滞在時間内で回りきれる順番を提案します。
        </p>
        <span class="usj-chip">待ち時間の自動取得</span>
        <span class="usj-chip">時間帯別の混雑予測</span>
        <span class="usj-chip">徒歩ルート最適化</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="usj-hint">👈 左上の «&nbsp;»&nbsp;ボタンから、来園時間・必見アトラクションなどの条件を変更できます。</div>',
    unsafe_allow_html=True,
)

start_at = dt.datetime.combine(plan_date, start_time)
end_at = dt.datetime.combine(plan_date, end_time)

if end_at <= start_at:
    st.error("退園時刻は入園時刻より後にしてください。")
    st.stop()

if not area_filtered:
    st.warning("エリアが選択されていません。サイドバーから1つ以上選んでください。")
    st.stop()

snapshot = get_wait_times(prefer_live, crowd_level, st.session_state.refresh_token)

# 計画日が今日でない場合、「現在の待ち時間」を基準にできないので推定に切り替える
if plan_date != dt.date.today():
    snapshot = simulate(
        at=start_at,
        crowd_level=crowd_level,
        seed_note="来園日が今日ではないため、実測値ではなく推定値で計算しています。",
    )

reference_now = snapshot.fetched_at if plan_date == dt.date.today() else start_at
planning_now = max(reference_now, start_at) if plan_date == dt.date.today() else start_at

config = PlanConfig(
    start_at=start_at,
    end_at=end_at,
    candidate_ids=tuple(a.id for a in area_filtered),
    must_see_ids=frozenset(must_see_ids),
    express_ids=frozenset(express_ids),
    walk_speed=float(walk_speed),
    buffer_minutes=int(buffer_minutes),
    lunch_minutes=int(lunch_minutes),
    lunch_from=lunch_from if lunch_minutes else None,
    return_to_entrance=return_to_entrance,
    popularity_bias=float(popularity_bias),
)

itinerary = plan_route(config, snapshot, now=planning_now)

# --- データソースの明示 ---
if snapshot.source == SOURCE_LIVE:
    st.success(
        f"実際の待ち時間を取得しました（{snapshot.fetched_at:%H:%M} 時点・{snapshot.note}）",
        icon="📡",
    )
else:
    st.warning(f"**推定値で表示しています。** {snapshot.note}", icon="⚠️")
    if snapshot.detail:
        with st.expander("取得できなかった理由（技術的な詳細）"):
            st.code(snapshot.detail, language="text")
            st.caption(
                "社内ネットワークやプロキシから queue-times.com へ接続できない場合に起こります。"
                "手元のPCで実行すると取得できることがあります。"
            )

for note in itinerary.notes:
    if "推定値" in note:
        continue  # 上のバナーと重複するため省く
    st.markdown(f'<div class="usj-note">{html.escape(note)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# サマリー
# ---------------------------------------------------------------------------

m1, m2, m3, m4 = st.columns(4)
m1.metric("回れる数", f"{len(itinerary.steps)} 件", f"候補 {len(area_filtered)} 件中")
m2.metric("待ち時間の合計", format_minutes(itinerary.total_wait))
m3.metric("歩く時間の合計", format_minutes(itinerary.total_walk))
m4.metric("終了予定", f"{itinerary.finish_at:%H:%M}", f"退園 {end_at:%H:%M}")

tab_route, tab_waits, tab_map = st.tabs(["🗺 おすすめルート", "⏱ 待ち時間一覧", "📍 マップ"])


# ---------------------------------------------------------------------------
# タブ1: ルート
# ---------------------------------------------------------------------------

with tab_route:
    if not itinerary.steps:
        st.info("この条件では1件も回れません。滞在時間を延ばすか、条件を緩めてください。")
    else:
        st.markdown('<div class="usj-section">行程</div>', unsafe_allow_html=True)

        lunch_rendered = False
        for index, step in enumerate(itinerary.steps, start=1):
            if (
                itinerary.lunch_at
                and not lunch_rendered
                and step.arrive_at >= itinerary.lunch_at
            ):
                st.markdown(
                    f"""
                    <div class="usj-step lunch">
                        <div class="usj-time">{itinerary.lunch_at:%H:%M}<small>休憩</small></div>
                        <div class="usj-body">
                            <div class="usj-name">🍽 昼食・休憩</div>
                            <div class="usj-meta">{itinerary.lunch_minutes}分</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                lunch_rendered = True

            badges = ""
            if step.is_must_see:
                badges += '<span class="usj-badge must">必見</span>'
            if step.uses_express:
                badges += '<span class="usj-badge express">エクスプレス</span>'
            if step.attraction.kind == "show":
                badges += '<span class="usj-badge show">ショー</span>'

            st.markdown(
                f"""
                <div class="usj-step{' must' if step.is_must_see else ''}">
                    <div class="usj-time">{step.arrive_at:%H:%M}<small>〜 {step.depart_at:%H:%M}</small></div>
                    <div class="usj-body">
                        <div class="usj-name">{index}. {html.escape(step.attraction.name)}{badges}</div>
                        <div class="usj-meta">
                            {html.escape(step.attraction.area)}　/　
                            徒歩 {step.walk_from_previous}分　→　待ち {step.wait_minutes}分　→　体験 {step.attraction.ride_minutes}分
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if return_to_entrance and itinerary.return_walk_minutes:
            st.markdown(
                f"""
                <div class="usj-step">
                    <div class="usj-time">{itinerary.finish_at:%H:%M}<small>到着</small></div>
                    <div class="usj-body">
                        <div class="usj-name">🚪 エントランスへ戻る</div>
                        <div class="usj-meta">徒歩 {itinerary.return_walk_minutes}分</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        schedule = pd.DataFrame(
            [
                {
                    "順": i,
                    "時刻": f"{s.arrive_at:%H:%M}",
                    "アトラクション": s.attraction.name,
                    "エリア": s.attraction.area,
                    "徒歩(分)": s.walk_from_previous,
                    "待ち(分)": s.wait_minutes,
                    "体験(分)": s.attraction.ride_minutes,
                    "出発": f"{s.depart_at:%H:%M}",
                }
                for i, s in enumerate(itinerary.steps, start=1)
            ]
        )
        st.download_button(
            "行程をCSVでダウンロード",
            schedule.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"usj_route_{plan_date:%Y%m%d}.csv",
            mime="text/csv",
        )

    if itinerary.skipped:
        with st.expander(f"今回は回らないアトラクション（{len(itinerary.skipped)}件）"):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "アトラクション": a.name,
                            "エリア": a.area,
                            "現在の待ち(分)": snapshot.get(a.id, 0),
                        }
                        for a in itinerary.skipped
                    ]
                ),
                hide_index=True,
                width="stretch",
            )


# ---------------------------------------------------------------------------
# タブ2: 待ち時間一覧
# ---------------------------------------------------------------------------

with tab_waits:
    st.markdown('<div class="usj-section">現在の待ち時間</div>', unsafe_allow_html=True)

    def shorten(name: str, limit: int = 14) -> str:
        """グラフの軸ラベル用に名前を詰める（狭い画面で軸が幅を食うため）。"""
        return name if len(name) <= limit else name[: limit - 1] + "…"

    waits_df = pd.DataFrame(
        [
            {
                "アトラクション": a.name,
                "表示名": shorten(a.name),
                "エリア": a.area,
                "待ち時間(分)": snapshot.get(a.id, 0),
                "体験(分)": a.ride_minutes,
                "ルート入り": "○" if any(s.attraction.id == a.id for s in itinerary.steps) else "",
            }
            for a in area_filtered
        ]
    ).sort_values("待ち時間(分)", ascending=False)

    chart = (
        alt.Chart(waits_df)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("待ち時間(分):Q", title="待ち時間（分）"),
            y=alt.Y("表示名:N", sort="-x", title=None),
            color=alt.Color(
                "エリア:N", legend=alt.Legend(orient="bottom", columns=3, title=None)
            ),
            tooltip=["アトラクション", "エリア", "待ち時間(分)"],
        )
        .properties(height=max(280, 26 * len(waits_df)))
    )
    st.altair_chart(chart, width="stretch")
    st.dataframe(
        waits_df.drop(columns=["表示名"]), hide_index=True, width="stretch"
    )


# ---------------------------------------------------------------------------
# タブ3: マップ
# ---------------------------------------------------------------------------

with tab_map:
    st.markdown('<div class="usj-section">ルートの見取り図</div>', unsafe_allow_html=True)
    st.caption(
        "座標は概算のため、実際の園路や位置関係とは差があります。順番の把握用としてご覧ください。"
    )

    points = pd.DataFrame(
        [
            {
                "name": s.attraction.name,
                "lat": s.attraction.lat,
                "lon": s.attraction.lon,
                "label": str(i),
                "wait": s.wait_minutes,
            }
            for i, s in enumerate(itinerary.steps, start=1)
        ]
    )

    if points.empty:
        st.info("表示できるルートがありません。")
    else:
        path_coords = [[ENTRANCE.lon, ENTRANCE.lat]]
        path_coords += [[s.attraction.lon, s.attraction.lat] for s in itinerary.steps]
        if return_to_entrance:
            path_coords.append([ENTRANCE.lon, ENTRANCE.lat])

        layers = [
            pdk.Layer(
                "PathLayer",
                data=[{"path": path_coords}],
                get_path="path",
                get_color=[47, 143, 208, 190],
                width_min_pixels=4,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=points,
                get_position=["lon", "lat"],
                get_fill_color=[228, 87, 46, 210],
                get_radius=26,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=points,
                get_position=["lon", "lat"],
                get_text="label",
                get_size=15,
                get_color=[255, 255, 255],
                get_alignment_baseline="'center'",
            ),
        ]

        st.pydeck_chart(
            pdk.Deck(
                map_style=None,  # 外部タイルに依存せず描画する
                initial_view_state=pdk.ViewState(
                    latitude=34.6662, longitude=135.4320, zoom=15.2, pitch=0
                ),
                layers=layers,
                tooltip={"text": "{name}\n待ち {wait} 分"},
            ),
            height=420,
        )

st.markdown(
    '<div class="usj-foot">'
    "待ち時間の取得元: queue-times.com（非公式の公開API）。"
    "本アプリはファンメイドの非公式ツールで、ユニバーサル・スタジオ・ジャパンとは関係ありません。"
    "アトラクションのラインナップ・座標・所要時間は概算のシードデータです。"
    "</div>",
    unsafe_allow_html=True,
)
