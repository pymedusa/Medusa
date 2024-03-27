# coding=utf-8
"""Tests for medusa.scene_exceptions module."""

from medusa.scene_exceptions import refresh_exceptions_cache, get_season_from_name

def test_referesh_series(monkeypatch_function_return, create_tvshow):
    series1 = create_tvshow(indexerid=1, name='series1')
    series2 = create_tvshow(indexerid=2, name='series2')

    # do an initial load of all exceptions
    initial_exceptions = [('medusa.db.DBConnection.select', [
        {
                'indexer': 1,
                'series_id': 1,
                'season': 1,
                'title': 'exception1',
                'custom': False
        },
        {
                'indexer': 1,
                'series_id': 2,
                'season': 1,
                'title': 'exception2',
                'custom': False
        }])]
    monkeypatch_function_return(initial_exceptions)
    refresh_exceptions_cache()

    assert get_season_from_name(series1, 'exception1') == 1
    assert get_season_from_name(series2, 'exception2') == 1

    # only refresh series2
    series_exceptions = [('medusa.db.DBConnection.select', [
        {
                'indexer': 1,
                'series_id': 2,
                'season': 2,
                'title': 'exception2 modified',
                'custom': False
        }])]
    monkeypatch_function_return(series_exceptions)
    refresh_exceptions_cache(series_obj=series2)

    # both series should be present in the exceptions cache
    assert get_season_from_name(series1, 'exception1') == 1
    assert get_season_from_name(series2, 'exception2 modified') == 2
