"""
Main content area: hero banner, data loading orchestration, and row display.
"""

import streamlit as st
from backend.data_loader import (
    HF_TOKEN,
    load_rows_from_upload,
    load_rows_streaming,
    load_rows_hfapi,
)
from backend.rendering import escape, render_row


def render_hero():
    """Render the hero banner and HF token status."""
    st.markdown(
        '<div class="hero-block"><h1>🔬 LLM Trace Viewer</h1>'
        '<p>Browse HuggingFace datasets or local CSV / JSONL files with nested chat traces, '
        'tool calls, and reasoning steps — rendered beautifully.</p></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"{'🔑 HF_TOKEN loaded' if HF_TOKEN else '🔓 No HF_TOKEN (public datasets only)'}  ·  "
        f"HuggingFace (streaming → HfApi) + CSV / JSONL upload"
    )


def init_session_state():
    """Ensure session state keys exist."""
    if "loaded_rows" not in st.session_state:
        st.session_state.loaded_rows = None
        st.session_state.loaded_features = None
        st.session_state.loaded_meta = {}


def handle_load(sidebar_state):
    """Orchestrate data loading based on sidebar selections."""
    data_source = sidebar_state["data_source"]
    dataset_id = sidebar_state["dataset_id"]
    uploaded_file = sidebar_state["uploaded_file"]
    selected_config = sidebar_state["selected_config"]
    selected_split = sidebar_state["selected_split"]
    hfapi_revision = sidebar_state["hfapi_revision"]
    num_rows = sidebar_state["num_rows"]
    sampling_mode = sidebar_state["sampling_mode"]
    random_seed = sidebar_state["random_seed"]
    load_btn = sidebar_state["load_btn"]

    can_load_hf = data_source == "HuggingFace Dataset" and dataset_id and selected_config and selected_split
    can_load_file = data_source != "HuggingFace Dataset" and uploaded_file is not None

    if load_btn and (can_load_hf or can_load_file):
        mode_str = "random" if sampling_mode == "Random sample" else "top"
        rows = None
        col_info = None
        load_method = None

        if can_load_file:
            try:
                with st.spinner(f"Reading {uploaded_file.name}..."):
                    rows, col_info = load_rows_from_upload(
                        uploaded_file, num_rows, mode_str, random_seed,
                    )
                    load_method = "upload"
            except Exception as file_err:
                st.error(f"Failed to read file: {file_err}")
                import traceback
                with st.expander("Full error"):
                    st.code(traceback.format_exc())
        else:
            # ── HuggingFace: try streaming first ──
            try:
                with st.spinner("Loading via streaming..."):
                    rows, col_info = load_rows_streaming(
                        dataset_id.strip(), selected_config, selected_split,
                        num_rows, mode_str, random_seed,
                    )
                    load_method = "streaming"
            except Exception as stream_err:
                st.warning(f"Streaming failed: {stream_err}")
                # ── Fallback to HfApi + parquet ──
                revision = hfapi_revision or "refs/convert/parquet"
                try:
                    with st.spinner("Falling back to HfApi parquet download..."):
                        rows, col_info = load_rows_hfapi(
                            dataset_id.strip(), selected_config, selected_split,
                            revision, num_rows, mode_str, random_seed,
                        )
                        load_method = "hfapi"
                except Exception as hf_err:
                    st.error(
                        f"Both methods failed.\n\nStreaming: {stream_err}\n\nHfApi: {hf_err}"
                    )
                    import traceback
                    with st.expander("Full error"):
                        st.code(traceback.format_exc())

        if rows is not None:
            st.session_state.loaded_rows = rows
            st.session_state.loaded_features = col_info
            meta_dataset = uploaded_file.name if can_load_file else dataset_id
            meta_config = "—" if can_load_file else selected_config
            meta_split = "—" if can_load_file else selected_split
            st.session_state.loaded_meta = {
                "dataset": meta_dataset, "config": meta_config,
                "split": meta_split, "mode": mode_str,
                "count": len(rows), "method": load_method,
            }


def render_data():
    """Render the loaded dataset rows, or the empty-state placeholder."""
    if st.session_state.loaded_rows is not None:
        meta = st.session_state.loaded_meta
        features = st.session_state.loaded_features or []
        rows = st.session_state.loaded_rows
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Dataset", meta.get("dataset", "").split("/")[-1])
        with c2:
            st.metric("Config / Split", f'{meta.get("config", "")}/{meta.get("split", "")}')
        with c3:
            st.metric("Loaded via", meta.get("method", "?"))
        with c4:
            st.metric("Showing", f'{meta.get("count", 0)} rows ({meta.get("mode", "top")})')
        if features:
            with st.expander("📋 Column Schema", expanded=False):
                st.markdown(
                    "".join(
                        f'<span class="feat-badge">'
                        f'<span class="feat-name">{escape(f["name"])}</span>'
                        f'<span class="feat-type">{escape(f["type"])}</span></span>'
                        for f in features
                    ),
                    unsafe_allow_html=True,
                )
        st.markdown("---")
        for i, row in enumerate(rows):
            render_row(row, i if meta.get("mode") == "top" else f"~{i}", features)
    else:
        st.markdown(
            '<div style="text-align:center;padding:80px 20px;color:#94a3b8">'
            '<div style="font-size:48px;margin-bottom:16px">🔬</div>'
            '<div style="font-size:18px;font-weight:600;color:#475569;margin-bottom:8px">'
            'No data loaded yet</div>'
            '<div style="font-size:14px;max-width:400px;margin:0 auto;line-height:1.6">'
            'Enter a HuggingFace dataset ID or upload a CSV / JSONL file in the sidebar, '
            'then click <strong>Load Data</strong> to start exploring.</div></div>',
            unsafe_allow_html=True,
        )
