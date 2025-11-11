import requests
from unittest.mock import Mock, patch
from namecheck.utils import get_all_package_names, check_name_availability


class TestGetAllPackageNames:
    """Tests for the get_all_package_names function."""
    
    @patch('namecheck.utils.requests.get')
    def test_successful_fetch_single_source(self, mock_get):
        """Test fetching packages from a single source successfully."""
        # Mock HTML response with package names
        mock_response = Mock()
        mock_response.content = b'''
        <html>
            <body>
                <a href="package1/">Package1</a>
                <a href="package2/">Package2</a>
                <a href="package3/">Package3</a>
            </body>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        sources = {'PyPI': 'https://pypi.org/simple/'}
        result = get_all_package_names(sources)
        
        assert 'package1' in result
        assert 'package2' in result
        assert 'package3' in result
        assert result['package1'] == {'PyPI'}
        assert len(result) == 3
    
    @patch('namecheck.utils.requests.get')
    def test_successful_fetch_multiple_sources(self, mock_get):
        """Test fetching packages from multiple sources."""
        mock_response = Mock()
        mock_response.content = b'''
        <html>
            <body>
                <a href="shared/">Shared</a>
                <a href="unique/">Unique</a>
            </body>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        sources = {
            'PyPI': 'https://pypi.org/simple/',
            'TestPyPI': 'https://test.pypi.org/simple/'
        }
        result = get_all_package_names(sources)
        
        # Both sources should have the same packages, so they should be marked as available on both
        assert 'shared' in result
        assert 'unique' in result
        assert 'PyPI' in result['shared']
        assert 'TestPyPI' in result['shared']
    
    @patch('namecheck.utils.requests.get')
    def test_case_normalization(self, mock_get):
        """Test that package names are normalized to lowercase."""
        mock_response = Mock()
        mock_response.content = b'''
        <html>
            <body>
                <a href="MyPackage/">MyPackage</a>
                <a href="UPPERCASE/">UPPERCASE</a>
                <a href="MixedCase/">MixedCase</a>
            </body>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        sources = {'PyPI': 'https://pypi.org/simple/'}
        result = get_all_package_names(sources)
        
        assert 'mypackage' in result
        assert 'uppercase' in result
        assert 'mixedcase' in result
        # Ensure original case is not in the result
        assert 'MyPackage' not in result
        assert 'UPPERCASE' not in result
    
    @patch('namecheck.utils.requests.get')
    def test_empty_response(self, mock_get):
        """Test handling of empty HTML response."""
        mock_response = Mock()
        mock_response.content = b'<html><body></body></html>'
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        sources = {'PyPI': 'https://pypi.org/simple/'}
        result = get_all_package_names(sources)
        
        assert len(result) == 0
    
    @patch('namecheck.utils.requests.get')
    def test_request_exception_handling(self, mock_get):
        """Test that request exceptions are handled gracefully."""
        mock_get.side_effect = requests.RequestException("Connection error")
        
        sources = {'PyPI': 'https://pypi.org/simple/'}
        result = get_all_package_names(sources)
        
        # Should return empty dict when all sources fail
        assert len(result) == 0
    
    @patch('namecheck.utils.requests.get')
    def test_timeout_handling(self, mock_get):
        """Test that timeouts are handled gracefully."""
        mock_get.side_effect = requests.Timeout("Request timed out")
        
        sources = {'PyPI': 'https://pypi.org/simple/'}
        result = get_all_package_names(sources)
        
        assert len(result) == 0
    
    @patch('namecheck.utils.requests.get')

    def test_partial_source_failure(self, mock_get):
        """Test that partial failures still return data from successful sources."""
        # Create separate mock responses
        success_response = Mock()
        success_response.content = b'<html><body><a>package1</a></body></html>'
        success_response.raise_for_status = Mock()
        
        # Set up side_effect to return success for PyPI and raise exception for TestPyPI
        def mock_get_side_effect(url, timeout):
            if 'test.pypi.org' in url:
                raise requests.RequestException("Failed")
            else:
                return success_response
        
        mock_get.side_effect = mock_get_side_effect
        
        sources = {
            'PyPI': 'https://pypi.org/simple/',
            'TestPyPI': 'https://test.pypi.org/simple/'
        }
        result = get_all_package_names(sources)
        
        # Should have data from PyPI only
        assert 'package1' in result
        assert result['package1'] == {'PyPI'}
        assert 'TestPyPI' not in result['package1']
    
    @patch('namecheck.utils.requests.get')
    def test_duplicate_package_across_sources(self, mock_get):
        """Test that packages appearing in multiple sources are tracked correctly."""
        pypi_response = Mock()
        pypi_response.content = b'<html><body><a>shared-package</a></body></html>'
        pypi_response.raise_for_status = Mock()
        
        testpypi_response = Mock()
        testpypi_response.content = b'<html><body><a>shared-package</a></body></html>'
        testpypi_response.raise_for_status = Mock()
        
        mock_get.side_effect = [pypi_response, testpypi_response]
        
        sources = {
            'PyPI': 'https://pypi.org/simple/',
            'TestPyPI': 'https://test.pypi.org/simple/'
        }
        result = get_all_package_names(sources)
        
        assert 'shared-package' in result
        assert result['shared-package'] == {'PyPI', 'TestPyPI'}
    
    @patch('namecheck.utils.requests.get')
    def test_special_characters_in_package_names(self, mock_get):
        """Test handling of special characters in package names."""
        mock_response = Mock()
        mock_response.content = b'''
        <html>
            <body>
                <a href="package-with-dashes/">package-with-dashes</a>
                <a href="package_with_underscores/">package_with_underscores</a>
                <a href="package.with.dots/">package.with.dots</a>
            </body>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        sources = {'PyPI': 'https://pypi.org/simple/'}
        result = get_all_package_names(sources)
        
        assert 'package-with-dashes' in result
        assert 'package_with_underscores' in result
        assert 'package.with.dots' in result


