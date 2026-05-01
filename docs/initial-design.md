# Tor LLM Support Tool 初期設計

## 方針転換

Tor Browser 拡張案は破棄する。

このプロジェクトは、Tor Browser に一切手を入れない独立支援ツールとして作る。ユーザーが画面上の範囲を指定し、その範囲のスクリーンショット画像と OCR テキストを local LLM に送り、翻訳、解説、要約、質問応答を行う。

最優先価値は、Tor Browser に手を入れない独立性と、local LLM だけで完結することに置く。Tor Browser の拡張、DOM 注入、Cookie 参照、ブラウザー権限の追加は行わない。一方で、LLM の判断材料として、OS から取得できるアクティブアプリ名、ウィンドウタイトル、URL らしき文字列はコンテキスト情報として扱う。

## 目的

画面上に表示されている任意の範囲について、local LLM に以下を依頼できる支援ツールを作る。

- 範囲内テキストの翻訳
- OCR 結果の整形
- 範囲内の内容説明
- 図表、UI、エラー画面、画像の解説
- 指定範囲に関する質問応答
- スクリーンショット画像と OCR テキストを組み合わせた文脈理解

対象は Tor Browser に限らない。PDF ビューア、画像ビューア、ターミナル、通常ブラウザー、チャット、ドキュメントなど、画面に表示できるものを対象にする。

## 前提と制約

- Tor Browser には拡張を入れない。
- Web ページの DOM、HTML、Cookie、localStorage、ブラウザー履歴にはアクセスしない。
- ツールが取得する主情報は、ユーザーが明示的に選択した画面範囲の画像と、そこから OCR したテキストに限定する。
- 補助情報として、アクティブアプリ名、ウィンドウタイトル、OS から取得できる URL または URL らしき文字列を扱う。
- LLM はローカル実行を前提にし、外部 API への送信は標準機能に含めない。
- 初期バックエンドは LM Studio とする。
- 後から Ollama、llama.cpp server、OpenAI-compatible local server などへ差し替えられるよう、backend provider を抽象化する。
- API key / token は provider 設定として扱い、LM Studio の認証トークンにも対応する。
- 画像、OCR テキスト、LLM 応答はデフォルトでは保存しない。

## 基本方針

1. Tor Browser に触らない
   - 拡張を入れない。
   - content script を使わない。
   - ページ側から観測可能な変更を加えない。

2. ユーザー操作だけで起動する
   - 常時監視しない。
   - 自動スクリーンショットを取らない。
   - ショートカットまたは明示ボタンから範囲選択を開始する。

3. 送信前に確認できる
   - 取得した画像プレビューを表示する。
   - OCR テキストを表示し、必要なら編集できる。
   - 画像、OCR テキスト、アプリ名、ウィンドウタイトル、URL 候補の送信内容を確認できる。

4. local LLM だけに送る
   - 初期接続先は LM Studio の `127.0.0.1` endpoint。
   - 外部 API provider は実装しない。
   - 将来 provider を増やす場合も、デフォルトは local only とする。

5. 記録を残さない
   - 画像、OCR テキスト、プロンプト、応答をデフォルトで永続化しない。
   - 設定のみ保存する。
   - ログに機密本文や API key を出さない。

6. バックエンドを差し替え可能にする
   - UI は LM Studio 固有 API を知らない。
   - backend adapter が API 差異を吸収する。
   - provider 設定は endpoint、model、API key、timeout、streaming 可否を持つ。

7. コンテキスト情報を活用する
   - アクティブアプリ名、ウィンドウタイトル、URL 候補は LLM への補助情報として利用する。
   - URL はブラウザー内部状態を直接読むのではなく、OS のアクセシビリティ、ウィンドウタイトル、選択範囲 OCR、任意のブラウザー別取得アダプターから得られる範囲で扱う。
   - 取得できない場合も、画像と OCR テキストだけで処理を続行する。

## 想定ユーザーフロー

### 範囲翻訳

1. ユーザーがショートカットを押す。
2. 画面上で矩形範囲を選択する。
3. ツールが範囲スクリーンショットを取得する。
4. OCR でテキストを抽出する。
5. アクティブアプリ名、ウィンドウタイトル、URL 候補を取得する。
6. プレビュー画面で画像、OCR テキスト、コンテキスト情報を確認する。
7. 「翻訳」を実行する。
8. LM Studio に画像、OCR テキスト、コンテキスト情報を送り、結果を表示する。

