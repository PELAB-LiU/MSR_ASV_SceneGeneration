import pprint
import queue
import threading
from typing import List

import dash
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

from concrete_level.data_parser import EvalDataParser
from concrete_level.models.concrete_scene import ConcreteScene
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData


class DashThread(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True, name="Dash Thread")
        self.data_queue: queue.Queue[ConcreteScene] = queue.Queue()
        self.dp = EvalDataParser()
        self.dirs: List[str] = []
        self.df, self.dirs = self.dp.load_dirs_merged(self.dirs)
        hidden_columns = [
            "best_scene",
            "path",
            "risk_vector",
            "error_message",
            "best_fitness",
            "timestamp",
            "vessel_number",
            "aggregate_strat",
            "random_seed",
            "num_parents_mating",
            "init_method",
            "c_1",
            "c_2",
            "w",
            "crossover_prob",
            "crossover_eta",
            "mutate_prob",
            "mutate_eta",
        ]

        self.app = dash.Dash(__name__)

        # Function to format cells (list or single value)
        def format_cell(value):
            if isinstance(value, list):
                return ", ".join(map(str, value))  # Comma-separated list as string
            return value

        def fetch_data():
            self.df, self.dirs = self.dp.load_dirs_merged(self.dirs)
            # self.df = self.df[self.df['best_scene'].apply(lambda s: not dict(s).get('is_relevant_by_fec', True))]
            return self.df

        self.app.layout = html.Div(
            [
                dcc.Interval(
                    id="interval-component",
                    interval=30
                    * 1000,  # Interval in milliseconds (1 second, only for demo purposes)
                    n_intervals=0,  # Start counting at 0 on page load
                ),
                dcc.Checklist(
                    id="column-checklist",
                    options=[{"label": i, "value": i} for i in self.df.columns],
                    value=[
                        i for i in self.df.columns if i not in hidden_columns
                    ],  # Default visible columns
                    inline=True,
                    style={"fontSize": "22px", "marginRight": "20px"},
                ),
                dcc.Dropdown(
                    id="page-size-dropdown",
                    options=[
                        {"label": str(size), "value": size}
                        for size in [5, 10, 20, 50, 100, 200]
                    ],
                    value=10,  # default value
                    clearable=False,
                ),
                dash_table.DataTable(
                    id="table",
                    data=[],
                    columns=[
                        {"name": i, "id": i}
                        for i in self.df.columns
                        if i not in hidden_columns
                    ],
                    sort_action="native",  # sorting
                    filter_action="native",  # filtering
                    row_selectable="single",  # Allow selecting a single row
                    page_size=10,  # default page size
                    page_current=0,  # current page
                    page_action="native",  # enables pagination
                    selected_rows=[],
                    # Prettify Table
                    style_table={
                        "overflowY": "auto",
                        "width": "100%",
                        "margin": "10px 10px 10px 10px",
                    },
                    style_cell={
                        "textAlign": "center",
                        "padding": "8px",
                        "font_family": "Arial, sans-serif",
                        "font_size": "18px",
                        "backgroundColor": "#f9f9f9",  # light gray background
                        "border": "1px solid #ddd",  # light border
                    },
                    style_header={
                        "backgroundColor": "#4CAF50",  # green header
                        "fontWeight": "bold",
                        "color": "white",
                        "border": "1px solid black",
                        "font_size": "20px",
                    },
                    style_data_conditional=[
                        {
                            "if": {"row_index": "odd"},
                            "backgroundColor": "#f2f2f2",  # Alternate row color (light gray)
                        },
                        {
                            "if": {"row_index": "even"},
                            "backgroundColor": "#ffffff",  # White background for even rows
                        },
                        {
                            "if": {
                                "column_id": "risk_distance",
                            },
                            "backgroundColor": "#e0f7fa",
                            "color": "#00796b",
                            "fontWeight": "bold",
                        },
                        {
                            "if": {
                                "column_id": "best_fitness_index",
                            },
                            "backgroundColor": "#e0f7fa",
                            "color": "#00796b",
                            "fontWeight": "bold",
                        },
                        {
                            "if": {"state": "selected"},  # Styling for the selected row
                            "backgroundColor": "#D6EAF8",
                            "color": "black",
                            "border": "1px solid blue",
                        },
                    ],
                ),
                html.Div(id="total-rows", style={"textAlign": "right"}),
                html.Div(id="selected-row"),
            ]
        )

        @self.app.callback(
            Output("table", "data"),
            Output("total-rows", "children"),
            Input(
                "interval-component", "n_intervals"
            ),  # Trigger on page load or at the interval
        )
        def update_data(n_intervals):
            # Fetch new data (or reload data)
            self.df = fetch_data()
            total_rows = f"Total rows: {len(self.df)}"
            return [
                {col: format_cell(val) for col, val in row.items()}
                for row in self.df.to_dict("records")
            ], total_rows

        @self.app.callback(
            Output("table", "columns"), Input("column-checklist", "value")
        )
        def update_columns(selected_columns):
            # Update the DataTable columns based on the selected checklist
            return [{"name": col, "id": col} for col in selected_columns]

        @self.app.callback(
            Output("table", "page_size"), Input("page-size-dropdown", "value")
        )
        def update_table(page_size):
            return page_size

        # Callback to update the graph based on the selected row
        @self.app.callback(
            Output("selected-row", "children"),
            [Input("table", "selected_rows")],  # Listen to row selection
        )
        def display_selected_row(selected_rows):
            if selected_rows:
                selected_index = selected_rows[0]
                row = self.df.iloc[selected_index]
                eval_data: EvaluationData = EvaluationData.from_dict(row)
                self.data_queue.put(eval_data.best_scene)
                return f"Selected Row:\n{pprint.pformat(dict(sorted(row.to_dict().items())))}"
            return "No row selected"

    def run(self):
        self.app.run(debug=False, use_reloader=False)
