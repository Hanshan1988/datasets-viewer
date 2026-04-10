# 🔬 LLM Trace Viewer

Browse HuggingFace datasets or local **CSV**, **JSONL** (one JSON object per line), or **JSON** (a single array of objects, `[{...}, {...}]`) with nested chat traces, tool calls, and reasoning steps — rendered beautifully in Streamlit.

## Setup

### 1. Install dependencies

```bash
pip install streamlit datasets huggingface-hub pandas pyarrow python-dotenv
```

### 2. (Optional) Set HuggingFace token

For private/gated datasets, set your token via a `.env` file or environment variable:

```bash
# .env file
HF_TOKEN=hf_your_token_here
```

or

```bash
export HF_TOKEN=hf_your_token_here
```

## Running the app

### Modular version (recommended)

```bash
streamlit run app.py
```

## Project structure

```
├── app.py                 # Entry point for modular version
├── backend/
│   ├── data_loader.py      # HF dataset discovery, streaming, parquet fallback, CSV/JSONL/JSON upload
│   └── rendering.py        # HTML rendering for chat messages, JSON, tool calls, row cards
├── frontend/
│   ├── sidebar.py          # Sidebar UI: data source, config/split pickers, sampling
│   └── main_content.py     # Main area: hero banner, load orchestration, row display
└── styles/
    └── styles.css          # All custom CSS
```
