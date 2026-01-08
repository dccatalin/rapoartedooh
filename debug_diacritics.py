
from src.utils.i18n import remove_diacritics, _

print(f"Original: Număr PO (Opțional)")
cleaned = remove_diacritics("Număr PO (Opțional)")
print(f"Cleaned: {cleaned}")

print(f"Original: Oraș(e)")
cleaned_city = remove_diacritics("Oraș(e)")
print(f"Cleaned City: {cleaned_city}")

# Check specific problem chars
chars = ['ă', 'ș', 'ț', 'î', 'â', 'ş', 'ţ']
for c in chars:
    print(f"Char {c}: {remove_diacritics(c)}")
