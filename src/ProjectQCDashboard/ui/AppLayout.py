import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, dash, ctx
from dash.exceptions import PreventUpdate
from ProjectQCDashboard.ui.processDataForFig import get_all_data, get_data_freshness
from ProjectQCDashboard.db.database import get_all_project_ids, search_project_ids, get_db_version
from ProjectQCDashboard.config.logger import get_configured_logger
from ProjectQCDashboard.config.configuration import PLOT_CONFIG
from ProjectQCDashboard.ui.AppLayoutComponents import (
    FigureComponents,
    create_full_html,
    create_page_header, create_page_footer, generateOptions, LABELS_FOR_PLOTS, 
    get_plot_keys, get_plot_graph_ids
)
from ProjectQCDashboard.config.configuration import ThresholdForTwoColumnsOfGraphs
from typing import Any
from pathlib import Path
import dash_bootstrap_components as dbc
import plotly.io as pio
from datetime import datetime

logger = get_configured_logger(__name__)
pio.templates.default = "plotly_white"

class AppLayout:
    def __init__(self) -> None:
        """
        Initialize the AppLayout class and set up the Dash application instance.

        This method configures the Dash app with Bootstrap styling, sets the assets folder,
        and defines the base URL path. Project IDs are loaded dynamically when the layout is created.
        """

        # Set URL base pathname for Apache proxy
        # Use only the Bootstrap theme in external stylesheets; serve `assets` folder explicitly
        external_style = [dbc.themes.LUX]
        assets_folder = Path(__file__).resolve().parent.parent / "assets"
        self.app = Dash(
            __name__,
            url_base_pathname='/ProjectQCDashboard/',
            external_stylesheets=external_style,
            assets_folder=str(assets_folder),
        )
       
    def _build_graphs_container(self) -> html.Div:
        """
        Build the container for all graph columns in the order specified by PLOT_CONFIG.

        Returns a Dash html.Div containing all graph columns, each wrapped in a Bootstrap column,
        in the order defined by PLOT_CONFIG. This ensures the layout matches the configuration.

        :return: HTML Div containing all graph columns in the correct order
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
           
    def createapp(self) -> Dash:
        """
        Create and configure the Dash application layout and callbacks.

        Sets up the main layout, dropdowns, controls, and all Dash callbacks for interactivity:
        - Project selection and search
        - Plot visibility toggling
        - Data export (CSV, HTML)
        - Dynamic updates when the database changes

        Database updates are recognizes via the _db_version that is stored in db-version-store-dropdown & db-version-store-figures. 

        :return: The configured Dash application instance
        :rtype: Dash
        """

        # Load project IDs only when creating the app layout
      
        logger.info("app_layout_creation_started")
        initial_ids = get_all_project_ids()
        
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
            logger.info("plotly_warmup_failed", extra={"error": str(e)})



        ##########################

        ## this is the actual layout now

        ##########################

        # Main container using Bootstrap grid. Each graph is wrapped in a card for nicer styling.
        self.app.layout = dbc.Container([
                    
                    dcc.Store(id='db-version-store-dropdown', data=0),
                    dcc.Store(id='db-version-store-figures', data=0),
                    dcc.Interval(id='interval-update-projectids', interval=1*60*1000, n_intervals=0), # every  min
                    # Header area (title) with a dark background spanning full width
                    create_page_header(),

                    dbc.Row(
                        dbc.Col(html.Div(id='data-refreshed', className='data-refreshed'), width=12),
                        className='mb-2',
                    ),
                 
                    # Dropdown and controls (not part of the dark header)

                    dbc.Row(
                        dbc.Col(
                        dcc.Dropdown(
                           options=[{"label": pid, "value": pid} for pid in initial_ids[:200]],  # only first 200 initially
                            value=initial_ids[0] if initial_ids else None,
                            id='ProjectIDs',
                            searchable=True
                        ), 
                        width=3),className="mb-3"),

                    # Checklist to select which plots are visible / exported
                    dbc.Row(dbc.Col(dcc.Checklist(
                                    id='plot-select',
                                    options=generateOptions(),
                                    value=list(LABELS_FOR_PLOTS.keys()),
                                    labelStyle={'margin-right': '12px'},
                                    style={'display': 'flex', 'flexDirection': 'row', 'flexWrap': 'wrap'}
                                ), width=12), className='mb-3'),
                    
                    dbc.Row(dbc.Col(self.graph_card('project-table', 'Project Data', className_card ="error-card mb-3"), width=6), id='table-style', className='mb-3'),
                    dbc.Row(dbc.Col(self.graph_card('error-table', 'Files with Errors', className_card ="error-card mb-3"), width=6), id='error-table-style', className='mb-3'),

                    # Placeholder for graphs — updated dynamically based on data size
                    self._build_graphs_container(),

                    dbc.Row(dbc.Col(html.Div([
                        dbc.Button("Download CSV", id="btn_csv", className="download-btn"),
                        dbc.Button("Download Page (HTML)", id="btn_download_html", className="download-btn ms-2"),
                        dcc.Download(id="download-dataframe-csv"),
                        dcc.Download(id="download-html")
                    ]), width=6)),
                    create_page_footer(),
                ], fluid=True)
        

        #####################
        ### here the callbacks and other update functions start
        #####################
      
        # Generate callback outputs dynamically from PLOT_CONFIG
        graph_outputs = [Output(component_id=graph_id, component_property='figure') 
                        for graph_id in get_plot_graph_ids()]
        
        # Generate callback outputs for column visibility (className)
        col_class_outputs = [Output(component_id=f'col-{key}', component_property='className')
                            for key in get_plot_keys()]
        
        
        @self.app.callback(
            [Output('ProjectIDs', 'options'), Output('ProjectIDs', 'value'), Output('db-version-store-dropdown', 'data') ],
            [Input('ProjectIDs', 'search_value'), Input('interval-update-projectids', 'n_intervals')],
            [State('ProjectIDs', 'value'), State('db-version-store-dropdown', 'data')]
        )
    
        def update_project_ids(search_value: str, n_intervals: Any, current_value: str, last_seen_version: Any) -> tuple[list[dict[str, str]], str | None, int]:
            """
            Callback to update the project ID dropdown options and value based on search or database change.

            Triggered by user search or periodic interval. Updates the dropdown list of project IDs if there is a new version or upon search
            and ensures the selected value remains valid. Also updates the stored DB version.

            :param search_value: The current search string entered by the user
            :type search_value: str
            :param n_intervals: Number of intervals elapsed (triggers periodic refresh)
            :type n_intervals: Any
            :param current_value: The currently selected project ID
            :type current_value: str
            :param last_seen_version: Last seen database version
            :type last_seen_version: Any
            :return: Tuple of (dropdown options, selected value, current DB version)
            :rtype: tuple[list[dict[str, str]], str | None, int]
            """
            # gets ID which triggered the update: when the database changed the 'db-version-store-dropdown' is updated and triggers the update of the list
            # when something is searched, this triggers an update of the dropdown list
            triggered = ctx.triggered_id
            current_version = get_db_version()

            if triggered == 'interval-update-projectids' and last_seen_version == current_version:
                raise PreventUpdate
            
            logger.debug(
                "update_project_ids_triggered",
                extra={
                    "triggered_by": triggered,
                    "search_value_type": type(search_value).__name__ if search_value is not None else None,
                    "search_value": str(search_value)[:100] if search_value is not None else None,
                    "current_value": str(current_value)[:30] if current_value is not None else None,
                },
            )

            pattern = search_value if (triggered == 'ProjectIDs' and isinstance(search_value, str)) else None
            project_ids = search_project_ids(pattern, limit=100)
            options = [{"label": pid, "value": pid} for pid in project_ids]
            if current_value and current_value not in project_ids:
                options.append({"label": current_value, "value": current_value})

            return options, current_value or (project_ids[0] if project_ids else None), current_version

        
        @self.app.callback(
            *graph_outputs,
            Output('error-table', 'figure'),
            Output('error-table-style', 'style'),
            Output('project-table', 'figure'),
            Output('table-style', 'style'),
            Output(component_id='graphs-container', component_property='className'),
            *col_class_outputs,
            Output('db-version-store-figures', 'data'),
            Input('ProjectIDs', 'value'), Input('interval-update-projectids', 'n_intervals'),
            State('db-version-store-figures', 'data')
        )
        
        def update_output_div(ProjectChosen: str, n_intervals: Any, last_seen_version: Any ) -> tuple[Any, ...]:
            """
            Update all output figures, tables, and layout styles when a project is selected or the database changes.

            Handles:
            - Generating all figures for the selected project
            - Updating error and project tables
            - Adjusting column visibility and layout based on data
            - Hiding/showing tables if no data is present

            :param ProjectChosen: The selected project ID
            :type ProjectChosen: str
            :param n_intervals: Number of intervals elapsed (triggers periodic refresh)
            :type n_intervals: Any
            :param last_seen_version: Last seen database version
            :type last_seen_version: Any
            :return: Tuple containing updated figures, tables, styles, column classes, and current DB version
            :rtype: tuple
            """
            triggered = ctx.triggered_id
            current_version = get_db_version()

            if triggered == 'interval-update-projectids' and last_seen_version == current_version:
                raise PreventUpdate

            if ProjectChosen is None:
                logger.debug("update_output_div_skipped_missing_project")
                empty_fig = go.Figure()
                col_classes = ["col-empty"] * len(PLOT_CONFIG)
                return tuple([empty_fig] * len(PLOT_CONFIG) + [empty_fig, {'display': 'none'}, empty_fig, {'display': 'none'}, ""] + col_classes + [current_version])
        
            logger.info("project_selected", extra={"project_id": ProjectChosen})
            Output_components = FigureComponents(ProjectChosen)
            
            try:
                # Generate all figures in PLOT_CONFIG order
                # Returns None if no data exists for this project
                all_figs, row_count = Output_components.generate_all_figures()
                
                if all_figs is None:
                    logger.warning("project_not_in_db", extra={"project_id": ProjectChosen})
                    empty_fig = go.Figure()
                    col_classes = ["col-empty"] * len(PLOT_CONFIG)
                    return tuple([empty_fig] * len(PLOT_CONFIG) + [empty_fig, {'display': 'none'}, empty_fig, {'display': 'none'}, ""] + col_classes + [current_version])

                # Generate error table
                error_table = Output_components.generate_table_error()
                project_table = Output_components.generate_table_project()

                # Decide whether to render graphs in one or two columns
                single_column = row_count >= ThresholdForTwoColumnsOfGraphs
                class_name = "single-column" if single_column else ""

                # Check which figures are empty and hide those columns
                col_classes = []
                for fig in all_figs:
                    if fig.layout.uirevision == "no-data":
                        col_classes.append("col-empty")
                    else:
                        col_classes.append("")

                # Return all figures plus tables in correct order
                if error_table is not None:
                    error_table_style = {'display': 'block'}
                else:
                    error_table = go.Figure()
                    error_table_style = {'display': 'none'}
                
                if project_table is not None:
                    project_table_style = {'display': 'block'}
                else:
                    project_table = go.Figure()
                    project_table_style = {'display': 'none'}
                
                return tuple(list(all_figs) + [error_table, error_table_style, project_table, project_table_style, class_name] + col_classes + [current_version])
                
            except Exception as e:
                logger.error("figure_generation_failed", extra={"error_class": type(e).__name__,
                                                                "error": str(e)}, exc_info=True)
                empty_fig = go.Figure()
                col_classes = ["col-empty"] * len(PLOT_CONFIG)
                return tuple([empty_fig] * len(PLOT_CONFIG) + [empty_fig, {'display': 'none'}, empty_fig, {'display': 'none'}, ""] + col_classes + [current_version])

        @self.app.callback(
            Output('data-refreshed', 'children'),
            Input('ProjectIDs', 'value'), Input('interval-update-projectids', 'n_intervals'),
            State('db-version-store-figures', 'data')
        )
        
        def update_data_refreshed(id: Any, n_intervals: Any, last_seen_version: Any) -> str:
            
            triggered = ctx.triggered_id
            current_version = get_db_version()

            if triggered == 'interval-update-projectids' and last_seen_version == current_version:
                raise PreventUpdate
        
            updated_at, new_rows = get_data_freshness()
            if not updated_at:
                return ""
            try:
                ts = pd.to_datetime(updated_at).strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts = str(updated_at)
            if new_rows and new_rows > 0:
                return f"Data refreshed {ts} · +{new_rows} samples"
            return f"Data refreshed {ts}"
        
        @self.app.callback(
            Output("download-dataframe-csv", "data"),
            Input("btn_csv", "n_clicks"),
            Input('ProjectIDs', 'value'),  # Add the dropdown value as input
            prevent_initial_call=True,
        )
        def download_csv(n_clicks: int | None, ProjectChosen: str) -> Any:
            """
            Callback to trigger CSV download for the selected project.

            :param n_clicks: Number of times the download button was clicked
            :type n_clicks: int | None
            :param ProjectChosen: The selected project ID
            :type ProjectChosen: str
            :return: Data for Dash dcc.Download component or no update
            :rtype: Any
            """

            if ProjectChosen is None:
                raise PreventUpdate

            if ctx.triggered_id == "btn_csv":
                FileName = "".join((ProjectChosen,'_ProjectData.csv'))
                df = get_all_data(ProjectChosen)
                if not df.empty:
                    return dcc.send_data_frame(df.to_csv, FileName)  # type: ignore
                
            return dash.no_update

        @self.app.callback(
            Output("download-html", "data"),
            Input("btn_download_html", "n_clicks"),
            Input('ProjectIDs', 'value'),
            Input('plot-select', 'value'),
            prevent_initial_call=True,
        )
        def download_html(n_clicks: int | None, ProjectChosen: str, selected_plots: list[str]) -> Any:
            """
            Callback to build and download a standalone HTML snapshot of the currently shown plots.

            :param n_clicks: Number of times the download button was clicked
            :type n_clicks: int | None
            :param ProjectChosen: The selected project ID
            :type ProjectChosen: str
            :param selected_plots: List of plot keys currently selected
            :type selected_plots: list[str]
            :return: Data for Dash dcc.Download component or no update
            :rtype: Any
            """


            if ctx.triggered_id != "btn_download_html":
                raise PreventUpdate
            
            if ProjectChosen is None:
                raise PreventUpdate

            try:
                
                today_filename = datetime.now().strftime("%Y%m%d")

                comp = FigureComponents(ProjectChosen)

                project_table = comp.generate_table_project()      # carries the last-measured title
                error_table   = comp.generate_table_error()        # None if no errors
                figs          = comp.generate_all_figures_labels(selected_plots)

                parts = []
                if project_table is not None:
                    parts.append(("Project Data", project_table, "export-table"))
                if error_table is not None:
                    parts.append(("Files with Errors", error_table, "export-table"))
                parts += [(title, fig, "export-plot") for title, fig in figs]

                plots_html = []
                for i, (title, fig, cls) in enumerate(parts):
                    # load plotly.js once (first fragment), reference it thereafter
                    frag = pio.to_html(fig, include_plotlyjs=("cdn" if i == 0 else False), full_html=False)
                    plots_html.append(f'<section class="{cls}">\n<h3>{title}</h3>\n{frag}\n</section>')

                body_html = "\n".join(plots_html)

                # Read app CSS to include in the exported HTML
                css_path = Path(__file__).resolve().parent.parent / "assets" / "custom.css"
                css_text = ""
                if css_path.exists():
                    css_text = css_path.read_text(encoding='utf-8')
                full_html = create_full_html(css_text, ProjectChosen, body_html)

                # Return bytes for download
                def _write_html_bytes(bio: Any) -> None:
                    """Writes the full HTML content to the provided binary IO stream.

                    :param bio: file-like object to write bytes to
                    :type bio: Any
                    """
                    bio.write(full_html.encode('utf-8'))

                return dcc.send_bytes(_write_html_bytes, filename=f"{today_filename}_ProjectQC_{ProjectChosen}.html")  # type: ignore

            except Exception as e:
                logger.error("html_export_failed", extra={"error_class": type(e).__name__,
                                                                "error": str(e)}, exc_info=True)
                raise PreventUpdate

        # Generate visibility toggle outputs dynamically from PLOT_CONFIG
        col_outputs = [Output(f'col-{key}', 'style') for key in get_plot_keys()]
        
        @self.app.callback(
            *col_outputs,
            Input('plot-select', 'value')
        )
        def toggle_plots(selected: list[str]) -> tuple[dict[str, str],...]:
            """
            Callback to toggle visibility of plot columns based on user selection.

            :param selected: List of selected plot keys
            :type selected: list[str]
            :return: Tuple of style dicts for each column
            :rtype: tuple[dict[str, str], ...]
            """
            return tuple(
                {} if key in selected else {'display': 'none'}
                for key in get_plot_keys()
            )

        return self.app
   

    def graph_card(self, graph_id: str, label_text: str, className_card: str ="graph-card mb-3") -> dbc.Card:
        """
        Create a Bootstrap Card containing a graph and its title.

        Returns a Bootstrap Card with a loading spinner and an empty Plotly figure as a placeholder.
        The actual figure is provided later by the update_output_div callback. Used for all graphs and tables.

        :param graph_id: The ID for the graph component
        :type graph_id: str
        :param label_text: The label text for the card header
        :type label_text: str
        :param className_card: The CSS class name(s) for the card
        :type className_card: str
        :return: A Bootstrap Card component containing the graph
        :rtype: dbc.Card
        """
        
        fig = go.Figure()
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
                        delay_show = 400
                    ),
                ),
            ],
            className=className_card,
            style={"border": "1px solid #e6e9ef"},
        )
        return card
