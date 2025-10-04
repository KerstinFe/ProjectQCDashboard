import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash, ctx
from ProjectQCDashboard.helper.UpdateCSV import  update_df
from ProjectQCDashboard.helper.common import CreateOutputFilePath
from ProjectQCDashboard.helper.database import Database_Call
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.helper.AppLayoutComponents import (
    generate_all_figures, generate_all_figures_labels, create_full_html,
    create_page_header, generateOptions, LABELS_FOR_PLOTS, PLOT_CONFIG,
    get_plot_keys, get_plot_graph_ids
)
from ProjectQCDashboard.config.configuration import ThresholdForTwoColumnsOfGraphs
from typing import Any, List, Optional, Union
from pathlib import Path
import dash_bootstrap_components as dbc
import plotly.io as pio
from datetime import datetime

logger = get_configured_logger(__name__)
pio.templates.default = "plotly_white"

class AppLayout:
    def __init__(self, metadata_db_path: Union[str, Path]) -> None:
        """
        Initialize the application layout with database paths.

        :param mqqc_db_path: Path to the MQQC SQLite database file
        :type mqqc_db_path: Union[str, Path]
        :param metadata_db_path: Path to the metadata SQLite database file
        :type metadata_db_path: Union[str, Path]

        """

        # Set URL base pathname for Apache proxy
        # Use only the Bootstrap theme in external stylesheets; serve our `assets` folder explicitly
        external_style = [dbc.themes.LUX]
        assets_folder = Path(__file__).resolve().parent.parent / "assets"
        self.app = Dash(
            __name__,
            url_base_pathname='/ProjectQCDashboard/',
            external_stylesheets=external_style,
            assets_folder=str(assets_folder),
        )
       
        self.metadata_db_path = metadata_db_path
        
        # Use metadata database for getting project names
        self.metadata_db = Database_Call(self.metadata_db_path)
        self.ProjectIDs = list(self.metadata_db.getProjectNamesDict("regex").keys())
        self.ProjectIDs.sort(reverse=True) 
      
        self.FileName = ""
        self.OutputFilePath =  ""
        self.df = pd.DataFrame()
    
    def _build_graphs_container(self) -> html.Div:
        """Build the graphs container with columns in the correct order from PLOT_CONFIG.
        
        :return: HTML Div containing all graph columns in proper order
        :rtype: html.Div
        """
        # Build columns list explicitly to ensure order matches PLOT_CONFIG
        columns = []
        for key, (_, display_label, graph_id) in PLOT_CONFIG.items():
            col = dbc.Col(
                self.graph_card(graph_id, display_label),
                md=6,
                id=f'col-{key}'
            )
            columns.append(col)
        
        return html.Div(id='graphs-container', children=[
            dbc.Row(columns, className="mb-4 g-4"),
        ])
           
    def CreateApp(self) -> Any:
        

        """
        Create the Dash application layout.

        :return: The Dash application layout
        :rtype: Any
        """

        # Load project IDs only when creating the app layout
      
        logger.info("Creating app layout...")
        # Warm up Plotly/px to avoid a large one-time initialization cost on
        # the first call to px.scatter/CreateFig. This typically reduces the
        # first-figure delay observed when the app is first used.
        try:
            small_df = pd.DataFrame({
                'DateTime': [pd.Timestamp.now()],
                'y': [1],
                'FileType': ['warmup'],
                'Name': ['warmup']
            })
            _ = px.scatter(small_df, x='DateTime', y='y', color='FileType', hover_name='Name')
           
        except Exception as e:
            logger.info(f"Plotly warmup failed: {e}")
        
        # Main container using Bootstrap grid. Each graph is wrapped in a card for nicer styling.
        self.app.layout = dbc.Container([
                    # Header area (title) with a dark background spanning full width
                    create_page_header(),
                 
                    # Dropdown and controls (not part of the dark header)
                    dbc.Row(dbc.Col(dcc.Dropdown(self.ProjectIDs, value=self.ProjectIDs[0] if self.ProjectIDs else None, id='ProjectIDs'), width=6), className="mb-3"),

                    # Checklist to select which plots are visible / exported
                    dbc.Row(dbc.Col(dcc.Checklist(
                                    id='plot-select',
                                    options=generateOptions(),             # no surrounding [ ... ]
                                    value=list(LABELS_FOR_PLOTS.keys()),   # a plain list of keys (default all selected)
                                    labelStyle={'display': 'inline-block', 'margin-right': '12px'}
                                ), width=12), className='mb-3'),

                    # Placeholder for graphs — updated dynamically based on data size
                    # Build graph columns explicitly to ensure correct order from PLOT_CONFIG
                    self._build_graphs_container(),

                    dbc.Row(dbc.Col(html.Div([
                        dbc.Button("Download CSV", id="btn_csv", className="download-btn"),
                        dbc.Button("Download Page (HTML)", id="btn_download_html", className="download-btn ms-2"),
                        dcc.Download(id="download-dataframe-csv"),
                        dcc.Download(id="download-html")
                    ]), width=6)),
                ], fluid=True)
        
        # Generate callback outputs dynamically from PLOT_CONFIG
        graph_outputs = [Output(component_id=graph_id, component_property='figure') 
                        for graph_id in get_plot_graph_ids()]
        
        @self.app.callback(
            *graph_outputs,
            Output(component_id='graphs-container', component_property='className'),
            Input('ProjectIDs', 'value')
            )
        def update_output_div(ProjectChosen: str) -> Any:
            """
            Update the output div with the selected project.

            :param ProjectChosen: The chosen project ID
            :type ProjectChosen: str
            :return: The updated figures for the graphs
            :rtype: Any
            """
            
          
            OutputFilePath = CreateOutputFilePath(ProjectChosen)
            logger.info(OutputFilePath)
                      
            # Check if CSV file exists and has data
            if not os.path.exists(OutputFilePath):
                logger.warning(f"CSV file does not exist: {OutputFilePath}")
                empty_fig = go.Figure()
                # Return empty figures for all plots plus the className
                return tuple([empty_fig] * len(PLOT_CONFIG) + [""])
            
            try:
                # Create figure generators and call their CreateFig method
                # Load data to decide on layout
                try:
                    df = pd.read_csv(OutputFilePath)
                except Exception:
                    df = pd.DataFrame()
              
                # Generate all figures in PLOT_CONFIG order
                all_figs = generate_all_figures(OutputFilePath)

                # Decide whether to render graphs in one or two columns
                single_column = len(df) >= ThresholdForTwoColumnsOfGraphs
                class_name = "single-column" if single_column else ""

                # Return all figures plus the className
                return tuple(list(all_figs) + [class_name])
            
            except Exception as e:
                logger.error(f"Error generating figures: {e}")
                empty_fig = go.Figure()
                # Return empty figures for all plots plus the className
                return tuple([empty_fig] * len(PLOT_CONFIG) + [""])

        @self.app.callback(
            Output("download-dataframe-csv", "data"),
            Input("btn_csv", "n_clicks"),
            Input('ProjectIDs', 'value'),  # Add the dropdown value as input
            prevent_initial_call=True,
        )
        def download_csv(n_clicks: Any, ProjectChosen: str) -> Any:
            """
            Download the CSV file for the selected project.

            :param n_clicks: Number of button clicks
            :param ProjectChosen: The chosen project ID from the dropdown
            :type n_clicks: Any
            :type ProjectChosen: str
            :return: The CSV file data for download
            :rtype: Any
            """

            if ctx.triggered_id == "btn_csv":
                OutputFilePath = CreateOutputFilePath(ProjectChosen)
                df = update_df(OutputFilePath)
                FileName = os.path.basename(OutputFilePath)
                if os.path.exists(OutputFilePath):
                    return dcc.send_data_frame(df.to_csv, FileName)
                
            return dash.no_update

        @self.app.callback(
            Output("download-html", "data"),
            Input("btn_download_html", "n_clicks"),
            Input('ProjectIDs', 'value'),
            Input('plot-select', 'value'),
            prevent_initial_call=True,
        )
        def download_html(n_clicks: Any, ProjectChosen: str, selected_plots: List[str]) -> Any:
            """
            Build a standalone HTML snapshot containing only the currently shown plots
            (no dropdown), preserving layout and styling. Returns a downloadable HTML file.
            """
            if ctx.triggered_id != "btn_download_html":
                return dash.no_update

            OutputFilePath = CreateOutputFilePath(ProjectChosen)
            if not os.path.exists(OutputFilePath):
                logger.warning(f"CSV file does not exist: {OutputFilePath}")
                return dash.no_update

            try:
                
                today_filename = datetime.now().strftime("%Y%m%d")

                figs = generate_all_figures_labels(OutputFilePath, selected_plots)

                # Read app CSS to include in the exported HTML
                css_path = Path(__file__).resolve().parent.parent / "assets" / "custom.css"
                css_text = ""
                if css_path.exists():
                    css_text = css_path.read_text(encoding='utf-8')

                # Build HTML body: include each figure's html fragment
                plots_html = []
                for title, fig in figs:
                    # to_html with full_html=False yields a div+script for the figure
                    fig_html = pio.to_html(fig, include_plotlyjs='cdn', full_html=False)
                    plots_html.append(f"<section class=\"export-plot\">\n<h3>{title}</h3>\n{fig_html}\n</section>")

                body_html = "\n".join(plots_html)
                full_html = create_full_html(css_text, ProjectChosen, body_html)

                # Return bytes for download (utf-8)
                def _write_html_bytes(bio: Any) -> None:
                    """Writes the full HTML content to the provided binary IO stream.

                    :param bio: file-like object to write bytes to
                    :type bio: Any
                    """
                    bio.write(full_html.encode('utf-8'))

                return dcc.send_bytes(_write_html_bytes, filename=f"{today_filename}_ProjectQC_{ProjectChosen}.html")

            except Exception as e:
                logger.error(f"Error creating HTML export: {e}")
                return dash.no_update

        # Generate visibility toggle outputs dynamically from PLOT_CONFIG
        col_outputs = [Output(f'col-{key}', 'style') for key in get_plot_keys()]
        
        @self.app.callback(
            *col_outputs,
            Input('plot-select', 'value')
        )
        def toggle_plots(selected: List[str]):
            # Return style dicts for each column: hide if not selected
            return tuple(
                {} if key in selected else {'display': 'none'}
                for key in get_plot_keys()
            )

        return self.app
   

    def graph_card(self, graph_id: str,label_text:str, figure: Optional[go.Figure] = None) -> dbc.Card:
        """
        Return a Bootstrap Card that contains the graph and its title.
        :param y_label: The label for the y-axis
        :param graph_id: The ID for the graph component
        :param figure: Optional pre-created figure to use
        :type y_label: str
        :type graph_id: str
        :type label_text: str
        :type figure: Optional[go.Figure]
        :return: A Bootstrap Card component containing the graph
        :rtype: dbc.Card
        """
        # Create an empty figure as placeholder. The real figures are provided
        # by the `update_output_div` callback. 

        if figure is not None:
            fig = figure
        else:
            fig = go.Figure()

        # Use CardHeader so the CSS pill selector (.graph-card .card-header) applies
        card = dbc.Card(
            [
                dbc.CardHeader(html.Div(label_text, className="card-header-title")),
                dbc.CardBody(
                    dcc.Loading(
                        dcc.Graph(
                            id=graph_id,
                            figure=fig,
                            config={"displayModeBar": True},
                            style={"background": "transparent"},
                        ),
                        type="circle",
                    ),
                ),
            ],
            className="graph-card mb-3",
            style={"border": "1px solid #e6e9ef"},
        )

        return card
