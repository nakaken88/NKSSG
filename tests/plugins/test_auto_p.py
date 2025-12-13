import pytest
from nkssg.plugins.auto_p import AutoPPlugin
from nkssg.structure.singles import Single
from nkssg.structure.config import Config

@pytest.mark.parametrize(
    "file_ext, input_doc, expected_output",
    [
        # Test cases for extensions that should be processed
        ("html", "Line 1.\nLine 2.", "<p>Line 1.<br />\nLine 2.</p>"),
        ("htm", "Line 1.\nLine 2.", "<p>Line 1.<br />\nLine 2.</p>"),
        ("txt", "Line 1.\nLine 2.", "<p>Line 1.<br />\nLine 2.</p>"),
        
        # Test cases for extensions that should be ignored
        ("md", "Line 1.\nLine 2.", "Line 1.\nLine 2."),
        ("py", "import os", "import os"),

        # Edge cases for content
        ("html", "", ""), # Empty string
        ("html", "Line 1.\n\nLine 2.", "<p>Line 1.</p>\n<p>Line 2.</p>"), # Double newline
        ("html", "<b>Bold</b>\nLine 2.", "<p><b>Bold</b><br />\nLine 2.</p>"), # Existing HTML
        ("html", "No newlines.", "<p>No newlines.</p>"), # No newlines
    ]
)
def test_auto_p_plugin(file_ext, input_doc, expected_output):
    """
    Test AutoPPlugin with various file extensions and content edge cases.
    """
    plugin = AutoPPlugin()
    config = Config.from_file()
    
    dummy_single = Single(abs_src_path=Config().docs_dir / "post" / f"dummy.{file_ext}", config=config)
    dummy_single.ext = file_ext

    processed_content = plugin.on_get_content(input_doc, config, dummy_single)
    
    assert processed_content == expected_output
