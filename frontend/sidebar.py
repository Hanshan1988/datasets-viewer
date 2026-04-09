"""
Sidebar UI components: data source selection, config/split pickers, sampling controls.
"""

import streamlit as st
from backend.data_loader import HF_TOKEN, get_configs_and_splits


def render_sidebar():
    """Render the sidebar and return the user's selections as a dict."""
    with st.sidebar:
        st.markdown("### 📦 Data Source")
        data_source = st.radio(
            "Source", ["HuggingFace Dataset", "Upload File (CSV / JSONL)"],
            index=0, horizontal=True,
        )

        dataset_id = None
        uploaded_file = None
        all_splits = []
        configs = []
        discovery_method = None
        selected_config = selected_split = None
        hfapi_revision = None

        if data_source == "HuggingFace Dataset":
            dataset_id = st.text_input(
                "HuggingFace Dataset ID",
                value="Agent-Ark/Toucan-1.5M",
                placeholder="org/dataset-name",
            )
            if dataset_id:
                try:
                    with st.spinner("Scanning dataset..."):
                        all_splits, discovery_method = get_configs_and_splits(dataset_id.strip())
                        configs = sorted(set(s["config"] for s in all_splits))
                        method_label = "streaming" if discovery_method == "streaming" else "HfApi parquet"
                        st.success(
                            f"{len(configs)} config(s), {len(all_splits)} split(s) — via {method_label}",
                            icon="✅",
                        )
                except Exception as e:
                    st.error(str(e))

            if configs:
                selected_config = st.selectbox("Subset (config)", configs, index=0)
                csplits = sorted(set(
                    s["split"] for s in all_splits if s["config"] == selected_config
                ))
                if csplits:
                    selected_split = st.selectbox("Split", csplits, index=0)
                    for s in all_splits:
                        if s["config"] == selected_config and s["split"] == selected_split:
                            hfapi_revision = s.get("revision")
                            break
        else:
            uploaded_file = st.file_uploader("Upload a CSV or JSONL file", type=["csv", "jsonl"])
            if uploaded_file:
                st.success(f"📄 {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)", icon="✅")

        st.markdown("---")
        st.markdown("### 🎯 Sampling")
        num_rows = st.slider("Number of rows", 1, 20, 5)
        sampling_mode = st.radio("Mode", ["Top rows", "Random sample"], index=0, horizontal=True)
        random_seed = 42
        if sampling_mode == "Random sample":
            random_seed = st.number_input("Random seed", min_value=0, value=42, step=1)
        st.markdown("---")
        load_btn = st.button("🚀  Load Data", use_container_width=True, type="primary")
        if data_source == "HuggingFace Dataset" and dataset_id:
            st.markdown(
                f'<a href="https://huggingface.co/datasets/{dataset_id}" target="_blank" '
                f'style="color:#60a5fa;font-size:13px">View on HuggingFace ↗</a>',
                unsafe_allow_html=True,
            )

    return {
        "data_source": data_source,
        "dataset_id": dataset_id,
        "uploaded_file": uploaded_file,
        "selected_config": selected_config,
        "selected_split": selected_split,
        "hfapi_revision": hfapi_revision,
        "num_rows": num_rows,
        "sampling_mode": sampling_mode,
        "random_seed": random_seed,
        "load_btn": load_btn,
    }
