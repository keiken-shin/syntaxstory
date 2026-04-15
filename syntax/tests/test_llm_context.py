from app.llm.context import truncate_string_middle, apply_context_budget

def test_truncate_string_middle_too_short():
    content = "Hello exactly 21 chars"
    assert truncate_string_middle(content, 22) == content

def test_truncate_string_middle_typical():
    content = "Line1\nLine2\nLine3\nLine4\nLine5\nLine6\nLine7"
    # Make it truncate lines 3-5
    truncated = truncate_string_middle(content, 35, marker="\n...[cut {lines}]...\n") 
    assert "Line7" in truncated

def test_apply_context_budget_single_file_limit():
    content = "A" * 1000
    files = [("main.py", content)]
    result = apply_context_budget(files, max_total_length=2000, max_file_length=500)
    assert len(result) == 1
    path, processed_content = result[0]
    assert path == "main.py"
    assert len(processed_content) <= 500
    assert "TRUNCATED" in processed_content

def test_apply_context_budget_total_limit():
    content1 = "A" * 500
    content2 = "B" * 500
    content3 = "C" * 500
    
    files = [("file1.txt", content1), ("file2.txt", content2), ("file3.txt", content3)]
    
    # 1st file: 500, 2nd file: truncated to 300, 3rd file dropped
    result = apply_context_budget(files, max_total_length=800, max_file_length=1000)
    assert len(result) == 2
    assert result[0][0] == "file1.txt"
    assert result[1][0] == "file2.txt"
    
    assert len(result[0][1]) == 500
    assert len(result[1][1]) <= 300
    assert "TRUNCATED" in result[1][1]

def test_apply_context_budget_empty():
    assert apply_context_budget([], 100, 100) == []
    
def test_apply_context_budget_no_drop_small():
    content = "Small"
    files = [("small.txt", content)]
    result = apply_context_budget(files, max_total_length=2, max_file_length=100)
    # Remaining is less than 100 in the loop so it wouldn't even append if we used a strict remaining limit, but 2 is actually smaller than the dummy marker.
    assert len(result) == 0
