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

    def test_shows_upload_prompt_when_no_files(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        assert any("請先上傳照片" in info.value for info in at.info)

    def test_sidebar_mode_options_present(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        radios = at.sidebar.radio
        assert any(r.label == "邊框模式" for r in radios)


class TestAppUploadAndProcessFlow:
    def test_upload_preview_process_and_download(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("sample.jpg", _sample_jpeg_bytes(), "image/jpeg")
        at.run(timeout=15)
        assert not at.exception
        # 有照片後應該看得到預覽圖，不再顯示「請先上傳照片」提示
        assert not any("請先上傳照片" in info.value for info in at.info)
        assert len(at.image) >= 1

        process_button = next(b for b in at.button if b.label == "開始批次處理")
        process_button.click().run(timeout=15)

        assert not at.exception
        assert any("完成" in s.value for s in at.success) or any(
            "完成" in w.value for w in at.warning
        )
        assert len(at.download_button) >= 1
