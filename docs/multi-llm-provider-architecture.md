# ai-translator 多 LLM 來源支援評估

## 目的

本文整理 `ai-translator` 目前的模型呼叫方式，評估如何修改成可支援多種 LLM 來源的架構，包含：

- 現有 `claude` CLI
- 其他遠端或本地 HTTP LLM 服務
- 本地由 `lemond` / `lemonade` 暴露的模型服務

目標是以最小改動保留現有翻譯流程，同時讓模型來源可插拔，並讓本機 Lemonade 成為第一個可落地的 HTTP backend。

## 目前架構

目前專案核心邏輯集中在 `ai_translator.py`，包含：

- context 自動蒐集
- prompt 建立
- 批次翻譯
- 快取
- CLI 入口

其中模型呼叫是直接寫死在 `Translator.batch_translate()`：

- `ai_translator.py` 內直接使用 `subprocess.run(['claude', '--print', prompt], ...)`
- 錯誤訊息與 timeout handling 也直接綁定 Claude CLI

這代表目前工具不是「多來源 LLM 工具」，而是「翻譯流程 + Claude CLI 包裝器」。

## 現有耦合點

### 1. Provider 耦合

主要耦合都在 `ai_translator.py`：

- prompt 建立
- 批次翻譯
- Claude CLI 呼叫
- 回應解析
- 錯誤訊息

最明顯的問題是 `Translator` 同時負責：

- 翻譯流程 orchestration
- provider transport 細節
- response parsing

### 2. 快取耦合

現有快取 key 只包含：

- `output_format`
- `context_hash`
- `text`

這在單一 Claude 來源時勉強可用，但一旦支援多 provider / model，就會出現快取污染：

- Claude 的翻譯可能被本地模型重用
- 不同 host 的同名 model 結果可能互相覆蓋
- prompt 改版後舊快取不會失效
- `max_length` 不同時仍可能命中錯誤快取

更重要的是，目前 `context_hash` 使用 Python 內建 `hash()`，這不是穩定 hash；不同 Python process 對相同字串的結果可能不同。這意味著目前快取 key 在跨 process 時就可能漂移，屬於功能性 bug，不只是多 provider 擴充議題。

### 3. 文件與產品定位耦合

以下檔案目前都寫成「使用 Claude 的翻譯工具」：

- `README.md`
- `pyproject.toml`
- `CLAUDE.md`

### 4. 次要問題

- `TranslationConfig` 已定義但幾乎沒有承接 provider 設定
- `--no-cache` 已有 CLI 參數，但目前沒有實際行為
- JSON 解析使用簡單 regex，對多 provider 會更脆弱
- 目前沒有測試，後續重構缺少安全網

## 為什麼不建議改成 agent-first 架構

這個專案的需求很單純：

- 單輪 prompt
- 要求固定 JSON 結果
- 要穩定快取
- 要能批次翻譯

因此它最需要的是穩定的 text generation backend，而不是互動式 agent session。

如果把專案改成「透過 agent 啟動不同模型再對話」，會有幾個問題：

- 流程過重，不符合單次翻譯需求
- 不利於測試與快取
- agent 輸出更容易夾帶額外說明文字，增加 JSON 解析風險
- 與本地服務整合時，HTTP API 會比 agent CLI 更穩定

結論：

- 不建議以 agent 作為主抽象
- 建議以 provider / protocol / parser 作為主抽象

## 本機 Lemonade 實測現況

本文件撰寫時已實測本機 Lemonade 狀態，結果如下：

- `lemonade version 10.2.0`
- `lemond version 10.2.0`
- `lemonade-server.service` 為 `active (running)`
- server 綁定在 `localhost:13305`，不是 `127.0.0.1:13305`
- config 顯示 `llamacpp.backend=rocm`
- 目前 loaded model 為 `user.gemma-4-26B-A4B-it-GGUF`
- 實際 `llama-server` 啟動參數包含 `--ctx-size 49152`
- journal 中可見 `POST /v1/chat/completions ... 200`

這幾個觀察很重要：

