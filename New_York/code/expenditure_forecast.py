from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from state_forecasts import build_expenditure_forecast

build_expenditure_forecast(project_root, 'New_York', 'New York', 'NY', 'ny')
