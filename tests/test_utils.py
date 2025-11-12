import os
import sys
import pickle
import difflib
import requests
import pytest
from io import StringIO
from unittest.mock import Mock, patch, MagicMock, call
from collections import defaultdict
from bs4 import BeautifulSoup
from rich.console import Console

from namecheck.utils import (
    load_package_names_from_cache,
    save_package_names_to_cache,
    get_all_package_names,
    get_sources_for_name,
    is_name_taken_global_index,
    is_name_taken_project_url,
    get_close_matches,
    get_name_availability,
    render_name_availability,
    print_available,
    print_taken,
    print_matches,
    SOURCES
)


class TestCacheFunctions:
    """Tests for cache loading and saving functions."""

    @patch('namecheck.utils.user_cache_dir')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('builtins.open', create=True)
    @patch('pickle.load')
    def test_load_package_names_from_cache_success(self, mock_pickle_load, mock_open, mock_getsize, mock_exists, mock_cache_dir):
        """Test successfully loading package names from cache."""
        mock_cache_dir.return_value = '/fake/cache/dir'
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        
        expected_data = {'package1': {'PyPI'}, 'package2': {'TestPyPI'}}
        mock_pickle_load.return_value = expected_data
        
        result = load_package_names_from_cache()
        
        assert result == {'package1': {'PyPI'}, 'package2': {'TestPyPI'}}
        mock_open.assert_called_once_with('/fake/cache/dir/package_names.pkl', 'rb')

    @patch('namecheck.utils.user_cache_dir')
    @patch('os.path.exists')
    def test_load_package_names_cache_not_exists(self, mock_exists, mock_cache_dir):
        """Test loading when cache file doesn't exist."""
        mock_cache_dir.return_value = '/fake/cache/dir'
        mock_exists.return_value = False
        
        result = load_package_names_from_cache()
        
        assert result is None

    @patch('namecheck.utils.user_cache_dir')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_load_package_names_cache_empty(self, mock_getsize, mock_exists, mock_cache_dir):
        """Test loading when cache file is empty."""
        mock_cache_dir.return_value = '/fake/cache/dir'
        mock_exists.return_value = True
        mock_getsize.return_value = 0
        
        result = load_package_names_from_cache()
        
        assert result is None

    @patch('namecheck.utils.user_cache_dir')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('builtins.open', create=True)
    @patch('pickle.load')
    def test_load_package_names_corrupted_cache(self, mock_pickle_load, mock_open, mock_getsize, mock_exists, mock_cache_dir, capsys):
        """Test loading when cache file is corrupted."""
        mock_cache_dir.return_value = '/fake/cache/dir'
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        mock_pickle_load.side_effect = pickle.UnpicklingError("Corrupted data")
        
        result = load_package_names_from_cache()
        
        assert result is None
        captured = capsys.readouterr()
        assert "corrupted" in captured.err.lower()

    @patch('namecheck.utils.user_cache_dir')
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    @patch('pickle.dump')
    def test_save_package_names_to_cache(self, mock_pickle_dump, mock_open, mock_makedirs, mock_cache_dir):
        """Test saving package names to cache."""
        mock_cache_dir.return_value = '/fake/cache/dir'
        test_data = {'package1': {'PyPI'}}
        
        save_package_names_to_cache(test_data)
        
        mock_makedirs.assert_called_once_with('/fake/cache/dir', exist_ok=True)
        mock_open.assert_called_once_with('/fake/cache/dir/package_names.pkl', 'wb')
        mock_pickle_dump.assert_called_once()


