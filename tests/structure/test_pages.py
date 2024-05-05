from nkssg.structure.pages import Page


def test_clean_name_no_underscore():
    ret = Page.clean_name('sample')
    assert ret == 'sample'


def test_clean_name_underscore_normal():
    ret = Page.clean_name('_10_sample')
    assert ret == 'sample'


def test_clean_name_underscore_first():
    ret = Page.clean_name('_sample')
    assert ret == '_sample'


def test_clean_name_underscore_first_last():
    ret = Page.clean_name('_sample_')
    assert ret == '_sample_'


def test_clean_name_underscore_first_middle_last():
    ret = Page.clean_name('_sample_sample_')
    assert ret == 'sample_'


def test_clean_name_underscore_middle():
    ret = Page.clean_name('sample_sample')
    assert ret == 'sample_sample'


def test_clean_name_underscore_first_middle_middle():
    ret = Page.clean_name('_sample1_sample2_sample3')
    assert ret == 'sample2_sample3'


def test_clean_name_underscore_double():
    ret = Page.clean_name('__sample')
    assert ret == '_sample'


def test_clean_name_underscore_triple():
    ret = Page.clean_name('___sample')
    assert ret == '__sample'
