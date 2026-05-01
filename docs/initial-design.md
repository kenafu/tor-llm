# Tor LLM Extension 初期設計

## 目的

Tor Browser 上で、閲覧中ページの翻訳、選択範囲の翻訳、選択範囲やページ全体の解説、ページ内容への質問応答、画像を含む内容の説明を local LLM に依頼できる拡張を作る。

このプロジェクトでは「クラウドへ送らない」ことを第一の価値に置く。ただし Tor Browser に拡張を追加すること自体が匿名性やフィンガープリントに影響するため、一般配布向けではなく、利用者がリスクを理解して導入するローカル支援ツールとして設計する。

## 前提と制約

- Tor Browser は Firefox 系の WebExtensions を基盤にできる。
- Tor Project は追加アドオンの導入を推奨していない。拡張はブラウザーの一意性、攻撃面、通信経路のリスクを増やし得る。
- ページ本文、選択テキスト、スクリーンショット、画像は高感度データとして扱う。
- LLM はローカル実行を前提にし、外部 API への送信は標準機能に含めない。
- 拡張の UI や DOM 挿入は、閲覧ページ側から観測される可能性を最小化する。
- Tor Browser のセキュリティレベル、NoScript、CSP、サイト構造により、一部ページでは機能が制限される。

## 基本方針

1. 既定では何もしない
   - ページ読み込み時の自動解析、自動翻訳、自動スクリーンショットは行わない。
   - ユーザー操作を起点にした明示的なリクエストのみ処理する。

2. ページを汚さない
   - 翻訳結果や解説は原則として拡張の sidebar / popup / dedicated panel に表示する。
   - インライン置換はオプション扱いにし、最初の MVP では実装しない。

3. ローカル境界を明確にする
   - 拡張は local LLM へ直接 `fetch("http://127.0.0.1:...")` する案と、Native Messaging 経由でローカルブリッジに接続する案を比較する。
   - Tor Browser 対応を重視するなら Native Messaging を第一候補にする。

4. 最小権限にする
   - `activeTab`, `contextMenus`, `storage`, `nativeMessaging` を中心に始める。
   - `<all_urls>` は極力避け、必要な時だけ任意権限として要求する。

5. 記録を残さない
   - ページ本文、選択範囲、画像、LLM 応答はデフォルトでは永続化しない。
   - 設定のみ `storage.local` に保存する。

## 想定ユーザーフロー

### 選択範囲の翻訳

1. ユーザーがページ上のテキストを選択する。
2. 右クリックメニューから「選択範囲を翻訳」を選ぶ。
3. content script が選択テキストとページ URL の最小情報を background に送る。
4. background が local bridge に翻訳リクエストを送る。
5. 結果を sidebar/popup に表示する。

### 選択範囲の解説

1. ユーザーがテキストを選択する。
2. 「選択範囲を解説」を選ぶ。
3. local LLM に、専門用語、文脈、要約、注意点を分けて説明させる。
4. 結果は元ページへ自動挿入せず、拡張 UI に表示する。

### ページ全体の要約・解説

1. ユーザーが拡張アイコンまたは sidebar から「ページを要約」を押す。
2. content script が Readability 風の抽出で主要本文を取る。
3. 長文は chunking して local bridge に送る。
4. bridge 側で map-reduce 形式の要約を行う。
5. UI に「要約」「重要点」「不明点」「用語」を表示する。

### ページ内容への質問

1. ユーザーが sidebar の質問欄に質問を入力する。
2. content script がページタイトル、URL、主要本文、必要に応じて選択範囲を取得する。
3. local bridge が本文を chunking し、質問に関連する chunk を抽出する。
4. local LLM に、ページ本文を根拠にして回答させる。
5. UI に「回答」「根拠になった箇所」「本文からは判断できない点」を分けて表示する。

方針:

- ページ本文に書かれていない内容を断定させない。
- モデルの一般知識で補う場合は「本文外の補足」として明示する。
- 長いページでは、全本文を毎回送るのではなく、質問に関連する chunk を優先する。
- 質問履歴はデフォルトでは保存しない。

### 画像を含む説明

1. ユーザーが画像を右クリックして「画像を説明」を選ぶ、または表示範囲スクリーンショットを明示的に取得する。
2. 画像データを local bridge に送る。
3. vision 対応 local LLM が画像説明、OCR、周辺文脈との関連を返す。
4. 結果を UI に表示する。

## アーキテクチャ

```text
Tor Browser
  WebExtension
    manifest.json
    background service/background script
    content script
    sidebar / popup UI
    options UI
        |
        | Native Messaging or localhost HTTP
        v
Local Bridge
  request validation
  prompt builder
  chunking / OCR / image preprocessing
  model adapter
        |
        v
Local LLM Runtime
  Ollama / llama.cpp server / OpenAI-compatible local server
  text model
  vision model
```

