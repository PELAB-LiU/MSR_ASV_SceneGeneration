import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Dict, List, Optional, Tuple

from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)

from concrete_level.models.concrete_actors import ConcreteActor
from concrete_level.models.trajectory_manager import TrajectoryManager
from utils.colors import light_colors
from utils.file_system_utils import EXPORTED_PLOTS_FOLDER
from visualization.colreg_scenarios.scenario_animation import (ANIM_REAL_TIME,
                                                               ANIM_SIM_TIME,
                                                               TWO_HOURS,
                                                               TWO_MINUTES)
from visualization.colreg_scenarios.scenario_metrics_plot import \
    ScenarioMetricsPlot
from visualization.colreg_scenarios.scenario_plot import ScenarioPlot


class StandaloneCheckbox:
    def __init__(
        self,
        master,
        artists: List[plt.Artist],
        color,
        init_checked: bool,
        fig: Optional[plt.Figure] = None,
        text="",
    ):
        self.artists = artists
        self.text = text
        self.fig = fig
        self.value = tk.BooleanVar(
            master=master, value=init_checked
        )  # BooleanVar linked to checkbox
        self.checkbox = tk.Checkbutton(
            master,
            variable=self.value,  # Correctly linked variable
            onvalue=True,
            text=text,
            offvalue=False,
            command=self.on_click,  # Calls show_selection when clicked
            background=color,
        )
        self.checkbox.pack(side=tk.TOP, anchor="w", fill=tk.NONE)
        self.set_state(init_checked)

    def on_click(self):
        if self.fig is not None:
            self.set_state(self.value.get())
            self.fig.canvas.draw()

    def set_state(self, state: bool):
        self.value.set(state)
        for a in self.artists:
            a.set_visible(state)


class CheckboxArray:
    def __init__(self, master, text: str, fig: plt.Figure):
        self.fig = fig
        self.managed_checkboxes: List[Checkbox] = []
        self.value = tk.BooleanVar(
            master=master, value=False
        )  # BooleanVar linked to checkbox
        self.checkbox = tk.Checkbutton(
            master,
            text=text,
            variable=self.value,  # Correctly linked variable
            onvalue=True,
            offvalue=False,
            command=self.on_click,  # Calls show_selection when clicked,
            background="grey",
        )
        self.checkbox.pack(side=tk.TOP, anchor="w")

    def add(self, cb):
        self.managed_checkboxes.append(cb)
        self.notify()

    def on_click(self):
        state = self.value.get()
        for cb in self.managed_checkboxes:
            cb.set_state(state)
        self.fig.canvas.draw()

    def notify(self):
        all_false = all(cb.value.get() == False for cb in self.managed_checkboxes)
        self.value.set(not all_false)
        self.fig.canvas.draw()


class Checkbox(StandaloneCheckbox):
    def __init__(
        self,
        master,
        artists: List[plt.Artist],
        checkbox_array: CheckboxArray,
        color: str,
        init_checked: bool,
    ):
        super().__init__(master, artists, color, init_checked)
        self.checkbox_array = checkbox_array
        self.checkbox_array.add(self)

    def on_click(self):
        self.set_state(self.value.get())
        self.checkbox_array.notify()


