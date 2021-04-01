from nkssg.plugins.auto_p import AutoPPlugin

def test_block_one_line():
    plugin = AutoPPlugin()
    before_text = '<p>sample</p>'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>sample</p>'
    assert after_text == should_be_text


def test_non_tag_one_line():
    plugin = AutoPPlugin()
    before_text = 'sample'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>sample</p>'
    assert after_text == should_be_text


def test_non_block_one_line():
    plugin = AutoPPlugin()
    before_text = '<span>sample</span>sample'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p><span>sample</span>sample</p>'
    assert after_text == should_be_text


def test_block_two_line():
    plugin = AutoPPlugin()
    before_text = '<p>line1\nline2</p>'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1\nline2</p>'
    assert after_text == should_be_text


def test_non_tag_two_line():
    plugin = AutoPPlugin()
    before_text = 'line1\nline2'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1<br />\nline2</p>'
    assert after_text == should_be_text


def test_non_block_two_line():
    plugin = AutoPPlugin()
    before_text = '<span>line1</span>\n<span>line2</span>'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p><span>line1</span><br />\n<span>line2</span></p>'
    assert after_text == should_be_text


def test_block_three_line():
    plugin = AutoPPlugin()
    before_text = '<p>line1\nline2\nline3</p>'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1\nline2\nline3</p>'
    assert after_text == should_be_text


def test_non_tag_three_line():
    plugin = AutoPPlugin()
    before_text = 'line1\nline2\nline3'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1<br />\nline2<br />\nline3</p>'
    assert after_text == should_be_text


def test_one_block_one_blank_one_block():
    plugin = AutoPPlugin()
    before_text = '<p>line1</p>\n\n<p>line2</p>'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1</p>\n\n<p>line2</p>'
    assert after_text == should_be_text


def test_one_non_block_one_blank_one_block():
    plugin = AutoPPlugin()
    before_text = 'line1\n\n<p>line2</p>'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1</p>\n\n<p>line2</p>'
    assert after_text == should_be_text


def test_one_non_block_two_blank_one_block():
    plugin = AutoPPlugin()
    before_text = 'line1\n\n\n<p>line2</p>'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1</p>\n\n\n<p>line2</p>'
    assert after_text == should_be_text


def test_two_non_block_two_blank_two_non_block():
    plugin = AutoPPlugin()
    before_text = 'line1\nline2\n\n\nline3\nline4'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1<br />\nline2</p>\n\n\n<p>line3<br />\nline4</p>'
    assert after_text == should_be_text


def test_hr_with_blank_line():
    plugin = AutoPPlugin()
    before_text = 'line1\nline2\n\n<hr>\n\nline3\nline4'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1<br />\nline2</p>\n\n<hr>\n\n<p>line3<br />\nline4</p>'
    assert after_text == should_be_text


def test_hr_with_no_blank_line():
    plugin = AutoPPlugin()
    before_text = 'line1\nline2\n<hr>\nline3\nline4'
    after_text = plugin.autoP(before_text)
    should_be_text = '<p>line1<br />\nline2<br />\n<hr>\nline3<br />\nline4</p>'
    assert after_text == should_be_text
