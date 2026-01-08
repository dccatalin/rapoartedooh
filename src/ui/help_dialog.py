from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTextBrowser, 
                             QDialogButtonBox, QTreeWidget, QTreeWidgetItem, QSplitter)
from PyQt6.QtCore import Qt

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Raportare DOOH - Help")
        self.resize(800, 600)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Navigation Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Topics")
        self.tree.itemClicked.connect(self.on_topic_selected)
        splitter.addWidget(self.tree)
        
        # Content Viewer
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        splitter.addWidget(self.viewer)
        
        splitter.setSizes([200, 600])
        
        # Add Topics
        self.populate_topics()
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def populate_topics(self):
        topics = {
            "Getting Started": "<h1>Getting Started</h1><p>Welcome to Raportare DOOH. This application helps you calculate campaign metrics, costs, and optimize routes.</p>",
            "Campaign Management": {
                "Creating a Campaign": "<h2>Creating a Campaign</h2><p>Click 'New Campaign' and fill in the details: Client Name, Period, and Daily Hours.</p>",
                "Import/Export": "<h2>Import/Export</h2><p>You can export campaigns to JSON/CSV and import them later. Use the 'Export' and 'Import' buttons in the toolbar.</p>"
            },
            "Metodologie Calcul": {
                "Impresii": """
                    <h2>Calculul Impresiilor</h2>
                    <p>Impresiile sunt calculate folosind urmatoarea formula pentru fiecare mod de transport:</p>
                    <ul>
                        <li><b>Auto:</b> Trafic Auto * Grad Ocupare (1.65) * Factor Vizibilitate * Share of Voice</li>
                        <li><b>Pietoni:</b> (Trafic Pietonal + Biciclisti) * Factor Vizibilitate * Share of Voice</li>
                    </ul>
                    <p><b>Factori Cheie:</b></p>
                    <ul>
                        <li><b>Trafic Baza:</b> Date istorice per oras (INS/OpenData) ajustate orar.</li>
                        <li><b>Modal Split:</b> Auto (~35%), Pietonal (~27%), Biciclete (~4%), Transport Public (~34%).</li>
                        <li><b>Evenimente:</b> Multiplicatori aplicati in zilele cu evenimente speciale (ex: targuri, concerte).</li>
                    </ul>
                """,
                "Reach & OTS": """
                    <h2>Reach si OTS</h2>
                    <p><b>Reach (Acoperire Unica):</b> Numarul estimat de persoane unice care au vazut campania.</p>
                    <p><i>Formula:</i> Populatie Activa * Rata Unicitate</p>
                    <p>Rata Unicitate depinde de acoperirea traseului (nr. de bucle realizate), maxim 60% din populatia activa.</p>
                    <br>
                    <p><b>OTS (Opportunity To See):</b> Frecventa medie de vizualizare.</p>
                    <p><i>Formula:</i> Total Impresii / Reach</p>
                """,
                "Distante si Rute": """
                    <h2>Distante si Rute</h2>
                    <p><b>Distanta Totala:</b> Calculata pe baza vitezei medii si orelor active, sau preluata din traseu GPX/KML.</p>
                    <p><b>Ore Efective:</b> Ore Totale - Timp Stationare (10 min/ora default).</p>
                    <p><b>Bucle Traseu:</b> Distanta Totala / Distanta Medie Naveta (8km).</p>
                """,
                "Factori de Eficienta": """
                    <h2>Factori de Eficienta</h2>
                    <p><b>Share of Voice (SOV):</b></p>
                    <ul>
                        <li><b>Standard:</b> Durata Spot / Durata Loop (ex: 10s / 60s = 16.6%)</li>
                        <li><b>Exclusiv:</b> 100% (Spotul ruleaza continuu)</li>
                    </ul>
                    <p><b>Factor de Vizibilitate:</b></p>
                    <ul>
                        <li><b>Standard:</b> 70% (rata medie de observare in trafic)</li>
                        <li><b>Exclusiv:</b> 100% (vizibilitate maxima datorita expunerii constante)</li>
                    </ul>
                """
            },
            "ROI & Costuri": {
                "Calcul ROI": "<h2>ROI (Return on Investment)</h2><p>ROI = ((Venit Estimat - Cost Total) / Cost Total) * 100</p>",
                "CPM": "<h2>CPM (Cost Per Mille)</h2><p>Costul pentru 1000 de impresii. <i>Formula:</i> (Cost Total / Impresii Totale) * 1000</p>"
            },
            "Route Optimization": {
                "Traffic Score": "<h2>Traffic Score</h2><p>A score from 0-100 based on population, traffic estimates, and POI density.</p>",
                "Spatial Logic": "<h2>Spatial Logic</h2><p>The optimizer uses a 'Nearest Neighbor' algorithm to suggest the most efficient route order.</p>"
            }
        }
        
        self.add_items(self.tree.invisibleRootItem(), topics)
        
    def add_items(self, parent, data):
        for key, value in data.items():
            item = QTreeWidgetItem(parent, [key])
            if isinstance(value, dict):
                self.add_items(item, value)
            else:
                item.setData(0, Qt.ItemDataRole.UserRole, value)
                
    def on_topic_selected(self, item, column):
        content = item.data(0, Qt.ItemDataRole.UserRole)
        if content:
            self.viewer.setHtml(content)
