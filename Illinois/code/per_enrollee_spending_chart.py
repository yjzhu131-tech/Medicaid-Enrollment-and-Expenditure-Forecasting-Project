from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from per_enrollee_spending import build_per_enrollee_spending_chart

build_per_enrollee_spending_chart(project_root, 'Illinois', 'Illinois', 'IL', 'il')
