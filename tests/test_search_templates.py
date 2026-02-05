# coding=utf-8
"""Tests for medusa.search_templates module."""

from medusa.search_templates import SearchTemplates


def _create_mock_functions(series, scene_exceptions, initial_templates, deleted_ids):
    """Create mock database functions for testing _clean() behavior.
    
    Args:
        series: The show object being tested
        scene_exceptions: List of scene exception dicts for this show
        initial_templates: List of template dicts in the database
        deleted_ids: List to track which template IDs are deleted
    
    Returns:
        Tuple of (mock_action, mock_select) functions
    """
    def mock_action(query, params):
        """Mock the database action method to track deletions."""
        if 'DELETE from search_templates' in query:
            for template in initial_templates:
                if (template['indexer'] == params[0] and
                    template['series_id'] == params[1] and
                    template['default'] == 1 and
                    template['title'] not in [e['title'] for e in scene_exceptions] and
                    template['title'] != series.name):
                    deleted_ids.append(template['search_template_id'])
    
    def mock_select(query, params):
        """Mock the database select method."""
        if 'FROM search_templates' in query:
            return [t for t in initial_templates if t['search_template_id'] not in deleted_ids]
        elif 'FROM scene_exceptions' in query:
            return scene_exceptions
        return []
    
    return mock_action, mock_select


def test_clean_preserves_custom_templates(monkeypatch, create_tvshow):
    """Test that _clean() preserves custom templates (default=0) even when titles don't match scene exceptions."""
    # Create a test show
    series = create_tvshow(indexer=1, indexerid=1, name='Test Show')
    
    # Mock the database to return scene exceptions (only one exception exists)
    scene_exceptions = [
        {
            'indexer': 1,
            'series_id': 1,
            'season': 1,
            'title': 'Valid Exception'
        }
    ]
    
    # Mock the initial templates in the database
    # Include both default and custom templates
    initial_templates = [
        {
            'search_template_id': 1,
            'template': '%SN S%0SE%0E',
            'title': 'Test Show',
            'indexer': 1,
            'series_id': 1,
            'season': -1,
            'enabled': 1,
            'default': 1,  # Default template with show name (should be preserved)
            'season_search': 0
        },
        {
            'search_template_id': 2,
            'template': '%SN S%0SE%0E',
            'title': 'Valid Exception',
            'indexer': 1,
            'series_id': 1,
            'season': 1,
            'enabled': 1,
            'default': 1,  # Default template with valid scene exception (should be preserved)
            'season_search': 0
        },
        {
            'search_template_id': 3,
            'template': '%SN S%0SE%0E',
            'title': 'Old Exception',
            'indexer': 1,
            'series_id': 1,
            'season': 2,
            'enabled': 1,
            'default': 1,  # Default template without scene exception (should be removed)
            'season_search': 0
        },
        {
            'search_template_id': 4,
            'template': '%SN custom template',
            'title': 'Custom Title',
            'indexer': 1,
            'series_id': 1,
            'season': 1,
            'enabled': 1,
            'default': 0,  # Custom template (should NEVER be removed)
            'season_search': 0
        },
        {
            'search_template_id': 5,
            'template': '%SN another custom',
            'title': 'Orphaned Custom',
            'indexer': 1,
            'series_id': 1,
            'season': 3,
            'enabled': 1,
            'default': 0,  # Custom template without scene exception (should still be preserved)
            'season_search': 0
        }
    ]
    
    deleted_ids = []
    
    # Apply mocks
    search_templates = SearchTemplates(series)
    mock_action, mock_select = _create_mock_functions(series, scene_exceptions, initial_templates, deleted_ids)
    monkeypatch.setattr(search_templates.main_db_con, 'action', mock_action)
    monkeypatch.setattr(search_templates.main_db_con, 'select', mock_select)
    
    # Execute read_from_db which calls _clean()
    search_templates.read_from_db()
    
    # Verify results
    # Should have deleted template ID 3 (Old Exception - default template without scene exception)
    assert 3 in deleted_ids, "Default template 'Old Exception' should be removed"
    
    # Should NOT have deleted template IDs 1, 2 (show name and valid exception)
    assert 1 not in deleted_ids, "Default template with show name should be preserved"
    assert 2 not in deleted_ids, "Default template with valid scene exception should be preserved"
    
    # Should NOT have deleted template IDs 4, 5 (custom templates)
    assert 4 not in deleted_ids, "Custom template should be preserved"
    assert 5 not in deleted_ids, "Custom template without scene exception should still be preserved"
    
    # Verify the templates list
    template_ids = [t.id for t in search_templates.templates]
    assert 1 in template_ids, "Show name template should be in results"
    assert 2 in template_ids, "Valid exception template should be in results"
    assert 3 not in template_ids, "Old exception template should not be in results"
    assert 4 in template_ids, "Custom template should be in results"
    assert 5 in template_ids, "Orphaned custom template should be in results"


