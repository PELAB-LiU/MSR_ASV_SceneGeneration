import threading
from typing import List

from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation

from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.trajectories import Trajectories
from visualization.colreg_scenarios.plot_components.plot_component import \
    PlotComponent

TWO_HOURS = 2 * 60 * 60
TWO_MINUTES = 2 * 60

ANIM_REAL_TIME = TWO_HOURS * 2
ANIM_SIM_TIME = TWO_MINUTES / 4

FRAMES_PER_SEC = 25.0
REAL_TIME = 1.0 / FRAMES_PER_SEC


class ScenarioAnimation:

    def speed_up_ratio(self):
        return self.real_time_value / self.sim_time_value

    def anim_max_frames(self):
        return self.sim_time_value * FRAMES_PER_SEC

    def get_sim_time_count(self) -> str:
        real_time = self.anim_frame_counter
        sim_time = real_time / self.speed_up_ratio()
        return f"Simulation time: {round(sim_time)} s, Real time: {round(real_time)} s"

    def __init__(
        self,
        fig: plt.Figure,
        trajectories: Trajectories,
        components: List[PlotComponent],
    ) -> None:
        self.fig = fig
        self.trajectories = trajectories
        self.components = components

        self.real_time_value = ANIM_REAL_TIME
        self.sim_time_value = ANIM_SIM_TIME

        self.trajectories = trajectories

        self.__frame_counter_lock = threading.Lock()
        self.__current_scene_lock = threading.Lock()
        self.reset_anim_frame_counter()
        self.refresh_current_scene(0)

        self.is_anim_paused = True
        self.anim = None
        self.init_anim()

    def refresh_current_scene(self, frame_index: int):
        with self.__current_scene_lock:
            self.__current_scene = self.trajectories.get_scene(frame_index)

    def increment_anim_frame_counter(self):
        with self.__frame_counter_lock:
            self.__anim_frame_counter += 1

    def reset_anim_frame_counter(self):
        with self.__frame_counter_lock:
            self.__anim_frame_counter = 0

    @property
    def anim_frame_counter(self) -> int:
        with self.__frame_counter_lock:
            return self.__anim_frame_counter

    @property
    def current_scene(self) -> ConcreteScene:
        with self.__current_scene_lock:
            return self.__current_scene

    def start(self):
        self.anim = FuncAnimation(
            self.fig,
            self.update_graphs,
            self.update_anim,
            init_func=self.init_anim,
            blit=True,
            interval=int((1 / FRAMES_PER_SEC) * 1000),
            cache_frame_data=False,
        )

    def update_anim(self):
        self.init_anim()
        while self.anim_frame_counter < self.anim_max_frames():
            frame_index = int(
                self.anim_frame_counter * REAL_TIME * self.speed_up_ratio()
            )
            if frame_index < self.trajectories.timespan and not self.is_anim_paused:
                self.refresh_current_scene(frame_index)
                self.increment_anim_frame_counter()
            yield self.current_scene

    def update_graphs(self, scene):
        # self.auto_scale()
        return [
            graph
            for component in self.components
            for graph in component.update(scene)
            if graph.get_visible()
        ]

    def init_anim(self):
        self.reset_anim_frame_counter()
        self.refresh_current_scene(0)
        return [graph for component in self.components for graph in component.reset()]

    # Function to start or pause the animation
    def toggle_anim(self, event):
        if event.key == "down":
            self.init_anim()
            self.is_anim_paused = True
            print("Animation reset")
        elif event.key == "up":
            if self.is_anim_paused:
                if self.anim == None:
                    self.start()
                self.is_anim_paused = False
                print("Animation started")
            else:
                self.is_anim_paused = True
                print("Animation paused")

    def auto_scale(self):
        for ax in self.fig.get_axes():
            # Recalculate the limits based on the current data
            ax.relim()
            # Automatically adjust xlim and ylim
            ax.autoscale_view()
