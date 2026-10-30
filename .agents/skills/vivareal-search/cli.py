"""VivaReal connector (see tools/grupozap.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from grupozap import main  # noqa: E402

if __name__ == "__main__":
    main("vivareal")