def test_clean_removes_default_templates_without_exceptions(monkeypatch, create_tvshow):
    """Test that _clean() removes default templates when their scene exceptions are removed."""
    # Create a test show
    series = create_tvshow(indexer=1, indexerid=2, name='Another Show')
    
    # Mock the database with NO scene exceptions
    scene_exceptions = []
    
    # Mock the initial templates in the database
    initial_templates = [
        {
            'search_template_id': 10,
            'template': '%SN S%0SE%0E',
            'title': 'Another Show',
            'indexer': 1,
            'series_id': 2,
            'season': -1,
            'enabled': 1,
            'default': 1,  # Default template with show name (should be preserved)
            'season_search': 0
        },
        {
            'search_template_id': 11,
            'template': '%SN S%0SE%0E',
            'title': 'Removed Exception 1',
            'indexer': 1,
            'series_id': 2,
            'season': 1,
            'enabled': 1,
            'default': 1,  # Default template without scene exception (should be removed)
            'season_search': 0
        },
        {
            'search_template_id': 12,
            'template': '%SN S%0SE%0E',
            'title': 'Removed Exception 2',
            'indexer': 1,
            'series_id': 2,
            'season': 2,
            'enabled': 1,
            'default': 1,  # Default template without scene exception (should be removed)
            'season_search': 0
        }
    ]
    
    deleted_ids = []
    
    # Apply mocks
    search_templates = SearchTemplates(series)
    mock_action, mock_select = _create_mock_functions(series, scene_exceptions, initial_templates, deleted_ids)
    monkeypatch.setattr(search_templates.main_db_con, 'action', mock_action)
    monkeypatch.setattr(search_templates.main_db_con, 'select', mock_select)
    
    # Execute read_from_db which calls _clean()
    search_templates.read_from_db()
    
    # Verify results
    # Should have deleted template IDs 11 and 12 (removed exceptions)
    assert 11 in deleted_ids, "Default template 'Removed Exception 1' should be removed"
    assert 12 in deleted_ids, "Default template 'Removed Exception 2' should be removed"
    
    # Should NOT have deleted template ID 10 (show name)
    assert 10 not in deleted_ids, "Default template with show name should be preserved"
    
    # Verify the templates list
    template_ids = [t.id for t in search_templates.templates]
    assert 10 in template_ids, "Show name template should be in results"
    assert 11 not in template_ids, "Removed exception 1 template should not be in results"
    assert 12 not in template_ids, "Removed exception 2 template should not be in results"


def test_clean_with_multiple_shows(monkeypatch, create_tvshow):
    """Test that _clean() only affects templates for the specific show."""
    # Create two test shows
    series1 = create_tvshow(indexer=1, indexerid=100, name='Show One')
    series2 = create_tvshow(indexer=1, indexerid=200, name='Show Two')
    
    # Mock the database with scene exceptions for both shows
    scene_exceptions_map = {
        100: [{'indexer': 1, 'series_id': 100, 'season': 1, 'title': 'Exception One'}],
        200: [{'indexer': 1, 'series_id': 200, 'season': 1, 'title': 'Exception Two'}]
    }
    
    # Mock templates for both shows
    all_templates = [
        # Show 1 templates
        {
            'search_template_id': 101,
            'template': '%SN S%0SE%0E',
            'title': 'Show One',
            'indexer': 1,
            'series_id': 100,
            'season': -1,
            'enabled': 1,
            'default': 1,
            'season_search': 0
        },
        {
            'search_template_id': 102,
            'template': '%SN S%0SE%0E',
            'title': 'Old Exception One',
            'indexer': 1,
            'series_id': 100,
            'season': 2,
            'enabled': 1,
            'default': 1,  # Should be removed for show 1
            'season_search': 0
        },
        # Show 2 templates
        {
            'search_template_id': 201,
            'template': '%SN S%0SE%0E',
            'title': 'Show Two',
            'indexer': 1,
            'series_id': 200,
            'season': -1,
            'enabled': 1,
            'default': 1,
            'season_search': 0
        },
        {
            'search_template_id': 202,
            'template': '%SN S%0SE%0E',
            'title': 'Old Exception Two',
            'indexer': 1,
            'series_id': 200,
            'season': 2,
            'enabled': 1,
            'default': 1,  # Should NOT be affected when cleaning show 1
            'season_search': 0
        }
    ]
    
    deleted_ids = []
    
    # Test cleaning for series1
    search_templates1 = SearchTemplates(series1)
    exceptions1 = scene_exceptions_map.get(series1.series_id, [])
    mock_action1, mock_select1 = _create_mock_functions(series1, exceptions1, all_templates, deleted_ids)
    
    # Wrap mock_select to filter by series_id for multi-show scenario
    original_select = mock_select1
    def filtered_select(query, params):
        """Filter templates by series_id for multi-show tests."""
        if 'FROM search_templates' in query:
            return [t for t in all_templates 
                    if t['series_id'] == series1.series_id and 
                    t['search_template_id'] not in deleted_ids]
        return original_select(query, params)
    
    monkeypatch.setattr(search_templates1.main_db_con, 'action', mock_action1)
    monkeypatch.setattr(search_templates1.main_db_con, 'select', filtered_select)
    
    search_templates1.read_from_db()
    
    # Verify only show 1's orphaned template was deleted
    assert 102 in deleted_ids, "Show 1's orphaned template should be removed"
    assert 202 not in deleted_ids, "Show 2's template should not be affected"
    
    # Verify show 1's templates
    template_ids1 = [t.id for t in search_templates1.templates]
    assert 101 in template_ids1, "Show 1's name template should be in results"
    assert 102 not in template_ids1, "Show 1's orphaned template should not be in results"
    assert 201 not in template_ids1, "Show 2's templates should not appear for show 1"
    assert 202 not in template_ids1, "Show 2's templates should not appear for show 1"
