"""
Proof of Play (PoP) Annex Report Generator
===========================================
Generates a standalone PDF annex with:
  - Per-spot VnNox table (Media Name, Screen, Plays, Duration, Date Range)
  - GPS Route Map (one per day, colored polylines)

This is a third, independent report type (report_type='pop_annex').
"""

import os
import datetime
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (Paragraph, Spacer, Image, Table,
                                TableStyle, PageBreak, SimpleDocTemplate)
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from src.reporting.report_generator import ReportGenerator
from src.data.company_settings import CompanySettings
from src.data.report_storage import ReportStorage
from src.utils.i18n import _, remove_diacritics


class PopAnnexReportGenerator(ReportGenerator):
    """Generates the optional Proof-of-Play Annex PDF."""

    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.company_settings = CompanySettings()
        self.report_storage = ReportStorage()

    def generate_pop_annex(self, campaign_data, include_map=True,
                           include_spots=True, include_photos=True, output_dir=None) -> str:
        """
        Generate the PoP Annex PDF.

        Parameters
        ----------
        campaign_data   : dict – full campaign dict including audited_data
        include_map     : bool – embed GPS route map
        include_spots   : bool – embed VnNox spot table
        output_dir      : str | None – target directory

        Returns
        -------
        str – absolute path to the generated PDF
        """
        client_clean = remove_diacritics(
            campaign_data.get('client_name', 'Client')).replace(' ', '_')
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"anexa_pop_{client_clean}_{timestamp}.pdf"
        output_path = (
            os.path.join(output_dir, filename)
            if output_dir and os.path.exists(output_dir)
            else self._get_report_path(filename)
        )

        self._build_pdf(campaign_data, output_path,
                        include_map=include_map, include_spots=include_spots,
                        include_photos=include_photos)
        self._open_report(output_path)

        # Persist metadata
        try:
            self.report_storage.save_report_metadata(
                campaign_id=campaign_data['id'],
                report_type='pop_annex',
                file_path=output_path,
                file_name=filename,
                frozen_data={
                    'include_map': include_map,
                    'include_spots': include_spots,
                    'include_photos': include_photos,
                }
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to save PoP annex history: {e}")

        return output_path

    # ------------------------------------------------------------------
    # Internal PDF builder
    # ------------------------------------------------------------------

    def _build_pdf(self, data, output_path, include_map, include_spots, include_photos):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        accent = colors.HexColor('#0d47a1')

        # --- Header --------------------------------------------------
        settings = self.company_settings.get_settings() or {}
        logo_path = settings.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            logo = Image(logo_path, width=1.8 * inch, height=0.9 * inch)
            logo.hAlign = 'LEFT'
            story.append(logo)

        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"<b><font size=16 color={accent.hexval()}>"
            + remove_diacritics(_("ANEXA – PROOF OF PLAY"))
            + "</font></b>",
            self.styles['Title']
        ))
        story.append(Paragraph(
            f"<font size=9 color=grey>"
            + remove_diacritics(_(
                "Validare executie campanie prin date GPS si VnNox Play Logs"))
            + "</font>",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 16))

        # --- Campaign identification ----------------------------------
        camp_rows = [
            [Paragraph(f"<b>{remove_diacritics(_('Client'))}:</b>", self.styles['Normal']),
             Paragraph(remove_diacritics(data.get('client_name', '-')), self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Campanie'))}:</b>", self.styles['Normal']),
             Paragraph(remove_diacritics(data.get('campaign_name', '-')), self.styles['Normal'])],
            [Paragraph(f"<b>{remove_diacritics(_('Perioada'))}:</b>", self.styles['Normal']),
             Paragraph(
                 f"{data['start_date'].strftime('%d.%m.%Y') if hasattr(data.get('start_date'), 'strftime') else str(data.get('start_date', '-'))} – "
                 f"{data['end_date'].strftime('%d.%m.%Y') if hasattr(data.get('end_date'), 'strftime') else str(data.get('end_date', '-'))}",
                 self.styles['Normal']
             )],
            [Paragraph(f"<b>{remove_diacritics(_('Generat la'))}:</b>", self.styles['Normal']),
             Paragraph(datetime.datetime.now().strftime('%d.%m.%Y %H:%M'), self.styles['Normal'])],
        ]
        t_camp = Table(camp_rows, colWidths=[1.8 * inch, 4.7 * inch])
        t_camp.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_camp)
        story.append(Spacer(1, 20))

        aud_data = data.get('audited_data', {})
        vnnox_imports = aud_data.get('vnnox_imports', [])
        gps_imports = aud_data.get('gps_imports', [])

        # -----------------------------------------------------------------
        # SECTION A: VnNox Spot Table
        # -----------------------------------------------------------------
        if include_spots and vnnox_imports:
            story.append(Paragraph(
                "<b>A. " + remove_diacritics(_("Detalii Difuzare VnNox")) + "</b>",
                self.styles['Heading2']
            ))
            story.append(Spacer(1, 6))

            # Summary per import file
            for v_imp in vnnox_imports:
                story.append(Paragraph(
                    f"<b>{remove_diacritics(_('Fisier'))}: {v_imp.get('filename', 'N/A')}</b>"
                    f"  |  {v_imp.get('spots', 0):,} {remove_diacritics(_('spoturi'))}"
                    f"  |  {v_imp.get('hours', 0):.2f} h",
                    ParagraphStyle('FileHdr', parent=self.styles['Normal'],
                                   fontSize=9, textColor=colors.HexColor('#1565c0'))
                ))
                spots = v_imp.get('spots_summary', [])
                if spots:
                    spot_rows = [[
                        Paragraph(f"<b>{remove_diacritics(_('Spot / Media'))}</b>", self.styles['Normal']),
                        Paragraph(f"<b>{remove_diacritics(_('Ecran'))}</b>", self.styles['Normal']),
                        Paragraph(f"<b>{remove_diacritics(_('Play-uri'))}</b>", self.styles['Normal']),
                        Paragraph(f"<b>{remove_diacritics(_('Durata'))}</b>", self.styles['Normal']),
                        Paragraph(f"<b>{remove_diacritics(_('Perioada'))}</b>", self.styles['Normal']),
                    ]]
                    for sp in spots:
                        hrs = sp.get('total_hours', 0)
                        dur_str = f"{int(sp.get('total_seconds', 0)//3600)}h {int((sp.get('total_seconds', 0)%3600)//60)}m"
                        period = f"{sp.get('date_start', '-')} / {sp.get('date_end', '-')}"
                        spot_rows.append([
                            Paragraph(remove_diacritics(sp.get('media_name', '-')), self.styles['Normal']),
                            Paragraph(remove_diacritics(sp.get('screen', '-')), self.styles['Normal']),
                            Paragraph(f"{sp.get('plays', 0):,}", self.styles['Normal']),
                            Paragraph(dur_str, self.styles['Normal']),
                            Paragraph(period, self.styles['Normal']),
                        ])
                    t_spots = Table(spot_rows, colWidths=[2.2 * inch, 1.0 * inch, 0.7 * inch, 0.9 * inch, 1.7 * inch])
                    t_spots.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), accent),
                        ('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('PADDING', (0, 0), (-1, -1), 5),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                         [colors.white, colors.HexColor('#e8eaf6')]),
                    ]))
                    story.append(t_spots)
                story.append(Spacer(1, 14))

        # -----------------------------------------------------------------
        # SECTION B: GPS Route Map
        # -----------------------------------------------------------------
        if include_map and gps_imports:
            story.append(PageBreak())
            story.append(Paragraph(
                "<b>B. " + remove_diacritics(_("Harta Traseului GPS")) + "</b>",
                self.styles['Heading2']
            ))
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                remove_diacritics(_(
                    "Traseele de mai jos sunt generate din punctele GPS colectate. "
                    "Fiecare culoare reprezinta o zi distincta de campanie."
                )),
                self.styles['Normal']
            ))
            story.append(Spacer(1, 10))

            # Merge all GPS points from all imports, add a 'import_date' field
            all_points = []
            for g_imp in gps_imports:
                pts = g_imp.get('gps_points', [])
                date_label = g_imp.get('date_start', '')
                for pt in pts:
                    if pt.get('timestamp'):
                        all_points.append(pt)
                    else:
                        all_points.append({**pt, 'timestamp': date_label + 'T00:00:00'})

            if all_points:
                try:
                    from src.utils.map_generator import generate_route_map
                    map_png = generate_route_map(all_points)
                    if map_png and os.path.exists(map_png):
                        story.append(Image(map_png, width=6.5 * inch, height=5.2 * inch))
                except Exception as e:
                    story.append(Paragraph(
                        f"<i>{remove_diacritics(_('Harta nu a putut fi generata'))}: {e}</i>",
                        self.styles['Normal']
                    ))

            # GPS summary table per import
            gps_rows = [[
                Paragraph(f"<b>{remove_diacritics(_('Fisier'))}</b>", self.styles['Normal']),
                Paragraph(f"<b>{remove_diacritics(_('Distanta'))}</b>", self.styles['Normal']),
                Paragraph(f"<b>{remove_diacritics(_('Pings'))}</b>", self.styles['Normal']),
                Paragraph(f"<b>{remove_diacritics(_('Perioada'))}</b>", self.styles['Normal']),
            ]]
            for g_imp in gps_imports:
                gps_rows.append([
                    Paragraph(remove_diacritics(g_imp.get('filename', '-')), self.styles['Normal']),
                    Paragraph(f"{g_imp.get('distance', 0):.2f} km", self.styles['Normal']),
                    Paragraph(f"{g_imp.get('pings', 0):,}", self.styles['Normal']),
                    Paragraph(
                        f"{g_imp.get('date_start', '-')} / {g_imp.get('date_end', '-')}",
                        self.styles['Normal']
                    ),
                ])
            t_gps = Table(gps_rows, colWidths=[2.5 * inch, 1.0 * inch, 0.8 * inch, 2.2 * inch])
            t_gps.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), accent),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor('#e8eaf6')]),
            ]))
            story.append(Spacer(1, 12))
            story.append(t_gps)

        # --- Photo Gallery Section ---
        if include_photos:
            self._embed_photo_gallery(story, data)

        # Disclaimer
        story.append(Spacer(1, 30))
        disc = ParagraphStyle('Disc', parent=self.styles['Normal'],
                              fontSize=7, textColor=colors.grey, alignment=1)
        story.append(Paragraph(
            remove_diacritics(_(
                "Anexa generata automat pe baza datelor de audit importate. "
                "Validat conform metodologiei DOOH Standard."
            )), disc
        ))
        
        doc.build(story)

    def _embed_photo_gallery(self, story, data):
        """Find and embed photos from campaign_photos directory"""
        campaign_id = data.get('id')
        if not campaign_id:
            return

        photo_dir = os.path.join('data', 'campaign_photos', campaign_id)
        if not os.path.exists(photo_dir):
            return

        photos = [os.path.join(photo_dir, f) for f in os.listdir(photo_dir) 
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not photos:
            return

        story.append(PageBreak())
        story.append(Paragraph(
            "<b>C. " + remove_diacritics(_("Galerie Foto (Dovada Executie)")) + "</b>",
            self.styles['Heading2']
        ))
        story.append(Spacer(1, 10))
        
        # Display photos in a grid (2 per row)
        rows = []
        current_row = []
        for i, photo_path in enumerate(photos):
            try:
                # Resize image to fit half page width
                img = Image(photo_path, width=3.0 * inch, height=2.25 * inch)
                current_row.append(img)
                
                if len(current_row) == 2:
                    rows.append(current_row)
                    current_row = []
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error loading photo {photo_path}: {e}")

        if current_row:
            rows.append(current_row + ['']) # Pad last row if needed

        if rows:
            t_photos = Table(rows, colWidths=[3.2 * inch, 3.2 * inch])
            t_photos.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ]))
            story.append(t_photos)

        doc.build(story)
