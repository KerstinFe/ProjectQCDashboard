import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from ProjectQCDashboard.helper.processDataForFig import Create_DFs
from ProjectQCDashboard.config.logger import get_configured_logger
from typing import Any, Optional


logger = get_configured_logger(__name__)

def ScatterPlot(df: pd.DataFrame, y_Label: str) -> go.Figure:
    """Create a scatter plot for the given DataFrame and y-axis label.
    :param df: The input DataFrame
    :type df: pd.DataFrame      
    :param y_Label: The y-axis label
    :type y_Label: str
    :return: The scatter plot figure
    :rtype: go.Figure
    """

    fig = px.scatter(
    df.loc[df[y_Label].notnull(),:],  # Filter out rows where y_Label is NaN
    x="DateTime",          
    y=y_Label, 
    color="FileType",  
    hover_name="Name"    
    )
    return fig

def updateAxes(fig: go.Figure) -> go.Figure:
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
    return fig   

def updateAxes_log(fig1: go.Figure, Template: Any) -> go.Figure:
    """Update the axes of the given figure for log scale.

    :param fig1: The figure to update
    :type fig1: go.Figure
    :param Template: The template to apply
    :type Template: Any
    :return: The updated figure
    :rtype: go.Figure
    """
    fig = go.Figure(
    data = fig1.data
        )
    fig.update_layout(template=Template)
    fig.update_layout(margin=dict(l=60, r=60, t=40, b=140),paper_bgcolor="white")
    fig.update_layout(
                yaxis = dict(
                    showexponent = 'all',
                    exponentformat = 'e'
                )
                    )
    
    return fig

class Create_Figures():
    def __init__(self, df_Filtered: pd.DataFrame, y_Label: str) -> None:
        """Initialize the figure creator with filtered DataFrame and y-axis label.

        :param df_Filtered: The filtered DataFrame
        :type df_Filtered: pd.DataFrame
        :param y_Label: The y-axis label
        :type y_Label: str
        :return: None
        :rtype: None
   
        """
        self.df_Filtered = df_Filtered
        self.y_Label = y_Label
        self.CreateDFs = Create_DFs(df_Filtered, y_Label)

    def _AddTraces_Rolling(self, fig: go.Figure, df_rolling: pd.DataFrame, label: str) -> Any:
        """Add rolling traces to the figure.

        :param fig: The figure to update
        :type fig: go.Figure
        :param df_rolling: The rolling DataFrame
        :type df_rolling: pd.DataFrame
        :param label: The label for the trace
        :type label: str
        :return: The updated figure
        :rtype: Any
        """

        
        if label == "Upper" or label == "Lower":
            name = f"{label} rolling standard deviation"
            color = "#444"  # Consistent gray color for bounds
      
        elif label == "Median":
            name = "Rolling median"
            color = "blue"  # Distinctive color for median
      
        fig.add_trace(go.Scatter(
                x=df_rolling["DateTime"], y=df_rolling[label],
                name = name,
                mode='lines',
                line=dict(color=color)))  # Explicitly set the color
        
        return fig


    def _AddTraces_Median(self, fig: go.Figure, df_median: pd.DataFrame, label: str) -> go.Figure:

        """Add median traces to the figure.
        :param fig: The figure to update
        :type fig: go.Figure
        :param df_median: The median DataFrame
        :type df_median: pd.DataFrame
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


        fig.add_trace(
                  go.Scatter(
                      name=name,
                      x=df_median["DateTime"],
                      y=df_median[label],
                      marker=dict(color=color),
                      line=dict(width=1),
                      mode='lines',
                      showlegend=True
                  )
               )

       
        return fig    

    def AddTraces_Rolling(self, fig: go.Figure, width: int) -> go.Figure:
        """Add rolling mean and std dev traces to the figure.

            :param fig: The figure to update
            :type fig: go.Figure
            :param width: The rolling window size
            :type width: int
            :return: The updated figure
            :rtype: go.Figure
        """
        df_rolling, mean_print, median_print, std_print = self.CreateDFs.RollingMean_DF(width)
       
        for label in ["Upper", "Lower", "Median"]:

            fig = self._AddTraces_Rolling(fig, df_rolling, label)
        try:
            fig = add_point_legend(fig, mean_print, median_print, std_print)
         
        except Exception:
            logger.exception("Failed to add legend-style summary for rolling plot")

        return fig

    def AddTraces_Median(self, fig: go.Figure) -> go.Figure:
        """Add median traces to the figure.

            :param fig: The figure to update
            :type fig: go.Figure
            :return: The updated figure
            :rtype: go.Figure
        """
        df_median, mean_print, median_print, std_print = self.CreateDFs.Median_DF()

        for label in ["Median", "Upper", "Lower"]:
            fig = self._AddTraces_Median(fig, df_median, label)
        
        try:
            fig = add_point_legend(fig, mean_print, median_print, std_print)
       
        except Exception:
            logger.exception("Failed to add legend-style summary for median plot")

        return fig

    def AddNothing(self, fig: go.Figure) -> go.Figure:
        """Add a notification to the figure indicating insufficient data.

            :param fig: The figure to update
            :type fig: go.Figure
            :return: The updated figure
            :rtype: go.Figure
        """

        fig.add_annotation(dict(font=dict(color='black',size=15),
                                x=0,
                                y=-0.4,
                                showarrow=False,
                                text="not enough samples for median or standard deviation trends",
                                textangle=0,
                                xanchor='left',
                                align="center",
                                xref="paper",
                                yref="paper"))
        return fig        


def format_val(v: Optional[float]) -> str:
    """Format a numeric value to string for display in annotations. Returns 'n/a' for None/NaN.
    :param v: The value to format
    :type v: Optional[float]
    :return: The formatted string
    :rtype: str
    """
    try:
        if v is None:
            return 'n/a'
        if isinstance(v, str):
            return 'n/a'
        # numpy NaN check
        if isinstance(v, (int, float)) and np.isnan(v):
            return 'n/a'
        return f"{float(v):.2f}"
    except Exception:
        return str(v)

def add_point_legend(fig, mean_print, median_print, std_print) -> go.Figure:
    """Add invisible legend entries to the figure for mean, median, and std dev.
    :param fig: The figure to update
    :type fig: go.Figure
    :param mean_print: The mean value
    :param median_print: The median value
    :param std_print: The standard deviation value
    :return: The updated figure
    :rtype: go.Figure
    """
    # Add three invisible legend entries so the legend shows a 3-line summary
    mean_text = f"mean: {format_val(mean_print)}"
    median_text = f"median: {format_val(median_print)}"
    std_text = f"std dev: {format_val(std_print)}"

    for txt in (mean_text, median_text, std_text):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers',
                                marker=dict(opacity=0, size=0), showlegend=True,
                                name=txt, hoverinfo='skip'))


    return fig

