import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash, ctx
from ProjectQCDashboard.helper.UpdateCSV import  update_df
from ProjectQCDashboard.components.GenerateFig import generate_Fig
from ProjectQCDashboard.helper.common import CreateOutputFilePath
from ProjectQCDashboard.helper.database import query, Database_Call
from ProjectQCDashboard.config.logger import get_configured_logger
from typing import Any, List, Optional, Union
from pathlib import Path

logger = get_configured_logger(__name__)

class AppLayout:
    def __init__(self, mqqc_db_path: Union[str, Path], metadata_db_path: Union[str, Path]) -> None:
        """
        Initialize the application layout with database paths.

        :param mqqc_db_path: Path to the MQQC SQLite database file
        :type mqqc_db_path: Union[str, Path]
        :param metadata_db_path: Path to the metadata SQLite database file
        :type metadata_db_path: Union[str, Path]

        """

        # Set URL base pathname for Apache proxy
        self.app = Dash(__name__, url_base_pathname='/ProjectQCDashboard/')
       
        self.metadata_db_path = metadata_db_path
        
        # Use metadata database for getting project names
        self.metadata_db = Database_Call(self.metadata_db_path)
        self.ProjectIDs = list(self.metadata_db.getProjectNamesDict().keys())
        self.ProjectIDs.sort(reverse=True)  # Sort in place (don't reassign)
      
        self.FileName = ""
        self.OutputFilePath =  ""
        self.df = pd.DataFrame()

        self.markdown_text = '''
                # Project QC Dashboard
                
                ### only Projects measured in the past month available for now
                
                #### Trendlines display the median and standard deviation, or the rolling equivalent when enough measurements have been done
                

                ''' 
           
    def CreateApp(self) -> Any:

        """
        Create the Dash application layout.

        :return: The Dash application layout
        :rtype: Any
        """

        # Load project IDs only when creating the app layout
                 
        logger.info("Creating app layout...")
        self.app.layout = html.Div(children=[
                    html.Div([dcc.Markdown(children=self.markdown_text)]),
                    html.Div([
                        dcc.Dropdown(self.ProjectIDs, value=self.ProjectIDs[0] if self.ProjectIDs else None, id='ProjectIDs')
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    *self.graph_section("Protein", "Protein-graph", "Proteins Identified per day in chosen Project"),
                    *self.graph_section("AllPeptides", "AllPeptides-graph", "Peptide counts by File Type"),
                    *self.graph_section("Intensity.100.", "Int-graph", "Intensity"),
                    *self.graph_section("uniPepCount", "uniPepCount-graph", "Unique Peptide Count"),
                    *self.graph_section("missed.cleavages.percent", "MisCleave-graph", "Missed Cleavages %"),
                    *self.graph_section("MaxPressure_Pump", "MaxPressure_Pump-graph", "Max Pressure (Pump)"),
                    html.Div([
                        html.Button("Download CSV", id="btn_csv"),
                        dcc.Download(id="download-dataframe-csv"),
                    ])
                ])
        @self.app.callback(
            Output(component_id="Protein-graph", component_property='figure'),
            Output(component_id="AllPeptides-graph", component_property='figure'),
            Output(component_id="Int-graph", component_property='figure'),
            Output(component_id="uniPepCount-graph", component_property='figure'),
            Output(component_id="MisCleave-graph", component_property='figure'),
            Output(component_id="MaxPressure_Pump-graph", component_property='figure'),
            
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
                return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
            
            try:
                # Create figure generators and call their CreateFig method
                GenFig = generate_Fig(OutputFilePath)
                protein_fig = GenFig.CreateFig("Protein")
                peptides_fig = GenFig.CreateFig("AllPeptides")
                intensity_fig = GenFig.CreateFig("Intensity.100.")
                unipep_fig = GenFig.CreateFig("uniPepCount")
                cleave_fig = GenFig.CreateFig("missed.cleavages.percent")
                maxpressure_fig = GenFig.CreateFig("MaxPressure_Pump")
                
                return protein_fig, peptides_fig, intensity_fig, unipep_fig, cleave_fig, maxpressure_fig
            
            except Exception as e:
                logger.error(f"Error generating figures: {e}")
                empty_fig = go.Figure()
                return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig 

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

        return self.app

    def graph_section(self, y_label: str, graph_id: str, label_text: str) -> List[Any]:
        """
        Create a graph section for the dashboard.

        :param y_label: The label for the y-axis
        :param graph_id: The ID for the graph component
        :param label_text: The text label for the graph
        :type y_label: str
        :type graph_id: str
        :type label_text: str
        :return: A list containing the graph section components
        :rtype: List[Any]
        """

        if self.df.empty:
            fig = go.Figure()
        else:
            try:
                fig = generate_Fig(self.OutputFilePath).CreateFig(y_label)
            except Exception as e:
                logger.error(f"Error creating initial figure for {y_label}: {e}")
                fig = go.Figure()
        return [
            html.Div(children=[label_text], style={"font-weight": "bold"}),
            dcc.Graph(id=graph_id, figure=fig)
        ]
