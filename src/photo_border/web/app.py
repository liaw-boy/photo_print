import mimetypes
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
    /* 側邊欄「收合／展開」是 Streamlit 兩個不同元件（收合鈕在側邊欄右緣、
       展開鈕釘在整個頁面左上角），原生位置不一致。這裡把兩顆都固定到畫面
       左上角同一個位置、同一個尺寸，不管側邊欄開或關，這顆按鈕看起來都是
       同一顆、位置不會跳來跳去。 */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stExpandSidebarButton"] button {
        visibility: visible !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"] {
        position: fixed !important;
        top: 0.6rem !important;
        left: 0.6rem !important;
        z-index: 999 !important;
        width: 3rem !important;
        height: 3rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stExpandSidebarButton"] svg {
        width: 2rem !important;
        height: 2rem !important;
    }
    [data-testid="stSidebarCollapseButton"] button {
        width: 100% !important;
        height: 100% !important;
    }
    .st-key-pfl_stage {
        position: relative;
        overflow: hidden;
        gap: 0 !important;
    }
    @keyframes pfl-fade-slide-in {
        from { opacity: 0; transform: scale(0.985); }
        to { opacity: 1; transform: scale(1); }
    }
    @keyframes pfl-slide-in-from-right {
        from { opacity: 0; transform: translateX(36px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes pfl-slide-in-from-left {
        from { opacity: 0; transform: translateX(-36px); }
        to { opacity: 1; transform: translateX(0); }
    }
    [class*="st-key-pfl_frame_init_"] {
        animation: pfl-fade-slide-in 0.28s ease;
    }
    [class*="st-key-pfl_frame_next_"] {
        animation: pfl-slide-in-from-right 0.32s cubic-bezier(0.22, 1, 0.36, 1);
        will-change: transform, opacity;
    }
    [class*="st-key-pfl_frame_prev_"] {
        animation: pfl-slide-in-from-left 0.32s cubic-bezier(0.22, 1, 0.36, 1);
        will-change: transform, opacity;
    }
    /* 這兩個 wrap 都撐滿整個 stage 的寬高（避免依賴 Streamlit 內部 width:100%
       的假設打架），實際的左右位置靠 flex justify-content 推到兩端，
       而不是用 left/right 直接定位——這樣才不會兩顆按鈕疊在一起。 */
    .st-key-pfl_prev_wrap,
    .st-key-pfl_next_wrap {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        width: 100% !important;
        height: 100% !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        z-index: 5;
        pointer-events: none;
    }
    .st-key-pfl_prev_wrap { justify-content: flex-start !important; }
    .st-key-pfl_next_wrap { justify-content: flex-end !important; }
    .st-key-pfl_prev_wrap > div,
    .st-key-pfl_next_wrap > div {
        pointer-events: none;
        width: auto !important;
    }
    .st-key-pfl_prev_wrap { padding-left: 0.5rem; }
    .st-key-pfl_next_wrap { padding-right: 0.5rem; }
    .st-key-pfl_prev_wrap button,
    .st-key-pfl_next_wrap button {
        pointer-events: auto;
        background: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(255, 255, 255, 0.4);
        border-radius: 50%;
        width: 3rem;
        height: 3rem;
        padding: 0;
        backdrop-filter: blur(6px);
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
        transition: transform 0.15s ease, background 0.15s ease;
    }
    .st-key-pfl_prev_wrap button span,
    .st-key-pfl_next_wrap button span {
        color: #fff;
        filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.6));
    }
    .st-key-pfl_prev_wrap button svg,
    .st-key-pfl_next_wrap button svg {
        width: 1.5rem !important;
        height: 1.5rem !important;
    }
    .st-key-pfl_prev_wrap button:hover:not(:disabled),
    .st-key-pfl_next_wrap button:hover:not(:disabled) {
        background: rgba(255, 255, 255, 0.28);
        transform: scale(1.08);
    }
    .st-key-pfl_prev_wrap button:disabled,
    .st-key-pfl_next_wrap button:disabled {
        opacity: 0.3;
        box-shadow: none;
    }
    .pfl-index-label {
        position: absolute;
        bottom: 0.5rem;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.45);
        color: #fff;
        padding: 0.15rem 0.75rem;
        border-radius: 999px;
        font-size: 0.8rem;
        z-index: 5;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 選單裡「自訂比例」那個選項的內部標記值，跟代表「原始比例」的 None 區分開來；
# 選到這個值時，UI 會多長出寬/高兩個數字輸入框讓使用者自己填。
_CUSTOM_RATIO = "custom"

# 依 Lightroom for iPad「加邊框」的比例清單順序整理，IG/TikTok 標註沿用其實際用途
# (ratio, 顯示文字, 平台標註或 None)
_RATIO_DEFS = [
    (None, "原始（維持比例）", None),
    ("1:1", "1:1", "IG 正方形貼文"),
    ("2:3", "2:3", None),
    ("3:2", "3:2", None),
    ("4:5", "4:5", "IG 直式貼文"),
    ("3:4", "3:4", "IG 直式貼文"),
    ("5:4", "5:4", "IG 橫寬貼文"),
    ("9:16", "9:16", "IG 限動/Reels・TikTok"),
    ("2:1", "2:1", None),
    (_CUSTOM_RATIO, "自訂比例", None),
]


def _ratio_shape_icon(ratio: str | None) -> str:
    """依比例的長寬關係回傳一個示意形狀的小圖示，不用讀數字就能看出方向。"""
    if ratio is None:
        return "🔁"
    if ratio == _CUSTOM_RATIO:
        return "✏️"
    width, height = (int(part) for part in ratio.split(":"))
    if width == height:
        return "⬜"
    # 用手機（直式）／螢幕（橫式）比方向箭頭更直覺，也比矩形符號好看，
    # 而且這兩個 emoji 在各字型/瀏覽器下都能穩定顯示成彩色圖示。
    return "🖥️" if width > height else "📱"


def _build_ratio_options() -> dict:
    options = {}
    for ratio, text, tag in _RATIO_DEFS:
        icon = _ratio_shape_icon(ratio)
        label = f"{icon}　{text}"
        if tag:
            label = f"{label}　({tag})"
        options[label] = ratio
    return options


RATIO_PRESET_OPTIONS = _build_ratio_options()

FORMAT_OPTIONS = {
    "維持原格式": "keep",
    "JPEG": "jpeg",
    "PNG": "png",
    "TIFF": "tiff",
}

EXPORT_MODE_OPTIONS = {
    "打包成 zip": "zip",
    "個別下載": "individual",
}


def _is_ios_user_agent(user_agent: str) -> bool:
    """純字串判斷，跟 Streamlit context 分開方便單元測試。"""
    ua_lower = user_agent.lower()
    return any(token in ua_lower for token in ("iphone", "ipad", "ipod"))


def _is_download_limited_user_agent(user_agent: str) -> bool:
    """判斷是不是「一次使用者操作只能觸發一個下載」的 WebKit 系瀏覽器。

    不只 iOS（不管殼是 Safari／Chrome／Firefox，底層都被迫用 WebKit）——連
    桌機版 macOS Safari 都有一樣的限制，連續同步觸發好幾個下載，實測只有
    最後一個真的會存下來，其餘都被悄悄吃掉。用「是不是 Safari／WebKit」
    判斷，而不是只挑 iOS，才不會漏掉桌機 Safari 這個同樣會出問題的情況。
    """
    ua_lower = user_agent.lower()
    if _is_ios_user_agent(user_agent):
        return True
    is_safari = "safari" in ua_lower
    is_other_engine = any(
        token in ua_lower
        for token in ("chrome", "chromium", "crios", "edg", "firefox", "fxios", "opr")
    )
    return is_safari and not is_other_engine


def _is_download_limited_client() -> bool:
    try:
        user_agent = st.context.headers.get("User-Agent", "")
    except Exception:
        return False
    return _is_download_limited_user_agent(user_agent)


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

    if ratio == _CUSTOM_RATIO:
        custom_col_w, custom_col_h = st.sidebar.columns(2)
        custom_width = custom_col_w.number_input("寬", min_value=1, value=16, step=1)
        custom_height = custom_col_h.number_input("高", min_value=1, value=9, step=1)
        ratio = f"{custom_width}:{custom_height}"

    percent = st.sidebar.slider("留白粗細（佔邊長比例）", 0.0, 0.3, 0.05, step=0.01)
    color = st.sidebar.color_picker("邊框顏色", "#FFFFFF")

    st.sidebar.divider()
    st.sidebar.markdown("### 2. 輸出設定")

    format_label = st.sidebar.selectbox("輸出格式", list(FORMAT_OPTIONS))
    output_format = FORMAT_OPTIONS[format_label]
    quality = st.sidebar.slider("JPEG 品質", 1, 100, 95)
    keep_metadata = st.sidebar.checkbox("保留 EXIF / ICC profile", value=True)
    export_label = st.sidebar.radio(
        "匯出方式", list(EXPORT_MODE_OPTIONS), index=1, horizontal=True
    )
    export_mode = EXPORT_MODE_OPTIONS[export_label]

    with st.sidebar.expander("進階設定"):
        # Metadata 這個下拉選單放前面：它離側邊欄底部越遠，展開選項時
        # 越不容易被 stSidebarContent 的內部捲軸邊界切到看不見。
        metadata_backend = st.selectbox("Metadata 處理方式", ["auto", "piexif", "exiftool"])
        edge_label = st.radio(
            "留白粗細的參考邊", ["短邊", "長邊"], index=0, horizontal=True
        )
        edge = "short" if edge_label == "短邊" else "long"

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
        "export_mode": export_mode,
    }


