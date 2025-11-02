from nkssg.plugins.auto_p import AutoPPlugin
from nkssg.structure.singles import Single
from nkssg.structure.config import Config

def test_auto_p_plugin_html_content():
    """Test that AutoPPlugin converts newlines in HTML content to <br> tags."""
    plugin = AutoPPlugin()
    config = Config.from_file()
    
    # A dummy Single object is required because on_get_content checks single.ext
    dummy_single = Single(abs_src_path=Config().docs_dir / "post" / "dummy.html", config=config)
    dummy_single.ext = "html"

    input_doc = "This is line 1.\nThis is line 2."
    
    processed_content = plugin.on_get_content(input_doc, config, dummy_single)

    expected_output = "<p>This is line 1.<br />\nThis is line 2.</p>"
    assert processed_content == expected_output

def test_auto_p_plugin_markdown_content_no_change():
    """Test that AutoPPlugin does not modify Markdown content."""
    plugin = AutoPPlugin()
    config = Config.from_file()
    
    # A dummy Single object is required because on_get_content checks single.ext
    dummy_single = Single(abs_src_path=Config().docs_dir / "post" / "dummy.md", config=config)
    dummy_single.ext = "md"

    input_doc = "This is line 1.\nThis is line 2."
    
    processed_content = plugin.on_get_content(input_doc, config, dummy_single)

    # The plugin should not modify the input if the extension is not html/htm/txt
    assert processed_content == input_doc
