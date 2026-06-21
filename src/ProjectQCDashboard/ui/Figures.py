import pandas as pd
from pathlib import Path
import numpy as np
from typing import Any
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.ui.processDataForFig import get_project_data
import plotly.graph_objects as go
from ProjectQCDashboard.config.configuration import ThresholdForRollingMean

logger = get_configured_logger(__name__)

class DataframeForFig:
    """
    Handles filtering and processing of project data for figure generation.
    Provides methods for rolling mean, median, and error extraction.
    """
    def __init__(self, ProjectID: str):
        """:param ProjectID: Project ID chosen in callback
        :type ProjectID: str"""
       
        self.ProjectID = ProjectID
        self.valid_data, self.error_data, self.last_measured, self.last_measured_time= get_project_data(ProjectID)
        self.nrows_valid_data = self.valid_data.shape[0]   
    
    def filter_df(self, y_Label: str) -> tuple[pd.DataFrame, pd.DataFrame, float, float, float]:
        """
        Filter the DataFrame based on the y-axis label and remove standard samples.

        Returns filtered data, all data, and rolling/median statistics as appropriate.

        :param y_Label: The y-axis label to filter by
        :type y_Label: str
        :return: The filtered DataFrame(s) and statistics
        :rtype: tuple[pd.DataFrame, pd.DataFrame, float, float, float]
        """
    
        df_Filtered = self.valid_data.copy()
        df_Filtered = df_Filtered.dropna(subset=[y_Label])
        df_Filtered[y_Label] = pd.to_numeric(df_Filtered[y_Label], errors='coerce')
        df_Filtered = df_Filtered.loc[df_Filtered[y_Label].notnull(),:]
        df_Filtered_all = df_Filtered.copy()
        df_Filtered = df_Filtered[(df_Filtered["FileType"] != "HSstd") & (df_Filtered["FileType"] != "OtherStandard")]
        
        if df_Filtered.shape[0] >= ThresholdForRollingMean: # 30 as cutoff for rolling average
            df_Filtered, mean, median, std = self._rolling_mean_df(df_Filtered, y_Label, width = 15)
            return df_Filtered, df_Filtered_all, mean, median, std

        elif df_Filtered.shape[0] > 5 and df_Filtered.shape[0] < ThresholdForRollingMean: 
            df_Filtered, mean, median, std = self._median_df(df_Filtered, y_Label)
            return df_Filtered, df_Filtered_all, mean, median, std

        else:
            return df_Filtered, df_Filtered_all, float('nan'), float('nan'), float('nan')

            
    def _rolling_mean_df(self, df_Filtered: pd.DataFrame, y_Label: str, width: int) -> tuple[pd.DataFrame, float, float, float]:
        """
        Calculate rolling mean and standard deviation DataFrame.

        Also calculates mean and std of the actual data (not rolling) for the legend.

        :param df_Filtered: The filtered DataFrame
        :type df_Filtered: pd.DataFrame
        :param y_Label: The y-axis label to filter by
        :type y_Label: str
        :param width: The rolling window width
        :type width: int
        :return: The rolling mean DataFrame, mean, median, and std values
        :rtype: tuple[pd.DataFrame, float, float, float]
        """

        # Use min_periods=1 to start calculating from the first data point
        # This makes the trend line start immediately but becomes more stable as more data is included
        median = df_Filtered[y_Label].rolling(window=width, min_periods=1).median()
        std = df_Filtered[y_Label].rolling(window=width, min_periods=1).std()
        y1 = median - std
        y2 = median + std

        df_rolling = pd.DataFrame({
            'DateTime': df_Filtered["DateTime"],
            y_Label: df_Filtered[y_Label],
            'Name': df_Filtered["RawFileName"],
            'FileType': df_Filtered["FileType"],
            'Median': median,
            'std': std,
            'Lower': y1,
            "Upper": y2
        })
        
        # Only drop rows where the actual y_Label data is missing, not the rolling calculations
        df_rolling = df_rolling.dropna(subset=[y_Label])

        data_non_na = df_Filtered[y_Label].dropna()
               
        if data_non_na.empty:
            mean_legend = float('nan')
            median_legend = float('nan')
            std_legend = float('nan')
        else:
            mean_legend = float(data_non_na.mean())
            median_legend = float(data_non_na.median())
            std_legend = float(data_non_na.std())
       
        return df_rolling, mean_legend, median_legend, std_legend
    
    def _median_df(self, df_Filtered: pd.DataFrame, y_Label: str) -> tuple[pd.DataFrame, float, float, float]:
        """
        Calculate mean, median, and standard deviation for the filtered DataFrame.

        :param df_Filtered: The filtered DataFrame
        :type df_Filtered: pd.DataFrame
        :param y_Label: The y-axis label to filter by
        :type y_Label: str
        :return: The filtered DataFrame, mean, median, and std values
        :rtype: tuple[pd.DataFrame, float, float, float]
        """
   
        # Coerce to numeric where possible; preserve NaN when coercion fails
        numeric_series = pd.to_numeric(df_Filtered[y_Label], errors='coerce')
        non_na_count = numeric_series.notna().sum()
        # If we have no numeric data, skip numeric ops and set safe defaults
        if non_na_count == 0:
            median = float('nan')
            std = float('nan')
            y1 = float('nan')
            y2 = float('nan')
            mean = float('nan')
            
        else:
            numeric_non_na = numeric_series.dropna()
            median = float(numeric_non_na.median())
            mean = float(numeric_non_na.mean())            
            std = float(numeric_non_na.std())
            y1 = median - std
            y2 = median + std

        df_median = pd.DataFrame({
            'DateTime': df_Filtered["DateTime"],
            y_Label: df_Filtered[y_Label],
            'FileType': df_Filtered["FileType"],
            'Name': df_Filtered["RawFileName"],
            'Median': median,
            'Lower': y1,
            "Upper": y2
        })

    
        

        return df_median, mean, median, std
    
    def get_error_data(self) -> tuple[pd.DataFrame, int]: 
        """
        Get error data with renamed columns.

        :return: tuple of error DataFrame and number of errors
        :rtype: tuple[pd.DataFrame, int]
        """
        df_error = self.error_data.copy()
        df_error.columns = pd.Index(["Rawfile Name", "Error"])
        return df_error, df_error.shape[0]


