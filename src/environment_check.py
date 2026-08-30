import platform
import sys

import duckdb
import matplotlib
import numpy
import pandas
import pyarrow
import scipy
import sklearn
import statsmodels


def main():
    print("=" * 60)
    print("QUANT RESEARCH PLATFORM")
    print("Environment Check")
    print("=" * 60)

    print(f"Python:       {sys.version.split()[0]}")
    print(f"Platform:     {platform.platform()}")
    print(f"NumPy:        {numpy.__version__}")
    print(f"pandas:       {pandas.__version__}")
    print(f"SciPy:        {scipy.__version__}")
    print(f"statsmodels:  {statsmodels.__version__}")
    print(f"scikit-learn: {sklearn.__version__}")
    print(f"matplotlib:   {matplotlib.__version__}")
    print(f"DuckDB:       {duckdb.__version__}")
    print(f"PyArrow:      {pyarrow.__version__}")

    print("\nAll core packages imported successfully.")
    print("Environment is ready for quantitative research.")


if __name__ == "__main__":
    main()