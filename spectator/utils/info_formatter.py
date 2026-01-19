from __future__ import annotations
from typing import Iterable, Mapping, Any, Tuple, List, Dict
import ast
import html
import re


def _split_param_value(line: str) -> Tuple[str, str]:
    """Best-effort split of a "param value" line into (param, value).
    Supports separators like ':', '=', whitespace blocks, or tabs.
    """
    s = line.strip()
    if not s:
        return "", ""
    # Special-case: patterns like "key', b'value" or "key', 'value"
    # Capture minimal key (no separators) followed by a quote, comma, optional b, then quoted/partial value
    m = re.match(r"^\s*([^,:=\t]+?)['\"]\s*,\s*b?['\"](.*)$", s)
    if m:
        left, right = m.group(1), m.group(2)
        return left.strip(), right.strip()

    # Try common separators first
    for sep in (":", "=", "\t"):
        if sep in s:
            left, right = s.split(sep, 1)
            return left.strip(), right.strip()
    # As a last resort, consider a single comma as key/value separator
    if "," in s and s.count(",") == 1:
        left, right = s.split(",", 1)
        return left.strip(), right.strip()
    # Fallback: split on multiple spaces
    parts = s.split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return s, ""


essential_css = """
<style>
  .info-root { font-family: Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 12px; }
  .group-title { color: #7fb3ff; font-weight: bold; margin-top: 10px; margin-bottom: 4px; }
  table.info { border-collapse: collapse; width: 100%; table-layout: fixed; }
  table.info td { border-top: 1px solid #333; padding: 3px 6px; vertical-align: top; }
  table.info td.key { color: #f7d774; width: 35%; word-break: break-word; }
  table.info td.val { color: #cfe2f3; white-space: pre-wrap; word-break: break-word; }
  .dim { color: #9aa0a6; }
</style>
"""


def _ensure_iterable_strings(info: Any) -> List[str]:
    """Normalize various possible info structures to a list of strings."""
    # Mapping/dict -> flatten to key: value strings
    if isinstance(info, Mapping):
        out: List[str] = []
        for k, v in info.items():
            out.append(f"{k}: {v}")
        return out
    # bytes array -> decode each element
    try:
        import numpy as np  # optional
        if isinstance(info, np.ndarray):
            # Try to vectorize to Python strs
            normalized: List[str] = []
            for x in info.tolist():
                if isinstance(x, (bytes, bytearray)):
                    normalized.append(x.decode(errors='ignore'))
                else:
                    sx = str(x)
                    sx = _strip_py_bytes_literal(sx)
                    sx = _strip_artifacts(sx)
                    normalized.append(sx)
            return normalized
    except Exception:
        pass
    # Generic iterable of items -> stringify
    if isinstance(info, Iterable) and not isinstance(info, (str, bytes, bytearray)):
        out: List[str] = []
        for x in info:
            if isinstance(x, (bytes, bytearray)):
                out.append(x.decode(errors='ignore'))
            else:
                sx = str(x)
                sx = _strip_py_bytes_literal(sx)
                sx = _strip_artifacts(sx)
                out.append(sx)
        return out
    # Last resort: single string
    sx = str(info)
    return [_strip_artifacts(_strip_py_bytes_literal(sx))]


def _strip_py_bytes_literal(s: str) -> str:
    """If s looks like a Python bytes literal (e.g., b'abc'), convert to text.
    Uses ast.literal_eval when safe; falls back to stripping b''.
    """
    st = s.strip()
    # Complete bytes literal like b'abc' or b"abc"
    if len(st) >= 3 and (st.startswith("b'") and st.endswith("'") or st.startswith('b"') and st.endswith('"')):
        try:
            val = ast.literal_eval(st)  # type: ignore[arg-type]
            if isinstance(val, (bytes, bytearray)):
                return val.decode(errors='ignore')
        except Exception:
            # Fallback: remove leading b and quotes
            st2 = st[1:]
            if (st2.startswith("'") and st2.endswith("'")) or (st2.startswith('"') and st2.endswith('"')):
                return st2[1:-1]
    # Incomplete like b'calibration (missing closing quote) -> drop leading b'
    if st.startswith("b'") or st.startswith('b"'):
        return st[2:]
    return s


