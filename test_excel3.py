import pandas as pd
import warnings
warnings.filterwarnings('ignore')

file_path = "/Users/catalin/Antigravity/rapoartedooh/samples/FoaieDeParcursDetaliata-7ABB-BC_59-20260304-20260304_5b95c648.xls"
df = pd.read_excel(file_path)
print("Columns:", df.columns.tolist())
print(df.head(2))
