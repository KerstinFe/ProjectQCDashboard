import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ProjectQCDashboard.config.logger import get_configured_logger
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path

logger = get_configured_logger(__name__)


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess the input DataFrame.

    :param df: The DataFrame to preprocess
    :type df: pd.DataFrame
    :return: The preprocessed DataFrame
    :rtype: pd.DataFrame
    """

    df['DateTime'] = pd.to_datetime(df['DateTime'])
    df = df.sort_values(by="DateTime", ascending=True)
    placeholder_rm = pd.Timestamp('1900.01.01')
    df = df[df['Date'] != placeholder_rm]
    df = df[df['Date'] != '1900.01.01']

    return df

def filter_df(df: pd.DataFrame, y_Label: str) -> pd.DataFrame:
    """Filter the DataFrame based on the y-axis label and remove standard samples.
    :param df: The input DataFrame
    :type df: pd.DataFrame
    :param y_Label: The y-axis label to filter by
    :type y_Label: str
    :return: The filtered DataFrame
    :rtype: pd.DataFrame
    """
 
    df_Filtered = df[(df["FileType"] != "HSstd") & (df["FileType"] != "OtherStandard")]
    df_Filtered2 = df_Filtered.dropna(subset=[y_Label])
    df_Filtered2.loc[:, y_Label] = pd.to_numeric(df_Filtered2.loc[:, y_Label], errors='coerce')

    return df_Filtered2


class Create_DFs():
    def __init__(self, df_Filtered: pd.DataFrame, y_Label: str) -> None:
        """Initialize with filtered DataFrame and y-axis label.
        :param df_Filtered: The filtered DataFrame
        :type df_Filtered: pd.DataFrame
        :param y_Label: The y-axis label
        :type y_Label: str
        """

        self.df_Filtered = df_Filtered
        self.y_Label = y_Label
     

    def RollingMean_DF(self, width: int) -> Tuple[pd.DataFrame, float, float]:
        """Calculate rolling mean and standard deviation DataFrame.
        :param width: The rolling window width
        :type width: int
        :return: The rolling mean DataFrame, mean and std values
        :rtype: Tuple[pd.DataFrame, float, float]
        """

        # Use min_periods=1 to start calculating from the first data point
        # This makes the trend line start immediately but becomes more stable as more data is included
        median = self.df_Filtered[self.y_Label].rolling(window=width, min_periods=1).median()
        std = self.df_Filtered[self.y_Label].rolling(window=width, min_periods=1).std()
        y1 = median - std
        y2 = median + std

        df_rolling = pd.DataFrame({
            'DateTime': self.df_Filtered["DateTime"],
            self.y_Label: self.df_Filtered[self.y_Label],
            'Median': median,
            'std': std,
            "Upper": y1,
            'Lower': y2
        })
        
        # Only drop rows where the actual y_Label data is missing, not the rolling calculations
        df_rolling = df_rolling.dropna(subset=[self.y_Label])

        median_print = median.mean()
        std_print = std.mean()

        return df_rolling, median_print, std_print
    
    def Median_DF(self) -> Tuple[pd.DataFrame, float, float]:
        """Calculate median and standard deviation DataFrame.
        :return: The median DataFrame, median and std values
        :rtype: Tuple[pd.DataFrame, float, float]
        """
        
        median = self.df_Filtered[self.y_Label].median()
        std = self.df_Filtered[self.y_Label].std()
        y1 = median - std
        y2 = median + std

        self.df_Filtered["Median"] = self.df_Filtered[self.y_Label].median()
        self.df_Filtered["Upper"] = y1
        self.df_Filtered["Lower"] = y2

        return self.df_Filtered, median, std
