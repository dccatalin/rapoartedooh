# Audit Sample Files

Aceste fișiere pot fi folosite pentru a testa funcționalitatea de auditare în pagina de Campanii.

### 📍 Fișier GPS (`sample_gps.csv`)

- **Format**: CSV
- **Câmp cheie**: `distance` (km). Sistemul va însuma această coloană.
- **Notă**: Dacă coloana `distance` lipsește, sistemul va calcula automat 0.1 km (100m) pentru fiecare rând (ping).

### 📺 Fișier VnNox (`sample_vnnox_log.txt`)

- **Format**: TXT / CSV
- **Câmp cheie**: Cuvântul cheie **"PLAY"**.
- **Logica**: Sistemul numără aparițiile cuvântului "PLAY" și calculează orele confirmate pe baza duratei spotului setate în campanie.

---

**Locație fișiere**: `/Users/catalin/Antigravity/rapoartedooh/samples/`
