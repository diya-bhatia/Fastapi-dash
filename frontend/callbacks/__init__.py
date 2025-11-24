from .calculatedf import register_calculated_fields_callbacks
from .dropdowns import register_dropdown_callbacks
from .rename_callbacks import register_rename_callbacks
from .filters import register_filter_callbacks
from .pivot_callback import register_pivot_table_callbacks
from .chart_callback import register_chart_callbacks
from .publish import register_publish_callbacks
from .dataset import register_dataset_callbacks

def register_all_callbacks(app):
    register_calculated_fields_callbacks(app)
    register_dropdown_callbacks(app)
    register_rename_callbacks(app)
    register_filter_callbacks(app)
    register_pivot_table_callbacks(app)
    register_chart_callbacks(app)
    register_publish_callbacks(app)
    register_dataset_callbacks(app)
