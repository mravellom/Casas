"""Generador de Dossier de Inversión PDF.

Crea un one-pager profesional con datos de la propiedad,
comparación de mercado, rentabilidad y QR code.
"""
import io
import logging
from datetime import datetime, timezone

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


def generate_property_pdf(prop: dict, market_avg: float | None = None) -> bytes:
    """Genera PDF de una página con el dossier de inversión."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=20 * mm, bottomMargin=15 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Estilos custom
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], fontSize=18,
        spaceAfter=6, textColor=colors.HexColor("#1e40af"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontSize=10,
        textColor=colors.grey, spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontSize=13,
        textColor=colors.HexColor("#1e3a5f"), spaceBefore=12, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=8, textColor=colors.grey,
    )

    # Header
    elements.append(Paragraph("InmoAlert Chile", title_style))
    elements.append(Paragraph("Dossier de Inversión Inmobiliaria", subtitle_style))
    elements.append(Spacer(1, 4 * mm))

    # Título propiedad
    elements.append(Paragraph(prop.get("title", "Propiedad"), heading_style))
    elements.append(Paragraph(
        f'{prop.get("commune", "")} | {prop.get("address", "Sin dirección")}',
        body_style,
    ))
    elements.append(Spacer(1, 6 * mm))

    # Datos principales
    price_uf = prop.get("price_uf") or 0
    m2 = prop.get("m2_total") or 0
    price_m2 = prop.get("price_m2_uf") or 0
    beds = prop.get("bedrooms") or "-"
    baths = prop.get("bathrooms") or "-"
    score = prop.get("opportunity_score") or "-"

    main_data = [
        ["Precio", "Superficie", "UF/m²", "Dormitorios", "Baños", "Score"],
        [
            f"{price_uf:,.0f} UF",
            f"{m2:.0f} m²" if m2 else "N/D",
            f"{price_m2:.1f}" if price_m2 else "N/D",
            str(beds),
            str(baths),
            str(score),
        ],
    ]

    main_table = Table(main_data, colWidths=[85, 75, 65, 75, 55, 55])
    main_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(main_table)
    elements.append(Spacer(1, 8 * mm))

    # Comparación con mercado
    if market_avg and price_m2:
        elements.append(Paragraph("Comparación con el Mercado", heading_style))

        pct = ((price_m2 - market_avg) / market_avg) * 100
        estimated_value = market_avg * m2 if m2 else 0
        potential_profit = estimated_value - price_uf if estimated_value else 0

        market_data = [
            ["", "Esta propiedad", "Promedio zona", "Diferencia"],
            [
                "UF/m²",
                f"{price_m2:.1f}",
                f"{market_avg:.1f}",
                f"{pct:+.1f}%",
            ],
            [
                "Valor total",
                f"{price_uf:,.0f} UF",
                f"{estimated_value:,.0f} UF" if estimated_value else "N/D",
                f"{potential_profit:+,.0f} UF" if potential_profit else "",
            ],
        ]

        market_table = Table(market_data, colWidths=[80, 110, 110, 100])
        market_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4ff")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TEXTCOLOR", (-1, 1), (-1, -1),
             colors.HexColor("#16a34a") if pct < 0 else colors.HexColor("#dc2626")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(market_table)
        elements.append(Spacer(1, 6 * mm))

    # Rentabilidad
    rent = prop.get("rentability")
    if rent:
        elements.append(Paragraph("Proyección Financiera", heading_style))

        rent_data = [
            ["Arriendo est.", "Cap Rate", "Cap Rate neto", "Payback", "Flujo mensual"],
            [
                f"{rent['estimated_rent_uf']} UF/mes",
                f"{rent['cap_rate']}%",
                f"{rent['cap_rate_net']}%",
                f"{rent['payback_years']} años",
                f"{rent['monthly_cashflow_uf']:+.1f} UF",
            ],
        ]

        rent_table = Table(rent_data, colWidths=[90, 75, 85, 70, 85])
        badge_color = colors.HexColor("#16a34a") if rent.get("is_high_rentability") else colors.HexColor("#666666")
        rent_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0fdf4")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(rent_table)

        if rent.get("is_high_rentability"):
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(
                '<font color="#16a34a"><b>ALTA RENTABILIDAD</b></font> — Cap Rate superior al 6%',
                body_style,
            ))
        elements.append(Spacer(1, 6 * mm))

    # Barrio
    neighborhood = prop.get("neighborhood")
    if neighborhood:
        elements.append(Paragraph("Inteligencia de Barrio", heading_style))

        metro = neighborhood.get("nearest_metro")
        services = neighborhood.get("services_500m", {})
        future = neighborhood.get("future_metro")

        barrio_lines = []
        if metro:
            barrio_lines.append(f"Metro más cercano: {metro['name']} ({metro['distance_m']}m, {metro['walk_minutes']} min)")
        barrio_lines.append(
            f"Servicios (500m): {services.get('supermarkets', 0)} supermercados, "
            f"{services.get('pharmacies', 0)} farmacias, {services.get('parks', 0)} parques"
        )
        if future:
            barrio_lines.append(f"Futuro Metro {future['line']}: Estación {future['name']} ({future['distance_m']}m)")
        barrio_lines.append(f"Score de conectividad: {neighborhood.get('connectivity_score', 0)}/100")

        for line in barrio_lines:
            elements.append(Paragraph(f"• {line}", body_style))

        if neighborhood.get("is_master_buy"):
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(
                '<font color="#7c3aed"><b>COMPRA MAESTRA</b></font> — Cerca de futuro Metro + buena rentabilidad',
                body_style,
            ))
        elements.append(Spacer(1, 6 * mm))

    # QR Code
    source_url = prop.get("source_url", "")
    if source_url:
        qr = qrcode.make(source_url, box_size=4, border=1)
        qr_buffer = io.BytesIO()
        qr.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        qr_img = Image(qr_buffer, width=25 * mm, height=25 * mm)

        qr_table = Table(
            [[qr_img, Paragraph(
                f'Escanea para ver el anuncio original<br/>'
                f'<font size="7" color="grey">{source_url[:80]}</font>',
                body_style,
            )]],
            colWidths=[35 * mm, 140 * mm],
        )
        qr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(qr_table)

    # Footer
    elements.append(Spacer(1, 8 * mm))
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    elements.append(Paragraph(
        f'Generado por InmoAlert Chile el {now}. '
        f'Este informe es referencial y no constituye asesoría financiera.',
        small_style,
    ))

    doc.build(elements)
    return buffer.getvalue()
