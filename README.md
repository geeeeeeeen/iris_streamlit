# USJ 最適散策ルート

ユニバーサル・スタジオ・ジャパンのアトラクション待ち時間を取得し、
**制限時間内で回りきれる順番**を提案する Streamlit アプリです。

> ファンメイドの非公式ツールです。USJ公式とは関係ありません。

## できること

- **待ち時間の取得** — queue-times.com の公開APIから取得。取得できない環境では
  混雑度と時間帯にもとづく推定値に自動で切り替わります（画面上で必ず区別して表示）。
- **ルート最適化** — 移動時間・待ち時間・体験時間を積み上げ、閉園時刻を超えない範囲で
  「回る対象」と「順番」の両方を選びます。
- **時間帯を考慮** — 待ち時間は一日を通して変動します。朝は目玉から、夕方は空いてきた
  ものへ、といった組み替えを自動で行います。
- **条件のカスタマイズ** — 必見指定、エクスプレス・パス、昼休憩、歩く速さ、対象エリア、
  「たくさん回る ↔ 目玉優先」の方針スライダー。

## 使い方

```bash
pip install -r requirements.txt
streamlit run usj_app.py
```

ブラウザで http://localhost:8501 が開きます。

## テスト

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -q
```

## Webに公開する（iPhoneから使う）

スマートフォン表示に対応済みです。以下の手順で、iPhoneのSafariから使えるURLを発行できます。

### Streamlit Community Cloud（無料・おすすめ）

1. <https://share.streamlit.io> にGitHubアカウントでサインインします。
2. **Create app** →（既存リポジトリを選ぶ）で以下を指定します。

   | 項目 | 値 |
   | --- | --- |
   | Repository | `geeeeeeeen/iris_streamlit` |
   | Branch | アプリのコードが入っているブランチ |
   | Main file path | `usj_app.py` |

3. **Deploy** を押すと `https://<任意の名前>.streamlit.app` が発行されます。

> **ブランチに注意。** `main` にはまだアプリのコードがありません。デプロイ時は
> コードのあるブランチを選ぶか、先に `main` へマージしてください。

依存関係は `requirements.txt` から自動でインストールされます（`pytest` は
`requirements-dev.txt` に分けてあるので、デプロイ先には入りません）。

### iPhoneのホーム画面に追加する

1. Safariで発行されたURLを開きます。
2. 共有ボタン → **ホーム画面に追加**。
3. アプリのように全画面で起動できるようになります。

### 知っておくべき制約

- **無音でスリープします。** Community Cloud の無料枠はしばらくアクセスがないと
  アプリが停止し、次回アクセス時の起動に30秒ほどかかります。
- **リポジトリが公開なので、アプリも公開されます。** 誰でもURLを知っていれば開けます。
- 待ち時間の取得元（queue-times.com）にデプロイ先から接続できる必要があります。
  接続できない場合でもアプリは止まらず、推定値に切り替わります。

### 同じWi-Fiのスマホから手元のPCを見る場合

公開せずに試すだけなら、PCで次を実行し、表示されたNetwork URLをスマホで開きます。

```bash
streamlit run usj_app.py --server.address 0.0.0.0
```

### そのほかの選択肢

Hugging Face Spaces、Render、Google Cloud Run などでも動きます。いずれも
`requirements.txt` と `streamlit run usj_app.py` があれば構成できます。

## 構成

| パス | 役割 |
| --- | --- |
| `usj_app.py` | Streamlit のUI（画面とウィジェット） |
| `usj/attractions.py` | アトラクションのシードデータ（座標・所要時間・人気度） |
| `usj/wait_times.py` | 待ち時間の取得（ライブAPI / 推定）と時間帯モデル |
| `usj/router.py` | ルート最適化（時間依存 orienteering problem） |
| `tests/test_usj.py` | テスト |

## 精度についての注意

- アトラクションの**座標・所要時間は概算**です。園内の実測値ではないため、徒歩時間は目安です。
- 待ち時間の予測は「時間帯カーブの比で伸縮させる」素朴なモデルです。個別の運休・入場制限・
  イベントは考慮していません。
- ラインナップは変わります。`usj/attractions.py` を編集して最新の状態に保つ運用を想定しています。
- 最適化はヒューリスティック（貪欲法＋局所探索）で、**最適解を保証しません**。