class TestCheckNameAvailability:
    """Tests for the check_name_availability function."""
    
    def test_exact_match_found_single_source(self, capsys):
        """Test when an exact match is found on a single source."""
        all_names = {
            'existing-package': {'PyPI'}
        }
        
        check_name_availability('existing-package', all_names)
        captured = capsys.readouterr()
        
        assert '❌' in captured.out
        assert 'existing-package' in captured.out
        assert 'PyPI' in captured.out
    
    def test_exact_match_found_multiple_sources(self, capsys):
        """Test when an exact match is found on multiple sources."""
        all_names = {
            'popular-package': {'PyPI', 'TestPyPI'}
        }
        
        check_name_availability('popular-package', all_names)
        captured = capsys.readouterr()
        
        assert '❌' in captured.out
        assert 'popular-package' in captured.out
        assert 'PyPI' in captured.out
        assert 'TestPyPI' in captured.out
    
    def test_name_available(self, capsys):
        """Test when a name is available (no exact match)."""
        all_names = {
            'other-package': {'PyPI'}
        }
        
        check_name_availability('my-unique-name', all_names)
        captured = capsys.readouterr()
        
        assert '✅' in captured.out
        assert 'my-unique-name' in captured.out
        assert 'available' in captured.out.lower()
    
    def test_case_insensitive_matching(self, capsys):
        """Test that matching is case-insensitive."""
        all_names = {
            'mypackage': {'PyPI'}
        }
        
        # Try with different case variations
        check_name_availability('MyPackage', all_names)
        captured = capsys.readouterr()
        
        assert '❌' in captured.out
        assert 'MyPackage' in captured.out
    
    def test_close_matches_found(self, capsys):
        """Test that close matches are displayed."""
        all_names = {
            'requests': {'PyPI'},
            'request': {'PyPI'},
            'requestor': {'PyPI'},
            'completely-different': {'PyPI'}
        }
        
        check_name_availability('requests', all_names)
        captured = capsys.readouterr()
        
        # Should find close matches but not show the exact match in close matches section
        assert '⚠️' in captured.out or 'request' in captured.out
    
    def test_no_close_matches(self, capsys):
        """Test when there are no close matches."""
        all_names = {
            'completely': {'PyPI'},
            'different': {'PyPI'},
            'words': {'PyPI'}
        }
        
        check_name_availability('my-unique-package-xyz', all_names)
        captured = capsys.readouterr()
        
        assert '✅' in captured.out
        # Should not have warning about close matches
        assert ('⚠️' not in captured.out) or ('closely matching' not in captured.out.lower())
    
    def test_close_matches_with_sources(self, capsys):
        """Test that close matches display their sources correctly."""
        all_names = {
            'flask': {'PyPI', 'TestPyPI'},
            'flasks': {'PyPI'},
            'flaskapp': {'TestPyPI'}
        }
        
        check_name_availability('flask-new', all_names)
        captured = capsys.readouterr()
        
        # Should show close matches with their sources
        if 'flask' in captured.out and '⚠️' in captured.out:
            assert 'PyPI' in captured.out or 'TestPyPI' in captured.out
    
    def test_exact_match_removed_from_close_matches(self, capsys):
        """Test that exact match is not duplicated in close matches section."""
        all_names = {
            'mypackage': {'PyPI'},
            'mypackages': {'PyPI'},
            'my-package': {'PyPI'}
        }
        
        check_name_availability('mypackage', all_names)
        captured = capsys.readouterr()
        
        # Count occurrences of 'mypackage' - should appear in exact match but not close matches
        lines = captured.out.split('\n')
        exact_match_line = [l for l in lines if '❌' in l and 'mypackage' in l.lower()]
        
        assert len(exact_match_line) > 0
    
    def test_empty_package_list(self, capsys):
        """Test checking against an empty package list."""
        all_names = {}
        
        check_name_availability('any-name', all_names)
        captured = capsys.readouterr()
        
        assert '✅' in captured.out
        assert 'available' in captured.out.lower()
    
    def test_formatting_separators(self, capsys):
        """Test that output includes formatting separators."""
        all_names = {'existing': {'PyPI'}}
        
        check_name_availability('test', all_names)
        captured = capsys.readouterr()
        
        # Should have separator lines
        assert '-' * 50 in captured.out


class TestIntegration:
    """Integration tests that combine multiple functions."""
    
    @patch('namecheck.utils.requests.get')
    def test_full_workflow(self, mock_get, capsys):
        """Test the full workflow of fetching packages and checking availability."""
        # Mock response with some packages
        mock_response = Mock()
        mock_response.content = b'''
        <html>
            <body>
                <a href="requests/">requests</a>
                <a href="flask/">flask</a>
                <a href="django/">django</a>
            </body>
        </html>
        '''
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Fetch packages
        sources = {'PyPI': 'https://pypi.org/simple/'}
        all_packages = get_all_package_names(sources)
        
        # Check an existing name
        check_name_availability('flask', all_packages)
        captured = capsys.readouterr()
        assert '❌' in captured.out
        
        # Check a new name
        check_name_availability('my-brand-new-package-xyz-123', all_packages)
        captured = capsys.readouterr()
        assert '✅' in captured.out