1. 本機 Lemonade 已經是可用中的 HTTP 服務，不是未驗證假設
2. 這個服務的實際可用入口是 network host，而不是只能假設 localhost
3. 至少 OpenAI-compatible 路徑已在被實際使用
4. Claude / OpenCode 類工具的大 prompt 已要求較大的 context window，因此整合時不能只考慮模型名稱，也要考慮 serving options

## 關於 Lemonade 的結論

對 `ai-translator` 而言，Lemonade 不應被視為第一層的特殊 provider 類型，而應被視為：

- 一個 HTTP backend
- 可能支援 OpenAI-compatible protocol
- 也可能支援 Anthropic-compatible protocol
- 由外部服務負責 model lifecycle

也就是說，`ai-translator` 不應先設計成 `LemonadeProvider` 優先，而應先設計為通用 HTTP provider，再由設定決定它要連到 Lemonade 還是其他 gateway。

## 建議架構

### 核心原則

保留 `Translator` 的責任：

- 收集 context
- 建立 prompt
- 管理快取
- 格式化輸出
- 提供 CLI / Python API

把以下責任抽離：

- 如何呼叫模型 → provider / protocol transport
- 如何解析 provider 回應 → parser

### 建議抽象層

第一層抽象：

- `LLMProvider`
- `TranslationResponseParser`

第二層實作：

- `ClaudeCLIProvider`
- `HTTPProvider`
  - `protocol="openai"`
  - `protocol="anthropic"`

比起先做 `LemonadeProvider`，更建議先做通用 `HTTPProvider`。若未來真的遇到 Lemonade 專屬格式差異，再補 `LemonadeProvider` 也不遲。

### 最小介面

```python
class LLMProvider:
    provider_name: str
    model_name: str

    def generate(self, prompt: str) -> str:
        raise NotImplementedError
```

可再加一層 response metadata：

```python
@dataclass
class ProviderResponse:
    text: str
    provider_name: str
    model_name: str
    metadata: dict[str, str] | None = None
```

若要最小改動，第一版先維持 `generate(prompt) -> str` 即可。

## Parser 應升級為一級元件

目前解析流程直接寫在 `Translator.batch_translate()` 中，使用簡單 regex 抓 JSON，對多 provider 風險很高。建議抽成獨立函式或類別，嘗試順序如下：

1. 直接 `json.loads(output)`
2. 嘗試擷取 fenced JSON block
3. 嘗試從整段文字中抓第一個 JSON object
4. 最後才使用寬鬆 fallback

抽離 parser 的好處：

- provider transport 與 response cleanup 可以分開測試
- 未來接入不同 protocol 時不必把解析邏輯散落在主流程
- 可針對 parser 做獨立單元測試

## Cache 設計建議

### 最低要求

快取 key 至少要擴充為：

- `provider`
- `model`
- `output_format`
- `context_digest`
- `text`

### 實務建議

更完整的 key 建議包含：

- `provider`
- `protocol`
- `model`
- `base_url` 或 endpoint fingerprint
- `output_format`
- `max_length`
- `prompt_version`
- `context_digest`
- `text`

建議 key 型態：

```text
provider|protocol|model|endpoint|output_format|max_length|prompt_version|context_digest|text
```

其中：

- `context_digest` 應改用穩定 digest，例如 `sha256(...).hexdigest()[:16]`
- `prompt_version` 應顯式寫死，例如 `v1`, `v2`

這樣當 prompt 內容、服務端點、或長度限制變更時，舊快取就不會污染新結果。

## CLI 與設定建議

目前 CLI 只有 context、format、cache 類參數。

建議新增：

- `--provider`
- `--protocol`
- `--model`
- `--base-url`
- `--api-key`
- `--timeout`

建議也支援環境變數：

- `AI_TRANSLATOR_PROVIDER`
- `AI_TRANSLATOR_PROTOCOL`
- `AI_TRANSLATOR_MODEL`
- `AI_TRANSLATOR_BASE_URL`
- `AI_TRANSLATOR_API_KEY`
- `AI_TRANSLATOR_TIMEOUT`

### CLI 範例

