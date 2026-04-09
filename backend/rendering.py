"""
HTML rendering helpers for chat messages, JSON display, tool calls, and row cards.
"""

import json
import html as html_mod
import streamlit as st


ROLE_ICONS = {
    "user": "👤", "human": "👤", "assistant": "🤖", "ai": "🤖", "gpt": "🤖",
    "system": "⚙️", "tool": "🔧", "function": "🔧", "tool_result": "📦",
    "tool_response": "📦", "thinking": "💭", "reasoning": "💭",
}
ROLE_NORM = {
    "human": "user", "ai": "assistant", "gpt": "assistant", "function": "tool",
    "tool_result": "tool_result", "tool_response": "tool_response",
    "thinking": "thinking", "reasoning": "reasoning",
}


def escape(t):
    if not isinstance(t, str):
        t = str(t)
    return html_mod.escape(t)


def try_parse_json(v):
    if not isinstance(v, str):
        return v
    s = v.strip()
    if not s or s[0] not in ('{', '['):
        return v
    try:
        return json.loads(s)
    except Exception:
        return v


def deep_parse_row(row):
    return {k: try_parse_json(v) for k, v in row.items()}


def fmt_json(obj, md=10, d=0):
    if d >= md:
        return '<span style="color:#64748b">…</span>'
    if isinstance(obj, dict):
        if not obj:
            return '<span style="color:#64748b">{}</span>'
        lines = ['<span style="color:#e2e8f0">{</span>']
        ind = "&nbsp;" * ((d + 1) * 2)
        for i, (k, v) in enumerate(obj.items()):
            c = "," if i < len(obj) - 1 else ""
            lines.append(
                f'{ind}<span style="color:#38bdf8">"{escape(str(k))}"</span>'
                f'<span style="color:#64748b">: </span>{fmt_json(v, md, d + 1)}'
                f'<span style="color:#64748b">{c}</span>'
            )
        lines.append("&nbsp;" * (d * 2) + '<span style="color:#e2e8f0">}</span>')
        return "<br>".join(lines)
    elif isinstance(obj, list):
        if not obj:
            return '<span style="color:#64748b">[]</span>'
        if len(obj) <= 4 and all(isinstance(x, (str, int, float, bool, type(None))) for x in obj):
            if all(isinstance(x, str) and len(x) < 30 for x in obj):
                return (
                    '<span style="color:#e2e8f0">[</span>'
                    + ", ".join(fmt_json(x, md, d + 1) for x in obj)
                    + '<span style="color:#e2e8f0">]</span>'
                )
        lines = ['<span style="color:#e2e8f0">[</span>']
        ind = "&nbsp;" * ((d + 1) * 2)
        for i, item in enumerate(obj):
            c = "," if i < len(obj) - 1 else ""
            lines.append(f'{ind}{fmt_json(item, md, d + 1)}<span style="color:#64748b">{c}</span>')
        lines.append("&nbsp;" * (d * 2) + '<span style="color:#e2e8f0">]</span>')
        return "<br>".join(lines)
    elif isinstance(obj, str):
        return f'<span style="color:#a5f3fc">"{escape(obj)}"</span>'
    elif isinstance(obj, bool):
        return f'<span style="color:#fbbf24">{str(obj).lower()}</span>'
    elif isinstance(obj, (int, float)):
        return f'<span style="color:#34d399">{obj}</span>'
    elif obj is None:
        return '<span style="color:#f87171">null</span>'
    return f'<span style="color:#a5f3fc">"{escape(str(obj))}"</span>'


def is_chat(v):
    if not isinstance(v, list) or not v:
        return False
    for item in v[:5]:
        if not isinstance(item, dict):
            return False
        if set(item.keys()) & {"role", "content", "tool_calls", "function_call"}:
            return True
    return False


def get_tool_calls(msg):
    tcs = []
    if "tool_calls" in msg and msg["tool_calls"]:
        for tc in msg["tool_calls"]:
            if isinstance(tc, dict):
                n = tc.get("function", {}).get("name", tc.get("name", "?"))
                a = tc.get("function", {}).get("arguments", tc.get("arguments", tc.get("input", {})))
                tcs.append({"name": n, "arguments": a})
    if "function_call" in msg and msg["function_call"]:
        fc = msg["function_call"]
        tcs.append({"name": fc.get("name", "?"), "arguments": fc.get("arguments", {})})
    return tcs


