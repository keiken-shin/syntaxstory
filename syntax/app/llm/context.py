import math
from typing import Dict, List, Tuple


def truncate_string_middle(content: str, max_length: int, marker: str = "\n... [TRUNCATED {lines} lines] ...\n") -> str:
    """
    Truncates a string from the middle if it exceeds max_length, 
    preserving the beginning and the end.
    Replaces the removed section with a marker indicating how many lines were dropped.
    """
    if not content or len(content) <= max_length:
        return content

    # Use a generic marker first to calculate split sizes
    dummy_marker = marker.format(lines=9999)  # Use worst-case realistic line count for length logic
    
    if max_length <= len(dummy_marker):
        return content[:max_length]  # fallback if max_length is too small
        
    chars_to_keep = max_length - len(dummy_marker)
    head_len = math.ceil(chars_to_keep * 0.5)
    tail_len = chars_to_keep - head_len

    head_content = content[:head_len]
    tail_content = content[-tail_len:] if tail_len > 0 else ""
    
    # Calculate how many lines were removed
    removed_section = content[head_len:len(content)-tail_len]
    removed_lines = removed_section.count('\n')
    
    actual_marker = marker.format(lines=removed_lines)
    
    return head_content + actual_marker + tail_content


def apply_context_budget(
    files: List[Tuple[str, str]], 
    max_total_length: int = 100_000, 
    max_file_length: int = 10_000
) -> List[Tuple[str, str]]:
    """
    Applies a strict character budget to a list of files.
    - Limits individual files to max_file_length.
    - Limits total prompt context to max_total_length.
    - Drops files entirely if budget runs out.
    
    Args:
        files: List of (path, content) tuples.
        max_total_length: Maximum allowed characters across all files.
        max_file_length: Maximum allowed characters for a single file.
        
    Returns:
        List of processed (path, content) tuples within budget constraints.
    """
    result: List[Tuple[str, str]] = []
    current_length = 0
    
    for path, content in files:
        if not content:
            continue
            
        # 1. Apply individual file limit
        truncated_content = truncate_string_middle(content, max_file_length)
        file_len = len(truncated_content)
        
        # 2. Check total budget
        if current_length + file_len > max_total_length:
            # We must truncate the file further to fit the remaining budget, or drop it
            remaining = max_total_length - current_length
            if remaining < 100:  # Too small to be useful
                continue
                
            truncated_content = truncate_string_middle(truncated_content, remaining)
            file_len = len(truncated_content)
            
            result.append((path, truncated_content))
            current_length += file_len
            break # Budget entirely consumed
            
        result.append((path, truncated_content))
        current_length += file_len
        
    return result
