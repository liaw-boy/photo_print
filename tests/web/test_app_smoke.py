from io import BytesIO
from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parent.parent.parent / "src" / "photo_border" / "web" / "app.py"


def _sample_jpeg_bytes(size=(400, 300), color=(20, 40, 60)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


class TestAppSmoke:
    def test_app_loads_without_exception(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        assert not at.exception

    def test_footer_always_visible_even_with_no_files(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        assert any("liaw-boy" in c.value and "Eric" in c.value for c in at.caption)

    def test_shows_upload_prompt_when_no_files(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        assert any("請先" in info.value and "上傳" in info.value for info in at.info)

    def test_sidebar_ratio_and_percent_controls_present(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        selectboxes = at.sidebar.selectbox
        assert any(sb.label == "補滿長寬比" for sb in selectboxes)
        sliders = at.sidebar.slider
        assert any(s.label == "留白粗細（佔邊長比例）" for s in sliders)
        # 短邊/長邊參考應該在進階設定裡，不在最上層
        assert not any(r.label == "邊框模式" for r in at.sidebar.radio)

    def test_ratio_selectbox_has_no_free_text_option(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        ratio_selectbox = next(
            sb for sb in at.sidebar.selectbox if sb.label == "補滿長寬比"
        )
        assert "自訂" not in ratio_selectbox.options
        # 選了任何比例選項後都不該冒出寬/高數字輸入框
        assert len(at.sidebar.number_input) == 0


class TestAppUploadAndProcessFlow:
    def test_upload_preview_process_and_download(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("sample.jpg", _sample_jpeg_bytes(), "image/jpeg")
        at.run(timeout=15)
        assert not at.exception
        # 有照片後應該看得到加框後的預覽圖，不再顯示上傳提示
        assert not any("請先" in info.value and "上傳" in info.value for info in at.info)
        assert len(at.image) >= 1

        process_button = next(b for b in at.button if b.label == "開始批次處理")
        process_button.click().run(timeout=15)

        assert not at.exception
        assert any("完成" in s.value for s in at.success) or any(
            "完成" in w.value for w in at.warning
        )
        assert len(at.download_button) >= 1


class TestAppStaleResultsInvalidated:
    def test_changing_color_after_processing_hides_stale_download(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("sample.jpg", _sample_jpeg_bytes(), "image/jpeg")
        at.run(timeout=15)

        process_button = next(b for b in at.button if b.label == "開始批次處理")
        process_button.click().run(timeout=15)
        assert len(at.download_button) >= 1

        # 處理完之後改邊框顏色，結果應視為過期，下載按鈕要消失並顯示提示
        color_picker = next(cp for cp in at.sidebar.color_picker if cp.label == "邊框顏色")
        color_picker.set_value("#000000").run(timeout=15)

        assert not at.exception
        assert len(at.download_button) == 0
        assert any("請重新按" in info.value for info in at.info)