### 範囲解説

1. ユーザーが説明してほしい画面範囲を選択する。
2. ツールが画像、OCR テキスト、アクティブアプリ名、ウィンドウタイトル、URL 候補を取得する。
3. ユーザーが説明レベルを選ぶ。
4. LLM が内容、前提、重要点、不明点を分けて説明する。

### 質問応答

1. ユーザーが範囲を選択する。
2. プレビュー画面で質問を入力する。
3. ツールが画像、OCR テキスト、コンテキスト情報、質問を LM Studio に送る。
4. LLM が選択範囲を根拠に回答する。
5. 画像や OCR から判断できない点は明確に「判断不能」と出す。

### OCR 整形

1. ユーザーが範囲を選択する。
2. OCR 結果を確認する。
3. 「整形」を実行する。
4. 改行、段落、表、箇条書き、コードブロックを読みやすく整える。

## アーキテクチャ

```text
Desktop App
  global hotkey
  screen region selector
  screenshot capture
  active window context capture
  OCR pipeline
  preview / edit UI
  result UI
        |
        v
Assistant Core
  request validation
  prompt builder
  image preprocessing
  backend provider adapter
        |
        v
Local LLM Backend
  LM Studio initially
  Ollama / llama.cpp server / OpenAI-compatible local server later
```

## コンポーネント設計

### Desktop App

責務:

- グローバルショートカットを登録する。
- 範囲選択 overlay を表示する。
- 選択範囲のスクリーンショットを取得する。
- プレビュー、OCR テキスト編集、実行ボタン、結果表示を提供する。
- 設定画面を提供する。

初期 UI:

- 範囲選択 overlay
- プレビュー画面
- OCR テキスト欄
- コンテキスト欄: アプリ名、ウィンドウタイトル、URL 候補
- 質問入力欄
- モード選択: 翻訳、解説、質問、OCR 整形
- 送信対象 toggle: 画像、OCR テキスト、コンテキスト情報
- 実行、キャンセル、再実行

### Capture

責務:

- 画面全体のスクリーンショットを取得する。
- ユーザーが選択した矩形で crop する。
- 高 DPI / マルチモニターに対応する。
- 一時画像をメモリ中心で扱う。

注意:

- 選択範囲外を LLM に送らない。
- プレビューで送信範囲を明確に見せる。
- 一時ファイルを作る場合は処理後に削除する。

### Context Metadata

責務:

- アクティブアプリ名を取得する。
- アクティブウィンドウタイトルを取得する。
- 取得可能な場合は URL を取得する。
- URL が直接取れない場合は、ウィンドウタイトルや OCR 結果から URL 候補を抽出する。
- 取得したメタデータをプレビュー画面で編集可能にする。

初期対応:

- Windows のアクティブウィンドウ情報取得。
- プロセス名または実行ファイル名からのアプリ名推定。
- ウィンドウタイトル取得。
- OCR テキスト内の URL 正規表現抽出。

Phase 2 以降:

- アクセシビリティ API によるブラウザーアドレスバー取得。
- ブラウザー別 adapter。
- PDF ビューアやターミナルなど、アプリ別 context adapter。

注意:

- URL 取得はベストエフォート扱いにする。
- 取得できない場合は空欄でよい。
- ユーザーがプレビュー画面で修正・削除できるようにする。

### OCR

責務:

- スクリーンショットからテキストを抽出する。
- OCR 結果と信頼度、可能なら bounding box を返す。
- 日本語、英語を初期対応にする。
- OCR engine を差し替え可能にする。

候補:

- PaddleOCR: 日本語を含む多言語 OCR で初期候補。
- Tesseract: 導入は単純だが、日本語精度は検証が必要。
- RapidOCR: 軽量候補。

初期は PaddleOCR を推奨する。導入負荷が問題になる場合は Tesseract fallback を用意する。

### Assistant Core

責務:

- タスク種別を正規化する。
- 画像と OCR テキストの送信可否を判断する。
- 入力サイズを制限する。
- プロンプトを生成する。
- backend adapter を呼ぶ。
- streaming 応答を UI に流す。