class ScenarioPlotManager:
    def __init__(self, trajectory_manager: TrajectoryManager):
        self.trajectory_manger = trajectory_manager
        self.colreg_plot = ScenarioPlot(trajectory_manager)
        self.metrics_plot = None
        self.root = tk.Tk()
        self.root.resizable(True, True)

        self.sim_time_update_id = None
        self.root.option_add("*Font", ("Times New Roman", 14))

        self.root.title("COLREG situation visualizer")

        # CANVAS FRAME
        self.canvas_frame = tk.Frame(master=self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        ## PLOT FRAME
        self.plot_frame = tk.Frame(master=self.canvas_frame)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = FigureCanvasTkAgg(self.colreg_plot.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # TOOLBAR FRAME
        self.toolbar_frame = tk.Frame(master=self.root, height=50)
        self.toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.toolbar_frame.pack_propagate(False)
        ## SLIDERS
        self.real_time_slider = self.create_slider(
            "Real time:", 10, TWO_HOURS * 4, ANIM_REAL_TIME, 10, self.get_anim_real_time
        )
        self.sim_time_slider = self.create_slider(
            "Sim time:", 10, TWO_MINUTES, ANIM_SIM_TIME, 10, self.get_anim_sim_time
        )
        ## TOOLBAR
        self.navigation_frame = tk.Frame(self.toolbar_frame)
        self.navigation_frame.pack(fill=tk.BOTH, side=tk.LEFT)
        self.navigation_toolbar = NavigationToolbar2Tk(
            self.canvas, self.navigation_frame
        )
        self.navigation_toolbar.update()
        self.navigation_toolbar.pack(fill=tk.BOTH, side=tk.LEFT)

        ## PLOT SELECTION
        self.plot_options = ["Scenario", "Metrics"]
        self.selected_plot = tk.StringVar()
        self.selected_plot.set(self.plot_options[0])  # Set the default value
        # Create the dropdown menu
        self.plot_dropdown = tk.OptionMenu(
            self.toolbar_frame,
            self.selected_plot,
            *self.plot_options,
            command=self.on_select_plot,
        )
        self.plot_dropdown.pack(side=tk.LEFT, padx=5)

        self.to_pdf_button = tk.Button(
            self.toolbar_frame, text="PDF", command=self.to_pdf
        )
        self.to_pdf_button.pack(side=tk.LEFT, padx=5)

        ## HIDE BUTTON
        self.hide_button = tk.Button(
            self.toolbar_frame, text="Hide control", command=self.hide_control
        )
        self.hide_button.pack(side=tk.LEFT, padx=5)

        ## EXIT BUTTONS
        exit_button = tk.Button(
            self.toolbar_frame, text="Exit", command=self.exit_application
        )
        exit_button.pack(side=tk.RIGHT, padx=5)
        continue_button = tk.Button(
            self.toolbar_frame, text="Continue", command=self.continue_application
        )
        continue_button.pack(side=tk.RIGHT, padx=5)

        ## CONTROL FRAME
        self.control_frame = tk.Frame(master=self.canvas_frame, width=70)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)

        self.add_control()
        self.root.wait_window()

    def add_control(self):
        ### TIME CONTROL
        self.time_control_frame = tk.Frame(self.control_frame, background="white")
        self.time_control_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.time_label = tk.Label(
            master=self.time_control_frame,
            text=self.colreg_plot.animation.get_sim_time_count(),
            background="white",
            width=30,
        )
        self.time_label.pack(side=tk.TOP, anchor="w", fill=tk.NONE)
        self.update_sim_time()

        ### ACTOR INFO FRAME
        self.actor_info_frame = tk.Frame(self.control_frame, background="white")
        self.actor_info_frame.pack(side=tk.TOP, fill=tk.BOTH, pady=(10, 0), expand=True)
        #### ACTOR INFOS
        self.actor_info_columns: List[tk.Frame] = []
        col = self.create_actor_info_col("grey")
        actors_label = tk.Label(master=col, text="Attribute", background="grey")
        actors_label.pack(side=tk.TOP, fill=tk.NONE, pady=(0, 5))
        for actor in self.trajectory_manger.logical_scenario.actor_variables:
            col = self.create_actor_info_col(light_colors[actor.id])
            actors_label = tk.Label(
                master=col, text=rf"{actor.name}", background=light_colors[actor.id]
            )
            actors_label.pack(side=tk.TOP, fill=tk.NONE, pady=(0, 5))

        self.actor_info_labels = self.create_actor_info_labels()
        self.update_actor_info_labels()

        #### LEGEND CHECKBOX
        self.legend_frame = tk.Frame(self.control_frame)
        self.legend_frame.pack(side=tk.TOP, fill=tk.NONE, pady=(10, 0), expand=True)
        StandaloneCheckbox(
            self.legend_frame,
            self.colreg_plot.legend_component.graphs,
            "white",
            False,
            fig=self.colreg_plot.fig,
            text="Legend",
        )

        ### ACTOR CONTROL
        self.actor_control_frame = tk.Frame(self.control_frame)
        self.actor_control_frame.pack(
            side=tk.TOP, fill=tk.NONE, pady=(0, 0), expand=True
        )

        #### ACTOR CHECKBOXES
        self.actor_control_columns: List[tk.Frame] = []
        col = self.create_actor_control_col("grey")
        actors_label = tk.Label(master=col, text="Component", background="grey")
        actors_label.pack(side=tk.TOP, fill=tk.NONE, pady=(0, 5))
        for actor in self.trajectory_manger.logical_scenario.actor_variables:
            col = self.create_actor_control_col(light_colors[actor.id])
            actors_label = tk.Label(
                master=col, text=rf"{actor.name}", background=light_colors[actor.id]
            )
            actors_label.pack(side=tk.TOP, fill=tk.NONE, pady=(0, 5))

        self.create_actor_checkbox_row(
            [self.colreg_plot.ship_markings_component.ship_dot_graphs], "Dot"
        )
        self.create_actor_checkbox_row(
            [self.colreg_plot.ship_markings_component.velocity_graphs], "Velocity"
        )
        self.create_actor_checkbox_row(
            [self.colreg_plot.ship_markings_component.radius_graphs], "Radius"
        )
        self.create_actor_checkbox_row(
            [self.colreg_plot.ship_image_component.image_graphs], "Image"
        )
        self.create_actor_checkbox_row(
            [self.colreg_plot.ship_image_component.traj_line_graphs], "Traj"
        )
        self.create_actor_checkbox_row(
            self.colreg_plot.angle_circle_component.graphs_by_vessel, "c"
        )
        self.create_actor_checkbox_row(
            self.colreg_plot.centered_angle_circle_component.graphs_by_vessel,
            "C",
            False,
        )

        ### COLREG CONTROL
        self.rel_control_frame = tk.Frame(self.control_frame)
        self.rel_control_frame.pack(
            side=tk.TOP, fill=tk.NONE, pady=(10, 0), expand=True
        )

        #### CORLEG CHECKBOXES
        self.rel_control_columns: List[tk.Frame] = []
        col = self.create_colreg_control_col("grey")
        rel_label = tk.Label(master=col, text="Component", background="grey")
        rel_label.pack(side=tk.TOP, fill=tk.NONE, pady=(0, 5))
        self.all_actor_pairs = (
            self.trajectory_manger.scenario.concrete_scene.all_vessel_pair_combinations_with_obstacles
        )
        for actor1, actor2 in self.all_actor_pairs:
            col = self.create_colreg_control_col(light_colors[actor2.id])
            rel_label = tk.Label(
                master=col,
                text=rf"{self.trajectory_manger.scenario.get_actor_name(actor1)} → {self.trajectory_manger.scenario.get_actor_name(actor2)}",
                background=light_colors[actor1.id],
            )
            rel_label.bind(
                "<Button-1>",
                lambda event, a1=actor1, a2=actor2: self.show_actor_info(a1, a2),
            )
            rel_label.pack(side=tk.TOP, fill=tk.NONE, pady=(0, 5))

        self.create_relation_checkbox_row(
            self.colreg_plot.distance_component.graphs_by_rels, "Dist", True
        )
        self.create_relation_checkbox_row(
            self.colreg_plot.vo_cone_component.graphs_by_rels[:1], "VO vec", False
        )
        self.create_relation_checkbox_row(
            self.colreg_plot.vo_cone_component.graphs_by_rels[1:], "VO cone", False
        )
        self.create_relation_checkbox_row(
            self.colreg_plot.add_vo_cone_component.graphs_by_rels, "VO calc", False
        )
        self.create_relation_checkbox_row(
            [self.colreg_plot.prime_component.p12_vec_graphs], "P12", False
        )
        self.create_relation_checkbox_row(
            [self.colreg_plot.prime_component.p21_vec_graphs], "P21", False
        )

    def show_actor_info(self, actor1: ConcreteActor, actor2: ConcreteActor):
        """Create a custom, wider message window."""
        var1 = self.trajectory_manger.scenario.to_variable(actor1)
        var2 = self.trajectory_manger.scenario.to_variable(actor2)

        popup = tk.Toplevel()
        popup.title(f"{var1.name} → {var2.name}")
        popup.geometry("500x500")  # Set custom width and height
        popup.resizable(True, True)

        geo_props_str = "\n".join(
            [
                f"{str(key)}: {str(value)}"
                for key, value in self.trajectory_manger.scenario.evaluation_cache.get_props(
                    var1, var2
                ).__dict__.items()
            ]
        )
        text = f"""
        Information about: {actor1} → {actor2}
        
        {self.trajectory_manger.scenario.penalty.pretty_info((var1, var2))}
        
        {self.trajectory_manger.scenario.penalty.pretty_info((var2, var1))}
        
        {geo_props_str}
        
        """

        label = tk.Label(
            popup, text=text, font=("Arial", 12), anchor="w", justify="left"
        )
        label.pack(pady=20, padx=20)

        close_button = tk.Button(popup, text="OK", command=popup.destroy)
        close_button.pack(pady=10)

        popup.transient()  # Make it a child window
        popup.grab_set()

    def create_actor_checkbox_row(
        self,
        plot_components: List[Dict[ConcreteActor, plt.Artist]],
        text: str,
        init_checked=True,
    ):
        for pc in plot_components:
            if len(self.actor_control_columns) != len(pc) + 1:
                raise Exception("data and column dimensions do not match!")

        cb_array = CheckboxArray(
            self.actor_control_columns[0], text, self.colreg_plot.fig
        )
        actor_columns = self.actor_control_columns[1:]
        for i, actor in enumerate(self.trajectory_manger.concrete_scene.actors):
            Checkbox(
                actor_columns[i],
                [cp[actor] for cp in plot_components],
                cb_array,
                light_colors[actor.id],
                init_checked,
            )

    def create_relation_checkbox_row(
        self,
        plot_components: List[Dict[Tuple[ConcreteActor, ConcreteActor], plt.Artist]],
        text: str,
        init_checked=True,
    ):
        for pc in plot_components:
            if len(self.rel_control_columns) != len(pc) + 1:
                raise Exception("data and column dimensions do not match!")

        cb_array = CheckboxArray(
            self.rel_control_columns[0], text, self.colreg_plot.fig
        )
        colreg_columns = self.rel_control_columns[1:]
        for i, (actor1, actor2) in enumerate(self.all_actor_pairs):
            Checkbox(
                colreg_columns[i],
                [cp[(actor1, actor2)] for cp in plot_components],
                cb_array,
                light_colors[actor1.id],
                init_checked,
            )

    def create_actor_control_col(self, color):
        col = tk.Frame(self.actor_control_frame, background=color)
        col.pack(side=tk.LEFT, fill=tk.NONE, expand=True)
        self.actor_control_columns.append(col)
        return col

    def create_actor_info_col(self, color):
        col = tk.Frame(self.actor_info_frame, background=color)
        col.pack(side=tk.LEFT, fill=tk.NONE, expand=True)
        self.actor_info_columns.append(col)
        return col

    def create_colreg_control_col(self, color):
        col = tk.Frame(self.rel_control_frame, background=color)
        col.pack(side=tk.LEFT, fill=tk.NONE, expand=True)
        self.rel_control_columns.append(col)
        return col

    def create_slider(self, label, min_val, max_val, init_val, step_value, command):
        label = tk.Label(self.toolbar_frame, text=label)
        label.pack(side=tk.LEFT)

        slider = tk.Scale(
            self.toolbar_frame,
            from_=min_val,
            to=max_val,
            orient="horizontal",
            resolution=step_value,
            command=command,
        )
        slider.set(init_val)
        slider.pack(fill=tk.BOTH, side=tk.LEFT)
        return slider

    def get_anim_real_time(self, event):
        self.colreg_plot.animation.real_time_value = self.real_time_slider.get()

    def get_anim_sim_time(self, event):
        self.colreg_plot.animation.sim_time_value = self.sim_time_slider.get()

    def update_sim_time(self):
        if not self.root.winfo_exists():
            return
        # Fetch new data
        self.time_label.config(text=self.colreg_plot.animation.get_sim_time_count())
        # Schedule the next update
        self.control_frame.after(250, self.update_sim_time)

    def update_actor_info_labels(self):
        if not self.root.winfo_exists():
            return
        actor_infos = self.get_actor_infos()
        for i, actor in enumerate(
            self.trajectory_manger.logical_scenario.actor_variables
        ):
            for j, info in enumerate(actor_infos[actor.id]):
                self.actor_info_labels[i][j].config(text=info)
        self.control_frame.after(50, self.update_actor_info_labels)

    def exit_application(self):
        if self.root and self.root.winfo_exists():
            self.root.destroy()
            self.root.quit()
        os._exit(0)

    def continue_application(self):
        if self.root and self.root.winfo_exists():
            self.root.destroy()
            self.root.quit()

    def to_pdf(self):
        file_name = (
            f'{self.selected_plot.get()}_{datetime.now().isoformat().replace(":","-")}'
        )
        self.canvas.figure.savefig(
            f"{EXPORTED_PLOTS_FOLDER}/{file_name}.svg",
            format="svg",
            bbox_inches="tight",
            dpi=350,
        )
        self.canvas.figure.savefig(
            f"{EXPORTED_PLOTS_FOLDER}/{file_name}.pdf",
            format="pdf",
            bbox_inches="tight",
            dpi=350,
        )
        print("image saved")

    def on_select_plot(self, value):
        if value == "Scenario":
            plot = self.colreg_plot
        elif value == "Metrics":
            if self.metrics_plot is None:
                self.metrics_plot = ScenarioMetricsPlot(self.trajectory_manger)
            plot = self.metrics_plot
        else:
            raise Exception("Not implemented plot.")
        self.navigation_toolbar.destroy()
        self.canvas.get_tk_widget().destroy()

        self.canvas = FigureCanvasTkAgg(plot.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.navigation_toolbar = NavigationToolbar2Tk(
            self.canvas, self.navigation_frame
        )
        self.navigation_toolbar.update()
        self.navigation_toolbar.pack(fill=tk.BOTH, side=tk.LEFT)

    def hide_control(self):
        if self.hide_button["text"] == "Hide control":
            self.control_frame.pack_forget()  # Hide the frame
            self.hide_button.config(text="Show control")
        elif self.hide_button["text"] == "Show control":
            self.control_frame.pack(
                side=tk.TOP, fill=tk.NONE, pady=(10, 0), expand=True
            )
            self.hide_button.config(text="Hide control")

    def create_actor_info_labels(self) -> List[List[tk.Label]]:
        tk.Label(
            master=self.actor_info_columns[0], text="Type", background="grey"
        ).pack(side=tk.TOP, fill=tk.NONE)
        tk.Label(
            master=self.actor_info_columns[0], text="Length (m)", background="grey"
        ).pack(side=tk.TOP, fill=tk.NONE)
        tk.Label(
            master=self.actor_info_columns[0], text="Radius (m)", background="grey"
        ).pack(side=tk.TOP, fill=tk.NONE)
        tk.Label(
            master=self.actor_info_columns[0], text="Position (m)", background="grey"
        ).pack(side=tk.TOP, fill=tk.NONE)
        tk.Label(
            master=self.actor_info_columns[0], text="Heading (rad)", background="grey"
        ).pack(side=tk.TOP, fill=tk.NONE)
        tk.Label(
            master=self.actor_info_columns[0], text="Speed (m/s)", background="grey"
        ).pack(side=tk.TOP, fill=tk.NONE)
        actor_infos = self.get_actor_infos()
        actor_info_labels = []
        actor_info_columns = self.actor_info_columns[1:]
        for i, var in enumerate(
            self.trajectory_manger.logical_scenario.actor_variables
        ):
            actor_info_label_list: List[tk.Label] = []
            actor_info_labels.append(actor_info_label_list)
            for info in actor_infos[var.id]:
                actor_info_label = tk.Label(
                    master=actor_info_columns[i],
                    text=info,
                    background=light_colors[var.id],
                    width=16,
                )
                actor_info_label.pack(side=tk.TOP, fill=tk.NONE)
                actor_info_label_list.append(actor_info_label)
        return actor_info_labels

    def get_actor_infos(self) -> Dict[int, List[str]]:
        actor_infos: Dict[int, List[str]] = {}
        for (
            actor,
            state,
        ) in self.colreg_plot.animation.current_scene.sorted_actor_states:
            length = 0 if not actor.is_vessel else actor.length
            actor_infos[actor.id] = [
                f"{actor.type}",
                f"{length:.2f}",
                f"{actor.radius:.2f}",
                f"({state.x:.2f}, {state.y:.2f})",
                f"{state.heading:.2f}",
                f"{state.speed:.2f}",
            ]
        return actor_infos
