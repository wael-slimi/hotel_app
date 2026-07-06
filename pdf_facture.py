# -*- coding: utf-8 -*-
"""
Module pdf_facture.py - Generation des documents PDF (factures, fiches
de police, historiques) pour la Gestion d'Hotel.
Extrait automatiquement du fichier unique gestion_hotel.py, sans aucune
modification du code original (seuls les imports necessaires ont ete
ajoutes pour que ce module fonctionne de maniere independante).
"""

import os
from datetime import date, datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image,
)

import database as db
from database import BASE_DIR
from widgets import iso_to_date_str
from num2words_fr import montant_en_lettres

# ==============================================================================
# Module : pdf_facture.py
# ==============================================================================

def generer_facture_pdf(facture_id, chemin_pdf):
    """Génère le fichier PDF de la facture `facture_id` à l'emplacement
    `chemin_pdf`."""

    facture, lignes = db.get_facture(facture_id)
    if facture is None:
        raise ValueError("Facture introuvable")

    nom_hotel = db.get_parametre("nom_hotel", "Hôtel")
    adresse_hotel = db.get_parametre("adresse_hotel", "")
    telephone_hotel = db.get_parametre("telephone_hotel", "")
    matricule_fiscal = db.get_parametre("matricule_fiscal", "")

    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_title = ParagraphStyle(
        "TitreHotel", parent=styles["Title"], alignment=TA_LEFT,
        fontSize=16, spaceAfter=2,
    )
    style_small = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=9, leading=12,
    )
    style_right = ParagraphStyle(
        "Right", parent=styles["Normal"], alignment=TA_RIGHT,
    )
    style_facture_titre = ParagraphStyle(
        "FactureTitre", parent=styles["Heading2"], alignment=TA_CENTER,
        textColor=colors.HexColor("#1F4E79"),
    )

    doc = SimpleDocTemplate(
        chemin_pdf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )

    elements = []

    # ----------------- En-tête -----------------
    # ----------------- En-tête -----------------
    logo_path = os.path.join(BASE_DIR, "logo_hotel.jpg")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=25 * mm, height=25 * mm)
        entete_gauche = [logo,
                         Paragraph(f"<b>{nom_hotel}</b>", style_title),
                         Paragraph(adresse_hotel, style_small),
                         Paragraph(f"Tél : {telephone_hotel}", style_small),
                         Paragraph(f"M.F. : {matricule_fiscal}", style_small)]
    else:
        entete_gauche = [
            Paragraph(f"<b>{nom_hotel}</b>", style_title),
            Paragraph(adresse_hotel, style_small),
            Paragraph(f"Tél : {telephone_hotel}", style_small),
            Paragraph(f"M.F. : {matricule_fiscal}", style_small),
        ]

    entete_droite = [
        Paragraph(f"<b>FACTURE N° {facture['numero']}</b>", style_right),
        Paragraph(f"Date : {iso_to_date_str(facture['date_facture']) or facture['date_facture']}",
                  style_right),
    ]

    entete_table = Table(
        [[entete_gauche, entete_droite]],
        colWidths=[100 * mm, 70 * mm],
    )
    entete_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(entete_table)
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#1F4E79"),
                                thickness=1.2))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("FACTURE", style_facture_titre))
    elements.append(Spacer(1, 4 * mm))

    # ----------------- Informations client -----------------
    nom_complet = f"{facture['prenom'] or ''} {facture['nom'] or ''}".strip()
    info_client = [
        ["Client :", nom_complet],
        ["Identifiant :", f"{facture['type_identifiant'] or ''} "
                           f"{facture['numero_identifiant'] or ''}"],
        ["Adresse :", facture["adresse"] or ""],
        ["Chambre :", facture["chambre_numero"] or ""],
        ["Date d'arrivée :", iso_to_date_str(facture["date_entree"]) or facture["date_entree"]],
        ["Date de départ :", iso_to_date_str(facture["date_sortie"]) or facture["date_sortie"]],
        ["Nombre de nuits :", str(facture["nb_nuits"])],
    ]
    client_table = Table(info_client, colWidths=[40 * mm, 130 * mm])
    client_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 6 * mm))

    # ----------------- Tableau des lignes -----------------
    data = [["Description", "Quantité", "Prix unitaire (TND)", "Montant (TND)"]]
    for ligne in lignes:
        data.append([
            ligne["description"],
            f"{ligne['quantite']:g}",
            f"{ligne['prix_unitaire']:.3f}",
            f"{ligne['montant']:.3f}",
        ])

    if facture["remise"]:
        data.append(["Remise", "", "", f"-{facture['remise']:.3f}"])

    data.append(["", "", "TOTAL", f"{facture['montant_total']:.3f} TND"])

    lignes_table = Table(
        data, colWidths=[80 * mm, 25 * mm, 35 * mm, 35 * mm],
        repeatRows=1,
    )
    lignes_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(lignes_table)
    elements.append(Spacer(1, 8 * mm))

    # ----------------- Montant en lettres -----------------
    montant_lettres = montant_en_lettres(facture["montant_total"])
    texte_arret = (
        f"Arrêtée la présente facture à la somme de : "
        f"<b>{montant_lettres}</b>."
    )
    elements.append(HRFlowable(width="100%", color=colors.grey, thickness=0.5))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(texte_arret, style_normal))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        f"Mode de paiement : {facture['mode_paiement']}", style_small))
    elements.append(Spacer(1, 12 * mm))

    # ----------------- Pied de page / signature -----------------
    pied_table = Table(
        [["Cachet et signature de l'hôtel", "Signature du client"]],
        colWidths=[85 * mm, 85 * mm],
    )
    pied_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 25),
        ("LINEABOVE", (0, 0), (0, 0), 0.5, colors.grey),
        ("LINEABOVE", (1, 0), (1, 0), 0.5, colors.grey),
    ]))
    elements.append(pied_table)

    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        f"{nom_hotel} - {adresse_hotel} - Tél : {telephone_hotel} - "
        f"M.F. : {matricule_fiscal}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                       alignment=TA_CENTER, textColor=colors.grey),
    ))

    doc.build(elements)
    return chemin_pdf
