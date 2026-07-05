"""Search-and-replace code patcher for AXON (Aider-style original/updated block replacements)."""

from __future__ import annotations

import re
from pathlib import Path


def apply_search_replace_patch(file_path: str | Path, patch_text: str) -> tuple[bool, str]:
    """
    Parses Aider-style search-and-replace blocks:
    <<<<<<< ORIGINAL
    [original code]
    =======
    [updated code]
    >>>>>>> UPDATED
    And applies them to the file. Returns (success, status_message).
    """
    path = Path(file_path)
    if not path.is_file():
        return False, f"File {file_path} does not exist"

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        return False, f"Failed to read file: {exc}"

    # Regex to find blocks of <<<<<<< ORIGINAL ... ======= ... >>>>>>> UPDATED
    pattern = re.compile(
        r"<<<<<<< ORIGINAL\n(.*?)\n=======\n(.*?)\n>>>>>>> UPDATED",
        re.DOTALL
    )

    blocks = pattern.findall(patch_text)
    if not blocks:
        # Fallback to simple replace if it's not wrapped in Aider tags but matches block structures
        return False, "No valid <<<<<<< ORIGINAL/=======/>>>>>>> UPDATED blocks found in patch"

    updated_content = content
    success_count = 0

    for original, replacement in blocks:
        # Exact match check first
        if original in updated_content:
            updated_content = updated_content.replace(original, replacement, 1)
            success_count += 1
            continue

        # If exact match fails, try ignoring leading/trailing whitespaces per line
        orig_lines = [line.strip() for line in original.strip().splitlines() if line.strip()]
        if not orig_lines:
            continue

        # Search for a block in the content where non-empty lines match our normalized target
        content_lines = updated_content.splitlines()
        found_start_idx = -1
        
        for idx in range(len(content_lines) - len(orig_lines) + 1):
            match = True
            for match_offset, target_line in enumerate(orig_lines):
                curr_line = content_lines[idx + match_offset].strip()
                if curr_line != target_line:
                    match = False
                    break
            if match:
                found_start_idx = idx
                break

        if found_start_idx != -1:
            # We found the block! Replace those lines
            before = "\n".join(content_lines[:found_start_idx])
            after = "\n".join(content_lines[found_start_idx + len(orig_lines):])
            
            # Reconstruct with indentation matching the first line of the original block
            orig_indent = len(content_lines[found_start_idx]) - len(content_lines[found_start_idx].lstrip())
            indent_str = " " * orig_indent
            
            indented_replacement_lines = []
            for r_line in replacement.splitlines():
                if r_line.strip():
                    indented_replacement_lines.append(indent_str + r_line.lstrip())
                else:
                    indented_replacement_lines.append("")
            
            middle = "\n".join(indented_replacement_lines)
            updated_content = f"{before}\n{middle}\n{after}" if before else f"{middle}\n{after}"
            success_count += 1

    if success_count == 0:
        return False, "Could not locate the original blocks inside the target file"

    try:
        path.write_text(updated_content, encoding="utf-8")
        return True, f"Successfully applied {success_count} patch blocks to {path.name}"
    except Exception as exc:
        return False, f"Failed to write patched file: {exc}"
