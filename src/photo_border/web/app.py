import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps

from photo_border.core import batch as batch_mod, border, config_builder, geometry
from photo_border.core.errors import PhotoBorderError
from photo_border.web import logic

st.set_page_config(page_title="PhotoFrame Lab", page_icon="🖼️", layout="centered")

# 放大預覽圖右上角的全螢幕（放大鏡）按鈕，預設太小不好點
st.markdown(
    """
    <style>
    div[data-testid="stImage"] button {
        width: 2.75rem !important;
        height: 2.75rem !important;
    }
    div[data-testid="stImage"] button svg {
        width: 1.75rem !important;
        height: 1.75rem !important;
    }
    [data-testid*="SidebarCollapse"] {
        width: 3rem !important;
        height: 3rem !important;
    }
    [data-testid*="SidebarCollapse"] svg {
        width: 2rem !important;
        height: 2rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 依 Lightroom for iPad「加邊框」的比例清單順序整理，IG/TikTok 標註沿用其實際用途
RATIO_PRESET_OPTIONS = {
    "原始（維持比例，四邊留白）": None,
    "1:1　📷 IG 正方形貼文": "1:1",
    "2:3": "2:3",
    "3:2": "3:2",
    "4:5　📷 IG 直式貼文": "4:5",
    "3:4　📷 IG 直式貼文": "3:4",
    "5:4　📷 IG 橫寬貼文": "5:4",
    "9:16　📷 IG 限動/Reels・🎵 TikTok": "9:16",
    "2:1": "2:1",
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
    ratio = RATIO_PRESET_OPTIONS[ratio_label]

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


_PREV_LABEL = "◀ 上一張"
_NEXT_LABEL = "下一張 ▶"


def _inject_swipe_handler() -> None:
    """在手機上左右滑動預覽圖時，模擬點擊上一張/下一張按鈕。

    Streamlit 本身沒有滑動手勢，這裡用注入的 JS 監聽 touch 事件，
    透過 window.parent.document 找到按鈕文字再觸發點擊（同源 iframe 才能這樣做）。
    用 __pfl_swipe_attached 旗標避免每次 rerun 重複註冊監聽器。
    """
    st.iframe(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;
            if (doc.__pfl_swipe_attached) return;
            doc.__pfl_swipe_attached = true;

            let startX = null;
            doc.addEventListener('touchstart', function(e) {{
                startX = e.changedTouches[0].screenX;
            }}, {{passive: true}});

            doc.addEventListener('touchend', function(e) {{
                if (startX === null) return;
                const dx = e.changedTouches[0].screenX - startX;
                startX = null;
                if (Math.abs(dx) < 60) return;

                const buttons = doc.querySelectorAll('button');
                let target = null;
                buttons.forEach(function(b) {{
                    const text = b.innerText || '';
                    if (dx < 0 && text.includes('下一張')) target = b;
                    if (dx > 0 && text.includes('上一張')) target = b;
                }});
                if (target && !target.disabled) target.click();
            }}, {{passive: true}});
        }})();
        </script>
        """,
        height=1,
    )


def _go_to_index(delta: int, total: int) -> None:
    """按鈕的 on_click callback：在 script rerun 之前先更新 session_state，
    這樣同一輪 rerun 裡按鈕的 disabled 狀態才會馬上反映新的 index，不會延遲一輪。
    """
    current = st.session_state.get("preview_index", 0)
    st.session_state["preview_index"] = max(0, min(total - 1, current + delta))


def _render_preview_navigator(uploaded_files):
    """多張照片時顯示「上一張/下一張」按鈕（含手機滑動），只有一張就不顯示。"""
    if len(uploaded_files) == 1:
        st.session_state["preview_index"] = 0
        return uploaded_files[0]

    total = len(uploaded_files)
    index = st.session_state.get("preview_index", 0)
    index = max(0, min(index, total - 1))
    st.session_state["preview_index"] = index

    col_prev, col_label, col_next = st.columns([1, 3, 1])
    with col_prev:
        st.button(
            _PREV_LABEL,
            disabled=(index == 0),
            on_click=_go_to_index,
            args=(-1, total),
            width="stretch",
        )
    with col_next:
        st.button(
            _NEXT_LABEL,
            disabled=(index == total - 1),
            on_click=_go_to_index,
            args=(1, total),
            width="stretch",
        )
    with col_label:
        st.markdown(
            f"<div style='text-align:center;padding-top:0.5rem'>"
            f"{index + 1} / {total}　{uploaded_files[index].name}</div>",
            unsafe_allow_html=True,
        )

    _inject_swipe_handler()
    return uploaded_files[index]


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

    st.image(bordered, caption="預覽（等比縮圖）", width="stretch")


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
    st.title("🖼️ PhotoFrame Lab")
    st.caption("留白，是為了讓照片自己說話。原始畫質與 EXIF/ICC 資訊完整保留。")

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
    preview_file = _render_preview_navigator(uploaded_files)
    _render_preview(preview_file, config)

    if st.button("開始批次處理", type="primary"):
        _run_batch(uploaded_files, config)

    _render_results(_compute_signature(uploaded_files, config))


def _render_footer() -> None:
    st.divider()
    st.caption(
        "作者：liaw-boy　・　特別感謝 Eric 支援硬體　・　"
        "[GitHub @liaw-boy](https://github.com/liaw-boy/photo_print)"
    )


main()
_render_footer()