class Create_Figures:
    """
    Generates plotly figures and tables for project data visualization.
    """
    def __init__(self, ProjectID: str) -> None:
        """
        Initialize the figure creator with filtered DataFrame and y-axis label.

        :param ProjectID: Project ID chosen in callback
        :type ProjectID: str
        """
        
        self.GetDataframes = DataframeForFig(ProjectID)
        self.valid_data = self.GetDataframes.valid_data
        self.last_measured = self.GetDataframes.last_measured
        self.last_measured_time = self.GetDataframes.last_measured_time
        self.nrows_valid_data = self.GetDataframes.nrows_valid_data
        self.df_error, self.numRows_errordf = self.GetDataframes.get_error_data()


    def generate_fig(self, y_Label: str) -> go.Figure:
        """
        Generate a complete figure with scatter plot and trend lines.

        Creates a scatter plot and adds rolling mean/median traces based on data size.
        Returns an empty figure with a message if no data is available.

        :param y_Label: Column name to plot on y-axis
        :type y_Label: str
        :return: Complete plotly figure with data and trend lines
        :rtype: go.Figure
        """
        self.df_Filtered, self.df_Filtered_all, self.mean, self.median, self.std = self.GetDataframes.filter_df(y_Label)
        self.y_Label = y_Label

        # Check if we have any data for this y_label
        has_data = self.df_Filtered_all.shape[0] > 0
        
        if not has_data:
            # Return empty figure marked with metadata
            empty_fig = go.Figure()
            empty_fig.update_layout(
                template="plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=8, r=8, t=36, b=8),
                font=dict(family="Inter, Arial", size=12),
                uirevision="no-data"  # Marker for empty figure
            )
            empty_fig.add_annotation(
                text=f"No data available for {y_Label}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="gray")
            )
            return empty_fig
        
        self.fig = self._Scatterplot()
              
        if self.df_Filtered.shape[0] >= ThresholdForRollingMean: # 30 as cutoff for rolling average
            self.fig = self._AddTraces(Type = "Rolling")

        elif self.df_Filtered.shape[0] > 5 and self.df_Filtered.shape[0] < ThresholdForRollingMean: 
            self.fig = self._AddTraces(Type = "Median")

        else:
            self.fig = self.add_nothing()   

        return self.fig   
    
    def create_table_project_data(self, ROWS_Table: list[str]) -> go.Figure:
        """
        Create a table figure displaying project metadata.

        :param ROWS_Table: List of column names to include in the table
        :type ROWS_Table: list
        :return: Plotly table figure with project information
        :rtype: go.Figure
        """

        subtitle = ""
        if self.last_measured:
            ts = self.last_measured_time
            try:
                if ts is not None and pd.notna(ts):
                    ts_str = pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M")
                    subtitle = f" <br> <br> <br> Last measured: <br> {self.last_measured} <br> Time:   {ts_str}"
                else:
                    subtitle = f" <br> <br> <br> Last measured:<br> {self.last_measured}"
            except Exception:
                subtitle = f" <br> <br> <br> Last measured:<br> {self.last_measured}"
        

        ColumnsTabDict =  {}

        def clean(x: Any, is_method: bool) -> str:
            if pd.isna(x):
                return "not available"
            s = f'{x}'.replace('\\', '/')
            return Path(s).name if is_method else s

        for Column in ROWS_Table:
            is_instrument_method = Column in ("InstrumentMethod_print", "InstrumentMethod", "Method")
            column_key = "InstrumentMethod" if is_instrument_method else Column
            unique_entries = set(self.valid_data[Column])

            # Single unique value
            if len(unique_entries) == 1:
                ColumnsTabDict[column_key] = [clean(list(unique_entries)[0], is_instrument_method)]
            # Multiple values
            else:
                values = []
                for row in self.valid_data[Column]:
                    value = clean(row, is_instrument_method)
                    if value not in values:
                        values.append(value)
                ColumnsTabDict[column_key] = values    

        col_widths = []
        for col in ColumnsTabDict.keys():
            # Ensure value is iterable (convert single values to list)
            col_values = ColumnsTabDict[col] #if isinstance(ColumnsTabDict[col], list) else [ColumnsTabDict[col]]
            
            # Get max length of header or any cell value
            max_len = max(
                len(str(col)),
                max((len(str(v)) for v in col_values), default=0),
            )

            col_widths.append(max_len)
               
        # Calculate height based on number of rows (header + data rows)
        row_height = 30  # approximate height per row in pixels
        header_height = 40  # height for header
        margin_height = 20  # top/bottom margins
        # calculated_height = header_height + (len(ColumnsTabDict)*row_height) + (margin_height * 1)
      
        fig = go.Figure(data=[go.Table(
            columnwidth=col_widths,
            header=dict(values=list(ColumnsTabDict.keys()),line_color='darkslategray', 
                                                   font=dict(family='Arial Black', color='black', size=12), align='left', fill_color="white"),
                        cells=dict(values=[ColumnsTabDict[col] for col in list(ColumnsTabDict.keys())], font=dict(family='Arial Black', color='black', size=12), fill_color='white', align='left'))
                            ])        
        

        title_space = 60 if subtitle else 0
        calculated_height = header_height + (len(ColumnsTabDict) * row_height) + margin_height + title_space
        # Set the figure height to fit content
        fig.update_layout(
            height=calculated_height,
            margin=dict(l=0, r=0, t=40+ title_space, b=0),
            title=dict(
                text=subtitle,
                x=0, xanchor="left",
                y=1, yanchor="top",
                font=dict(family="Arial", size=13, color="#0f172a"),
                pad=dict(l=4, t=4),
            ),
        )
            
       
        return fig
    
    def create_table_error(self) -> go.Figure | None:
        """Create a table figure displaying error data for files with issues.
        
        :return: Plotly table figure with error information, or None if no errors
        :rtype: go.Figure | None
        """
        if self.numRows_errordf > 0: 

            # Calculate height based on number of rows (header + data rows)
            row_height = 30  # approximate height per row in pixels
            header_height = 40  # height for header
            margin_height = 20  # top/bottom margins
            calculated_height = header_height + (self.numRows_errordf * row_height) + (margin_height * 1)

            fig = go.Figure(data=[go.Table(header=dict(values=self.df_error.columns, font=dict(family='Arial Black', color='black', size=12), align='left', fill_color="red"),
                            cells=dict(values=[self.df_error["Rawfile Name"], self.df_error["Error"]], font=dict(family='Arial Black', color='red', size=12), fill_color='white', align='left'))
                                ])
            
            # Set the figure height to fit content
            fig.update_layout(
                height=calculated_height,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            
        else:
            fig = None    
            
        return fig
       
    def _Scatterplot(self) -> go.Figure:
        """Create a scatter plot using the already-filtered DataFrame.
        
        :return: The scatter plot figure, or empty figure if no data
        :rtype: go.Figure
        """
        if self.df_Filtered_all.shape[0] == 0:  
            return go.Figure()
        
        fig = go.Figure()
   
        for file_type, group in self.df_Filtered_all.groupby("FileType", sort=False):
            fig.add_trace(go.Scatter(  
                x=group["DateTime"],
                y=group[self.y_Label],
                mode="markers",
                name=str(file_type),
                text=group["RawFileName"].tolist(),
                hovertemplate="<b>%{text}</b><br>%{x}<br>%{y}<extra></extra>",
                showlegend=True
            ))


        
        fig = self._updateAxes_layout(fig)

        return fig
    
    def _updateAxes_layout(self, fig: go.Figure) -> go.Figure:
        """Update the axes of the given figure.

        :param fig: The figure to update
        :type fig: go.Figure
        :return: The updated figure
        :rtype: go.Figure
        """
        fig.update_xaxes(
        dtick=24*60*60*1000, # days between ticks
        tickformat="%d \n %b",
        ticklabelmode="period") 

        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=8, r=8, t=36, b=8),
            font=dict(family="Inter, Arial", size=12),
            yaxis=dict(showexponent='all', exponentformat='e')
        ) 

        return fig   

  
    def _AddTraces_Rolling(self, label: str) -> go.Figure:
        """Add rolling traces to the figure.

        :param fig: The figure to update
        :type fig: go.Figure
        :param df_rolling: The rolling DataFrame
        :type df_rolling: pd.DataFrame
        :param label: The label for the trace
        :type label: str
        :return: The updated figure
        :rtype: go.Figure
        """

        
        if label == "Upper" or label == "Lower":
            name = f"{label} rolling standard deviation"
            color = "#444"  # gray color for bounds
      
        elif label == "Median":
            name = "Rolling median"
            color = "blue"  # Distinctive color for median
      
        self.fig.add_trace(go.Scatter(
                x=self.df_Filtered["DateTime"], y=self.df_Filtered[label],
                name = name,
                mode='lines',
                line=dict(color=color))) 
        
        return self.fig  
    
    def _AddTraces_Median(self, label: str) -> go.Figure:

        """Add median traces to the figure.
        :param fig: The figure to update
        :type fig: go.Figure
        :param label: The label for the trace
        :type label: str
        :return: The updated figure
        :rtype: go.Figure
        """
            
        if label == "Median":
            name = "Median"
            color = "red"
        elif label == "Upper":
            name = "Upper std dev"
            color = "blue"
        elif label == "Lower":
            name = "Lower std dev"
            color = "blue"


        self.fig.add_trace(
                  go.Scatter(
                      name=name,
                      x=self.df_Filtered["DateTime"],
                      y=self.df_Filtered[label],
                      marker=dict(color=color),
                      line=dict(width=1),
                      mode='lines',
                      showlegend=True
                  )
               )

       
        return self.fig    

    def _AddTraces(self, Type: str) -> go.Figure:
        """Add rolling mean and std dev traces to the figure.

            :param Type: The type of traces to add ("Rolling" or "Median")
            :type Type: str
            :return: The updated figure
            :rtype: go.Figure
        """
       
        for label in ["Upper", "Lower", "Median"]:

            if Type == "Rolling":
                self.fig = self._AddTraces_Rolling(label)
            elif Type == "Median":
                self.fig = self._AddTraces_Median(label)

        try:
            self.fig = self._add_point_legend()
         
        except Exception:
            logger.exception("legend_summary_add_failed_rolling_plot")

        return self.fig

    def add_nothing(self) -> go.Figure:
        """Add a notification to the figure indicating insufficient data.

            :param fig: The figure to update
            :type fig: go.Figure
            :return: The updated figure
            :rtype: go.Figure
        """

        self.fig.add_annotation(dict(font=dict(color='black',size=15),
                                x=0,
                                y=-0.4,
                                showarrow=False,
                                text="not enough samples for median or standard deviation trends",
                                textangle=0,
                                xanchor='left',
                                align="center",
                                xref="paper",
                                yref="paper"))
        return self.fig        
    
    def _format_val(self, v: float | None) -> str:
        """Format a numeric value to string for display in annotations. Returns 'n/a' for None/NaN.
        :param v: The value to format
        :type v: float | None
        :return: The formatted string
        :rtype: str
        """
        try:
            if v is None:
                return 'n/a'
            if isinstance(v, str):
                return 'n/a'
            if isinstance(v, (int, float)) and np.isnan(v):
                return 'n/a'
            return f"{float(v):.2f}"
        except Exception:
            return str(v)

    def _add_point_legend(self) -> go.Figure:
        """Add invisible legend entries to the figure for mean, median, and std dev.
        
        :return: The updated figure
        :rtype: go.Figure
        """
        # Add three invisible legend entries so the legend shows a 3-line summary
        mean_text = f"mean: {self._format_val(self.mean)}"
        median_text = f"median: {self._format_val(self.median)}"
        std_text = f"std dev: {self._format_val(self.std)}"

        for txt in (mean_text, median_text, std_text):
            self.fig.add_trace(go.Scatter(x=[np.nan], y=[np.nan], mode='markers',
                                    marker=dict(opacity=0, size=0), showlegend=True,
                                    name=txt, hoverinfo='skip'))


        return self.fig