```bash
# 維持現有行為
ai-translator --provider claude-cli "測試流程"

# 遠端 OpenAI-compatible 服務
ai-translator \
  --provider http \
  --protocol openai \
  --base-url https://example.com/v1 \
  --model gpt-4.1 \
  "測試流程"

# 本機 Lemonade（OpenAI-compatible）
ai-translator \
  --provider http \
  --protocol openai \
  --base-url http://localhost:13305/v1 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  "測試流程"
```

### 關於 Anthropic-compatible

考量既有本機代理整合偏好，長期建議也支援：

```bash
ai-translator \
  --provider http \
  --protocol anthropic \
  --base-url http://localhost:13305 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  "測試流程"
```

也就是說：

- 第一版先用 OpenAI-compatible 落地 Lemonade 接入
- 第二版再補 Anthropic-compatible，與既有本機代理習慣對齊

## Lemonade 接入建議

### 第一版策略

優先採用本地 HTTP 服務接法，而不是 agent 啟動接法。

原因：

- `ai-translator` 是 translation client，不是 serving orchestrator
- 本機 Lemonade 已經有穩定運行中的 HTTP service
- 從 journal 可確認 OpenAI-compatible 路徑有成功請求

### 邊界建議

第一版不要讓 `ai-translator` 負責：

- `lemonade load`
- `lemonade unload`
- backend 安裝或升級
- model lifecycle 切換

應只負責：

- 發送推論請求
- 解析結果
- 呈現清楚錯誤訊息

換句話說，若指定的 model 未可用，`ai-translator` 應回報明確錯誤，但不應自行接管 Lemonade 的運維邏輯。

### Readiness 應以 smoke test 為主

不要只靠 `lemonade backends` 或 metadata 表格判斷是否可用。

實測中已出現以下情況：

- backend 表格顯示 `update_required`
- 但實際 loaded model 與 `/v1/chat/completions` 仍可成功回應

因此更可靠的整合驗證方式應是：

1. 真正打一個最小 request
2. 確認 HTTP 200
3. 確認有可解析輸出

## 建議的分階段實作

### Phase 1：內部解耦與可靠性修補

只改：

- `ai_translator.py`
- 新增 `tests/`
- 必要時更新 `README.md`

內容：

- 抽出 `LLMProvider`
- 實作 `ClaudeCLIProvider`
- `Translator` 改為依賴 provider
- parser 抽成獨立函式 / 類別
- 快取 key 改用穩定 digest
- 快取 key 納入 provider / model / prompt_version / max_length
- 修正 `--no-cache`
- 補單元測試

### Phase 2：HTTP provider

內容：

- 實作 `HTTPProvider`
- 先支援 `protocol=openai`
- CLI 加入 `--provider --protocol --model --base-url --api-key --timeout`
- README / package metadata 改為多 provider 敘述
- 加上最小 smoke test / mocking tests

### Phase 3：Lemonade 實整合

內容：

- 用本機 Lemonade 實測 `ai-translator` 對 `http://localhost:13305/v1`
- 驗證 `user.gemma-4-26B-A4B-it-GGUF` 的翻譯輸出與快取行為
- 視需求再支援 `protocol=anthropic`
- 視需要補 `LemonadeProvider`，但不是預設前提

## 修改範圍評估

### 最小版本

若要避免過早拆檔，第一版 provider class 與 parser 函式可以先留在 `ai_translator.py`。

### 後續再拆檔

當 provider 種類增加後，再考慮拆成：

- `providers.py`
- `parser.py`
- `config.py`
- `tests/test_cache.py`
- `tests/test_parser.py`
- `tests/test_translator.py`

## 總結

對 `ai-translator` 來說，最合理的演進方向不是「多 agent」，而是「多 provider + 多 protocol」。

建議架構：

- 維持 `Translator` 作為翻譯流程中心
- 將 LLM 呼叫方式抽成 provider
- 將 response parsing 抽成 parser
- 保留 Claude CLI 作為預設 provider
- 增加 HTTP provider 以支援遠端與本地服務
- 先以 OpenAI-compatible 方式整合 Lemonade
- 後續再視需要補 Anthropic-compatible，與既有本機代理習慣對齊

這樣可以用最小修改成本，把目前專案從 Claude 專用工具演進為可支援多來源 LLM 的翻譯工具，同時也能直接對接本機已在運作中的 Lemonade 服務。