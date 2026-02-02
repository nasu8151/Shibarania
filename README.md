# Shibarania

Google Tasks と同期するシンプルなタスクボードアプリです。2カラム（現在/完了）表示とドラッグ&ドロップ操作で、タスクを直感的に管理できます。

![Block Diagram](block.svg)

## 主な機能

- 「現在のタスク」「完了済みのタスク」の2カラム表示
- ドラッグ&ドロップでタスク移動（完了/完了取り消し）
- Google Tasks と双方向同期
- 起動時と60秒ごとの自動同期
- 完了済みは「最新2件のみ」表示
- 完了時ポップアップ表示（画像＋メッセージ＋ねぎらい）
- フルスクリーン時は自動で文字サイズ/余白を縮小して収まり優先

## セットアップ

> 事前に Google Cloud Console で Google Tasks API を有効化し、OAuth クライアント（デスクトップアプリ）を作成して `credentials.json` を取得してください。

1) 仮想環境作成

```powershell
python -m venv env
```

2) 仮想環境を有効化

```powershell
.\env\Scripts\Activate.ps1
```

3) 依存関係をインストール

```powershell
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib PyQt6
```

4) `credentials.json` をプロジェクト直下に配置

- ルートに置きます（例: README と同じ階層）。
- `token.json` は初回認可時に自動生成されます。

## 起動方法

通常起動:

```powershell
python .\main.py
```

フルスクリーン起動:

```powershell
python .\main.py --fullscreen
```

## 使い方

- 左（現在のタスク）→右（完了済みのタスク）へドラッグで「完了」
- 右 → 左へドラッグで「完了取り消し」
- 操作は Google Tasks 側にも反映されます

## 完了ポップアップ

- 完了時に `assets/rect1.png` を使ったポップアップを表示
- タスク名 + 「完了しました！」 + ねぎらいの言葉を表示
- 表示時間は `popup_duration_ms`（ミリ秒）で調整可能

## 同期仕様

- 起動時にタスクを取得
- 60秒間隔で自動同期
- 完了済みは「完了日時の降順で最新2件のみ」表示

## 主要ファイル

- UI/操作/同期: [main.py](main.py)
- Google Tasks API 連携: [backend.py](backend.py)
- 完了ポップアップ画像: [assets/rect1.png](assets/rect1.png)

## 注意事項

- `credentials.json` と `token.json` は機密情報のため Git 管理外にしてください（.gitignore に登録済み）。
- 認可エラー（403 等）が出た場合、再認可が必要なことがあります。

# ライセンス

このソフトウェアはMITライセンスです。
また、README.md, block.drawio, block.svgはパブリックドメインです。
assets/以下：
- rect1.png : SIL Openfont Licenceであり、著作権はGoogleに帰属します
