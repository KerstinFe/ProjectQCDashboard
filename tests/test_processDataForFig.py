"""Tests for data processing helper functions."""

import pandas as pd
from unittest.mock import patch, MagicMock, Mock
from ProjectQCDashboard.ui.processDataForFig import (
    get_all_data,
    get_project_data
)


class TestProcessDataForFig:
    """Test suite for data processing functions."""
    
    @patch('ProjectQCDashboard.ui.processDataForFig.duckdb.connect')
    def test_get_all_data_success(self, mock_connect: Mock) -> None:
        """Test successful data retrieval."""
        mock_con = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_con
        
        mock_df = pd.DataFrame({
            'ProjectID': ['Test_Project'] * 5,
            'DateTime': pd.date_range('2025-01-01', periods=5),
            'MS1.TIC': [1000000.0] * 5
        })
        mock_con.execute.return_value.df.return_value = mock_df
        
        result = get_all_data('Test_Project')
        
        assert len(result) == 5
        assert 'ProjectID' in result.columns
    
    
    @patch('ProjectQCDashboard.ui.processDataForFig.duckdb.connect')
    def test_get_project_data_success(self, mock_connect: Mock) -> None:
        """Test successful project data retrieval with valid/error split."""
        mock_con = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_con
        
        mock_df = pd.DataFrame({
            'ProjectID': ['Test_Project'] * 10,
            'DateTime': pd.date_range('2025-01-01', periods=10),
            'Date': pd.date_range('2025-01-01', periods=10),
            'RawFileName': [f'file_{i}.raw' for i in range(10)],
            'Error': [None] * 9 + ['Error'],
            'MS1.TIC': [1000000.0] * 10
        })
        mock_con.execute.return_value.df.return_value = mock_df
        
        valid_data, error_data, last_measured, last_measured_time = get_project_data('Test_Project')
        
        assert len(valid_data) == 9  # 9 valid entries
        assert len(error_data) == 1  # 1 error entry
        assert 'RawFileName' in error_data.columns
        assert 'Error' in error_data.columns
    
    @patch('ProjectQCDashboard.ui.processDataForFig.duckdb.connect')
    def test_get_project_data_error(self, mock_connect: Mock) -> None:
        """Test error handling in get_project_data."""
        mock_connect.side_effect = Exception("Database error")
        
        valid_data, error_data, last_measured, last_measured_time = get_project_data('Test_Project')
        
        assert valid_data.empty
        assert error_data.empty
    
    