def generer_fiche_police(client):
    """Génère une Fiche Police PDF pour un client. Retourne le chemin du fichier."""
    import subprocess, platform

    output_dir = os.path.join(BASE_DIR, "fiches_police")
    os.makedirs(output_dir, exist_ok=True)

    nom_fichier = f"fiche_police_{client['id']}_{client['nom']}_{client['prenom']}.pdf"
    chemin = os.path.join(output_dir, nom_fichier)

    BLEU = colors.HexColor("#2C3E6B")
    GRIS = colors.HexColor("#F5F5F5")
    styles = getSampleStyleSheet()

    titre_style = ParagraphStyle(
        "Titre", parent=styles["Title"],
        fontSize=18, textColor=BLEU, spaceAfter=4
    )
    sous_titre_style = ParagraphStyle(
        "SousTitre", parent=styles["Normal"],
        fontSize=10, textColor=colors.grey, spaceAfter=12
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"],
        fontSize=11, textColor=colors.white,
        backColor=BLEU, leftIndent=6, spaceBefore=10, spaceAfter=4, leading=18
    )
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey, alignment=TA_CENTER
    )

    def ligne(label, valeur):
        return [
            Paragraph(f"<b>{label}</b>", styles["Normal"]),
            Paragraph(str(valeur) if valeur else "—", styles["Normal"]),
        ]

    story = []

    # En-tête
    # En-tête
    logo_path = os.path.join(BASE_DIR, "logo_hotel.jpg")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=22 * mm, height=22 * mm)
        entete_fiche = Table(
            [[logo, Paragraph("FICHE POLICE", titre_style)]],
            colWidths=[28 * mm, 140 * mm],
        )
        entete_fiche.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(entete_fiche)
    else:
        story.append(Paragraph("FICHE POLICE", titre_style))

    story.append(Paragraph(
        f"Générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        sous_titre_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=BLEU, spaceAfter=12))

    # Section Identité
    story.append(Paragraph("  IDENTITÉ DU CLIENT", section_style))
    story.append(Spacer(1, 4))
    t1 = Table([
        ligne("Nom", client.get("nom")),
        ligne("Prénom", client.get("prenom")),
        ligne("Date de naissance", iso_to_date_str(client.get("date_naissance", "")) or "—"),
        ligne("Lieu de naissance", client.get("lieu_naissance")),
        ligne("Adresse", client.get("adresse")),
        ligne("Téléphone", client.get("telephone")),
    ], colWidths=[55*mm, 120*mm])
    t1.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRIS, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t1)

    # Section Pièce d'identité
    story.append(Paragraph("  PIÈCE D'IDENTITÉ", section_style))
    story.append(Spacer(1, 4))
    t2 = Table([
        ligne("Type d'identifiant", client.get("type_identifiant")),
        ligne("Numéro d'identifiant", client.get("numero_identifiant")),
    ], colWidths=[55*mm, 120*mm])
    t2.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRIS, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)

    # Section Séjour
    story.append(Paragraph("  INFORMATIONS DU SÉJOUR", section_style))
    story.append(Spacer(1, 4))
    t3 = Table([
        ligne("Chambre N°", client.get("chambre_numero")),
        ligne("Prix / nuit", f"{client.get('chambre_prix', '—')} TND"),
        ligne("Date d'entrée", iso_to_date_str(client.get("date_entree", "")) or "—"),
        ligne("Date de sortie", iso_to_date_str(client.get("date_sortie", "")) or "—"),
        ligne("Venant de", client.get("venant_de")),
        ligne("Allant à", client.get("allant_a")),
        ligne("Statut", client.get("statut")),
    ], colWidths=[55*mm, 120*mm])
    t3.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRIS, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t3)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Document officiel — Usage interne uniquement", footer_style))

    nom_hotel = db.get_parametre("nom_hotel", "Hôtel")
    doc = SimpleDocTemplate(
        chemin, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )
    doc.build(story)

    # Ouvrir automatiquement
    try:
        if platform.system() == "Windows":
            os.startfile(chemin)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", chemin])
        else:
            subprocess.Popen(["xdg-open", chemin])
    except Exception:
        pass

    return chemin
