import sys
from pathlib import Path

# Add Proj_01/src directory to sys.path
proj_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(proj_dir))
