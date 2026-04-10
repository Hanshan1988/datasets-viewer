"""
Data loading functions for HuggingFace datasets, local CSV/JSONL/JSON files.

Primary:   datasets library (streaming mode)
Fallback:  huggingface_hub (HfApi + hf_hub_download) + pandas parquet reader
"""

import json
import os
import random
import streamlit as st
from huggingface_hub import HfApi, hf_hub_download
from datasets import load_dataset, get_dataset_config_names, get_dataset_split_names

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

api = HfApi(token=HF_TOKEN)


# ── Configs & splits discovery ─────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def get_configs_and_splits(dataset_id: str):
    """Discover configs/splits. Streaming lib first, HfApi parquet scan fallback."""
    # ── Strategy 1: datasets library ──
    try:
        configs = get_dataset_config_names(dataset_id, token=HF_TOKEN, trust_remote_code=True)
        results = []
        for c in configs:
            try:
                splits = get_dataset_split_names(dataset_id, config_name=c,
                                                 token=HF_TOKEN, trust_remote_code=True)
                for s in splits:
                    results.append({"config": c, "split": s})
            except Exception:
                continue
        if results:
            return results, "streaming"
    except Exception:
        pass

    # ── Strategy 2: HfApi — scan parquet files on Hub ──
    try:
        results = []
        for revision in ["refs/convert/parquet", "main"]:
            try:
                files = list(api.list_repo_tree(dataset_id, repo_type="dataset",
                                                revision=revision, recursive=True))
                pq_files = [f for f in files
                            if hasattr(f, 'rfilename') and f.rfilename.endswith('.parquet')]
                seen = set()
                for f in pq_files:
                    parts = f.rfilename.split('/')
                    if len(parts) >= 3:
                        config, split = parts[0], parts[1]
                    elif len(parts) == 2:
                        config = parts[0]
                        split = (parts[1].split('-')[0] if '-' in parts[1]
                                 else parts[1].replace('.parquet', ''))
                    else:
                        config = "default"
                        split = parts[0].split('-')[0]
                    key = (config, split)
                    if key not in seen:
                        seen.add(key)
                        results.append({"config": config, "split": split,
                                        "revision": revision})
                if results:
                    return results, "hfapi"
            except Exception:
                continue
    except Exception:
        pass

    raise RuntimeError("Could not discover configs/splits via streaming or HfApi.")


# ── Local file loading (CSV / JSONL / JSON array) ──────────────────────────────

def _col_info_from_dict_rows(rows: list) -> list:
    """Build column schema from a list of dict rows (name + inferred type)."""
    if not rows:
        return []
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    col_info = []
    for name in sorted(all_keys):
        sample = None
        for r in rows:
            if name in r and r[name] is not None:
                sample = r[name]
                break
        tname = type(sample).__name__ if sample is not None else "NoneType"
        col_info.append({"name": name, "type": tname})
    return col_info


def load_rows_from_upload(uploaded_file, num_rows: int, mode: str, seed: int = 42):
    """Load rows from an uploaded CSV, JSONL, or JSON file (array of objects)."""
    import pandas as pd

    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif name.endswith(".jsonl"):
        df = pd.read_json(uploaded_file, lines=True)
    elif name.endswith(".json"):
        uploaded_file.seek(0)
        text = uploaded_file.read().decode("utf-8")
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(
                "JSON file must be an array of objects, e.g. [{...}, {...}]. "
                f"Got {type(data).__name__}."
            )
        if not data:
            raise ValueError("JSON array is empty.")
        rows_raw = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Each array element must be a JSON object; index {i} is {type(item).__name__}."
                )
            rows_raw.append(dict(item))
        total = len(rows_raw)
        if mode == "random" and total > num_rows:
            rng = random.Random(seed)
            picked = rng.sample(rows_raw, k=min(num_rows, total))
        else:
            picked = rows_raw[:num_rows]
        col_info = _col_info_from_dict_rows(picked)
        return picked, col_info
    else:
        raise ValueError(
            f"Unsupported file type: {uploaded_file.name}. Use .csv, .jsonl, or .json"
        )

    total = len(df)
    if mode == "random" and total > num_rows:
        df = df.sample(n=min(num_rows, total), random_state=seed)
    else:
        df = df.head(num_rows)

    rows = []
    for _, r in df.iterrows():
        d = {}
        for col in df.columns:
            val = r[col]
            if pd.isna(val) if not isinstance(val, (list, dict)) else False:
                d[col] = None
            elif hasattr(val, 'item'):
                d[col] = val.item()
            else:
                d[col] = val
        rows.append(d)

    col_info = [{"name": c, "type": str(df[c].dtype)} for c in df.columns]
    return rows, col_info


# ── Row loading ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_rows_streaming(dataset_id: str, config: str, split: str,
                        num_rows: int, mode: str, seed: int = 42):
    """Load rows via `datasets` library in streaming mode."""
    ds = load_dataset(dataset_id, name=config, split=split,
                      streaming=True, token=HF_TOKEN, trust_remote_code=True)

    if mode == "random":
        ds = ds.shuffle(seed=seed, buffer_size=max(num_rows * 20, 1000))

    rows = []
    for i, item in enumerate(ds):
        if i >= num_rows:
            break
        rows.append(dict(item))

    # Get feature names/types
    col_info = []
    try:
        for fname, ftype in ds.features.items():
            col_info.append({"name": fname, "type": str(ftype)})
    except Exception:
        if rows:
            col_info = [{"name": k, "type": type(rows[0][k]).__name__} for k in rows[0]]

    return rows, col_info


@st.cache_data(ttl=300, show_spinner=False)
def load_rows_hfapi(dataset_id: str, config: str, split: str, revision: str,
                    num_rows: int, mode: str, seed: int = 42):
    """Fallback: download first parquet shard via HfApi, read with pandas."""
    import pandas as pd

    # Find parquet files for this config/split
    files = list(api.list_repo_tree(dataset_id, repo_type="dataset",
                                    revision=revision, recursive=True))
    pq_files = []
    for f in files:
        if not hasattr(f, 'rfilename') or not f.rfilename.endswith('.parquet'):
            continue
        parts = f.rfilename.split('/')
        if len(parts) >= 3 and parts[0] == config and parts[1] == split:
            pq_files.append(f.rfilename)
        elif len(parts) == 2 and parts[0] == config:
            fname = parts[1]
            if split in fname or fname.startswith(split):
                pq_files.append(f.rfilename)
        elif len(parts) == 1 and config == "default":
            if split in parts[0]:
                pq_files.append(f.rfilename)
    pq_files.sort()

    if not pq_files:
        raise RuntimeError(f"No parquet files found for config='{config}' split='{split}'")

    local_path = hf_hub_download(
        repo_id=dataset_id, filename=pq_files[0],
        repo_type="dataset", revision=revision, token=HF_TOKEN,
    )

    # Read with pandas (avoids pyarrow >=19 histogram bug)
    df = pd.read_parquet(local_path, engine="pyarrow")
    total = len(df)
    if mode == "random" and total > num_rows:
        df = df.sample(n=min(num_rows, total), random_state=seed)
    else:
        df = df.head(num_rows)

    rows = []
    for _, r in df.iterrows():
        d = {}
        for col in df.columns:
            val = r[col]
            if pd.isna(val) if not isinstance(val, (list, dict)) else False:
                d[col] = None
            elif hasattr(val, 'item'):
                d[col] = val.item()
            else:
                d[col] = val
        rows.append(d)

    col_info = [{"name": c, "type": str(df[c].dtype)} for c in df.columns]
    return rows, col_info
