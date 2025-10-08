from typing import Union
from pathlib import Path
import plotly.graph_objects as go
from ProjectQCDashboard.helper.Figures import ScatterPlot, updateAxes,updateAxes_log, Create_Figures
from ProjectQCDashboard.helper.processDataForFig import preprocess_data, filter_df
from ProjectQCDashboard.helper.UpdateCSV import  update_df
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.configuration import ThresholdForRollingMean

logger = get_configured_logger(__name__)


class generate_Fig():

    def __init__(self, OutputFilePath: Union[str, Path]) -> None:
        """Initialize the figure generator with a CSV file path.

        :param OutputFilePath: Path to the CSV file containing the data
        :type OutputFilePath: Union[str, Path]
        """
        df = update_df(OutputFilePath)

        self.df = preprocess_data(df)

        self.DefaultTemplate = "none"

    def CreateFig(self, y_Label: str) -> go.Figure:

        """Create and return a Plotly figure based on the filtered data and y-axis label.
        :param y_Label: The y-axis label to filter and plot
        :type y_Label: str
        :return: A Plotly figure
        :rtype: go.Figure
        """

        self.df_Filtered = filter_df(self.df, y_Label)

        self.fig_creator = Create_Figures(self.df_Filtered, y_Label)
        # Use unfiltered data for scatter plot (shows all points including standards)
        # but filtered data for trend lines (excludes standards from calculations)
        fig1 = ScatterPlot(self.df, y_Label)
        fig1 = updateAxes(fig1)
        fig = updateAxes_log(fig1, self.DefaultTemplate)
   
        if self.df_Filtered.shape[0] >= ThresholdForRollingMean: # 30 as cutoff for rolling average
            fig = self.fig_creator.AddTraces_Rolling(fig, width = 15)

        elif self.df_Filtered.shape[0] > 5 and self.df_Filtered.shape[0] < 30 : 
            fig = self.fig_creator.AddTraces_Median(fig)

        else:
            fig = self.fig_creator.AddNothing(fig)
         
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            # margin=dict(l=10, r=10, t=36, b=10),
            margin=dict(l=8, r=8, t=36, b=8),

            font=dict(family="Inter, Arial", size=12)
        ) 
        return fig