_PREV_ICON = ":material/chevron_left:"
_NEXT_ICON = ":material/chevron_right:"


def _inject_swipe_handler() -> None:
    """在手機上左右滑動預覽圖時，模擬點擊上一張/下一張按鈕；並在切換照片時，
    讓「舊照片」往滑動方向淡出滑走，模擬手機相簿左右滑動瀏覽的手感。

    Streamlit 本身沒有滑動手勢也不會保留舊的圖片節點（整個 re-render 直接換掉），
    這裡注入 JS：
    1. 監聽 touch 事件，模擬點擊上一張/下一張按鈕（同源 iframe 才能這樣做）。
    2. 用 MutationObserver 盯著預覽區：Streamlit 換上新照片、舊的 <img> 節點被
       移除的當下，把舊圖片複製一份浮貼在原本的位置上，再讓它往反方向滑出淡出，
       跟新照片（由 CSS keyframe 負責滑入）交叉播放，湊成一個雙向的滑動轉場。
    用 __pfl_swipe_attached 旗標避免每次 rerun 重複註冊監聽器/Observer。
    """
    st.iframe(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            if (doc.__pfl_swipe_attached) return;
            doc.__pfl_swipe_attached = true;

            let dir = 1;  // 1 = 下一張（新照片從右滑入，舊照片往左滑出），-1 = 上一張

            function bindDirButtons() {
                const next = doc.querySelector('.st-key-pfl_next_btn button');
                const prev = doc.querySelector('.st-key-pfl_prev_btn button');
                if (next && !next.__pflBound) {
                    next.__pflBound = true;
                    next.addEventListener('click', function() { dir = 1; });
                }
                if (prev && !prev.__pflBound) {
                    prev.__pflBound = true;
                    prev.addEventListener('click', function() { dir = -1; });
                }
            }

            let startX = null;
            doc.addEventListener('touchstart', function(e) {
                startX = e.changedTouches[0].screenX;
            }, {passive: true});

            doc.addEventListener('touchend', function(e) {
                if (startX === null) return;
                const dx = e.changedTouches[0].screenX - startX;
                startX = null;
                if (Math.abs(dx) < 60) return;

                dir = dx < 0 ? 1 : -1;
                const selector = dx < 0
                    ? '.st-key-pfl_next_btn button'
                    : '.st-key-pfl_prev_btn button';
                const target = doc.querySelector(selector);
                if (target && !target.disabled) target.click();
            }, {passive: true});

            // 左右方向鍵切換上一張/下一張；正在輸入框（文字/數字/下拉選單）裡打字時
            // 不要攔截，不然使用者按方向鍵微調數字輸入會被誤判成換照片。
            doc.addEventListener('keydown', function(e) {
                if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;

                const active = doc.activeElement;
                const isEditable = active && (
                    active.tagName === 'INPUT'
                    || active.tagName === 'TEXTAREA'
                    || active.tagName === 'SELECT'
                    || active.isContentEditable
                );
                if (isEditable) return;

                dir = e.key === 'ArrowRight' ? 1 : -1;
                const selector = e.key === 'ArrowRight'
                    ? '.st-key-pfl_next_btn button'
                    : '.st-key-pfl_prev_btn button';
                const target = doc.querySelector(selector);
                if (target && !target.disabled) {
                    e.preventDefault();
                    target.click();
                }
            });

            function attachGhostObserver() {
                const stage = doc.querySelector('.st-key-pfl_stage');
                if (!stage || stage.__pflObserved) return;
                stage.__pflObserved = true;

                const observer = new MutationObserver(function(mutations) {
                    bindDirButtons();
                    for (const mutation of mutations) {
                        mutation.removedNodes.forEach(function(node) {
                            if (!(node instanceof doc.defaultView.HTMLElement)) return;
                            const oldImg = node.querySelector && node.querySelector("img");
                            if (!oldImg) return;

                            const stageRect = stage.getBoundingClientRect();
                            const oldRect = oldImg.getBoundingClientRect();

                            // 不能直接重用 oldImg.src：Streamlit 換照片後，舊圖片在
                            // 伺服器那邊的媒體網址通常會馬上失效（重新抓會 404、
                            // 顯示破圖），所以改用 canvas 把「已經解碼好的舊畫面」
                            // 原地畫下來當作幽靈圖，不用再發一次網路請求。
                            let dataUrl = null;
                            try {
                                const canvas = document.createElement("canvas");
                                canvas.width = oldImg.naturalWidth || oldRect.width;
                                canvas.height = oldImg.naturalHeight || oldRect.height;
                                canvas.getContext("2d").drawImage(
                                    oldImg, 0, 0, canvas.width, canvas.height
                                );
                                dataUrl = canvas.toDataURL("image/png");
                            } catch (err) {
                                return;  // 畫不出來就乾脆不播幽靈圖轉場，跳過即可
                            }
                            if (!dataUrl) return;

                            const ghost = document.createElement("img");
                            ghost.src = dataUrl;
                            ghost.style.cssText = [
                                "position:absolute",
                                "left:" + (oldRect.left - stageRect.left) + "px",
                                "top:" + (oldRect.top - stageRect.top) + "px",
                                "width:" + oldRect.width + "px",
                                "height:" + oldRect.height + "px",
                                "object-fit:contain",
                                "z-index:3",
                                "pointer-events:none",
                                "transition: transform 0.32s cubic-bezier(0.22,1,0.36,1), opacity 0.32s ease",
                                "will-change: transform, opacity",
                            ].join(";");
                            stage.appendChild(ghost);
                            ghost.getBoundingClientRect();  // 強制 reflow，讓 transition 真的會播放
                            requestAnimationFrame(function() {
                                ghost.style.transform = "translateX(" + (dir * -40) + "px)";
                                ghost.style.opacity = "0";
                            });
                            setTimeout(function() { ghost.remove(); }, 360);
                        });
                    }
                });
                observer.observe(stage, {childList: true, subtree: true});
            }

            bindDirButtons();
            attachGhostObserver();
            // stage 有時會比這段 script 晚掛載，短暫重試幾次
            let tries = 0;
            const retry = setInterval(function() {
                bindDirButtons();
                attachGhostObserver();
                tries += 1;
                if (tries > 20) clearInterval(retry);
            }, 300);
        })();
        </script>
        """,
        height=1,
    )


def _go_to_index(delta: int, uploaded_files) -> None:
    """按鈕的 on_click callback：在 script rerun 之前先更新 session_state，
    這樣同一輪 rerun 裡按鈕的 disabled 狀態才會馬上反映新的 index，不會延遲一輪。

    同時更新 preview_file_id，確保切換後鎖定的是「那一張照片」本身，而不是
    單純的位置索引（位置在檔案被刪除/新增後意義會跟著改變）。
    """
    total = len(uploaded_files)
    current = st.session_state.get("preview_index", 0)
    new_index = max(0, min(total - 1, current + delta))
    st.session_state["preview_index"] = new_index
    st.session_state["preview_file_id"] = uploaded_files[new_index].file_id
    st.session_state["preview_dir"] = "next" if delta > 0 else "prev"


def _select_preview_file(uploaded_files):
    """選出這次要預覽的檔案。

    用 preview_file_id（Streamlit 上傳檔案的穩定識別碼）追蹤「使用者正在看哪一張」，
    而不是單純的 list 位置索引——否則刪除某張照片後，其餘照片在 list 裡的位置
    會全部往前移，若只靠索引，畫面會悄悄跳去顯示另一張不相干的照片。
    只有在目前預覽的那張本身被刪除、找不到對應 file_id 時，才退回用舊的位置索引
    （並修正越界），改顯示同一個位置上現在的照片。
    """
    total = len(uploaded_files)
    if total == 1:
        st.session_state["preview_index"] = 0
        st.session_state["preview_file_id"] = uploaded_files[0].file_id
        return uploaded_files[0], 1, 0

    file_id = st.session_state.get("preview_file_id")
    index = next(
        (i for i, f in enumerate(uploaded_files) if f.file_id == file_id), None
    )
    if index is None:
        index = st.session_state.get("preview_index", 0)
        index = max(0, min(index, total - 1))

    st.session_state["preview_index"] = index
    st.session_state["preview_file_id"] = uploaded_files[index].file_id
    return uploaded_files[index], total, index


def _render_preview_nav_overlay(uploaded_file, total: int, index: int, uploaded_files) -> None:
    """在預覽圖上浮貼半透明的上一張/下一張圓形按鈕（垂直置中於圖片高度）。"""
    with st.container(key="pfl_prev_wrap"):
        st.button(
            "",
            icon=_PREV_ICON,
            disabled=(index == 0),
            on_click=_go_to_index,
            args=(-1, uploaded_files),
            key="pfl_prev_btn",
        )
    with st.container(key="pfl_next_wrap"):
        st.button(
            "",
            icon=_NEXT_ICON,
            disabled=(index == total - 1),
            on_click=_go_to_index,
            args=(1, uploaded_files),
            key="pfl_next_btn",
        )
    st.markdown(
        f"<div class='pfl-index-label'>{index + 1} / {total}　{uploaded_file.name}</div>",
        unsafe_allow_html=True,
    )
    _inject_swipe_handler()


def _render_preview(uploaded_file, config) -> bool:
    """畫出加框後的預覽圖，回傳是否成功（失敗時只顯示警告，不畫圖）。"""
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image) or image
    image.thumbnail((800, 800))

    try:
        plan = geometry.calculate_canvas(image.size, config)
        bordered = border.apply_border(image, plan, config.color)
    except PhotoBorderError as exc:
        st.warning(f"預覽失敗：{exc}")
        return False

    st.image(bordered, width="stretch")
    return True


def _render_preview_stage(uploaded_files, config) -> None:
    """預覽圖 + 浮動導覽按鈕的容器；只有一張照片時不顯示導覽按鈕。

    圖片包在一個以 file_id 命名的 container 裡（而不是位置索引）：換照片時
    key 改變會讓 Streamlit 重新掛載該節點，瀏覽器才會重新播放 CSS 進場動畫；
    用 file_id 而非索引，是為了在其他照片被刪除、目前這張只是位置往前移時，
    不會誤判成「換了一張」而多播一次動畫。

    key 裡還帶了上一次按「上一張/下一張」的方向（next/prev，第一次載入是
    init），讓 CSS 進場動畫可以依方向從左或右滑入，搭配 _inject_swipe_handler
    注入的 JS（讓舊照片往反方向滑出淡出），模擬手機相簿左右滑動的效果。
    """
    preview_file, total, index = _select_preview_file(uploaded_files)
    direction = st.session_state.get("preview_dir", "init")
    with st.container(key="pfl_stage"):
        with st.container(key=f"pfl_frame_{direction}_{preview_file.file_id}"):
            ok = _render_preview(preview_file, config)
        if ok and total > 1:
            _render_preview_nav_overlay(preview_file, total, index, uploaded_files)
    if ok:
        st.caption("預覽（等比縮圖）")


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

        # 兩種匯出方式（zip / 個別下載）都先算好存起來，事後切換匯出方式
        # 不需要重新按一次「開始批次處理」。
        individual_files = [
            (result.dst_path.name, result.dst_path.read_bytes())
            for result in report.results
            if result.success and result.dst_path is not None
        ]

        st.session_state["last_report"] = report
        st.session_state["last_zip"] = logic.zip_directory(output_dir)
        st.session_state["last_files"] = individual_files
        st.session_state["last_signature"] = _compute_signature(uploaded_files, config)


def _compute_signature(uploaded_files, config) -> tuple:
    """代表「這次處理用的檔案 + 參數」的簽章，用來偵測結果是否已過期。"""
    files_signature = tuple((f.name, f.size) for f in uploaded_files)
    return (files_signature, config)


def _inject_auto_download() -> None:
    """處理完成後自動幫使用者點一次下載按鈕，不用使用者自己再按第二次。

    下載按鈕本體還在（瀏覽器下載一定要有真實的使用者互動/點擊事件才能觸發），
    只是整個 container 用 CSS 藏起來，改用注入的 JS 自動 .click() 一次。
    多檔案時所有按鈕要在同一輪、不中斷地連續點完（不能用 setTimeout 分開間隔）——
    瀏覽器的下載觸發跟「使用者互動」的有效期很短，中間只要一有非同步延遲，
    間隔開來的後面幾個點擊就會被瀏覽器悄悄擋掉，只有第一個下載會成功。

    點過的按鈕不能只在 DOM 節點本身標記：download_button 被點擊本身也算一次
    Streamlit 互動，會觸發 script rerun，而 rerun 之間 Streamlit 不一定會重用
    同一個按鈕的 DOM 節點——節點換掉的話，標記在節點上的旗標就跟著消失，這個
    retry loop 就會把同一個檔案重新點一次，造成間歇性的重複下載。改成把「點過
    哪些」記在 window.parent.document 本身（跨這個 iframe 每次 rerun 重新注入
    都還在），用按鈕自己的 Streamlit key（穩定不變）當識別，而不是 DOM 節點。
    """
    st.markdown(
        """
        <style>
        [class*="st-key-pfl_dlarea_"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.iframe(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            if (!doc.__pflClickedDownloadKeys) {
                doc.__pflClickedDownloadKeys = new Set();
            }

            function autoClickDownloads() {
                const items = doc.querySelectorAll(
                    '[class*="st-key-pfl_dlarea_"] [class*="st-key-pfl_download_"]'
                );
                items.forEach(function(item) {
                    const match = item.className.match(/st-key-pfl_download_\\S+/);
                    if (!match) return;
                    const stableKey = match[0];
                    if (doc.__pflClickedDownloadKeys.has(stableKey)) return;

                    const button = item.querySelector('button');
                    if (!button) return;
                    doc.__pflClickedDownloadKeys.add(stableKey);
                    button.click();
                });
            }

            autoClickDownloads();
            let tries = 0;
            const retry = setInterval(function() {
                autoClickDownloads();
                tries += 1;
                if (tries > 10) clearInterval(retry);
            }, 300);
        })();
        </script>
        """,
        height=1,
    )


def _render_results(current_signature: tuple, export_mode: str, export_attempt: int) -> None:
    if "last_report" not in st.session_state:
        return

    if st.session_state.get("last_signature") != current_signature:
        st.info("設定或上傳的照片已變更，請重新按「匯出」以取得最新結果。")
        return

    report = st.session_state["last_report"]
    if report.failed == 0:
        st.success(f"全部完成：{report.succeeded}/{report.total}")
    else:
        st.warning(f"完成 {report.succeeded}/{report.total}，失敗 {report.failed}")
        for result in report.results:
            if not result.success:
                st.error(f"✗ {result.src_path.name}：{result.error}")

    # 這個 container 裡的下載按鈕不會真的顯示給使用者按——處理完成後用注入的 JS
    # 自動幫忙點過一次，直接開始下載，使用者不用再手動點。多檔案時所有按鈕會在
    # 同一輪同步點完（見 _inject_auto_download 的說明），瀏覽器才不會漏掉。
    # key 裡帶著 export_attempt：每次「真的按下匯出」都是新的嘗試，重新掛載這個
    # container 讓按鈕變成全新的 DOM 節點，這樣使用者才能靠重按「匯出」來重試
    # 下載（例如 iOS Safari 只成功下載第一張時，可以重按幾次補下載其餘檔案）。
    with st.container(key=f"pfl_dlarea_{export_attempt}"):
        if export_mode == "individual":
            for name, content in st.session_state["last_files"]:
                st.download_button(
                    f"下載 {name}",
                    data=content,
                    file_name=name,
                    mime=mimetypes.guess_type(name)[0] or "application/octet-stream",
                    key=f"pfl_download_{export_attempt}_{name}",
                )
        else:
            st.download_button(
                "下載全部結果（zip）",
                data=st.session_state["last_zip"],
                file_name="bordered_photos.zip",
                mime="application/zip",
                key=f"pfl_download_zip_{export_attempt}",
            )
        _inject_auto_download()


def main() -> None:
    st.title("🖼️ PhotoFrame Lab", anchor=False)
    st.caption("留白，是為了讓照片自己說話。原始畫質與 EXIF/ICC 資訊完整保留。")

    uploaded_files = _render_uploader()
    ui_values = _render_sidebar_controls()
    export_mode = ui_values.pop("export_mode")

    if not uploaded_files:
        st.info("請先在左側上傳照片。")
        return

    if export_mode == "individual" and len(uploaded_files) > 1 and _is_download_limited_client():
        # Safari／WebKit（含桌機版與 iOS）一次操作只能觸發一次下載，個別下載
        # 模式對多張照片一定會漏檔，這裡直接改用 zip 打包，一次下載一個檔案
        # 就不會踩到這個平台限制。
        export_mode = "zip"
        st.info("偵測到 Safari／iOS 瀏覽器：多張照片會自動改用「打包成 zip」下載，避免下載失敗。")

    try:
        config = config_builder.build_border_config(**ui_values)
    except PhotoBorderError as exc:
        st.error(f"參數錯誤：{exc}")
        return

    st.write(f"已上傳 {len(uploaded_files)} 張照片")
    _render_preview_stage(uploaded_files, config)

    current_signature = _compute_signature(uploaded_files, config)
    if st.button("匯出", type="primary"):
        # 照片和設定都跟上次那次「匯出」完全一樣的話，不用重新跑一次批次處理
        # （純粹省運算，結果反正一樣）；但每次「真的按下」這顆按鈕都算一次新的
        # 匯出嘗試（export_attempt 遞增），讓下載按鈕的 container 重新掛載、
        # 自動下載的 JS 標記跟著重置——這樣使用者才能在下載失敗時重按「匯出」
        # 重新觸發一次下載，而不是永遠被舊的「已經點過」標記卡住。
        if st.session_state.get("last_signature") != current_signature:
            _run_batch(uploaded_files, config)
        st.session_state["export_attempt"] = st.session_state.get("export_attempt", 0) + 1

    _render_results(current_signature, export_mode, st.session_state.get("export_attempt", 0))


def _render_footer() -> None:
    st.divider()
    st.caption(
        "作者：liaw-boy　・　特別感謝 Eric 支援硬體、網域　・　"
        "[GitHub @liaw-boy](https://github.com/liaw-boy/photo_print)"
    )
    st.caption(
        "隱私聲明：上傳的照片僅用於本次加框處理，暫存於伺服器記憶體/暫存資料夾，"
        "處理完成或分頁關閉後即釋放，不會另外保存、備份或提供第三方使用。"
        "本工具不建立帳號、不做任何追蹤或分析。"
    )


main()
_render_footer()
