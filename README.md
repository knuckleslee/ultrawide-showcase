# UltraWide Studio — 5120 × 1440 Virtual Desktop Showcase

以 **32:9（5120 × 1440）超寬螢幕**為目標的互動展示網頁。這是一個模擬桌面，不需要登入聊天軟體、Discord，也不必安裝剪輯器或程式編輯器。畫面採用接近真實桌面應用程式的視覺結構，而非實際可操作的第三方服務。

![日常使用場景](demo-initial.svg)

## 功能

- **自動展示**：依序播放日常使用、影片剪輯、程式設計場景，搭配放大游標導覽。
- **自由操作**：可拖曳視窗標題列、縮放右下角、最小化／最大化、切換焦點。
- **視窗內容自適應**：依視窗大小調整模擬應用程式版面；應用程式不是實際可操作的生產力工具。
- **自動整理／重設**：切換工作區配置，快速恢復展示。
- **全螢幕展示**：透過網頁按鈕進入全螢幕。
- **新聞內容**：GitHub Actions 每天兩次（台灣時間 **08:17／20:17**）擷取 Google News RSS 並產生 `news.json`；使用者開啟網站時讀取一次，展示中不改變標題。
- **日常聊天**：以桌面通訊軟體的三欄式視窗、對話列表、未讀通知與綠色訊息泡泡呈現，不顯示品牌名稱、使用真實帳號或聯絡人。
- **遊戲娛樂**：新增第 4 場景，左側 Discord 風格群組聊天、中央 **嚴格 16:9** 的模擬遊戲畫面、右側巴哈姆特風格攻略論壇；拖曳或縮放視窗時，遊戲不會被拉伸。
- **真實專案示範**：「程式設計」場景以本儲存庫 `knuckleslee/ultrawide-showcase` 為範本，顯示 `scripts/fetch_news.py` 真實程式碼節錄、README、檔案結構與 GitHub 資訊（操作與 Terminal 輸出仍為模擬）。

![影片剪輯場景](demo-editing.svg)

## 使用方法

### 最簡單：純靜態網頁

透過 GitHub Pages 開啟網站即可操作四種場景、視窗動畫和展示功能。新聞會從 `news.json` 載入最近一次 Actions 成功擷取的資料；直接以 `file://` 開啟則通常無法取得 JSON，會顯示明確標示的示範資料。

### 即時新聞：Python 本機服務

需安裝 Python 3，無需第三方套件：

```bash
python server.py
```

接著在瀏覽器開啟 <http://127.0.0.1:8765/>。Windows 也可以雙擊 `啟動展示.bat`。

新聞資料由本機 `/api/news` 提供，使用 Google News RSS，每 5 分鐘更新快取一次。來源無法存取時，網頁會保留示範內容而不宣稱其為最新新聞。

## 操作快捷鍵

| 按鍵 | 功能 |
| --- | --- |
| `1` / `2` / `3` / `4` | 切換日常／剪輯／程式／遊戲場景 |
| `Space` | 暫停／繼續自動展示 |
| `R` | 重設當前場景 |
| `F` | 切換全螢幕 |
| `H` | 顯示／隱藏提示 |
| `Esc` | 離開全螢幕 |

## 部署說明

此專案使用 GitHub Actions 排程擷取新聞，並直接發布 GitHub Pages；不依賴外部 API 或常駐伺服器。

1. 開啟 [Repository Settings → Pages](https://github.com/knuckleslee/ultrawide-showcase/settings/pages)，將 **Build and deployment → Source** 設為 **GitHub Actions**（首次啟用必要）。
2. 開啟 [Repository Settings → Actions → General](https://github.com/knuckleslee/ultrawide-showcase/settings/actions) 確認允許 GitHub Actions 執行，且 **Workflow permissions** 可寫入儲存庫內容；工作流程本身宣告 `contents: write`。
3. 前往 [Actions → Refresh news and deploy GitHub Pages](https://github.com/knuckleslee/ultrawide-showcase/actions/workflows/update-news.yml)，按 **Run workflow** 手動執行首次部署。
4. 成功後可開啟 https://knuckleslee.github.io/ultrawide-showcase/ 。Google 新聞排程在 **UTC 00:17、12:17**（台灣時間 **08:17、20:17**）執行，GitHub 可能延後執行，並非即時保證。一般推送 `main` 會重新部署頁面，**不會額外擷取新聞**；手動 `Run workflow` 則可以額外更新一次。

新聞更新只在 GitHub Actions 排程或手動執行時進行，不在瀏覽器內執行爬取。每次進入網頁只讀取一次 JSON。RSS 取得失敗時保留上一版資料；從未成功擷取時則顯示標示清楚的展示內容。`server.py` 仍供本機使用。

## 專案結構

```
index.html           # 虛擬桌面 UI、四種場景、動畫與互動
news.json            # 自動更新的新聞快照
scripts/fetch_news.py # RSS 擷取程式
.github/workflows/update-news.yml # 定時抓新聞與部署 Pages
server.py            # 可選的本機 RSS API 服務
啟動展示.bat          # Windows 啟動器
demo-initial.svg     # 日常模式預覽
demo-editing.svg     # 剪輯模式預覽
README.md            # 使用說明
```

> 聊天、影片剪輯、程式編輯、遊戲、Discord 與巴哈姆特論壇的介面及訊息皆為示意；新聞標題可來自 Google News RSS，但不是嵌入真實 Google 新聞網站。本專案與 Google、LINE、Discord 或巴哈姆特均無官方合作關係。

> GitHub 上的 SVG 預覽為示意圖；原始 PNG 截圖保留在本次提供的完整 ZIP 內。

## 遊戲場景畫面配置

預設在 32:9 桌面中：Discord 風格聊天（左，約 420px）、16:9 遊戲視窗（中央，約 784px）、巴哈姆特論壇（右，約 640px）。**遊戲內容以 SVG 的 1600×900 比例繪製，永遠保持 16:9**，若視窗本身比例不同則顯示黑邊，不會拉伸畫面。這個畫面不是實際可執行的遊戲。
