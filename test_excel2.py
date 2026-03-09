import sys
import src.utils.gps_parser as parser

file_path = "/Users/catalin/Antigravity/rapoartedooh/samples/FoaieDeParcursDetaliata-7ABB-BC_59-20260304-20260304_5b95c648.xls"

try:
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    
    res = parser.parse_gps_log(file_bytes, filename="FoaieDeParcursDetaliata.xls")
    print(res)
except Exception as e:
    print("Error:", e)

