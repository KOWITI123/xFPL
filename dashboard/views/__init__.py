"""
Views package for xFPL Streamlit dashboard.
"""
try:
    from .scouting import render_scouting_view
    from .regression import render_regression_view
    from .fixtures import render_fixtures_view
    from .call_log import render_call_log_view
    from .profile import render_profile_view
    from .compare import render_compare_view
    from .planner import render_planner_view
except ImportError:
    from views.scouting import render_scouting_view
    from views.regression import render_regression_view
    from views.fixtures import render_fixtures_view
    from views.call_log import render_call_log_view
    from views.profile import render_profile_view
    from views.compare import render_compare_view
    from views.planner import render_planner_view

__all__ = [
    "render_scouting_view",
    "render_regression_view",
    "render_fixtures_view",
    "render_call_log_view",
    "render_profile_view",
    "render_compare_view",
    "render_planner_view",
]