def render_tc(tc):
    n = escape(str(tc.get("name", "?")))
    a = tc.get("arguments", {})
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except Exception:
            pass
    ah = fmt_json(a) if isinstance(a, (dict, list)) else escape(str(a))
    return (
        f'<div class="tool-call-block">'
        f'<div class="tool-call-header">🔧 Tool Call</div>'
        f'<div class="tool-call-name">{n}</div>'
        f'<div style="margin-top:6px">{ah}</div></div>'
    )


def render_chat(messages):
    parts = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        rr = str(msg.get("role", msg.get("type", "unknown"))).lower().strip()
        role = ROLE_NORM.get(rr, rr)
        icon = ROLE_ICONS.get(rr, ROLE_ICONS.get(role, "💬"))
        content = msg.get("content", "")
        if isinstance(content, list):
            tp = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        tp.append(str(item.get("text", "")))
                    elif item.get("type") == "tool_use":
                        tp.append(f'[Tool: {item.get("name", "?")}]')
                    elif item.get("type") == "tool_result":
                        tp.append(f'[Result: {str(item.get("content", ""))}]')
                    else:
                        tp.append(json.dumps(item, indent=2))
                else:
                    tp.append(str(item))
            content = "\n".join(tp)
        if content is None:
            content = ""
        cs = escape(str(content)).replace("\n", "<br>")
        # reasoning
        reas = msg.get("reasoning", msg.get("thinking", msg.get("reasoning_content", "")))
        rh = ""
        if reas:
            rh = (
                f'<div class="chat-msg" style="margin-bottom:10px;opacity:.85">'
                f'<div class="chat-avatar avatar-thinking">💭</div>'
                f'<div style="flex:1;min-width:0">'
                f'<div class="chat-role-label" style="color:#db2777">thinking</div>'
                f'<div class="chat-bubble bubble-thinking">'
                f'{escape(str(reas)).replace(chr(10), "<br>")}</div></div></div>'
            )
        tcs = get_tool_calls(msg)
        tch = "".join(render_tc(tc) for tc in tcs) if tcs else ""
        parts.append(
            f'{rh}<div class="chat-msg">'
            f'<div class="chat-avatar avatar-{role}">{icon}</div>'
            f'<div style="flex:1;min-width:0">'
            f'<div class="chat-role-label">{escape(rr)}</div>'
            f'<div class="chat-bubble bubble-{role}">'
            f'{cs if cs else "<span style=opacity:.5>(empty)</span>"}{tch}</div></div></div>'
        )
    return '<div class="chat-container">' + "".join(parts) + "</div>"


def classify(v):
    if isinstance(v, list):
        return "chat" if is_chat(v) else "json"
    if isinstance(v, dict):
        return "json"
    return "scalar"


def render_row(row_data, row_idx, features):
    parsed = deep_parse_row(row_data)
    scalars, rich = {}, {}
    for k, v in parsed.items():
        kind = classify(v)
        if kind == "scalar":
            scalars[k] = v
        else:
            rich[k] = (kind, v)

    hdr = (
        f'<div class="row-card-header">'
        f'<span class="idx-badge">#{row_idx}</span>'
        f'<span>Row {row_idx}</span>'
        f'<span style="margin-left:auto;font-size:12px;color:#94a3b8;font-weight:400">'
        f'{len(scalars)} scalar · {len(rich)} structured</span></div>'
    )
    meta = ""
    if scalars:
        rh = ""
        for k, v in scalars.items():
            vs = escape(str(v)) if v is not None else '<span style="color:#94a3b8">null</span>'
            rh += f'<tr><td class="meta-key">{escape(str(k))}</td><td class="meta-val">{vs}</td></tr>'
        meta = f'<table class="meta-table">{rh}</table>'
    st.markdown(f'<div class="row-card">{hdr}{meta}</div>', unsafe_allow_html=True)

    for col, (kind, val) in rich.items():
        if kind == "chat":
            label = f"💬  {col}  —  {len(val) if isinstance(val, list) else '?'} messages"
        elif isinstance(val, list):
            label = f"📋  {col}  —  list of {len(val)} items"
        else:
            nk = len(val) if isinstance(val, dict) else ""
            label = f"📂  {col}" + (f"  —  {nk} keys" if nk else "")
        with st.expander(label, expanded=(kind == "chat")):
            if kind == "chat":
                st.markdown(render_chat(val), unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="json-block">{fmt_json(val)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="row-spacer"></div>', unsafe_allow_html=True)
