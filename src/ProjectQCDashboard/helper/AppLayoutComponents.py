from collections import OrderedDict
from typing import Union, Tuple, Optional, List
from pathlib import Path
import plotly.graph_objects as go
from dash import html
import dash_bootstrap_components as dbc
from ProjectQCDashboard.helper.GenerateFig import generate_Fig
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.configuration import PLOT_CONFIG, ThresholdForRollingMean, DaysToMonitor
from datetime import datetime
logger = get_configured_logger(__name__)


# Dictionaries derived from PLOT_CONFIG for backwards compatibility
DEFAULT_PLOTS = OrderedDict([(key, value[0]) for key, value in PLOT_CONFIG.items()])
LABELS_FOR_PLOTS = {key: value[1] for key, value in PLOT_CONFIG.items()}


def get_plot_keys() -> List[str]:
    """Return ordered list of plot keys.
    
    :return: List of plot keys in display order
    :rtype: List[str]
    """
    return list(PLOT_CONFIG.keys())


def get_plot_graph_ids() -> List[str]:
    """Return ordered list of graph IDs for Dash components.
    
    :return: List of graph IDs in display order
    :rtype: List[str]
    """
    return [value[2] for value in PLOT_CONFIG.values()]


def generateOptions() -> list[dict]:
    """
    Return a list of option dicts for dash Checklist/Dropdown:
      [{'label': <human label>, 'value': <key>}, ...]
    Order follows LABELS_FOR_PLOTS.

    :return: List of option dicts for dash components
    :rtype: list[dict]
    """
    # Use the canonical key as the option 'value' so it matches app logic
    return [{'label': item, 'value': key} for key, item in LABELS_FOR_PLOTS.items()]
        
                 

def generate_all_figures(output_file_path: Union[Path, str], keys: Optional[List[str]] = None) -> Tuple[go.Figure, ...]:
    """
    Create figures for all default plots and return them as an ordered tuple.
    The order matches DEFAULT_PLOTS.keys(). If `keys` is provided, only those keys
    will be included (but ordering is preserved relative to DEFAULT_PLOTS).

    :param output_file_path: Path to the output file containing data
    :type output_file_path: Union[Path, str]
    :param keys: Optional list of keys to include (subset of DEFAULT_PLOTS keys)
    :type keys: Optional[List[str]]
    :return: Tuple of plotly Figure objects
    :rtype: Tuple[go.Figure, ...]
    """
    gen = generate_Fig(output_file_path)
    figs = []
    for key, y_label in DEFAULT_PLOTS.items():
        if keys is not None and key not in keys:
            continue
        try:
            figs.append(gen.CreateFig(y_label))
        except Exception as e:
            logger.error(f"Error creating figure {key}: {e}")
            figs.append(go.Figure())

    return tuple(figs)


def generate_all_figures_labels(output_file_path: Union[Path, str], selected_plots: List[str]) -> List[Tuple[str, go.Figure]]:
    """
    Return a list of (label, figure) tuples for the selected plots in the order
    of DEFAULT_PLOTS.

    :param output_file_path: Path to the output file containing data
    :type output_file_path: Union[Path, str]
    :param selected_plots: List of keys to include (subset of DEFAULT_PLOTS keys)
    :type selected_plots: List[str]
    :return: List of (label, figure) tuples
    :rtype: List[Tuple[str, go.Figure]]
    """
    gen = generate_Fig(output_file_path)
    out: List[Tuple[str, go.Figure]] = []
    for key, y_label in DEFAULT_PLOTS.items():
        if key not in selected_plots:
            continue
        try:
            fig = gen.CreateFig(y_label)
        except Exception as e:
            logger.error(f"Error creating figure for export {key}: {e}")
            fig = go.Figure()    
        out.append((LABELS_FOR_PLOTS.get(key, key), fig))

    return out


def create_page_header() -> html.Div:
    """Create the page header component.

    :return: Dash HTML Div component for the page header
    :rtype: html.Div
    """
    return html.Div(
            dbc.Row(
                dbc.Col(
                    html.Div([
                        html.H1(
                            "Project QC Dashboard",
                            className="page-title",
                        ),
                        html.H5(
                            f"only Projects measured in the past {DaysToMonitor} days are available for now",
                            className="page-subtitle",
                        ),
                        html.H5(
                            [
                                "Trendlines display the median and standard deviation, or the rolling equivalent ",
                                html.Br(),
                                f"when at least {ThresholdForRollingMean} measurements have been done",
                            ],
                            className="page-note",
                        ),
                    ], className="page-header-content"),
                    width=12,
                ),
                className="mb-2",
            ),
            className="page-header",
        )

def create_full_html(css_text: str, ProjectChosen: str, body_html: str) -> str:
    today = datetime.now().strftime("%d.%m.%Y")

    """Create a full HTML document for exporting plots.
    :param css_text: CSS styles to include in the HTML
    :type css_text: str
    :param ProjectChosen: Name of the chosen project
    :type ProjectChosen: str
    :return: Full HTML document as a string
    """

    full_html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Project QC Dashboard Export</title>
  <style>{css_text}</style>
  <!-- Plotly JS will be loaded from CDN by the figure fragments -->
</head>
<body>
  <div class="export-page">
    <h1>Project QC</h1>
    <h2>Project: {ProjectChosen}, exported on {today}</h2>
    {body_html}
  </div>
</body>
</html>
"""
    return full_html