### Backend Provider / Model Adapter

初期 provider は LM Studio とする。

LM Studio 設定:

- default endpoint: `http://127.0.0.1:1234/v1`
- default API type: OpenAI-compatible
- default chat endpoint: `POST /v1/chat/completions`
- model: LM Studio 上でロードした model identifier
- visionModel: 画像対応モデルを使う場合の model identifier
- apiKey: 任意。LM Studio の `Require Authentication` を有効にした場合は Bearer token として送る。
- network: `Serve on Local Network` は匿名性重視では無効を推奨する。
- CORS: デスクトップアプリから直接呼ぶため不要。

provider adapter の内部インターフェース:

```ts
type BackendProvider = "lmstudio" | "ollama" | "llama-cpp" | "openai-compatible";

type BackendConfig = {
  provider: BackendProvider;
  baseUrl: string;
  apiKey?: string;
  model: string;
  visionModel?: string;
  timeoutMs: number;
  stream: boolean;
};

type AssistantTask =
  | "translate-region"
  | "explain-region"
  | "ask-region"
  | "clean-ocr"
  | "extract-structured";

type AssistantRequest = {
  id: string;
  task: AssistantTask;
  context?: {
    appName?: string;
    processName?: string;
    windowTitle?: string;
    url?: string;
    urlCandidates?: string[];
  };
  source: {
    ocrText: string;
    image?: {
      mimeType: string;
      dataBase64: string;
    };
    question?: string;
  };
  options: {
    targetLanguage?: string;
    explanationLevel?: "brief" | "normal" | "deep";
    outputFormat?: "plain" | "markdown" | "structured";
    sendImage: boolean;
    sendContext: boolean;
    model?: string;
  };
};
```

設定保存の原則:

- API key は OS の資格情報ストアを優先する。
- 難しい場合はユーザー権限でのみ読める設定ファイルに保存する。
- API key はログ、エラー表示、診断情報に出さない。
- 設定エクスポート時は API key を含めない。

## 設定仕様

MVP では設定項目は設計上広めに定義する。ただし UI に出す項目は最小限にする。

初期設定画面に出す項目:

- `baseUrl`
- `apiKey`
- `model`
- `visionModel`
- `hotkey`
- `targetLanguage`
- `sendImage`
- `sendContext`

### LLM 接続設定

```yaml
llm:
  provider: lmstudio
  baseUrl: http://127.0.0.1:1234/v1
  apiKey: null
  model: ""
  visionModel: ""
  timeoutSec: 120
  stream: true
```

方針:

- `provider` は初期値 `lmstudio`。
- `apiKey` は LM Studio の `Require Authentication` を使う場合のみ必要。
- `model` はテキスト用、`visionModel` は画像入力用として分ける。
- `visionModel` が空の場合は `model` を使う。ただし画像非対応モデルならエラーにする。

### 送信対象設定

```yaml
request:
  sendImage: true
  sendOcrText: true
  sendContext: true
  confirmBeforeSend: true
```

方針:

- `confirmBeforeSend` は MVP では常に true 扱いにする。
- 画像、OCR テキスト、コンテキスト情報はそれぞれ送信 toggle で制御できる。
- `sendOcrText` と `sendImage` がどちらも false の場合は実行不可にする。

### OCR 設定

```yaml
ocr:
  provider: paddleocr
  languages:
    - ja
    - en
  autoRunOcr: true
  preprocessImage: true
  confidenceVisible: false
```

方針:

- 初期 OCR provider は `paddleocr`。
- 導入負荷が問題になる場合は `tesseract` fallback を用意する。
- OCR 失敗時でも、画像送信が有効なら vision model で処理を続行できる。

### キャプチャ設定

```yaml
capture:
  hotkey: Ctrl+Shift+Space
  includeCursor: false
  multiMonitor: true
  captureDelayMs: 100
  maxImageLongEdge: 1600
  imageFormat: png
  jpegQuality: 90
```

方針:

- `maxImageLongEdge` を超える場合は、LLM 送信用画像だけ縮小する。
- プレビューには可能な限り元画像に近いものを表示する。
- 一時ファイルを作る場合は処理後に削除する。

