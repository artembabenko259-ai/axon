"""Terminal Side-by-Side Diff Renderer using Rich for premium visual presentation."""

from __future__ import annotations

import difflib
from rich.style import Style
from rich.table import Table
from rich.text import Text


def render_side_by_side_diff(original_text: str, modified_text: str, width: int = 90) -> Table:
    """Renders a side-by-side diff comparison in a beautifully formatted Rich Table."""
    orig_lines = original_text.splitlines()
    mod_lines = modified_text.splitlines()

    matcher = difflib.SequenceMatcher(None, orig_lines, mod_lines)
    left_side: list[Text] = []
    right_side: list[Text] = []

    style_normal = Style(color="white")

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i1, i2):
                line = orig_lines[idx]
                left_side.append(Text(f" {line}", style=style_normal))
                right_side.append(Text(f" {line}", style=style_normal))
        elif tag == "delete":
            for idx in range(i1, i2):
                line = orig_lines[idx]
                left_side.append(Text(f"- {line}", style=Style(color="red")))
                right_side.append(Text(""))
        elif tag == "insert":
            for idx in range(j1, j2):
                line = mod_lines[idx]
                left_side.append(Text(""))
                right_side.append(Text(f"+ {line}", style=Style(color="green")))
        elif tag == "replace":
            orig_len = i2 - i1
            mod_len = j2 - j1
            max_len = max(orig_len, mod_len)
            
            for idx in range(max_len):
                o_line = orig_lines[i1 + idx] if idx < orig_len else ""
                m_line = mod_lines[j1 + idx] if idx < mod_len else ""
                
                left_style = Style(color="red") if o_line else Style(color="white")
                right_style = Style(color="green") if m_line else Style(color="white")
                
                left_side.append(Text(f"- {o_line}" if o_line else "", style=left_style))
                right_side.append(Text(f"+ {m_line}" if m_line else "", style=right_style))

    return _build_table_from_columns(left_side, right_side, width)


def render_side_by_side_from_diff(diff_text: str, width: int = 90) -> Table:
    """Parses a raw unified diff string and formats it side-by-side."""
    left_side: list[Text] = []
    right_side: list[Text] = []
    
    # We parse the lines
    lines = diff_text.splitlines()
    
    # Temporary buffers for consecutive deletes and inserts to align them
    deletes: list[str] = []
    inserts: list[str] = []
    
    def flush_buffers():
        max_len = max(len(deletes), len(inserts))
        for idx in range(max_len):
            d_line = deletes[idx] if idx < len(deletes) else ""
            i_line = inserts[idx] if idx < len(inserts) else ""
            
            left_side.append(Text(f"- {d_line}" if d_line else "", style=Style(color="red") if d_line else Style(color="white")))
            right_side.append(Text(f"+ {i_line}" if i_line else "", style=Style(color="green") if i_line else Style(color="white")))
        deletes.clear()
        inserts.clear()

    for line in lines:
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            flush_buffers()
            # Mark metadata as a separator line across both panels
            meta = Text(line, style=Style(color="cyan", dim=True))
            left_side.append(meta)
            right_side.append(Text(""))
            continue
            
        if line.startswith("-"):
            deletes.append(line[1:])
        elif line.startswith("+"):
            inserts.append(line[1:])
        else:
            flush_buffers()
            body = line[1:] if line.startswith(" ") else line
            left_side.append(Text(f" {body}", style=Style(color="white")))
            right_side.append(Text(f" {body}", style=Style(color="white")))
            
    flush_buffers()
    return _build_table_from_columns(left_side, right_side, width)


def _build_table_from_columns(left_side: list[Text], right_side: list[Text], width: int) -> Table:
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=None,
        expand=True
    )
    
    col_width = (width - 6) // 2
    table.add_column("Original Code", width=col_width)
    table.add_column(" │ ", style="dim white", width=3)
    table.add_column("Modified Code", width=col_width)

    max_display_lines = min(len(left_side), 150)
    for i in range(max_display_lines):
        l_text = left_side[i]
        r_text = right_side[i]
        
        if len(l_text.plain) > col_width:
            l_text.truncate(col_width - 3)
            l_text.append("...")
        if len(r_text.plain) > col_width:
            r_text.truncate(col_width - 3)
            r_text.append("...")
            
        table.add_row(l_text, " │ ", r_text)

    if len(left_side) > 150:
        table.add_row(
            Text(f"... (truncated {len(left_side) - 150} lines) ...", style="dim italic"),
            " │ ",
            Text(f"... (truncated {len(left_side) - 150} lines) ...", style="dim italic")
        )

    return table
