from typing import Optional

from concrete_level.models.trajectory_manager import TrajectoryManager
from visualization.colreg_scenarios.scenario_plot_manager import \
    ScenarioPlotManager
from visualization.dash_thread import DashThread

dash_thread = DashThread()
dash_thread.start()

colreg_plot_manager: Optional[ScenarioPlotManager] = None

# Main loop to listen for data and create windows
while dash_thread.is_alive():
    concrete_scene = dash_thread.data_queue.get()  # Wait for data with a timeout
    colreg_plot_manager = ScenarioPlotManager(TrajectoryManager(concrete_scene))
