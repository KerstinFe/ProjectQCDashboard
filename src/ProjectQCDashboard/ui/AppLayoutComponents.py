from collections import OrderedDict
import plotly.graph_objects as go
from dash import html
from datetime import datetime
import dash_bootstrap_components as dbc
from ProjectQCDashboard.ui.Figures import Create_Figures
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.configuration import PLOT_CONFIG, ThresholdForRollingMean, ROWS_Table  
from datetime import datetime
logger = get_configured_logger(__name__)


REPO_URL    = "https://github.com/KerstinFe/ProjectQCDashboard"
AUTHOR_NOTE = "Built by Kerstin Fentker"

# Dictionaries derived from PLOT_CONFIG for backwards compatibility
# For keys ending in _iQC, the column name in project_data is value[0] + "_iQC"
DEFAULT_PLOTS = OrderedDict([
    (key, value[0] + "_iQC" if key.endswith("_iQC") else value[0])
    for key, value in PLOT_CONFIG.items()
])

LABELS_FOR_PLOTS = {key: value[1] for key, value in PLOT_CONFIG.items()}


def get_plot_keys() -> list[str]:
    """
    Return an ordered list of plot keys as defined in PLOT_CONFIG.

    :return: List of plot keys in display order
    :rtype: list[str]
    """
    return list(PLOT_CONFIG.keys())


def get_plot_graph_ids() -> list[str]:
    """
    Return an ordered list of graph IDs for Dash components as defined in PLOT_CONFIG.

    :return: List of graph IDs in display order
    :rtype: list[str]
    """
    return [value[2] for value in PLOT_CONFIG.values()]


def generateOptions() -> list[dict[str, str]]:
    """
    Generate a list of option dictionaries for Dash Checklist/Dropdown components.

    Each option dict contains a human-readable label and a value key, following LABELS_FOR_PLOTS order.

    :return: List of option dicts for Dash components
    :rtype: list[dict[str, str]]
    """
    return [{'label': item, 'value': key} for key, item in LABELS_FOR_PLOTS.items()]
        
                 
class FigureComponents:
    """
    Handles generation of all figure components for project visualization.
    """
    
    def __init__(self, ProjectChosen: str) -> None:
        """
        Initialize the FigureComponents class for a given project.

        :param ProjectChosen: ProjectID to generate figures for
        :type ProjectChosen: str
        """
        self.ProjectChosen = ProjectChosen

    def generate_all_figures(self) -> tuple[tuple[go.Figure, ...] | None, int]:
        """
        Create figures for all default plots and return them as an ordered tuple.

        The order matches DEFAULT_PLOTS.keys(). If `keys` is provided, only those keys
        will be included (but ordering is preserved relative to DEFAULT_PLOTS).

        :return: tuple of (plotly Figure objects tuple or None if no data, row count)
        :rtype: tuple[tuple[go.Figure, ...] | None, int]
        """
        # Get row count from first instance
        gen = Create_Figures(self.ProjectChosen)
        row_count = gen.nrows_valid_data
        
        if row_count == 0:
            return None, 0
        
        figs = []
        for key, y_label in DEFAULT_PLOTS.items():
 
            try:             
                fig = gen.generate_fig(y_label)              
                figs.append(fig)
            except Exception as e:
                logger.error(
                    "figure_creation_failed",
                    extra={"figure_key": key, 
                           "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
                fig = go.Figure()
                figs.append(fig)

        return tuple(figs), row_count 


    def generate_all_figures_labels(self, selected_plots: list[str]) -> list[tuple[str, go.Figure]]:
        """
        Return a list of (label, figure) tuples for the selected plots in the order of DEFAULT_PLOTS.

        :param selected_plots: list of keys to include (subset of DEFAULT_PLOTS keys)
        :type selected_plots: list[str]
        :return: list of (label, figure) tuples
        :rtype: list[tuple[str, go.Figure]]
        """
        gen = Create_Figures(self.ProjectChosen)
        out: list[tuple[str, go.Figure]] = []

        for key, y_label in DEFAULT_PLOTS.items():
            if not isinstance(key, str) or key not in selected_plots:
                continue
            try:
                fig = gen.generate_fig(y_label)
            except Exception as e:
                logger.error(
                    "figure_export_creation_failed",
                    extra={"figure_key": key, 
                           "error_class": type(e).__name__, "error": str(e)}, exc_info=True)
                fig = go.Figure()
            if fig.layout.uirevision == "no-data":        
                continue
            out.append((LABELS_FOR_PLOTS.get(key, key), fig))

        return out


    def generate_table_error(self) -> go.Figure | None:
        """
        Return a table figure with list of files that have an error.

        :return: Table figure or None if no errors
        :rtype: go.Figure | None
        """
        gen = Create_Figures(self.ProjectChosen)
        ErrorTable = gen.create_table_error()
    
        return ErrorTable
    
    def generate_table_project(self) -> go.Figure | None:
        """
        Return a table figure with project metadata.

        :return: Table figure or None if no errors
        :rtype: go.Figure | None
        """
        gen = Create_Figures(self.ProjectChosen)
        ProjectTable = gen.create_table_project_data(ROWS_Table)
    
        return ProjectTable
        
    

def create_page_header() -> html.Div:
    """
    Create the page header component.

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
                            [
                                "Trendlines display the median and standard deviation, or the rolling equivalent ",
                                html.Br(),
                                f"when at least {ThresholdForRollingMean} measurements have been done",
                                html.Br(),
                                "Shows only plots that contain data and are selected."
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


def create_page_footer() -> html.Div:
    """
    Create the page footer component.

    :return: Dash HTML Div component for the page footer
    :rtype: html.Div
    """
    return html.Div(
        dbc.Row(
            html.Div([
                html.Span('© 2026 Kerstin Fentker | ', className="page-footer-text"),
                html.A(
                    "MAX-DELBRUECK CENTRUM FOR MOLECULAR MEDICINE",
                    href="https://www.mdc-berlin.de/imprint",
                    className="page-footer-link"
                ),
                html.Span('; Berlin-Buch; Germany', className="page-footer-text"),
                html.Div(className="footer-break"),
                html.Span('Code at @ ', className="page-footer-text"),
                html.A("GitHub Repro",
                    href=REPO_URL,
                    className="page-footer-link"
                ),
            ], className="page-footer-content"),
            className="page-footer-box",
        ),
        className="page-footer",
    )



def footer_html_fragment() -> str:
    return (
        '<footer class="export-footer"><div class="export-bar-inner">'
        '© 2026 Kerstin Fentker | '
        '<a href="https://www.mdc-berlin.de/imprint">MAX-DELBRUECK CENTRUM FOR MOLECULAR MEDICINE</a>'
        '; Berlin-Buch; Germany'
        '<br>Code at @ '
        f'<a href="{REPO_URL}">GitHub Repo</a>'
        '</div></footer>'
    )

def create_full_html(css_text: str, ProjectChosen: str, body_html: str) -> str:
    downloaded = datetime.now().strftime("%Y-%m-%d %H:%M")
    footer_html = footer_html_fragment()
    return f"""<!doctype html>
        <html>
        <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Project QC Dashboard Export</title>
        <style>{css_text}</style>
        </head>
        <body>
        <header class="export-header">
            <div class="export-bar-inner">
            <h1>Project QC Dashboard</h1>
            <p class="export-meta">Project: {ProjectChosen} &middot; Downloaded {downloaded}</p>
            </div>
        </header>

        <div class="export-page">
            {body_html}
        </div>

        {footer_html}
        </body>
        </html>
        """