### コンテキスト取得設定

```yaml
context:
  captureAppName: true
  captureProcessName: true
  captureWindowTitle: true
  extractUrlsFromOcr: true
  useAccessibilityForUrl: false
  editableBeforeSend: true
```

方針:

- MVP ではアクティブアプリ名、プロセス名、ウィンドウタイトル、OCR 由来の URL 候補を扱う。
- `useAccessibilityForUrl` は MVP では false。Phase 2 で検討する。
- 取得したコンテキストはプレビュー画面で編集・削除できるようにする。

### UI 設定

```yaml
ui:
  theme: system
  defaultTask: explain-region
  targetLanguage: ja
  explanationLevel: normal
  resultFormat: markdown
  alwaysOnTop: true
```

方針:

- `defaultTask` は `explain-region`。
- 結果表示は markdown を基本にする。
- 結果ウィンドウは既定で前面表示する。

### 保存・ログ設定

```yaml
storage:
  saveHistory: false
  saveScreenshots: false
  saveOcrText: false

logging:
  level: error
  redactSensitiveLogs: true
```

方針:

- 履歴保存は MVP では無効。
- スクリーンショット、OCR テキスト、prompt、response は保存しない。
- ログはエラー中心にし、本文・画像・API key・URL 全文を出さない。

### 設定保存場所

Windows MVP:

- 通常設定: `%APPDATA%\tor-llm-tool\config.yaml`
- API key: 可能なら Windows Credential Manager
- 一時ファイル: OS temp 以下。処理後削除。

## エラー設計

エラーは「どこで失敗したか」「ユーザーが何をすればよいか」「再試行できるか」を明確にする。

### 共通エラー形式

```ts
type ErrorCategory =
  | "capture"
  | "ocr"
  | "context"
  | "provider"
  | "model"
  | "settings"
  | "network"
  | "validation"
  | "internal";

type AppError = {
  code: string;
  category: ErrorCategory;
  message: string;
  detail?: string;
  retryable: boolean;
  userAction?: string;
};
```

例:

```json
{
  "code": "LMSTUDIO_NOT_RUNNING",
  "category": "provider",
  "message": "LM Studio に接続できません。",
  "detail": "http://127.0.0.1:1234/v1 に接続できませんでした。",
  "retryable": true,
  "userAction": "LM Studio の Local Server を起動してから再試行してください。"
}
```

### MVP エラーコード

| code | category | 表示メッセージ | 再試行 | 主な対応 |
|---|---|---|---|---|
| `CAPTURE_CANCELLED` | capture | 範囲選択をキャンセルしました。 | no | 何もしない |
| `CAPTURE_FAILED` | capture | スクリーンショットを取得できませんでした。 | yes | 再度範囲選択 |
| `EMPTY_REGION` | validation | 選択範囲が小さすぎます。 | yes | 範囲を選び直す |
| `OCR_FAILED` | ocr | OCR に失敗しました。 | yes | OCR 再実行、または画像だけで続行 |
| `OCR_NO_TEXT` | ocr | テキストを検出できませんでした。 | yes | 画像だけで続行、または範囲を選び直す |
| `CONTEXT_FAILED` | context | アプリ情報の取得に失敗しました。 | yes | コンテキストなしで続行 |
| `LMSTUDIO_NOT_RUNNING` | provider | LM Studio に接続できません。 | yes | Local Server 起動後に再試行 |
| `MODEL_NOT_SET` | settings | モデルが設定されていません。 | no | 設定画面で model を指定 |
| `MODEL_NOT_LOADED` | model | モデルがロードされていません。 | yes | LM Studio でモデルをロード |
| `API_KEY_INVALID` | provider | API key が無効です。 | no | API key を確認 |
| `REQUEST_TIMEOUT` | network | 応答がタイムアウトしました。 | yes | 再送信、timeout 延長 |
| `INPUT_TOO_LARGE` | validation | 入力が大きすぎます。 | yes | 画像縮小、範囲縮小 |
| `UNSUPPORTED_IMAGE_MODE` | model | このモデルは画像入力に対応していません。 | no | visionModel を設定、または画像送信 off |
| `PROVIDER_BAD_RESPONSE` | provider | LLM の応答を解釈できませんでした。 | yes | 再送信 |
| `INTERNAL_ERROR` | internal | 予期しないエラーが発生しました。 | yes | 再試行、必要なら debug 情報確認 |

