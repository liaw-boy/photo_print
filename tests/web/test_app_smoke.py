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
        # 就算打字篩選，也只能點選清單內的選項，不該冒出寬/高數字輸入框
        assert len(at.sidebar.number_input) == 0

    def test_ratio_options_have_shape_icons(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        ratio_selectbox = next(
            sb for sb in at.sidebar.selectbox if sb.label == "補滿長寬比"
        )
        # 每個選項都要有形狀圖示開頭（原始／方形／直式／橫式／自訂其中一種）
        icon_prefixes = ("🔁", "⬜", "📱", "🖥️", "✏️")
        assert all(
            opt.startswith(icon_prefixes) for opt in ratio_selectbox.options
        )
        # 直式比例（寬<高）要用手機圖示、橫式比例（寬>高）要用螢幕圖示
        assert any(opt.startswith("📱　9:16") for opt in ratio_selectbox.options)
        assert any(opt.startswith("🖥️　3:2") for opt in ratio_selectbox.options)
        assert any(opt.startswith("⬜　1:1") for opt in ratio_selectbox.options)
        assert any(opt.startswith("✏️　自訂比例") for opt in ratio_selectbox.options)

    def test_custom_ratio_shows_width_height_inputs_and_applies(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("a.jpg", _sample_jpeg_bytes(), "image/jpeg")
        at.run(timeout=15)

        ratio_selectbox = next(
            sb for sb in at.sidebar.selectbox if sb.label == "補滿長寬比"
        )
        custom_option = next(
            opt for opt in ratio_selectbox.options if opt.startswith("✏️　自訂比例")
        )
        ratio_selectbox.set_value(custom_option).run(timeout=15)

        assert not at.exception
        width_input = next(ni for ni in at.sidebar.number_input if ni.label == "寬")
        height_input = next(ni for ni in at.sidebar.number_input if ni.label == "高")
        assert width_input.value == 16
        assert height_input.value == 9

        width_input.set_value(21).run(timeout=15)
        height_input.set_value(9).run(timeout=15)

        assert not at.exception
        assert len(at.image) >= 1


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

        process_button = next(b for b in at.button if b.label == "匯出")
        process_button.click().run(timeout=15)

        assert not at.exception
        assert any("完成" in s.value for s in at.success) or any(
            "完成" in w.value for w in at.warning
        )
        assert len(at.download_button) >= 1

    def test_individual_export_mode_shows_one_download_per_file(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("a.jpg", _sample_jpeg_bytes(color=(10, 20, 30)), "image/jpeg")
        at.file_uploader[0].upload(
            "b.jpg", _sample_jpeg_bytes(color=(200, 100, 50)), "image/jpeg"
        )
        at.run(timeout=15)

        export_radio = next(r for r in at.sidebar.radio if r.label == "匯出方式")
        export_radio.set_value("個別下載").run(timeout=15)

        process_button = next(b for b in at.button if b.label == "匯出")
        process_button.click().run(timeout=15)

        assert not at.exception
        download_labels = {b.label for b in at.download_button}
        assert "下載 a.jpg" in download_labels
        assert "下載 b.jpg" in download_labels
        assert "下載全部結果（zip）" not in download_labels


class TestAppMultiFilePreviewNavigator:
    def test_no_nav_buttons_when_single_file(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("a.jpg", _sample_jpeg_bytes(), "image/jpeg")
        at.run(timeout=15)

        assert not at.exception
        assert not any(b.key in ("pfl_prev_btn", "pfl_next_btn") for b in at.button)

    def test_nav_buttons_appear_and_boundaries_are_disabled(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("a.jpg", _sample_jpeg_bytes(color=(10, 20, 30)), "image/jpeg")
        at.file_uploader[0].upload(
            "b.jpg", _sample_jpeg_bytes(color=(200, 100, 50)), "image/jpeg"
        )
        at.run(timeout=15)

        assert not at.exception
        prev_button = at.button(key="pfl_prev_btn")
        next_button = at.button(key="pfl_next_btn")
        # 一開始在第一張，上一張要禁用
        assert prev_button.disabled is True
        assert next_button.disabled is False

    def test_next_button_advances_preview_and_disables_at_last(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("a.jpg", _sample_jpeg_bytes(color=(10, 20, 30)), "image/jpeg")
        at.file_uploader[0].upload(
            "b.jpg", _sample_jpeg_bytes(color=(200, 100, 50)), "image/jpeg"
        )
        at.run(timeout=15)

        next_button = at.button(key="pfl_next_btn")
        next_button.click().run(timeout=15)

        assert not at.exception
        assert at.session_state["preview_index"] == 1
        prev_button = at.button(key="pfl_prev_btn")
        next_button = at.button(key="pfl_next_btn")
        assert prev_button.disabled is False
        assert next_button.disabled is True

    def test_deleting_earlier_file_keeps_viewing_same_photo(self):
        """刪除「目前預覽的那張」前面的照片時，畫面不該悄悄跳去顯示別張照片。

        位置索引在刪除後意義會改變（後面的照片全部往前移一格），只有靠
        file_id 才能正確認出「使用者原本在看的就是這張」。這裡刻意選在非邊界
        的位置（b.jpg，前面還有 a、後面還有 c/d），純位置索引在刪除 a 後不會
        觸發邊界修正，會直接誤指到往前移一格後、原本屬於 c.jpg 的位置。
        """
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        uploader = at.file_uploader[0]
        uploader.upload("a.jpg", _sample_jpeg_bytes(color=(10, 20, 30)), "image/jpeg")
        uploader.upload("b.jpg", _sample_jpeg_bytes(color=(200, 100, 50)), "image/jpeg")
        uploader.upload("c.jpg", _sample_jpeg_bytes(color=(50, 200, 50)), "image/jpeg")
        uploader.upload("d.jpg", _sample_jpeg_bytes(color=(50, 50, 200)), "image/jpeg")
        at.run(timeout=15)

        next_button = at.button(key="pfl_next_btn")
        next_button.click().run(timeout=15)  # 現在預覽 b.jpg（index 1）

        current_files = at.session_state[uploader.id]
        assert [f.name for f in current_files] == ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]
        b_file = next(f for f in current_files if f.name == "b.jpg")

        # 模擬使用者刪除最前面的 a.jpg：只留下 b、c、d，且保留它們原本的 file_id
        at.session_state[uploader.id] = [f for f in current_files if f.name != "a.jpg"]
        at.run(timeout=15)

        assert not at.exception
        assert at.session_state["preview_file_id"] == b_file.file_id
        assert at.session_state["preview_index"] == 0
        assert any("1 / 3" in md.value and "b.jpg" in md.value for md in at.markdown)


class TestAppStaleResultsInvalidated:
    def test_changing_color_after_processing_hides_stale_download(self):
        at = AppTest.from_file(str(APP_PATH))
        at.run(timeout=15)

        at.file_uploader[0].upload("sample.jpg", _sample_jpeg_bytes(), "image/jpeg")
        at.run(timeout=15)

        process_button = next(b for b in at.button if b.label == "匯出")
        process_button.click().run(timeout=15)
        assert len(at.download_button) >= 1

        # 處理完之後改邊框顏色，結果應視為過期，下載按鈕要消失並顯示提示
        color_picker = next(cp for cp in at.sidebar.color_picker if cp.label == "邊框顏色")
        color_picker.set_value("#000000").run(timeout=15)

        assert not at.exception
        assert len(at.download_button) == 0
        assert any("請重新按" in info.value for info in at.info)


class TestIosUserAgentDetection:
    def test_iphone_user_agent_detected_as_ios(self):
        src_dir = APP_PATH.parent.parent.parent
        at = AppTest.from_string(
            f"""
import sys
sys.path.insert(0, {str(src_dir)!r})
from photo_border.web.app import _is_ios_user_agent
import streamlit as st

st.write(str(_is_ios_user_agent(
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)))
st.write(str(_is_ios_user_agent(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)))
st.write(str(_is_ios_user_agent(
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) CriOS/120.0 Mobile/15E148 Safari/604.1"
)))
""",
            default_timeout=15,
        )
        at.run()

        assert not at.exception
        # 匯入 photo_border.web.app 會連帶把整個模組頂層的 main() 也跑一次，
        # 混進一堆跟這個測試無關的 markdown；只挑出字面剛好是 True/False 的
        # 結果來比對，濾掉那些雜訊。
        bool_values = [md.value for md in at.markdown if md.value in ("True", "False")]
        assert bool_values == ["True", "False", "True"]

    def test_download_limited_detection_covers_desktop_and_mobile_safari(self):
        src_dir = APP_PATH.parent.parent.parent
        at = AppTest.from_string(
            f"""
import sys
sys.path.insert(0, {str(src_dir)!r})
from photo_border.web.app import _is_download_limited_user_agent
import streamlit as st

# iPhone Safari -> 限制
st.write(str(_is_download_limited_user_agent(
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)))
# 桌機版 macOS Safari -> 一樣有限制（這是先前漏掉、只抓 iOS 沒抓到的情況）
st.write(str(_is_download_limited_user_agent(
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)))
# 桌機版 Chrome（UA 裡也有 Safari 字樣，但引擎不是 WebKit 限制）-> 不算
st.write(str(_is_download_limited_user_agent(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)))
# iOS 上的 Chrome（CriOS，底層仍是 WebKit）-> 一樣算
st.write(str(_is_download_limited_user_agent(
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) CriOS/120.0 Mobile/15E148 Safari/604.1"
)))
# Firefox -> 不算
st.write(str(_is_download_limited_user_agent(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
)))
""",
            default_timeout=15,
        )
        at.run()

        assert not at.exception
        bool_values = [md.value for md in at.markdown if md.value in ("True", "False")]
        assert bool_values == ["True", "True", "False", "True", "False"]