def generer_liste_factures_pdf(factures_data, chemin_pdf, titre="Historique des factures"):
    """
    Génère un PDF listant des factures.
    factures_data : liste de tuples (numero, date, client, identifiant, montant, statut)
    """
    nom_hotel = db.get_parametre("nom_hotel", "Hôtel")
    adresse_hotel = db.get_parametre("adresse_hotel", "")

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "TitreListe", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=16, textColor=colors.HexColor("#1F4E79"), spaceAfter=4,
    )
    style_small = ParagraphStyle(
        "SmallCenter", parent=styles["Normal"], fontSize=9,
        alignment=TA_CENTER, textColor=colors.grey, spaceAfter=10,
    )

    doc = SimpleDocTemplate(
        chemin_pdf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
    )
    elements = []

    elements.append(Paragraph(nom_hotel, style_title))
    elements.append(Paragraph(adresse_hotel, style_small))
    elements.append(Paragraph(titre, ParagraphStyle(
        "SousTitre", parent=styles["Heading2"], alignment=TA_CENTER,
        textColor=colors.HexColor("#1F4E79"),
    )))
    elements.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        style_small))
    elements.append(Spacer(1, 4 * mm))

    data = [["N° Facture", "Date", "Client", "Identifiant", "Montant (TND)", "Statut"]]
    total = 0.0
    for numero, date_f, client, identifiant, montant, statut in factures_data:
        data.append([numero, date_f, client, identifiant,
                     f"{montant:.3f}".replace(".", ","), statut])
        total += montant

    data.append(["", "", "", "", f"TOTAL : {total:.3f} TND".replace(".", ","), ""])

    table = Table(
        data, colWidths=[28 * mm, 22 * mm, 38 * mm, 30 * mm, 35 * mm, 28 * mm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        f"Nombre de factures : {len(factures_data)}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=9)))

    doc.build(elements)
    return chemin_pdf


def generer_liste_depenses_pdf(depenses_data, chemin_pdf, titre="Liste des dépenses"):
    """
    Génère un PDF listant des dépenses.
    depenses_data : liste de tuples (date, categorie, description, montant, mode)
    """
    nom_hotel = db.get_parametre("nom_hotel", "Hôtel")
    adresse_hotel = db.get_parametre("adresse_hotel", "")

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "TitreListe", parent=styles["Title"], alignment=TA_CENTER,
        fontSize=16, textColor=colors.HexColor("#C0392B"), spaceAfter=4,
    )
    style_small = ParagraphStyle(
        "SmallCenter", parent=styles["Normal"], fontSize=9,
        alignment=TA_CENTER, textColor=colors.grey, spaceAfter=10,
    )

    doc = SimpleDocTemplate(
        chemin_pdf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm,
        leftMargin=12 * mm, rightMargin=12 * mm,
    )
    elements = []

    elements.append(Paragraph(nom_hotel, style_title))
    elements.append(Paragraph(adresse_hotel, style_small))
    elements.append(Paragraph(titre, ParagraphStyle(
        "SousTitre", parent=styles["Heading2"], alignment=TA_CENTER,
        textColor=colors.HexColor("#C0392B"),
    )))
    elements.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        style_small))
    elements.append(Spacer(1, 4 * mm))

    data = [["Date", "Catégorie", "Description", "Montant (TND)", "Mode de paiement"]]
    total = 0.0
    for date_d, categorie, description, montant, mode in depenses_data:
        data.append([date_d, categorie, description,
                     f"{montant:.3f}".replace(".", ","), mode])
        total += montant

    data.append(["", "", "", f"TOTAL : {total:.3f} TND".replace(".", ","), ""])

    table = Table(
        data, colWidths=[24 * mm, 35 * mm, 55 * mm, 32 * mm, 35 * mm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C0392B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 0), (-1, -1), "LEFT"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        f"Nombre de dépenses : {len(depenses_data)}",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=9)))

    doc.build(elements)
    return chemin_pdf