### 表示方針

- 範囲選択中のエラー: 小さなトースト表示。
- プレビュー画面のエラー: 対象欄の近くに表示。
- LLM 実行中のエラー: 結果欄に表示。
- 設定画面のエラー: 該当フィールドの下に表示。
- 致命的エラー: ダイアログで表示。

### 再試行アクション

- OCR 失敗: `OCRを再実行`
- LM Studio 未起動: `接続を再確認`
- タイムアウト: `再送信`
- 入力が大きすぎる: `画像を縮小して再送信`
- モデル未ロード: `再確認`

### 処理継続できる失敗

- コンテキスト取得失敗: アプリ名、タイトル、URL 候補なしで続行する。
- OCR 失敗: 画像送信が有効なら画像だけで続行できる。
- 画像送信不可: OCR テキストだけで続行できる。
- URL 候補なし: 空欄で続行する。

### エラーログ

ログに出してよいもの:

```yaml
timestamp: "2026-05-01T00:00:00+09:00"
code: LMSTUDIO_NOT_RUNNING
category: provider
retryable: true
technicalDetail: Connection refused
```

ログに出さないもの:

- スクリーンショット画像
- OCR 本文
- prompt
- LLM response
- API key
- URL 全文

エラー関連設定:

```yaml
error:
  showTechnicalDetails: false
  logLevel: error
  redactSensitiveLogs: true
  autoRetryProviderConnection: false
  maxProviderRetries: 1
  retryBackoffMs: 800
```

## プロンプト設計

### 翻訳

- OCR 誤りがあり得る前提で翻訳する。
- 画像も渡されている場合は、画像上の見た目や配置を補助情報にする。
- アプリ名、ウィンドウタイトル、URL 候補がある場合は、文脈判断に利用する。
- 固有名詞、URL、コード、コマンドは不用意に翻訳しない。
- 出力は「翻訳」「OCR上の不確実点」「補足」に分ける。

### 解説

- まず短い要約を出す。
- 次に文脈、用語、重要点、注意点を分ける。
- 画像から見える事実、OCR テキストに書かれている事実、推測を分ける。
- アプリ名、ウィンドウタイトル、URL 候補を使い、何の画面かを推定する。
- 判断できない点は断定しない。

### 質問応答

- 回答は選択範囲の画像、OCR テキスト、コンテキスト情報を主な根拠にする。
- 根拠になった箇所を短く示す。
- 範囲内情報だけでは答えられない場合は、その旨を明確に言う。
- 一般知識で補う場合は「範囲外の補足」として分ける。

### OCR 整形

- OCR 誤りを勝手に大きく補完しない。
- 表、箇条書き、コード、ログは元の構造を保つ。
- 推測修正した箇所は必要に応じて注記する。

## データ取り扱い設計

- Tor Browser に拡張を入れない。
- ページ DOM、HTML、Cookie、履歴を取得しない。
- アクティブアプリ名、ウィンドウタイトル、URL 候補は LLM の判断材料として取得・送信できる。
- 選択範囲外の画面を送らない。
- 送信前プレビューを必須にする。
- 画像、OCR テキスト、コンテキスト情報はそれぞれ送信 toggle で制御できる。
- 既定で履歴保存しない。
- 外部ネットワーク送信を実装しない。
- LM Studio は `127.0.0.1` のみ bind する運用を推奨する。
- LM Studio の `Serve on Local Network` は無効を推奨する。
- LM Studio の `Require Authentication` は有効を推奨し、API token を設定する。
- LM Studio の MCP 関連機能は、不要なら無効を推奨する。
- ログには画像、OCR テキスト、コンテキスト情報、prompt、response、API key を出さない。

## 動作モード

### standard

既定モード。

- 画像、OCR テキスト、コンテキスト情報を送信前に表示する。
- 画像、OCR テキスト、コンテキスト情報を LM Studio に送る。
- 履歴保存なし。
- 外部 API なし。
- LM Studio は `127.0.0.1` のみ。

