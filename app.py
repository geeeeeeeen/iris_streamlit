import streamlit as st

st.set_page_config(
    page_title="第XX回 学術集会 2026",
    page_icon="🧠",
    layout="wide",
)

st.markdown(
    """
    <style>
        :root {
            --brand-navy: #10233f;
            --brand-blue: #1d4e89;
            --brand-cyan: #2d8fce;
            --brand-gold: #d2a756;
            --text-main: #1a2233;
            --bg-soft: #f7f9fc;
        }

        .stApp {
            background: linear-gradient(180deg, #f3f6fb 0%, #ffffff 40%, #f8fbff 100%);
        }

        .hero {
            position: relative;
            overflow: hidden;
            border-radius: 22px;
            background:
                radial-gradient(circle at 82% 20%, rgba(45, 143, 206, 0.35), transparent 28%),
                radial-gradient(circle at 18% 35%, rgba(210, 167, 86, 0.30), transparent 26%),
                linear-gradient(140deg, #0f2443 0%, #173768 42%, #1f5696 100%);
            color: white;
            padding: 56px 52px;
            box-shadow: 0 14px 34px rgba(16, 35, 63, 0.25);
            margin-bottom: 22px;
        }

        .hero h1 {
            font-size: 2.2rem;
            margin: 0;
            font-weight: 700;
            letter-spacing: .02em;
        }

        .hero .sub {
            margin-top: 12px;
            opacity: 0.92;
            font-size: 1.0rem;
            line-height: 1.8;
            max-width: 62ch;
        }

        .chip {
            display: inline-block;
            margin-top: 16px;
            background: rgba(255,255,255,0.18);
            border: 1px solid rgba(255,255,255,0.24);
            color: #fff;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            margin-right: 8px;
        }

        .section-title {
            margin-top: 8px;
            margin-bottom: 10px;
            color: var(--brand-navy);
            font-size: 1.45rem;
            font-weight: 700;
            letter-spacing: .01em;
        }

        .card {
            background: #ffffff;
            border: 1px solid #e2e9f3;
            border-radius: 16px;
            padding: 20px 18px;
            box-shadow: 0 6px 18px rgba(14, 40, 75, 0.08);
            height: 100%;
        }

        .card h4 {
            margin: 0 0 8px 0;
            color: var(--brand-blue);
            font-size: 1.05rem;
        }

        .event-list {
            background: var(--bg-soft);
            border: 1px solid #d8e4f3;
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 10px;
        }

        .event-date {
            font-weight: 700;
            color: var(--brand-navy);
            font-size: 0.95rem;
        }

        .footer-note {
            margin-top: 24px;
            color: #5d6981;
            font-size: 0.86rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>第XX回 日本○○学会 学術集会 2026</h1>
        <div class="sub">
            先進医療とデータサイエンスをつなぐ、次世代学術プラットフォームへ。<br>
            厳格で信頼性の高い運営を担保しながら、参加者体験を高めるUIへ刷新しました。
        </div>
        <span class="chip">会期: 2026年10月16日(金)–18日(日)</span>
        <span class="chip">会場: ○○コンベンションセンター</span>
        <span class="chip">開催形式: 現地＋オンライン</span>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.4, 1], gap="large")

with left:
    st.markdown('<div class="section-title">開催概要</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(
            """
            <div class="card">
                <h4>会長挨拶</h4>
                学会テーマ「Integrative Intelligence in Medicine」のもと、
                臨床現場で活用可能な研究成果と産学連携を促進します。
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="card">
                <h4>演題募集</h4>
                一般演題、シンポジウム企画、公募ワークショップを受付中。<br>
                採択後はオンデマンド配信にも対応予定です。
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">お知らせ</div>', unsafe_allow_html=True)
    for date, body in [
        ("2026.05.12", "Webサイトをリニューアル公開しました。"),
        ("2026.05.20", "演題登録システムを公開予定です。"),
        ("2026.06.01", "参加登録（早期割引）を開始します。"),
    ]:
        st.markdown(
            f"""
            <div class="event-list">
                <div class="event-date">{date}</div>
                <div>{body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with right:
    st.markdown('<div class="section-title">主要日程</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="card">
            <h4>Important Dates</h4>
            <ul>
                <li><b>演題登録開始:</b> 2026年5月20日</li>
                <li><b>演題登録締切:</b> 2026年7月31日</li>
                <li><b>採択通知:</b> 2026年8月25日</li>
                <li><b>事前参加登録締切:</b> 2026年9月20日</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">お問い合わせ</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="card">
            <h4>運営事務局</h4>
            〒000-0000 東京都○○区○○ 1-2-3<br>
            E-mail: office@example.jp<br>
            TEL: 03-1234-5678
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="footer-note">© 2026 Japanese Society of XXX. All Rights Reserved.</div>', unsafe_allow_html=True)
