"""
HTML rendering helpers for chat messages, JSON display, tool calls, and row cards.
"""

import json
import html as html_mod
import streamlit as st


ROLE_ICONS = {
    "user": "👤",
    "human": "👤",
    "assistant": "🤖",
    "ai": "🤖",
    "gpt": "🤖",
    "system": "⚙️",
    "tool": "🔧",
    "function": "🔧",
    "tool_result": "📦",
    "tool_response": "📦",
    "thinking": "💭",
    "reasoning": "💭",
}
ROLE_NORM = {
    "human": "user",
    "ai": "assistant",
    "gpt": "assistant",
    "function": "tool",
    "tool_result": "tool_result",
    "tool_response": "tool_response",
    "thinking": "thinking",
    "reasoning": "reasoning",
}


def escape(t):
    if not isinstance(t, str):
        t = str(t)
    return html_mod.escape(t)


def try_parse_json(v):
    if not isinstance(v, str):
        return v
    s = v.strip()
    if not s or s[0] not in ("{", "["):
        return v
    try:
        return json.loads(s)
    except Exception:
        return v


def deep_parse_row(row):
    return {k: try_parse_json(v) for k, v in row.items()}


def fmt_json(obj, md=10, d=0):
    """Legacy flat JSON formatter (used as fallback)."""
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
        if len(obj) <= 4 and all(
            isinstance(x, (str, int, float, bool, type(None))) for x in obj
        ):
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
            lines.append(
                f'{ind}{fmt_json(item, md, d + 1)}<span style="color:#64748b">{c}</span>'
            )
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


# ---------------------------------------------------------------------------
# Collapsible JSON rendering
# ---------------------------------------------------------------------------