class TestGetAllPackageNames:
    """Tests for the get_all_package_names function."""

    @patch('namecheck.utils.load_package_names_from_cache')
    def test_get_all_package_names_from_cache(self, mock_load_cache):
        """Test that cached data is returned when available."""
        cached_data = {'package1': {'PyPI'}, 'package2': {'TestPyPI'}}
        mock_load_cache.return_value = cached_data
        
        result = get_all_package_names()
        
        assert result == cached_data

    @patch('namecheck.utils.load_package_names_from_cache')
    @patch('namecheck.utils.save_package_names_to_cache')
    @patch('namecheck.utils.requests.get')
    def test_get_all_package_names_fetch_success(self, mock_get, mock_save, mock_load_cache, capsys):
        """Test fetching packages from sources when cache is empty."""
        mock_load_cache.return_value = None
        
        mock_response = Mock()
        mock_response.content = b'''
        <html>
            <body>
                <a href="package1/">Package1</a>
                <a href="package2/">Package2</a>
            </body>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = get_all_package_names()
        
        assert 'package1' in result
        assert 'package2' in result
        # Both PyPI and TestPyPI will have these packages since we return the same mock for both
        assert result['package1'] == {'PyPI', 'TestPyPI'}
        assert result['package2'] == {'PyPI', 'TestPyPI'}
        mock_save.assert_called_once()

    @patch('namecheck.utils.load_package_names_from_cache')
    @patch('namecheck.utils.save_package_names_to_cache')
    @patch('namecheck.utils.requests.get')
    def test_get_all_package_names_multiple_sources(self, mock_get, mock_save, mock_load_cache):
        """Test fetching from multiple sources with overlapping packages."""
        mock_load_cache.return_value = None
        
        pypi_response = Mock()
        pypi_response.content = b'<html><body><a>shared</a><a>pypi-only</a></body></html>'
        pypi_response.raise_for_status = Mock()
        
        testpypi_response = Mock()
        testpypi_response.content = b'<html><body><a>shared</a><a>testpypi-only</a></body></html>'
        testpypi_response.raise_for_status = Mock()
        
        mock_get.side_effect = [pypi_response, testpypi_response]
        
        result = get_all_package_names()
        
        assert 'shared' in result
        assert result['shared'] == {'PyPI', 'TestPyPI'}
        assert result['pypi-only'] == {'PyPI'}
        assert result['testpypi-only'] == {'TestPyPI'}

    @patch('namecheck.utils.load_package_names_from_cache')
    @patch('namecheck.utils.save_package_names_to_cache')
    @patch('namecheck.utils.requests.get')
    def test_get_all_package_names_request_exception(self, mock_get, mock_save, mock_load_cache, capsys):
        """Test handling of request exceptions."""
        mock_load_cache.return_value = None
        mock_get.side_effect = requests.RequestException("Connection error")
        
        result = get_all_package_names()
        
        assert result == {}
        captured = capsys.readouterr()
        assert "Error fetching data" in captured.err

    @patch('namecheck.utils.load_package_names_from_cache')
    @patch('namecheck.utils.requests.get')
    def test_get_all_package_names_case_normalization(self, mock_get, mock_load_cache):
        """Test that package names are normalized to lowercase."""
        mock_load_cache.return_value = None
        
        mock_response = Mock()
        mock_response.content = b'<html><body><a>MyPackage</a><a>UPPERCASE</a></body></html>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with patch('namecheck.utils.save_package_names_to_cache'):
            result = get_all_package_names()
        
        assert 'mypackage' in result
        assert 'uppercase' in result


class TestGetSourcesForName:
    """Tests for the get_sources_for_name function."""

    def test_get_sources_for_name_single_source(self):
        """Test getting sources for a name with one source."""
        all_names = {'package1': {'PyPI'}}
        
        result = get_sources_for_name('package1', all_names)
        
        assert result == ['PyPI']

    def test_get_sources_for_name_multiple_sources(self):
        """Test getting sources for a name with multiple sources."""
        all_names = {'package1': {'TestPyPI', 'PyPI'}}
        
        result = get_sources_for_name('package1', all_names)
        
        assert result == ['PyPI', 'TestPyPI']  # Should be sorted

    def test_get_sources_for_name_case_insensitive(self):
        """Test that name lookup is case-insensitive."""
        all_names = {'mypackage': {'PyPI'}}
        
        result = get_sources_for_name('MyPackage', all_names)
        
        assert result == ['PyPI']

    def test_get_sources_for_name_not_found(self):
        """Test getting sources for a non-existent name."""
        all_names = {'package1': {'PyPI'}}
        
        result = get_sources_for_name('nonexistent', all_names)
        
        assert result == []


class TestIsNameTakenGlobalIndex:
    """Tests for the is_name_taken_global_index function."""

    def test_is_name_taken_global_index_found(self):
        """Test when name is found in global index."""
        all_names = {'existing-package': {'PyPI'}}
        
        result = is_name_taken_global_index('existing-package', all_names)
        
        assert result is True

    def test_is_name_taken_global_index_not_found(self):
        """Test when name is not found in global index."""
        all_names = {'existing-package': {'PyPI'}}
        
        result = is_name_taken_global_index('new-package', all_names)
        
        assert result is False

    def test_is_name_taken_global_index_case_insensitive(self):
        """Test case-insensitive matching."""
        all_names = {'mypackage': {'PyPI'}}
        
        result = is_name_taken_global_index('MyPackage', all_names)
        
        assert result is True


class TestIsNameTakenProjectUrl:
    """Tests for the is_name_taken_project_url function."""

    @patch('namecheck.utils.requests.get')
    def test_is_name_taken_project_url_exists(self, mock_get):
        """Test when package exists on PyPI."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <div class="package-header">
                <h1>Package Name</h1>
            </div>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = is_name_taken_project_url('test-package')
        
        assert 'PyPI' in result

    @patch('namecheck.utils.requests.get')
    def test_is_name_taken_project_url_not_found(self, mock_get):
        """Test when package doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <body>
                <p>Couldn't find this page</p>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = is_name_taken_project_url('nonexistent-package')
        
        assert result == []

    @patch('namecheck.utils.requests.get')
    def test_is_name_taken_project_url_request_exception(self, mock_get, capsys):
        """Test handling of request exceptions."""
        mock_get.side_effect = requests.RequestException("Connection error")
        
        result = is_name_taken_project_url('test-package')
        
        assert result == []
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch('namecheck.utils.requests.get')
    def test_is_name_taken_project_url_project_description(self, mock_get):
        """Test detection using project-description class."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <div class="project-description">
                <p>Project description</p>
            </div>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = is_name_taken_project_url('test-package')
        
        assert 'PyPI' in result


class TestGetCloseMatches:
    """Tests for the get_close_matches function."""

    def test_get_close_matches_found(self):
        """Test finding close matches."""
        all_names = {
            'requests': {'PyPI'},
            'request': {'PyPI'},
            'requestor': {'PyPI'},
            'completely-different': {'PyPI'}
        }
        
        result = get_close_matches('requester', all_names)
        
        assert 'request' in result or 'requests' in result

    def test_get_close_matches_exact_removed(self):
        """Test that exact match is removed from close matches."""
        all_names = {
            'mypackage': {'PyPI'},
            'mypackages': {'PyPI'},
            'my-package': {'PyPI'}
        }
        
        result = get_close_matches('mypackage', all_names)
        
        assert 'mypackage' not in result

    def test_get_close_matches_none_found(self):
        """Test when no close matches are found."""
        all_names = {
            'completely': {'PyPI'},
            'different': {'PyPI'},
            'words': {'PyPI'}
        }
        
        result = get_close_matches('xyz123unique', all_names)
        
        assert result == []

    def test_get_close_matches_case_insensitive(self):
        """Test case-insensitive matching."""
        all_names = {
            'mypackage': {'PyPI'},
            'mypackages': {'PyPI'}
        }
        
        result = get_close_matches('MyPackage', all_names)
        
        assert 'mypackage' not in result  # Exact match removed
        assert len(result) >= 0  # May or may not have other matches


class TestGetNameAvailability:
    """Tests for the get_name_availability function."""

    @patch('namecheck.utils.is_name_taken_project_url')
    def test_get_name_availability_taken_in_index(self, mock_project_url):
        """Test when name is taken (found in global index)."""
        all_names = {'existing-package': {'PyPI'}}
        
        is_available, taken_sources, close_matches = get_name_availability('existing-package', all_names)
        
        assert is_available is False
        assert taken_sources == ['PyPI']

    @patch('namecheck.utils.is_name_taken_project_url')
    def test_get_name_availability_available(self, mock_project_url):
        """Test when name is available."""
        all_names = {'other-package': {'PyPI'}}
        mock_project_url.return_value = []
        
        is_available, taken_sources, close_matches = get_name_availability('new-package', all_names)
        
        assert is_available is True
        assert taken_sources == []

    @patch('namecheck.utils.is_name_taken_project_url')
    def test_get_name_availability_not_in_index_but_exists(self, mock_project_url):
        """Test when name is not in cached index but exists via URL check."""
        all_names = {'other-package': {'PyPI'}}
        mock_project_url.return_value = ['PyPI']
        
        is_available, taken_sources, close_matches = get_name_availability('new-package', all_names)
        
        assert is_available is False
        assert taken_sources == ['PyPI']

    @patch('namecheck.utils.is_name_taken_project_url')
    def test_get_name_availability_with_close_matches(self, mock_project_url):
        """Test that close matches are returned."""
        all_names = {
            'mypackage': {'PyPI'},
            'mypackages': {'PyPI'},
            'my-package': {'PyPI'}
        }
        mock_project_url.return_value = []
        
        is_available, taken_sources, close_matches = get_name_availability('mypackagee', all_names)
        
        assert is_available is True
        assert len(close_matches) > 0


class TestRenderFunctions:
    """Tests for rendering/printing functions."""

    def test_print_available(self):
        """Test printing availability message."""
        console = Console(file=StringIO())
        
        print_available('test-package', console)
        
        output = console.file.getvalue()
        assert 'test-package' in output
        assert 'available' in output.lower()

    def test_print_taken_single_source(self):
        """Test printing taken message with single source."""
        console = Console(file=StringIO())
        
        print_taken('test-package', ['PyPI'], console)
        
        output = console.file.getvalue()
        assert 'test-package' in output
        assert 'taken' in output.lower()
        assert 'PyPI' in output

    def test_print_taken_multiple_sources(self):
        """Test printing taken message with multiple sources."""
        console = Console(file=StringIO())
        
        print_taken('test-package', ['PyPI', 'TestPyPI'], console)
        
        output = console.file.getvalue()
        assert 'test-package' in output
        assert 'PyPI' in output
        assert 'TestPyPI' in output

    def test_print_matches(self):
        """Test printing close matches."""
        console = Console(file=StringIO())
        all_names = {
            'flask': {'PyPI'},
            'flasks': {'TestPyPI'}
        }
        matches = ['flask', 'flasks']
        
        print_matches(matches, all_names, console)
        
        output = console.file.getvalue()
        assert 'matching' in output.lower()
        assert 'flask' in output

    def test_render_name_availability_available(self):
        """Test rendering when name is available."""
        console = Console(file=StringIO())
        all_names = {}
        
        render_name_availability('test', True, [], [], all_names, console)
        
        output = console.file.getvalue()
        assert 'available' in output.lower()

    def test_render_name_availability_taken(self):
        """Test rendering when name is taken."""
        console = Console(file=StringIO())
        all_names = {}
        
        render_name_availability('test', False, ['PyPI'], [], all_names, console)
        
        output = console.file.getvalue()
        assert 'taken' in output.lower()

    def test_render_name_availability_with_matches(self):
        """Test rendering with close matches."""
        console = Console(file=StringIO())
        all_names = {'test1': {'PyPI'}}
        
        render_name_availability('test', True, [], ['test1'], all_names, console)
        
        output = console.file.getvalue()
        assert 'test1' in output


class TestConstants:
    """Tests for constants and configuration."""

    def test_sources_defined(self):
        """Test that SOURCES is properly defined."""
        assert 'PyPI' in SOURCES
        assert 'TestPyPI' in SOURCES
        assert 'https://pypi.org/' in SOURCES.values()

    def test_sources_urls_valid(self):
        """Test that source URLs are valid."""
        for source_name, url in SOURCES.items():
            assert url.startswith('https://')
            assert url.endswith('/')


class TestIntegration:
    """Integration tests combining multiple functions."""

    @patch('namecheck.utils.load_package_names_from_cache')
    @patch('namecheck.utils.save_package_names_to_cache')
    @patch('namecheck.utils.requests.get')
    @patch('namecheck.utils.is_name_taken_project_url')
    def test_full_workflow_available(self, mock_project_url, mock_get, mock_save, mock_load):
        """Test full workflow for an available name."""
        mock_load.return_value = None
        mock_project_url.return_value = []
        
        mock_response = Mock()
        mock_response.content = b'<html><body><a>flask</a><a>django</a></body></html>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        all_names = get_all_package_names()
        is_available, taken_sources, close_matches = get_name_availability('my-unique-package', all_names)
        
        assert is_available is True
        assert taken_sources == []

    @patch('namecheck.utils.load_package_names_from_cache')
    @patch('namecheck.utils.save_package_names_to_cache')
    @patch('namecheck.utils.requests.get')
    def test_full_workflow_taken(self, mock_get, mock_save, mock_load):
        """Test full workflow for a taken name."""
        mock_load.return_value = None
        
        mock_response = Mock()
        mock_response.content = b'<html><body><a>flask</a><a>django</a></body></html>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        all_names = get_all_package_names()
        is_available, taken_sources, close_matches = get_name_availability('flask', all_names)
        
        assert is_available is False
        assert len(taken_sources) > 0

    @patch('namecheck.utils.load_package_names_from_cache')
    @patch('namecheck.utils.save_package_names_to_cache')
    @patch('namecheck.utils.requests.get')
    def test_full_workflow_with_render(self, mock_get, mock_save, mock_load):
        """Test full workflow including rendering."""
        mock_load.return_value = None
        
        mock_response = Mock()
        mock_response.content = b'<html><body><a>flask</a></body></html>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        all_names = get_all_package_names()
        is_available, taken_sources, close_matches = get_name_availability('flask', all_names)
        
        console = Console(file=StringIO())
        render_name_availability('flask', is_available, taken_sources, close_matches, all_names, console)
        
        output = console.file.getvalue()
        assert 'flask' in output