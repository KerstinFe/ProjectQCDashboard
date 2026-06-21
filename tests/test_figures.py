"""Tests for Figures module."""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from unittest.mock import patch
from ProjectQCDashboard.ui.Figures import (
    DataframeForFig,
    Create_Figures
)
from typing import Any


class TestDataframeForFig:
    """Test suite for DataframeForFig class."""
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_filter_df_removes_standards(self, mock_get_data: Any) -> None:
        """Test that filter_df removes standard samples."""
        mock_valid = pd.DataFrame({
            'DateTime': pd.date_range('2025-01-01', periods=15),
            'FileType': ['Sample'] * 10 + ['HSstd'] * 3 + ['OtherStandard'] * 2,
            'Name': [f'file_{i}' for i in range(15)],
            'RawFileName': [f'file_{i}' for i in range(15)],
            'MS1.TIC': np.random.rand(15) * 1000000
        })
        mock_error = pd.DataFrame(columns = ['Rawfile Name','Error' ])
        mock_get_data.return_value =  (mock_valid, mock_error, '', None)

        df_fig = DataframeForFig('Test_Project')
        filtered, *_ = df_fig.filter_df('MS1.TIC')

        # Should filter out 5 standard samples
        assert len(filtered) == 10
        assert 'HSstd' not in filtered['FileType'].values
        assert 'OtherStandard' not in filtered['FileType'].values
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_filter_df_with_na_values(self, mock_get_data: Any) -> None:
        """Test filter_df handles NaN values correctly."""
        mock_valid = pd.DataFrame({
            'DateTime': pd.date_range('2025-01-01', periods=10),
            'FileType': ['Sample'] * 10,
            'Name': [f'file_{i}' for i in range(10)],
            'RawFileName': [f'file_{i}' for i in range(10)],
            'MS1.TIC': [100.0, 200.0, None, 400.0, 500.0, None, 700.0, 800.0, 900.0, 1000.0]
        })
        mock_error = pd.DataFrame(columns=['RawFileName', 'Error'])
        mock_get_data.return_value = (mock_valid, mock_error, '', None)
        
        df_fig = DataframeForFig('Test_Project')
        filtered, filtered_all, mean, median, std = df_fig.filter_df('MS1.TIC')
        
        # Should remove 2 rows with None
        assert len(filtered) == 8
        assert filtered['MS1.TIC'].notna().all()
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_rolling_mean_df_calculation(self, mock_get_data: Any) -> None:
        """Test rolling mean calculations."""
        # Create data with 50 points for rolling mean threshold
        mock_valid = pd.DataFrame({
            'DateTime': pd.date_range('2025-01-01', periods=50),
            'FileType': ['Sample'] * 50,
            'Name': [f'file_{i}' for i in range(50)],
            'RawFileName': [f'file_{i}' for i in range(50)],
            'MS1.TIC': np.linspace(1000000, 2000000, 50)
        })
        mock_error = pd.DataFrame(columns=['RawFileName', 'Error'])
        mock_get_data.return_value = (mock_valid, mock_error, '', None)
        
        df_fig = DataframeForFig('Test_Project')
        filtered, filtered_all, mean, median, std = df_fig.filter_df('MS1.TIC')
        
        # Should calculate statistics
        assert isinstance(mean, float)
        assert isinstance(median, float)
        assert isinstance(std, float)
        assert 'Median' in filtered.columns
        assert 'Upper' in filtered.columns
        assert 'Lower' in filtered.columns


class TestCreateFigures:
    """Test suite for Create_Figures class."""
        
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_generate_fig_with_data(self, mock_get_data: Any) -> None:
        """Test figure generation with valid data."""
        mock_valid = pd.DataFrame({
            'DateTime': pd.date_range('2025-01-01', periods=10),
            'FileType': ['Sample'] * 10,
            'Name': [f'file_{i}' for i in range(10)],
            'RawFileName': [f'file_{i}' for i in range(10)],
            'MS1.TIC': np.random.rand(10) * 1000000
        })
        mock_error = pd.DataFrame(columns=['RawFileName', 'Error'])
        mock_get_data.return_value = (mock_valid, mock_error, '', None)
        
        fig_gen = Create_Figures('Test_Project')
        fig = fig_gen.generate_fig('MS1.TIC')

        assert fig_gen.nrows_valid_data == 10
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_generate_fig_no_data(self, mock_get_data: Any) -> None:
        """Test figure generation with no data."""
        mock_valid = pd.DataFrame({
            'DateTime': [],
            'FileType': [],
            'Name': [],
            'MS1.TIC': []
        })
        mock_error = pd.DataFrame(columns=['RawFileName', 'Error'])
        mock_get_data.return_value = (mock_valid, mock_error, '', None)
        
        fig_gen = Create_Figures('Test_Project')
        fig = fig_gen.generate_fig('MS1.TIC')
        
        assert isinstance(fig, go.Figure)
        # Should have "no-data" marker
        assert fig.layout.uirevision == "no-data"
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_create_table_project_data(self, mock_get_data: Any) -> None:
        """Test project data table creation."""
        mock_valid = pd.DataFrame({
            'DateTime': pd.date_range('2025-01-01', periods=5),
            'FileType': ['Sample'] * 5,
            'Instrument': ['Instrument_A'] * 5,
            'InstrumentMethod': ['Method_1'] * 5,
            'InstrumentMethod_print': ['Method_1'] * 5,
        })
        mock_error = pd.DataFrame(columns=['RawFileName', 'Error'])
        mock_get_data.return_value = (mock_valid, mock_error, 'Project1', pd.Timestamp('2025-01-15'))
        
        fig_gen = Create_Figures('Test_Project')
        rows_to_show = ['Instrument', 'InstrumentMethod']
        fig = fig_gen.create_table_project_data(rows_to_show)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_create_table_error_with_errors(self, mock_get_data: Any) -> None:
        """Test error table creation with error data."""
        mock_valid = pd.DataFrame()
        mock_error = pd.DataFrame({
            'RawFileName': ['file_1.raw', 'file_2.raw'],
            'Error': ['Error message 1', 'Error message 2']
        })
        mock_get_data.return_value = (mock_valid, mock_error, "", None)
        
        fig_gen = Create_Figures('Test_Project')
        fig = fig_gen.create_table_error()
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_create_table_error_no_errors(self, mock_get_data: Any) -> None:
        """Test error table creation with no errors."""
        mock_valid = pd.DataFrame()
        mock_error = pd.DataFrame(columns=['RawFileName', 'Error'])
        mock_get_data.return_value = (mock_valid, mock_error, "", None)
        
        fig_gen = Create_Figures('Test_Project')
        fig = fig_gen.create_table_error()
        
        # Should return None when no errors
        assert fig is None
    
    @patch('ProjectQCDashboard.ui.Figures.get_project_data')
    def test_format_val_numeric(self, mock_get_data: Any) -> None:
        """Test value formatting for numeric values."""
        mock_get_data.return_value = (pd.DataFrame(), pd.DataFrame(columns=['RawFileName', 'Error']), "", None)
        
        fig_gen = Create_Figures('Test_Project')
        
        assert fig_gen._format_val(123.456) == "123.46"
        assert fig_gen._format_val(0.001) == "0.00"
        assert fig_gen._format_val(None) == "n/a"
        assert fig_gen._format_val(np.nan) == "n/a"