def _obj_size(obj):
    """Estimate the 'visual weight' of an object for collapse decisions."""
    if isinstance(obj, dict):
        return sum(_obj_size(v) for v in obj.values()) + len(obj)
    elif isinstance(obj, list):
        return sum(_obj_size(x) for x in obj) + len(obj)
    elif isinstance(obj, str):
        return max(1, len(obj) // 40)
    return 1


def _preview_value(obj, max_len=60):
    """Generate a short inline preview of a value for the summary line."""
    if isinstance(obj, dict):
        keys = list(obj.keys())[:4]
        preview = ", ".join(keys)
        if len(obj) > 4:
            preview += ", …"
        return f'{{{preview}}} <span class="nest-badge">{len(obj)} keys</span>'
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        # Try to describe list items
        first = obj[0]
        if isinstance(first, dict):
            # Look for identifying keys
            id_keys = [
                k for k in ("turn", "step", "name", "role", "id", "type") if k in first
            ]
            if id_keys:
                previews = []
                for item in obj[:3]:
                    vals = [str(item.get(k, ""))[:20] for k in id_keys[:2]]
                    previews.append(":".join(vals))
                desc = ", ".join(previews)
                if len(obj) > 3:
                    desc += ", …"
                return f'[{desc}] <span class="nest-badge">{len(obj)} items</span>'
            return f'<span class="nest-badge">{len(obj)} objects</span>'
        elif isinstance(first, str):
            joined = ", ".join(f'"{s[:15]}"' for s in obj[:3])
            if len(obj) > 3:
                joined += ", …"
            return f"[{joined}]"
        return f'<span class="nest-badge">{len(obj)} items</span>'
    elif isinstance(obj, str):
        if len(obj) <= max_len:
            return f'<span style="color:#a5f3fc">"{escape(obj)}"</span>'
        return f'<span style="color:#a5f3fc">"{escape(obj[:max_len])}…"</span>'
    elif isinstance(obj, bool):
        return f'<span style="color:#fbbf24">{str(obj).lower()}</span>'
    elif isinstance(obj, (int, float)):
        return f'<span style="color:#34d399">{obj}</span>'
    elif obj is None:
        return '<span style="color:#f87171">null</span>'
    return f'<span style="color:#a5f3fc">"{escape(str(obj)[:max_len])}"</span>'


def _is_simple(obj):
    """Check if a value is simple enough to render inline without collapsing."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        if isinstance(obj, str) and len(obj) > 120:
            return False
        return True
    if isinstance(obj, list):
        if len(obj) <= 4 and all(
            isinstance(x, (str, int, float, bool, type(None))) for x in obj
        ):
            total_len = sum(len(str(x)) for x in obj)
            return total_len < 100
        return False
    if isinstance(obj, dict):
        if len(obj) <= 2 and all(_is_simple(v) for v in obj.values()):
            total_len = sum(len(str(v)) for v in obj.values())
            return total_len < 80
        return False
    return False


def _should_expand(key, obj, depth, parent_context=None):
    """Decide whether a collapsible section should be open by default."""
    # Always expand the first level
    if depth == 0:
        return True
    # Expand small objects
    size = _obj_size(obj)
    if size <= 4:
        return True
    # Expand important-looking keys at shallow depth
    important_keys = {
        "content",
        "response",
        "reasoning",
        "rationale",
        "description",
        "output_summary",
        "stop_rationale",
    }
    if depth <= 1 and key in important_keys:
        return True
    # Collapse larger structures at deeper levels
    if depth >= 2 and size > 6:
        return False
    # Default: expand at depth 1 if not too large
    if depth == 1 and size <= 12:
        return True
    return False


def _fmt_scalar(obj):
    """Format a scalar value with syntax highlighting."""
    if isinstance(obj, str):
        return f'<span style="color:#a5f3fc">"{escape(obj)}"</span>'
    elif isinstance(obj, bool):
        return f'<span style="color:#fbbf24">{str(obj).lower()}</span>'
    elif isinstance(obj, (int, float)):
        return f'<span style="color:#34d399">{obj}</span>'
    elif obj is None:
        return '<span style="color:#f87171">null</span>'
    return f'<span style="color:#a5f3fc">"{escape(str(obj))}"</span>'


def _fmt_simple_list(obj):
    """Format a short list of scalars inline."""
    items = ", ".join(_fmt_scalar(x) for x in obj)
    return f'<span style="color:#e2e8f0">[</span>{items}<span style="color:#e2e8f0">]</span>'


def fmt_json_collapsible(obj, depth=0, key="", max_depth=12):
    """
    Render JSON with collapsible <details>/<summary> for nested structures.

    Design:
    - Scalars and short values render inline
    - Dicts/lists with nesting get collapsible sections
    - Auto-expand based on depth, size, and key importance
    - Each level shows a preview in the summary
    """
    if depth >= max_depth:
        return '<span style="color:#64748b">…</span>'

    # Simple values: render inline
    if _is_simple(obj):
        if isinstance(obj, list):
            return _fmt_simple_list(obj)
        if isinstance(obj, dict):
            # Small inline dicts: render as compact key:value
            if not obj:
                return '<span style="color:#64748b">{}</span>'
            parts = []
            for k, v in obj.items():
                parts.append(
                    f'<span style="color:#38bdf8">"{escape(str(k))}"</span>'
                    f'<span style="color:#64748b">:</span> {_fmt_scalar(v)}'
                )
            return (
                '<span style="color:#e2e8f0">{</span>'
                + '<span style="color:#64748b">, </span>'.join(parts)
                + '<span style="color:#e2e8f0">}</span>'
            )
        return _fmt_scalar(obj)

    # Long strings: truncate with expand
    if isinstance(obj, str) and len(obj) > 120:
        truncated = escape(obj[:120])
        full = escape(obj).replace("\n", "<br>")
        return (
            f'<details class="nest-details nest-depth-{min(depth, 3)}">'
            f'<summary class="nest-summary">'
            f'<span style="color:#a5f3fc">"{truncated}…"</span>'
            f' <span class="nest-badge">{len(obj)} chars</span></summary>'
            f'<div class="nest-content"><span style="color:#a5f3fc">"{full}"</span></div>'
            f"</details>"
        )

    # Dict rendering
    if isinstance(obj, dict):
        if not obj:
            return '<span style="color:#64748b">{}</span>'

        expanded = _should_expand(key, obj, depth)
        open_attr = " open" if expanded else ""
        preview = _preview_value(obj)

        inner_parts = []
        for k, v in obj.items():
            k_html = f'<span style="color:#38bdf8">"{escape(str(k))}"</span>'
            if _is_simple(v):
                v_html = (
                    _fmt_scalar(v) if not isinstance(v, list) else _fmt_simple_list(v)
                )
                inner_parts.append(
                    f'<div class="nest-row">{k_html}'
                    f'<span style="color:#64748b">: </span>{v_html}</div>'
                )
            else:
                v_html = fmt_json_collapsible(v, depth + 1, key=k, max_depth=max_depth)
                inner_parts.append(
                    f'<div class="nest-row">{k_html}'
                    f'<span style="color:#64748b">: </span>{v_html}</div>'
                )

        inner = "".join(inner_parts)
        return (
            f'<details class="nest-details nest-depth-{min(depth, 3)}"{open_attr}>'
            f'<summary class="nest-summary">'
            f'<span class="nest-toggle-icon"></span>{preview}</summary>'
            f'<div class="nest-content">{inner}</div>'
            f"</details>"
        )

    # List rendering
    if isinstance(obj, list):
        if not obj:
            return '<span style="color:#64748b">[]</span>'

        expanded = _should_expand(key, obj, depth)
        open_attr = " open" if expanded else ""
        preview = _preview_value(obj)

        inner_parts = []
        for i, item in enumerate(obj):
            idx_html = f'<span class="nest-index">{i}</span>'
            if _is_simple(item):
                v_html = (
                    _fmt_scalar(item)
                    if not isinstance(item, list)
                    else _fmt_simple_list(item)
                )
                inner_parts.append(f'<div class="nest-row">{idx_html}{v_html}</div>')
            else:
                # For list items that are dicts, show a helpful label
                label = ""
                if isinstance(item, dict):
                    # Find a useful label from the item
                    for lk in (
                        "turn",
                        "step",
                        "name",
                        "role",
                        "id",
                        "type",
                        "tool_name",
                    ):
                        if lk in item:
                            label = f' <span class="nest-item-label">{escape(str(lk))}={escape(str(item[lk])[:30])}</span>'
                            break
                v_html = fmt_json_collapsible(
                    item, depth + 1, key=key, max_depth=max_depth
                )
                inner_parts.append(
                    f'<div class="nest-row">{idx_html}{label}{v_html}</div>'
                )

        inner = "".join(inner_parts)
        return (
            f'<details class="nest-details nest-depth-{min(depth, 3)}"{open_attr}>'
            f'<summary class="nest-summary">'
            f'<span class="nest-toggle-icon"></span>{preview}</summary>'
            f'<div class="nest-content">{inner}</div>'
            f"</details>"
        )

    return _fmt_scalar(obj)


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
                a = tc.get("function", {}).get(
                    "arguments", tc.get("arguments", tc.get("input", {}))
                )
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
                        tp.append(f"[Tool: {item.get('name', '?')}]")
                    elif item.get("type") == "tool_result":
                        tp.append(f"[Result: {str(item.get('content', ''))}]")
                    else:
                        tp.append(json.dumps(item, indent=2))
                else:
                    tp.append(str(item))
            content = "\n".join(tp)
        if content is None:
            content = ""
        cs = escape(str(content)).replace("\n", "<br>")
        # reasoning
        reas = msg.get(
            "reasoning", msg.get("thinking", msg.get("reasoning_content", ""))
        )
        rh = ""
        if reas:
            rh = (
                f'<div class="chat-msg" style="margin-bottom:10px;opacity:.85">'
                f'<div class="chat-avatar avatar-thinking">💭</div>'
                f'<div style="flex:1;min-width:0">'
                f'<div class="chat-role-label" style="color:#db2777">thinking</div>'
                f'<div class="chat-bubble bubble-thinking">'
                f"{escape(str(reas)).replace(chr(10), '<br>')}</div></div></div>"
            )
        tcs = get_tool_calls(msg)
        tch = "".join(render_tc(tc) for tc in tcs) if tcs else ""
        parts.append(
            f'{rh}<div class="chat-msg">'
            f'<div class="chat-avatar avatar-{role}">{icon}</div>'
            f'<div style="flex:1;min-width:0">'
            f'<div class="chat-role-label">{escape(rr)}</div>'
            f'<div class="chat-bubble bubble-{role}">'
            f"{cs if cs else '<span style=opacity:.5>(empty)</span>'}{tch}</div></div></div>"
        )
    return '<div class="chat-container">' + "".join(parts) + "</div>"


def classify(v):
    """Classify a value for rendering purposes."""
    if isinstance(v, list):
        # Check multi-turn first (more specific than generic chat)
        if _is_multi_turn(v):
            return "turns"
        if is_chat(v):
            return "chat"
        return "json"
    if isinstance(v, dict):
        return "json"
    return "scalar"


def _is_multi_turn(v):
    """Detect if a list looks like multi-turn conversation data."""
    if not isinstance(v, list) or not v:
        return False
    for item in v[:5]:
        if not isinstance(item, dict):
            return False
        keys = set(item.keys())
        # Has turn-like structure: numbered turns with role/content/response
        if keys & {"turn", "step"} and keys & {
            "role",
            "content",
            "response",
            "tool_trajectory",
        }:
            return True
    return False


def render_turns(turns):
    """Render multi-turn conversation data with rich formatting."""
    parts = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        turn_num = turn.get("turn", turn.get("step", "?"))
        role = str(turn.get("role", "unknown")).lower()
        icon = ROLE_ICONS.get(role, "💬")

        # Build turn header
        parts.append(
            f'<div class="turn-block">'
            f'<div class="turn-header">'
            f'<span class="turn-badge">Turn {turn_num}</span>'
            f'<span class="turn-role">{icon} {escape(role)}</span>'
            f"</div>"
        )

        # Content/query
        content = turn.get("content", "")
        if content:
            parts.append(f'<div class="turn-content">{escape(str(content))}</div>')

        # Tool trajectory
        trajectory = turn.get("tool_trajectory", [])
        if trajectory and isinstance(trajectory, list):
            parts.append('<div class="turn-trajectory">')
            for step in trajectory:
                if not isinstance(step, dict):
                    continue
                step_num = step.get("step", "?")
                tool = escape(str(step.get("tool_name", "unknown")))
                args = step.get("arguments", {})
                output = step.get("output_summary", "")
                reasoning = step.get("reasoning", "")
                stop = step.get("stop_decision", "")
                stop_rat = step.get("stop_rationale", "")

                # Tool call header
                parts.append(
                    f'<div class="traj-step">'
                    f'<div class="traj-header">'
                    f'<span class="traj-step-badge">Step {step_num}</span>'
                    f'<span class="traj-tool-name">🔧 {tool}</span>'
                    f"</div>"
                )

                # Arguments (collapsible)
                if args:
                    args_html = fmt_json_collapsible(args, depth=2, key="arguments")
                    parts.append(
                        f'<details class="traj-section" open>'
                        f'<summary class="traj-section-label">Arguments</summary>'
                        f'<div class="traj-section-body">{args_html}</div>'
                        f"</details>"
                    )

                # Output summary (shown directly - it's usually short)
                if output:
                    parts.append(
                        f'<div class="traj-output">'
                        f'<span class="traj-section-label-inline">Output:</span> '
                        f"{escape(str(output))}</div>"
                    )

                # Reasoning (collapsible if long)
                if reasoning:
                    if len(str(reasoning)) > 80:
                        parts.append(
                            f'<details class="traj-section">'
                            f'<summary class="traj-section-label">Reasoning</summary>'
                            f'<div class="traj-section-body traj-reasoning">{escape(str(reasoning))}</div>'
                            f"</details>"
                        )
                    else:
                        parts.append(
                            f'<div class="traj-output">'
                            f'<span class="traj-section-label-inline">Reasoning:</span> '
                            f'<span class="traj-reasoning-inline">{escape(str(reasoning))}</span></div>'
                        )

                # Stop decision
                if stop:
                    stop_class = (
                        "traj-stop-go" if stop == "continue" else "traj-stop-halt"
                    )
                    parts.append(
                        f'<div class="traj-stop {stop_class}">'
                        f"{'▶' if stop == 'continue' else '⏹'} {escape(str(stop))}"
                        f"{' — ' + escape(str(stop_rat)) if stop_rat else ''}"
                        f"</div>"
                    )

                parts.append("</div>")  # close traj-step
            parts.append("</div>")  # close turn-trajectory

        # Response
        response = turn.get("response", "")
        if response:
            resp_html = escape(str(response)).replace("\n", "<br>")
            parts.append(
                f'<details class="turn-response-details" open>'
                f'<summary class="traj-section-label">Response</summary>'
                f'<div class="turn-response">{resp_html}</div>'
                f"</details>"
            )

        parts.append("</div>")  # close turn-block

    return '<div class="turns-container">' + "".join(parts) + "</div>"


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
        f"<span>Row {row_idx}</span>"
        f'<span style="margin-left:auto;font-size:12px;color:#94a3b8;font-weight:400">'
        f"{len(scalars)} scalar · {len(rich)} structured</span></div>"
    )
    meta = ""
    if scalars:
        rh = ""
        for k, v in scalars.items():
            vs = (
                escape(str(v))
                if v is not None
                else '<span style="color:#94a3b8">null</span>'
            )
            rh += f'<tr><td class="meta-key">{escape(str(k))}</td><td class="meta-val">{vs}</td></tr>'
        meta = f'<table class="meta-table">{rh}</table>'
    st.markdown(f'<div class="row-card">{hdr}{meta}</div>', unsafe_allow_html=True)

    for col, (kind, val) in rich.items():
        if kind == "chat":
            label = (
                f"💬  {col}  —  {len(val) if isinstance(val, list) else '?'} messages"
            )
        elif kind == "turns":
            label = f"🔄  {col}  —  {len(val)} turns"
        elif isinstance(val, list):
            label = f"📋  {col}  —  list of {len(val)} items"
        else:
            nk = len(val) if isinstance(val, dict) else ""
            label = f"📂  {col}" + (f"  —  {nk} keys" if nk else "")
        with st.expander(label, expanded=(kind in ("chat", "turns"))):
            if kind == "chat":
                st.markdown(render_chat(val), unsafe_allow_html=True)
            elif kind == "turns":
                st.markdown(render_turns(val), unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="json-block">{fmt_json_collapsible(val, depth=0, key=col)}</div>',
                    unsafe_allow_html=True,
                )
    st.markdown('<div class="row-spacer"></div>', unsafe_allow_html=True)
