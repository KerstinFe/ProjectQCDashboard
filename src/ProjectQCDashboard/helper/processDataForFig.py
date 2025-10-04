import pandas as pd
from ProjectQCDashboard.config.logger import get_configured_logger
from typing import Tuple

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
     

    def RollingMean_DF(self, width: int) -> Tuple[pd.DataFrame, float, float, float]:
        """Calculate rolling mean and standard deviation DataFrame.
        And additionally calculate mean and std of the actual data (not rolling) for the legend.

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

        data_non_na = self.df_Filtered[self.y_Label].dropna()
               
        if data_non_na.empty:
            mean_print = "NaN"
            median_print = "NaN"
            std_print = "NaN"
        else:
            mean_print = float(data_non_na.mean())
            median_print = float(data_non_na.median())
            std_print = float(data_non_na.std())
       
        return df_rolling, mean_print, median_print, std_print
    
    def Median_DF(self) -> Tuple[pd.DataFrame, float, float, float]:
        """Calculate mean, median and standard deviation DataFrame.
        :return: The filtered DataFrame, mean, median, and std values
        :rtype: Tuple[pd.DataFrame, float, float, float]
        """
   
        # Coerce to numeric where possible; preserve NaN when coercion fails
        numeric_series = pd.to_numeric(self.df_Filtered[self.y_Label], errors='coerce')
        non_na_count = numeric_series.notna().sum()
        # If we have no numeric data, skip numeric ops and set safe defaults
        if non_na_count == 0:
            median = float('nan')
            std = float('nan')
            y1 = float('nan')
            y2 = float('nan')
            
        else:
            numeric_non_na = numeric_series.dropna()
            median = float(numeric_non_na.median())
            mean = float(numeric_non_na.mean())            
            std = float(numeric_non_na.std())
            y1 = median - std
            y2 = median + std

    
        self.df_Filtered['Median'] = median
        self.df_Filtered['Upper'] = y1
        self.df_Filtered['Lower'] = y2

        return self.df_Filtered, mean, median, std