## コンポーネント設計

### WebExtension

責務:

- コンテキストメニューを提供する。
- 選択範囲、ページ本文、画像などをユーザー操作に応じて取得する。
- ローカルブリッジへリクエストを渡す。
- 結果を sidebar / popup で表示する。
- 設定を保存する。

初期 API 候補:

- `browser.contextMenus`
- `browser.runtime.sendMessage`
- `browser.tabs.sendMessage`
- `browser.storage.local`
- `browser.sidebarAction` または popup UI
- `browser.runtime.connectNative`

### Content Script

責務:

- `window.getSelection()` で選択テキストを取得する。
- ページ本文抽出を行う。
- 画像 URL、alt、周辺テキスト、必要なら canvas 変換可能な画像データを取得する。
- DOM へ恒久的な変更を加えない。

注意:

- ページ側 JavaScript と共有しない isolated world の前提を守る。
- ページへ独自要素を挿入する場合は、オプション機能として Shadow DOM を使い、MVP では避ける。

### Background

責務:

- context menu のイベントを受ける。
- content script と UI と local bridge の仲介をする。
- タスク状態、キャンセル、タイムアウトを管理する。
- bridge 未起動、モデル未ロード、入力過大などのエラーを UI に返す。

### Sidebar / Popup

責務:

- リクエスト種別を選ぶ。
- 結果を表示する。
- 実行中、キャンセル、再実行を扱う。
- 翻訳先言語、説明の深さ、モデル選択を設定できるようにする。

MVP では popup より sidebar を優先する。長文の翻訳・解説は popup だと表示領域が不足するため。

### Local Bridge

責務:

- 拡張からのメッセージを受け取る。
- 入力サイズ、URL、タスク種別を検証する。
- local LLM の API 差異を吸収する。
- 長文 chunking、画像変換、プロンプト生成を担当する。
- ストリーミング応答を拡張へ返す。

候補実装:

- Node.js: 拡張開発と型共有しやすい。
- Python: OCR、画像前処理、LLM 周辺ライブラリを使いやすい。

初期は Python bridge を推奨する。vision/OCR/画像前処理を含めるなら Python の方が拡張しやすい。

### Model Adapter

責務:

- Ollama API
- llama.cpp server
- OpenAI-compatible local endpoint

上記を同じ内部インターフェースで扱う。

```ts
type LlmTask =
  | "translate-selection"
  | "explain-selection"
  | "summarize-page"
  | "ask-page"
  | "explain-image"
  | "ocr-image";
```

## 通信方式の比較

### Native Messaging

メリット:

- Firefox WebExtensions の公式機構。
- 拡張とローカルアプリの境界が明確。
- localhost ポートを常時開けずに済む。
- 拡張 ID による許可制にできる。

デメリット:

- OS ごとの native manifest 配置が必要。
- インストール手順が増える。
- 開発中のセットアップがやや重い。

### localhost HTTP

メリット:

- 実装とデバッグが簡単。
- Ollama など既存 local server とつなぎやすい。
- ストリーミングしやすい。

デメリット:

- Tor Browser / Firefox の CSP や権限設定に影響を受ける。
- ローカルポート公開の扱いに注意が必要。
- ページ側ではなく拡張からの通信であることを設計上明確に管理する必要がある。

結論:

- MVP は `localhost HTTP` で早く検証してよい。
- Tor Browser 用の正式導入経路は `Native Messaging` に寄せる。
- bridge 内部は同じにし、transport だけ差し替え可能にする。

## データモデル

```ts
type AssistantRequest = {
  id: string;
  task: LlmTask;
  source: {
    url?: string;
    title?: string;
    text?: string;
    html?: string;
    question?: string;
    image?: {
      mimeType: string;
      dataBase64: string;
      alt?: string;
      surroundingText?: string;
    };
  };
  options: {
    targetLanguage?: string;
    explanationLevel?: "brief" | "normal" | "deep";
    outputFormat?: "plain" | "markdown" | "structured";
    model?: string;
  };
};

type AssistantResponse = {
  id: string;
  status: "ok" | "error" | "stream";
  task: LlmTask;
  content?: string;
  error?: {
    code: string;
    message: string;
    retryable: boolean;
  };
};
```

## プロンプト設計

### 翻訳

- 原文の意味を保つ。
- 固有名詞、URL、コード、コマンドは不用意に翻訳しない。
- 不明瞭な箇所は断定せず補足する。
- 出力は「翻訳」「補足」に分ける。

### 解説

