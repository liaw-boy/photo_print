import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

from photo_border.core import batch as batch_mod, border, config_builder, geometry
from photo_border.core.errors import PhotoBorderError
from photo_border.web import logic

st.set_page_config(page_title="加白邊工具", page_icon="🖼️", layout="centered")

RATIO_PRESET_OPTIONS = {
    "不需要（維持原比例）": None,
    "1:1 正方形": "1:1",
    "4:5 直式貼文": "4:5",
    "3:2 標準相片": "3:2",
    "9:16 限時動態": "9:16",
    "自訂": "__custom__",
}

FORMAT_OPTIONS = {
    "維持原格式": "keep",
    "JPEG": "jpeg",
    "PNG": "png",
    "TIFF": "tiff",
}


def _resolve_mode(ratio: str | None, percent: float) -> str:
    """依「有沒有選比例」與「留白百分比是否大於 0」決定內部的 BorderMode，
    使用者不需要理解 percent/aspect/aspect-then-percent 這幾個內部概念。
    """
    if ratio is not None:
        return "aspect-then-percent" if percent > 0 else "aspect"
    return "percent"


def _render_uploader():
    return st.sidebar.file_uploader(
        "上傳照片（可多選）",
        type=["jpg", "jpeg", "png", "tif", "tiff", "heic", "heif"],
        accept_multiple_files=True,
    )


def _render_sidebar_controls() -> dict:
    st.sidebar.markdown("### 1. 邊框樣式")

    ratio_label = st.sidebar.selectbox("補滿長寬比", list(RATIO_PRESET_OPTIONS), index=0)
    ratio_choice = RATIO_PRESET_OPTIONS[ratio_label]

    ratio = None
    if ratio_choice == "__custom__":
        col1, col2 = st.sidebar.columns(2)
        width = col1.number_input("寬", min_value=1, max_value=100, value=4)
        height = col2.number_input("高", min_value=1, max_value=100, value=5)
        ratio = f"{int(width)}:{int(height)}"
    elif ratio_choice is not None:
        ratio = ratio_choice

    percent = st.sidebar.slider("留白粗細（佔邊長比例）", 0.0, 0.3, 0.05, step=0.01)
    color = st.sidebar.color_picker("邊框顏色", "#FFFFFF")

    st.sidebar.divider()
    st.sidebar.markdown("### 2. 輸出設定")

    format_label = st.sidebar.selectbox("輸出格式", list(FORMAT_OPTIONS))
    output_format = FORMAT_OPTIONS[format_label]
    quality = st.sidebar.slider("JPEG 品質", 1, 100, 95)
    keep_metadata = st.sidebar.checkbox("保留 EXIF / ICC profile", value=True)

    with st.sidebar.expander("進階設定"):
        edge_label = st.radio(
            "留白粗細的參考邊", ["短邊", "長邊"], index=0, horizontal=True
        )
        edge = "short" if edge_label == "短邊" else "long"
        metadata_backend = st.selectbox("Metadata 處理方式", ["auto", "piexif", "exiftool"])

    return {
        "mode": _resolve_mode(ratio, percent),
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

    col_before, col_after = st.columns(2)
    with col_before:
        st.image(image, caption="原圖", use_container_width=True)
    with col_after:
        st.image(bordered, caption="加框後", use_container_width=True)


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
        st.session_state["last_signature"] = _compute_signature(uploaded_files, config)


def _compute_signature(uploaded_files, config) -> tuple:
    """代表「這次處理用的檔案 + 參數」的簽章，用來偵測結果是否已過期。"""
    files_signature = tuple((f.name, f.size) for f in uploaded_files)
    return (files_signature, config)


def _render_results(current_signature: tuple) -> None:
    if "last_report" not in st.session_state:
        return

    if st.session_state.get("last_signature") != current_signature:
        st.info("設定或上傳的照片已變更，請重新按「開始批次處理」以取得最新結果。")
        return

    report = st.session_state["last_report"]
    if report.failed == 0:
        st.success(f"全部完成：{report.succeeded}/{report.total}")
    else:
        st.warning(f"完成 {report.succeeded}/{report.total}，失敗 {report.failed}")
        for result in report.results:
            if not result.success:
                st.error(f"✗ {result.src_path.name}：{result.error}")

    st.download_button(
        "下載全部結果（zip）",
        data=st.session_state["last_zip"],
        file_name="bordered_photos.zip",
        mime="application/zip",
    )


def main() -> None:
    st.title("🖼️ 加白邊批次工具")
    st.caption("模仿 Lightroom for iPad「加邊框並匯出」，純留白 padding，保留原始 EXIF/ICC。")

    uploaded_files = _render_uploader()
    ui_values = _render_sidebar_controls()

    if not uploaded_files:
        st.info("請先在左側上傳照片。")
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

    _render_results(_compute_signature(uploaded_files, config))


main()
