def test_mark(bitmapist):
    ev = bitmapist.UniqueEvents('foo')
    bitmapist.mark_unique('foo', 1)
    assert 1 in ev
    assert 2 not in ev


def test_unmark(bitmapist):
    ev = bitmapist.UniqueEvents('foo')
    bitmapist.mark_unique('foo', 1)
    bitmapist.unmark_unique('foo', 1)
    assert 1 not in ev


def test_ops(bitmapist):
    bitmapist.mark_unique('foo', 1)
    bitmapist.mark_unique('foo', 2)
    bitmapist.mark_unique('bar', 2)
    bitmapist.mark_unique('bar', 3)

    foo = bitmapist.UniqueEvents('foo')
    bar = bitmapist.UniqueEvents('bar')
    assert list(foo & bar) == [2]
    assert list(foo | bar) == [1, 2, 3]


def test_ops_with_dates(bitmapist):
    bitmapist.mark_event('active', 1)
    bitmapist.mark_event('active', 2)
    bitmapist.mark_unique('foo', 2)
    bitmapist.mark_unique('foo', 3)

    foo = bitmapist.UniqueEvents('foo')
    active = bitmapist.DayEvents('active')

    assert list(foo & active) == [2]
    assert list(foo | active) == [1, 2, 3]

    assert list(foo & active.prev()) == []
    assert list(foo | active.prev()) == [2, 3]


def test_track_unique(bitmapist, bitmapist_non_unique):
    bitmapist.mark_event('foo', 1)
    bitmapist_non_unique.mark_event('foo', 2)
    assert list(bitmapist.DayEvents('foo')) == [1, 2]
    assert list(bitmapist_non_unique.UniqueEvents('foo')) == [1]
