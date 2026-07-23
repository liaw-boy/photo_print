# PhotoFrame Lab

模仿 Adobe Lightroom for iPad「加邊框並匯出」功能的照片批次處理工具。讀取照片、依設定比例計算並加上白邊，輸出高解析度、保留 EXIF/ICC 的成品——提供 CLI 批次處理與 Streamlit 網頁介面兩種使用方式。

## 功能特色

- **白邊計算與裁切**
  - 依長邊或短邊的百分比加上白邊
  - 補滿指定長寬比（1:1、4:5、9:16 等社群常用比例，或自訂比例），不改變原圖比例
- **品質與中繼資料保留**
  - 匯出保持原始解析度、無損視覺品質
  - 完整保留 EXIF（相機型號、光圈、快門、ISO 等）與 ICC color profile
  - 支援 `piexif` 或 `exiftool` 兩種 metadata 處理後端
- **批次處理**：指定輸入/輸出資料夾，一次處理整批照片，CLI 與網頁共用同一套核心邏輯
- **模組化架構**：核心影像處理邏輯與 CLI / Web 介面分離，方便未來擴充（浮水印、LUT 濾鏡等）

## 安裝

需要 Python 3.10+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[web,dev]
```

- `.[web]`：包含 Streamlit 網頁介面依賴
- `.[dev]`：包含測試/lint 工具（pytest、ruff、mypy）

## 使用方式

### CLI

```bash
photo-border <輸入路徑> <輸出路徑> [選項]
```

常用選項：

| 選項 | 說明 |
|---|---|
| `--mode` | `percent`（純百分比留白）／`aspect`（補滿比例）／`aspect-then-percent`（先補比例再留白） |
| `--percent` | 留白百分比，例如 `0.05` |
| `--edge` | 百分比參考邊：`short`（短邊，預設）／`long`（長邊） |
| `--ratio` | 目標長寬比，例如 `4:5` |
| `--color` | 邊框顏色，支援 hex/named/rgb |
| `--format` | 輸出格式：`jpeg`／`png`／`tiff`／`heif`／`keep`（維持原格式） |
| `--quality` | JPEG 品質 1–100（預設 95） |
| `--no-metadata` | 不保留 EXIF/ICC |
| `--metadata-backend` | `auto`／`piexif`／`exiftool` |
| `--recursive` | 遞迴處理子資料夾 |
| `-v`, `--verbose` | 顯示逐張處理結果 |

範例：

```bash
# 將 ./input 內所有照片補滿 4:5 比例、留白 5%，輸出到 ./output
photo-border ./input ./output --ratio 4:5 --percent 0.05

# 單一檔案處理，維持原比例只加 3% 留白
photo-border photo.jpg output/photo.jpg --mode percent --percent 0.03
```

### 網頁介面

```bash
streamlit run src/photo_border/web/app.py
```

啟動後依終端機顯示的網址開啟瀏覽器，可以：

- 拖拉/選擇多張照片，即時預覽加框後效果，左右切換預覽
- 側邊欄調整比例、留白粗細、邊框顏色、輸出格式、metadata 處理方式
- 選擇匯出方式：打包成 zip 或個別下載，按下「匯出」即自動觸發下載（部分瀏覽器如 iOS Safari 因平台限制，多張照片會自動改用 zip）

## 架構

```
src/photo_border/
├── core/           # 純邏輯層，不依賴任何 UI 框架，CLI/Web 共用
│   ├── geometry.py     # 邊框/畫布尺寸計算
│   ├── border.py       # 影像合成
│   ├── color.py        # 顏色解析
│   ├── metadata.py     # EXIF/ICC 讀取與轉移
│   ├── io.py           # 影像讀寫
│   ├── pipeline.py     # 單張影像完整處理流程
│   ├── batch.py        # 批次處理與進度回報
│   └── config_builder.py  # 把字串參數組成 BorderConfig
├── cli/            # Typer CLI 入口
└── web/            # Streamlit 網頁介面
```

## 測試

```bash
pytest
```

測試涵蓋核心邏輯（geometry/border/color/metadata/io/pipeline/batch）、CLI 與網頁介面（`streamlit.testing.v1.AppTest`）。

## 技術棧

Python + [Pillow](https://python-pillow.org/) / [pillow-heif](https://github.com/bigcat88/pillow_heif) 處理影像、[piexif](https://github.com/hMatoba/Piexif) 處理 EXIF、[Typer](https://typer.tiangolo.com/) 建 CLI、[Streamlit](https://streamlit.io/) 建網頁介面。