### text-only

OCR テキスト中心のモード。

- 画像は送らない。
- OCR テキストとコンテキスト情報を送る。
- vision model が不要な翻訳や文章整形に使う。

### debug

開発時のみ使う。

- OCR 結果、処理時間、model response metadata を表示する。
- 本文や画像はログに出さない。
- 明示的に有効化した場合のみ。

## MVP スコープ

含める:

- Windows 向けデスクトップアプリ
- グローバルショートカット
- 範囲選択 overlay
- スクリーンショット crop
- アクティブアプリ名、ウィンドウタイトル、URL 候補取得
- OCR
- プレビュー画面
- OCR テキスト編集
- LM Studio provider
- API key / endpoint / model 設定
- 翻訳、解説、質問、OCR 整形
- 送信対象 toggle: 画像、OCR テキスト、コンテキスト情報
- 履歴保存なし

含めない:

- Tor Browser 拡張
- DOM 取得
- ページ全体自動取得
- クラウド API
- 自動常時監視
- 画面録画
- 自動履歴保存

## Phase 2

- macOS / Linux 対応
- vision model の本格対応
- アプリ別 context adapter
- アクセシビリティ API による URL 取得
- OCR engine 切り替え
- streaming 表示
- structured output
- 表抽出
- 数式やコードの整形
- Ollama / llama.cpp server provider
- OS credential store 対応強化

## Phase 3

- ローカル履歴 vault。明示 opt-in のみ。
- 範囲テンプレート
- ホットキーの複数割り当て
- プロンプトテンプレート管理
- ローカル RAG
- オフライン辞書、用語集

## 推奨ディレクトリ構成

```text
tor-llm/
  docs/
    initial-design.md
  app/
    pyproject.toml
    tor_llm_tool/
      main.py
      ui/
      capture/
      ocr/
      assistant/
      providers/
      prompts/
      settings/
    tests/
  scripts/
    run-dev.ps1
```

## 技術選定案

- App: Python + PySide6
- Capture: mss または Qt screen capture
- OCR: PaddleOCR initially, Tesseract fallback
- LLM: LM Studio initially
- LLM API: OpenAI-compatible `/v1/chat/completions` initially
- Config: Pydantic Settings
- HTTP: httpx
- Test: pytest

Python + PySide6 を推奨する。OCR、画像処理、LM Studio 連携をまとめやすく、Windows 向け MVP を早く作れるため。

## 未決定事項

- 初期 OCR engine を PaddleOCR にするか Tesseract にするか
- 初期 vision model の候補
- URL 取得をどこまで MVP に含めるか
- グローバルショートカットの既定値
- OS credential store を MVP に含めるか
- 配布形態: portable exe、installer、ソース実行

## 初期の実装順

1. `app/` に Python + PySide6 の最小アプリを作る。
2. グローバルショートカットで overlay を開く。
3. 矩形範囲を選択して screenshot crop を取得する。
4. アクティブアプリ名とウィンドウタイトルを取得する。
5. プレビュー画面に画像とコンテキスト情報を表示する。
6. OCR を実行してテキスト欄に表示する。
7. OCR テキストから URL 候補を抽出する。
8. LM Studio provider を実装する。
9. 翻訳タスクを実装する。
10. 解説、質問、OCR 整形を追加する。
11. endpoint/model/API key/送信対象 toggle を設定可能にする。
12. ログと一時ファイルの扱いを監査する。

## 参照

- Tor Project Support: additional add-ons can compromise privacy features.
  - https://support.torproject.org/glossary/add-on-extension-or-plugin/
- Tor Project Support: Tor Browser fingerprinting protections.
  - https://support.torproject.org/ja/tor-browser/features/fingerprinting-protections/
- LM Studio: Developer Docs.
  - https://lmstudio.ai/docs/developer
- LM Studio: Local LLM API server.
  - https://lmstudio.ai/docs/developer/core/server
- LM Studio: OpenAI Compatibility Endpoints.
  - https://lmstudio.ai/docs/developer/openai-compat
- LM Studio: Authentication.
  - https://lmstudio.ai/docs/developer/core/authentication
- LM Studio: Server Settings.
  - https://lmstudio.ai/docs/developer/core/server/settings