- まず短い要約を出す。
- 次に文脈、用語、注意点を分ける。
- 推測と本文に書かれている事実を分ける。
- 違法行為や危険行為を助長する内容は、説明範囲を安全側に制限する。

### ページQ&A

- 回答はページ本文を主な根拠にする。
- 根拠になる文や段落を短く示す。
- 本文だけでは答えられない場合は、その旨を明確に言う。
- 推測、一般知識、本文外の補足を混ぜない。
- 質問が曖昧な場合は、可能な解釈を示してから回答する。

### 画像

- 見えている事実と推測を分ける。
- OCR 結果がある場合は信頼度を示す。
- ページ周辺テキストがある場合は、それとの関係を説明する。

## セキュリティ・プライバシー設計

- 既定で自動送信しない。
- 既定で履歴保存しない。
- 外部ネットワーク送信を実装しない。
- local bridge は `127.0.0.1` のみ bind する。
- bridge に allowlist token を持たせ、任意ローカルプロセスからの利用を避ける。
- 入力サイズ上限を設定する。
- URL、title、本文を LLM に渡すかをユーザー設定で分ける。
- 画像送信は明示操作のみ。
- ページへのインライン挿入はオプションにし、初期は無効。
- ログには本文や画像を出さない。

## MVP スコープ

含める:

- Firefox/Tor Browser 向け WebExtension 雛形
- 右クリックメニュー
- 選択範囲の翻訳
- 選択範囲の解説
- ページ内容への質問
- sidebar での結果表示
- localhost HTTP bridge
- Ollama text model adapter
- 設定画面: endpoint、model、target language

含めない:

- ページ全体の自動翻訳
- DOM 直接置換
- 画像認識
- OCR
- クラウド API
- 会話履歴保存

## Phase 2

- ページ本文抽出と要約
- 長文 chunking
- 関連 chunk 抽出によるページQ&A精度改善
- streaming 表示
- bridge の Native Messaging 対応
- model adapter 抽象化
- エラー分類とリトライ
- プロンプトテンプレート管理

## Phase 3

- 画像右クリックからの説明
- visible tab capture による範囲説明
- OCR
- インライン翻訳表示
- 用語集、ユーザー辞書
- 複数モデル切替

## 推奨ディレクトリ構成

```text
tor-llm/
  docs/
    initial-design.md
  extension/
    manifest.json
    src/
      background/
      content/
      ui/
      options/
      shared/
    public/
  bridge/
    pyproject.toml
    tor_llm_bridge/
      main.py
      transport/
      adapters/
      prompts/
      chunking.py
      schemas.py
    tests/
  packages/
    shared/
      schemas/
  scripts/
    install-native-host.ps1
    install-native-host.sh
```

## 技術選定案

- Extension: TypeScript, Vite, WebExtension Polyfill
- UI: React または Svelte
- Bridge: Python, FastAPI initially, Native Messaging transport later
- LLM: Ollama initially
- Schema: JSON Schema または Pydantic
- Test: Vitest, Playwright, pytest

React/Svelte はどちらでもよいが、拡張 UI の状態管理が小さく済むなら Svelte が軽い。既存資産がないため、初期は Svelte + TypeScript を推奨する。

## 未決定事項

- Tor Browser の対象バージョン
- Manifest V2 / V3 のどちらを主対象にするか
- sidebar API の利用可否と fallback UI
- Native Messaging を MVP に含めるか
- vision model の候補
- Windows/macOS/Linux のどこまで初期対応するか
- 配布形態: 個人利用、署名済み XPI、開発者向け手動導入

## 初期の実装順

1. `extension/` に最小 WebExtension を作る。
2. context menu から選択テキストを取得する。
3. sidebar に固定文を表示する。
4. `bridge/` に `/v1/assist` を作り、Ollama に翻訳を投げる。
5. extension から bridge へ送って結果表示する。
6. タイムアウト、キャンセル、エラー表示を整える。
7. 解説タスクを追加する。
8. sidebar にページ質問フォームを追加する。
9. ページ本文抽出を追加し、`ask-page` タスクを bridge に送る。
10. 設定画面で endpoint/model/target language を変更可能にする。

## 参照

- Tor Project Support: additional add-ons can compromise privacy features.
  - https://support.torproject.org/glossary/add-on-extension-or-plugin/
- Tor Project Support: Tor Browser fingerprinting protections.
  - https://support.torproject.org/ja/tor-browser/features/fingerprinting-protections/
- MDN: Firefox extensions are built with WebExtensions APIs.
  - https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions
- MDN: Native Messaging lets extensions communicate with local native applications.
  - https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_messaging
- MDN: Extension CSP and localhost handling.
  - https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Content_Security_Policy
