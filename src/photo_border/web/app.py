import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

from photo_border.core import batch as batch_mod, border, config_builder, geometry
from photo_border.core.constants import ASPECT_PRESETS
from photo_border.core.errors import PhotoBorderError
from photo_border.web import logic

st.set_page_config(page_title="加白邊工具", page_icon="🖼️", layout="centered")

RATIO_PRESET_OPTIONS = {
    "1:1 正方形": "1:1",
    "4:5 直式貼文": "4:5",
    "3:2 標準相片": "3:2",
    "9:16 限時動態": "9:16",
    "自訂": None,
}

MODE_OPTIONS = {
    "百分比留白": "percent",
    "補滿目標比例": "aspect",
    "先補比例再留白": "aspect-then-percent",
}

FORMAT_OPTIONS = {
    "維持原格式": "keep",
    "JPEG": "jpeg",
    "PNG": "png",
    "TIFF": "tiff",
}


def _render_sidebar_controls() -> dict:
    st.sidebar.header("參數設定")

    mode_label = st.sidebar.radio("邊框模式", list(MODE_OPTIONS), index=2)
    mode = MODE_OPTIONS[mode_label]

    percent = None
    edge = "short"
    if mode in ("percent", "aspect-then-percent"):
        percent = st.sidebar.slider("留白百分比", 0.0, 0.3, 0.05, step=0.01)
        edge_label = st.sidebar.radio("百分比參考邊", ["短邊", "長邊"], index=0, horizontal=True)
        edge = "short" if edge_label == "短邊" else "long"

    ratio = None
    if mode in ("aspect", "aspect-then-percent"):
        ratio_label = st.sidebar.selectbox("目標長寬比", list(RATIO_PRESET_OPTIONS))
        if RATIO_PRESET_OPTIONS[ratio_label] is None:
            col1, col2 = st.sidebar.columns(2)
            width = col1.number_input("寬", min_value=1, max_value=100, value=4)
            height = col2.number_input("高", min_value=1, max_value=100, value=5)
            ratio = f"{int(width)}:{int(height)}"
        else:
            ratio = RATIO_PRESET_OPTIONS[ratio_label]

    color = st.sidebar.color_picker("邊框顏色", "#FFFFFF")

    with st.sidebar.expander("進階設定"):
        format_label = st.selectbox("輸出格式", list(FORMAT_OPTIONS))
        output_format = FORMAT_OPTIONS[format_label]
        quality = st.slider("JPEG 品質", 1, 100, 95)
        keep_metadata = st.checkbox("保留 EXIF / ICC profile", value=True)
        metadata_backend = st.selectbox("Metadata 處理方式", ["auto", "piexif", "exiftool"])

    return {
        "mode": mode,
        "percent": percent,
        "edge": edge,
        "ratio": ratio,
        "color": color,
        "format": output_format,
        "quality": quality,
        "no_metadata": not keep_metadata,
        "metadata_backend": metadata_backend,
    }


def _render_preview(uploaded_file, config) -> None:
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image) or image
    image.thumbnail((800, 800))

    try:
        plan = geometry.calculate_canvas(image.size, config)
        bordered = border.apply_border(image, plan, config.color)
    except PhotoBorderError as exc:
        st.warning(f"預覽失敗：{exc}")
        return

    st.image(bordered, caption="預覽（第一張，等比縮圖）", use_container_width=True)


def _run_batch(uploaded_files, config) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_dir = tmp_path / "in"
        output_dir = tmp_path / "out"

        uploads = [(f.name, f.getvalue()) for f in uploaded_files]
        logic.save_uploads(uploads, input_dir)

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def on_progress(index: int, total: int, result) -> None:
            progress_bar.progress(index / total)
            status = "完成" if result.success else f"失敗：{result.error}"
            status_text.text(f"[{index}/{total}] {result.src_path.name}：{status}")

        report = batch_mod.process_batch(
            input_dir, output_dir, config, progress_cb=on_progress
        )

        st.session_state["last_report"] = report
        st.session_state["last_zip"] = logic.zip_directory(output_dir)


def main() -> None:
    st.title("🖼️ 加白邊批次工具")
    st.caption("模仿 Lightroom for iPad「加邊框並匯出」，純留白 padding，保留原始 EXIF/ICC。")

    ui_values = _render_sidebar_controls()

    uploaded_files = st.file_uploader(
        "上傳照片（可多選）",
        type=["jpg", "jpeg", "png", "tif", "tiff", "heic", "heif"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("請先上傳照片。")
        return

    try:
        config = config_builder.build_border_config(**ui_values)
    except PhotoBorderError as exc:
        st.error(f"參數錯誤：{exc}")
        return

    st.write(f"已上傳 {len(uploaded_files)} 張照片")
    _render_preview(uploaded_files[0], config)

    if st.button("開始批次處理", type="primary"):
        _run_batch(uploaded_files, config)

    if "last_report" in st.session_state:
        report = st.session_state["last_report"]
        if report.failed == 0:
            st.success(f"全部完成：{report.succeeded}/{report.total}")
        else:
            st.warning(f"完成 {report.succeeded}/{report.total}，失敗 {report.failed}")
            for result in report.results:
                if not result.success:
                    st.text(f"✗ {result.src_path.name}：{result.error}")

        st.download_button(
            "下載全部結果（zip）",
            data=st.session_state["last_zip"],
            file_name="bordered_photos.zip",
            mime="application/zip",
        )


main()
