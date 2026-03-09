import pandas as pd
import warnings

warnings.filterwarnings('ignore')

file_path = "/Users/catalin/Antigravity/rapoartedooh/samples/FoaieDeParcursDetaliata-7ABB-BC_59-20260304-20260304_5b95c648.xls"

try:
    df = pd.read_excel(file_path)
    print("Successfully read as Excel!")
    print("Columns:", df.columns.tolist())
    print(df.head(5))
except Exception as e:
    print("Error reading as excel:", e)
    
    try:
        dfs = pd.read_html(file_path)
        print("Successfully read as HTML!")
        for i, df in enumerate(dfs):
            print(f"Table {i} shape:", df.shape)
            if df.shape[0] > 1:
                print("Columns:", df.columns.tolist()[:10])
                print(df.head(2))
    except Exception as e2:
        print("Error reading as HTML:", e2)