def _strip_brackets_group(s: str) -> str:
    """Extract group name from a header like [calibration] or [b'calibration'].
    - Works even if closing bracket is missing (e.g., "[b'calibration").
    - Strips quotes and Python bytes literal prefix b''.
    """
    st = s.strip()
    if not st.startswith('['):
        return st
    # Find closing bracket if present
    end = st.rfind(']')
    inner = st[1:end] if end > 1 else st[1:]
    inner = inner.strip()
    # Remove surrounding quotes if any
    if (len(inner) >= 2 and ((inner[0] == "'" and inner[-1] == "'") or (inner[0] == '"' and inner[-1] == '"'))):
        inner = inner[1:-1]
    # If it's a Python bytes literal-like, normalize
    inner = _strip_py_bytes_literal(inner)
    # Final cleanup of quotes in case _strip_py_bytes_literal returned quoted text
    if (len(inner) >= 2 and ((inner[0] == "'" and inner[-1] == "'") or (inner[0] == '"' and inner[-1] == '"'))):
        inner = inner[1:-1]
    return inner.strip()


def _strip_artifacts(s: str) -> str:
    """Remove common artifacts: trailing ] directly after a quote and stray commas at end."""
    st = s.strip()
    # Remove trailing ], '], "] after a quoted token
    if len(st) >= 2 and st[-1] == ']' and (len(st) >= 2 and (st[-2] == "'" or st[-2] == '"')):
        st = st[:-1]
    # Remove trailing single comma (often used as delimiter in raw lines)
    if st.endswith(','):
        st = st[:-1]
    # Remove surrounding quotes
    if (len(st) >= 2 and ((st[0] == "'" and st[-1] == "'") or (st[0] == '"' and st[-1] == '"'))):
        st = st[1:-1]
    return st.strip()


def format_info_to_html(info: Any) -> str:
    """Format an info structure into grouped, colored HTML for the Info window.

    Group keys by the prefix before the first '.', and render as:

    measurement
        name: value
        something: value

    Returns a full HTML snippet including minimal CSS for readability.
    """
    lines = _ensure_iterable_strings(info)

    groups: Dict[str, List[Tuple[str, str]]] = {}
    current_group: str | None = None
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        s = _strip_artifacts(_strip_py_bytes_literal(raw.strip()))
        if not s:
            i += 1
            continue
        # Detect explicit [group] header lines and use them as the active group
        if s.startswith('[') and s.endswith(']') and len(s) > 2:
            inner = s[1:-1].strip()
            # Only treat as header if it looks like a simple token (possibly quoted/bytes),
            # not a key-value line with separators or spaces.
            if (':' not in inner and '=' not in inner and '\t' not in inner and ' ' not in inner):
                current_group = _strip_brackets_group(s)
                if current_group:
                    i += 1
                    continue
        # Also treat bare tokens (no separators, no trailing comma, no dot) as headers
        if (':' not in s and '=' not in s and '\t' not in s and ',' not in s and '.' not in s and len(s) > 0):
            current_group = s
            i += 1
            continue

        # Handle two-line key,value form: "key," followed by "value"
        if (s.endswith(',') and (':' not in s and '=' not in s)):
            key = s[:-1].strip()
            # find next non-empty line as value
            j = i + 1
            val = ''
            while j < n:
                nxt = _strip_artifacts(_strip_py_bytes_literal(lines[j].strip()))
                j += 1
                if nxt:
                    val = nxt
                    break
            i = j
        else:
            key, val = _split_param_value(s)
            i += 1
        if not key:
            continue

        # Clean any bytes-literal looking values
        val = _strip_py_bytes_literal(val)
        val = _strip_artifacts(val.strip())
        if val.endswith("'") or val.endswith('"'):
            val = val[:-1].strip()

        # Determine group and subkey
        group: str
        sub: str
        if '.' in key:
            group, sub = key.split('.', 1)
        else:
            group = current_group or 'misc'
            sub = key
        group = _strip_brackets_group(group.strip()) or 'misc'
        # Clean subkey: remove artifacts and any stray trailing quote
        sub = _strip_artifacts(sub.strip())
        if sub.endswith("'") or sub.endswith('"'):
            sub = sub[:-1].strip()
        groups.setdefault(group, []).append((sub, val))

    # Sort groups and keys for stable layout
    html_parts: List[str] = [essential_css, '<div class="info-root">']

    if not groups:
        html_parts.append('<div class="dim">No info entries.</div>')
    else:
        for gname in sorted(groups.keys()):
            html_parts.append(f'<div class="group-title">{html.escape(gname)}</div>')
            html_parts.append('<table class="info">')
            for sub, val in sorted(groups[gname], key=lambda kv: kv[0]):
                key_html = html.escape(sub)
                val_html = html.escape(val)
                html_parts.append(
                    f'<tr><td class="key">{key_html}</td><td class="val">{val_html}</td></tr>'
                )
            html_parts.append('</table>')

    html_parts.append('</div>')
    return "\n".join(html_parts)
