# -*- coding: utf-8 -*-
"""
Module database.py - Acces aux donnees (SQLite) pour la Gestion d'Hotel.
Extrait automatiquement du fichier unique gestion_hotel.py, sans aucune
modification du code original (seuls les imports necessaires ont ete
ajoutes pour que ce module fonctionne de maniere independante).
"""

import os
import sqlite3
from datetime import date, datetime, timedelta

# ==============================================================================
# Module : database.py
# ==============================================================================

# Emplacement de la base de données (dans le même dossier que l'application)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hotel.db")

# États possibles d'une chambre
ETATS_CHAMBRE = ["Libre", "Occupée", "Réservée", "Maintenance"]

# Catégories de dépenses
CATEGORIES_DEPENSE = [
    "Maintenance",
    "Ménage",
    "STEG (Électricité)",
    "SONEDE (Eau)",
    "Internet / Télécom",
    "Fournitures",
    "Salaires",
    "Impôts / Taxes",
    "Autre",
]

# Types d'identifiants pour les clients
TYPES_IDENTIFIANT = ["CIN", "Passeport", "Carte de séjour"]


def get_connection():
    """Retourne une connexion SQLite avec les clés étrangères activées."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée les tables si elles n'existent pas et insère des données de
    base (paramètres + quelques chambres) lors du premier lancement."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chambres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL DEFAULT 'Simple',
            prix REAL NOT NULL DEFAULT 0,
            etat TEXT NOT NULL DEFAULT 'Libre',
            description TEXT DEFAULT ''
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            type_identifiant TEXT NOT NULL DEFAULT 'CIN',
            numero_identifiant TEXT NOT NULL,
            date_naissance TEXT DEFAULT '',
            lieu_naissance TEXT DEFAULT '',
            adresse TEXT DEFAULT '',
            telephone TEXT DEFAULT '',
            venant_de TEXT DEFAULT '',
            allant_a TEXT DEFAULT '',
            chambre_id INTEGER,
            date_entree TEXT DEFAULT '',
            date_sortie TEXT DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'En cours',
            FOREIGN KEY (chambre_id) REFERENCES chambres(id) ON DELETE SET NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            nom_client TEXT DEFAULT '',
            date_facture TEXT NOT NULL,
            date_entree TEXT DEFAULT '',
            date_sortie TEXT DEFAULT '',
            nb_nuits INTEGER DEFAULT 0,
            montant_total REAL NOT NULL DEFAULT 0,
            remise REAL NOT NULL DEFAULT 0,
            mode_paiement TEXT DEFAULT 'Espèces',
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
        )
        """
    )
    # Ajouter la colonne si elle n'existe pas (base existante)
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN nom_client TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN payee INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE clients ADD COLUMN solde REAL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN montant_paye REAL DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS facture_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facture_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantite REAL NOT NULL DEFAULT 1,
            prix_unitaire REAL NOT NULL DEFAULT 0,
            montant REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (facture_id) REFERENCES factures(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            categorie TEXT NOT NULL,
            description TEXT DEFAULT '',
            montant REAL NOT NULL DEFAULT 0,
            mode_paiement TEXT DEFAULT 'Espèces'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            telephone TEXT DEFAULT '',
            type_identifiant TEXT DEFAULT 'CIN',
            numero_identifiant TEXT DEFAULT '',
            chambre_id INTEGER,
            date_arrivee TEXT NOT NULL,
            date_depart TEXT NOT NULL,
            nb_personnes INTEGER DEFAULT 1,
            notes TEXT DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'RESERVE',
            FOREIGN KEY (chambre_id) REFERENCES chambres(id) ON DELETE SET NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS parametres (
            cle TEXT PRIMARY KEY,
            valeur TEXT
        )
        """
    )

    conn.commit()

    # Paramètres par défaut (informations de l'hôtel utilisées sur les factures)
    defaults = {
        "nom_hotel": "Hôtel ",
        "adresse_hotel": "Adresse de l'hôtel, Tunisie",
        "telephone_hotel": "+216 00 000 000",
        "matricule_fiscal": "0000000A/A/M/000",
        "prochain_numero_facture": "1",
    }
    for cle, valeur in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
            (cle, valeur),
        )
    conn.commit()

    # Si aucune chambre n'existe, on crée un parc de chambres par défaut
    # Si aucune chambre n'existe, on crée un parc de chambres par défaut
    # 4 étages x 4 chambres = 16 chambres, numérotées "étage-chambre" (ex: 1-3)
    cur.execute("SELECT COUNT(*) AS n FROM chambres")
    if cur.fetchone()["n"] == 0:
        chambres_defaut = []
        for etage in range(1, 5):
            for i in range(1, 5):
                numero = f"{etage}-{i}"
                if i == 1:
                    type_ch, prix = "Suite", 180.0
                elif i == 2:
                    type_ch, prix = "Double", 120.0
                else:
                    type_ch, prix = "Simple", 80.0
                chambres_defaut.append((numero, type_ch, prix, "Libre", ""))
        cur.executemany(
            "INSERT INTO chambres (numero, type, prix, etat, description) "
            "VALUES (?, ?, ?, ?, ?)",
            chambres_defaut,
        )
        conn.commit()

    conn.close()


# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------
def get_parametre(cle, defaut=""):
    conn = get_connection()
    row = conn.execute(
        "SELECT valeur FROM parametres WHERE cle = ?", (cle,)
    ).fetchone()
    conn.close()
    return row["valeur"] if row else defaut


def set_parametre(cle, valeur):
    conn = get_connection()
    conn.execute(
        "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
        (cle, str(valeur)),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Chambres
# ---------------------------------------------------------------------------
def get_chambres():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM chambres ORDER BY numero").fetchall()
    conn.close()
    return rows


def get_chambre(chambre_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM chambres WHERE id = ?", (chambre_id,)
    ).fetchone()
    conn.close()
    return row


def get_chambres_libres():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chambres WHERE etat = 'Libre' ORDER BY numero"
    ).fetchall()
    conn.close()
    return rows


def add_chambre(numero, type_ch, prix, etat="Libre", description=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chambres (numero, type, prix, etat, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (numero, type_ch, prix, etat, description),
    )
    conn.commit()
    conn.close()


def update_chambre(chambre_id, numero, type_ch, prix, etat, description):
    conn = get_connection()
    conn.execute(
        "UPDATE chambres SET numero=?, type=?, prix=?, etat=?, description=? "
        "WHERE id=?",
        (numero, type_ch, prix, etat, description, chambre_id),
    )
    conn.commit()
    conn.close()


def set_chambre_etat(chambre_id, etat):
    conn = get_connection()
    conn.execute("UPDATE chambres SET etat=? WHERE id=?", (etat, chambre_id))
    conn.commit()
    conn.close()


def delete_chambre(chambre_id):
    conn = get_connection()
    conn.execute("DELETE FROM chambres WHERE id=?", (chambre_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
def get_clients(statut=None):
    conn = get_connection()
    if statut:
        rows = conn.execute(
            """
            SELECT c.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
            FROM clients c
            LEFT JOIN chambres ch ON ch.id = c.chambre_id
            WHERE c.statut = ?
            ORDER BY c.id DESC
            """,
            (statut,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT c.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
            FROM clients c
            LEFT JOIN chambres ch ON ch.id = c.chambre_id
            ORDER BY c.id DESC
            """
        ).fetchall()
    conn.close()
    return rows


def get_client(client_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT c.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
        FROM clients c
        LEFT JOIN chambres ch ON ch.id = c.chambre_id
        WHERE c.id = ?
        """,
        (client_id,),
    ).fetchone()
    conn.close()
    return row


def add_client(data):
    """data: dict avec les clés correspondant aux colonnes de la table."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clients (
            nom, prenom, type_identifiant, numero_identifiant,
            date_naissance, lieu_naissance, adresse, telephone,
            venant_de, allant_a, chambre_id, date_entree, date_sortie, statut
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["nom"], data["prenom"], data["type_identifiant"],
            data["numero_identifiant"], data["date_naissance"],
            data["lieu_naissance"], data["adresse"], data["telephone"],
            data["venant_de"], data["allant_a"], data["chambre_id"],
            data["date_entree"], data["date_sortie"], data.get("statut", "En cours"),
        ),
    )
    client_id = cur.lastrowid
    # Si une chambre est associée, on la marque occupée
    if data.get("chambre_id"):
        cur.execute(
            "UPDATE chambres SET etat='Occupée' WHERE id=?",
            (data["chambre_id"],),
        )
    conn.commit()
    conn.close()
    return client_id


def update_client(client_id, data):
    conn = get_connection()
    cur = conn.cursor()

    # Récupérer l'ancienne chambre pour la libérer si elle change
    ancien = cur.execute(
        "SELECT chambre_id FROM clients WHERE id=?", (client_id,)
    ).fetchone()
    ancienne_chambre = ancien["chambre_id"] if ancien else None

    cur.execute(
        """
        UPDATE clients SET
            nom=?, prenom=?, type_identifiant=?, numero_identifiant=?,
            date_naissance=?, lieu_naissance=?, adresse=?, telephone=?,
            venant_de=?, allant_a=?, chambre_id=?, date_entree=?,
            date_sortie=?, statut=?
        WHERE id=?
        """,
        (
            data["nom"], data["prenom"], data["type_identifiant"],
            data["numero_identifiant"], data["date_naissance"],
            data["lieu_naissance"], data["adresse"], data["telephone"],
            data["venant_de"], data["allant_a"], data["chambre_id"],
            data["date_entree"], data["date_sortie"], data.get("statut", "En cours"),
            client_id,
        ),
    )

    nouvelle_chambre = data.get("chambre_id")

    # Libérer l'ancienne chambre si elle a changé
    if ancienne_chambre and ancienne_chambre != nouvelle_chambre:
        cur.execute(
            "UPDATE chambres SET etat='Libre' WHERE id=?", (ancienne_chambre,)
        )

    # Occuper la nouvelle chambre si le client est toujours en cours
    if nouvelle_chambre and data.get("statut", "En cours") == "En cours":
        cur.execute(
            "UPDATE chambres SET etat='Occupée' WHERE id=?", (nouvelle_chambre,)
        )

    # Si le client est marqué "Sorti", on libère sa chambre
    if data.get("statut") == "Sorti" and nouvelle_chambre:
        cur.execute(
            "UPDATE chambres SET etat='Libre' WHERE id=?", (nouvelle_chambre,)
        )

    conn.commit()
    conn.close()


def delete_client(client_id):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT chambre_id FROM clients WHERE id=?", (client_id,)
    ).fetchone()
    cur.execute("DELETE FROM clients WHERE id=?", (client_id,))
    if row and row["chambre_id"]:
        cur.execute(
            "UPDATE chambres SET etat='Libre' WHERE id=?", (row["chambre_id"],)
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Factures
# ---------------------------------------------------------------------------
def get_next_numero_facture():
    n = get_parametre("prochain_numero_facture", "1")
    try:
        n = int(n)
    except ValueError:
        n = 1
    annee = datetime.now().year
    return f"F{annee}-{n:05d}"


def create_facture(client_id, date_facture, date_entree, date_sortie,
                    nb_nuits, lignes, remise=0.0, mode_paiement="Espèces",
                    nom_client=""):
    """
    lignes: liste de tuples (description, quantite, prix_unitaire)
    Retourne (facture_id, numero, montant_total)
    """
    montant_total = 0.0
    lignes_calc = []
    for description, quantite, prix_unitaire in lignes:
        montant = round(float(quantite) * float(prix_unitaire), 3)
        montant_total += montant
        lignes_calc.append((description, quantite, prix_unitaire, montant))
    montant_total = round(montant_total - float(remise or 0), 3)

    numero = get_next_numero_facture()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO factures (numero, client_id, nom_client, date_facture,
                               date_entree, date_sortie, nb_nuits, montant_total,
                               remise, mode_paiement)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (numero, client_id, nom_client, date_facture, date_entree, date_sortie,
         nb_nuits, montant_total, remise, mode_paiement),
    )
    facture_id = cur.lastrowid

    for description, quantite, prix_unitaire, montant in lignes_calc:
        cur.execute(
            """
            INSERT INTO facture_lignes
                (facture_id, description, quantite, prix_unitaire, montant)
            VALUES (?, ?, ?, ?, ?)
            """,
            (facture_id, description, quantite, prix_unitaire, montant),
        )

    # Incrémenter le compteur de factures
    try:
        prochain = int(get_parametre("prochain_numero_facture", "1")) + 1
    except ValueError:
        prochain = 2
    cur.execute(
        "UPDATE parametres SET valeur=? WHERE cle='prochain_numero_facture'",
        (str(prochain),),
    )

    conn.commit()
    conn.close()
    return facture_id, numero, montant_total


def get_facture(facture_id):
    conn = get_connection()
    facture = conn.execute(
        """
        SELECT f.*, c.nom, c.prenom, c.numero_identifiant, c.type_identifiant,
               c.adresse, ch.numero AS chambre_numero
        FROM factures f
        LEFT JOIN clients c ON c.id = f.client_id
        LEFT JOIN chambres ch ON ch.id = c.chambre_id
        WHERE f.id = ?
        """,
        (facture_id,),
    ).fetchone()
    lignes = conn.execute(
        "SELECT * FROM facture_lignes WHERE facture_id=? ORDER BY id",
        (facture_id,),
    ).fetchall()
    conn.close()
    return facture, lignes


def get_factures(date_debut=None, date_fin=None):
    conn = get_connection()
    if date_debut and date_fin:
        rows = conn.execute(
            """
            SELECT f.*, c.nom, c.prenom
            FROM factures f
            LEFT JOIN clients c ON c.id = f.client_id
            WHERE f.date_facture BETWEEN ? AND ?
            ORDER BY f.date_facture DESC, f.id DESC
            """,
            (date_debut, date_fin),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT f.*, c.nom, c.prenom
            FROM factures f
            LEFT JOIN clients c ON c.id = f.client_id
            ORDER BY f.date_facture DESC, f.id DESC
            """
        ).fetchall()
    conn.close()
    return rows
def set_facture_payee(facture_id):
    conn = get_connection()
    conn.execute("UPDATE factures SET payee=1 WHERE id=?", (facture_id,))
    conn.commit()
    conn.close()
def set_facture_paiement_partiel(facture_id, montant_paye):
    conn = get_connection()
    conn.execute(
        "UPDATE factures SET payee=0, montant_paye=? WHERE id=?",
        (montant_paye, facture_id)
    )
    conn.commit()
    conn.close()
def set_client_solde(client_id, solde):
    conn = get_connection()
    conn.execute("UPDATE clients SET solde=? WHERE id=?", (solde, client_id))
    conn.commit()
    conn.close()

def get_client_solde(client_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT solde FROM clients WHERE id=?", (client_id,)
    ).fetchone()
    conn.close()
    return row["solde"] if row else 0.0


# ---------------------------------------------------------------------------
# Dépenses
# ---------------------------------------------------------------------------
def get_depenses(date_debut=None, date_fin=None):
    conn = get_connection()
    if date_debut and date_fin:
        rows = conn.execute(
            "SELECT * FROM depenses WHERE date BETWEEN ? AND ? "
            "ORDER BY date DESC, id DESC",
            (date_debut, date_fin),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM depenses ORDER BY date DESC, id DESC"
        ).fetchall()
    conn.close()
    return rows


def add_depense(date, categorie, description, montant, mode_paiement="Espèces"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO depenses (date, categorie, description, montant, mode_paiement) "
        "VALUES (?, ?, ?, ?, ?)",
        (date, categorie, description, montant, mode_paiement),
    )
    conn.commit()
    conn.close()


def update_depense(depense_id, date, categorie, description, montant, mode_paiement):
    conn = get_connection()
    conn.execute(
        "UPDATE depenses SET date=?, categorie=?, description=?, montant=?, "
        "mode_paiement=? WHERE id=?",
        (date, categorie, description, montant, mode_paiement, depense_id),
    )
    conn.commit()
    conn.close()


def delete_depense(depense_id):
    conn = get_connection()
    conn.execute("DELETE FROM depenses WHERE id=?", (depense_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Statistiques / récapitulatifs
# ---------------------------------------------------------------------------
def recap_recettes(date_debut, date_fin, group_by="day"):
    """
    Retourne une liste de tuples (periode, total_recettes) entre deux dates.
    group_by: 'day' -> 'YYYY-MM-DD', 'month' -> 'YYYY-MM', 'year' -> 'YYYY'
    """
    fmt = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}[group_by]
    conn = get_connection()
    rows = conn.execute(
        f"""
        SELECT strftime('{fmt}', date_facture) AS periode,
               SUM(montant_total) AS total
        FROM factures
        WHERE date_facture BETWEEN ? AND ?
        GROUP BY periode
        ORDER BY periode
        """,
        (date_debut, date_fin),
    ).fetchall()
    conn.close()
    return rows


def recap_depenses(date_debut, date_fin, group_by="day"):
    fmt = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}[group_by]
    conn = get_connection()
    rows = conn.execute(
        f"""
        SELECT strftime('{fmt}', date) AS periode,
               SUM(montant) AS total
        FROM depenses
        WHERE date BETWEEN ? AND ?
        GROUP BY periode
        ORDER BY periode
        """,
        (date_debut, date_fin),
    ).fetchall()
    conn.close()
    return rows


def recap_depenses_par_categorie(date_debut, date_fin):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT categorie, SUM(montant) AS total
        FROM depenses
        WHERE date BETWEEN ? AND ?
        GROUP BY categorie
        ORDER BY total DESC
        """,
        (date_debut, date_fin),
    ).fetchall()
    conn.close()
    return rows


def total_recettes(date_debut, date_fin):
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(montant_total),0) AS total FROM factures "
        "WHERE date_facture BETWEEN ? AND ?",
        (date_debut, date_fin),
    ).fetchone()
    conn.close()
    return row["total"] or 0.0


def total_depenses(date_debut, date_fin):
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(montant),0) AS total FROM depenses "
        "WHERE date BETWEEN ? AND ?",
        (date_debut, date_fin),
    ).fetchone()
    conn.close()
    return row["total"] or 0.0


def taux_occupation(date_ref=None):
    """Retourne (nb_occupees, nb_total) chambres à l'instant présent."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) AS n FROM chambres").fetchone()["n"]
    occ = conn.execute(
        "SELECT COUNT(*) AS n FROM chambres WHERE etat='Occupée'"
    ).fetchone()["n"]
    conn.close()
    return occ, total
# ---------------------------------------------------------------------------
# Réservations
# ---------------------------------------------------------------------------
def get_reservations(statut=None):
    conn = get_connection()
    if statut:
        rows = conn.execute(
            """
            SELECT r.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
            FROM reservations r
            LEFT JOIN chambres ch ON ch.id = r.chambre_id
            WHERE r.statut = ?
            ORDER BY r.date_arrivee ASC
            """, (statut,)
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT r.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
            FROM reservations r
            LEFT JOIN chambres ch ON ch.id = r.chambre_id
            ORDER BY r.date_arrivee ASC
            """
        ).fetchall()
    conn.close()
    return rows


def get_reservation(reservation_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT r.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
        FROM reservations r
        LEFT JOIN chambres ch ON ch.id = r.chambre_id
        WHERE r.id = ?
        """, (reservation_id,)
    ).fetchone()
    conn.close()
    return row


def add_reservation(data):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reservations (
            nom, prenom, telephone, type_identifiant, numero_identifiant,
            chambre_id, date_arrivee, date_depart, nb_personnes, notes, statut
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["nom"], data["prenom"], data["telephone"],
            data["type_identifiant"], data["numero_identifiant"],
            data["chambre_id"], data["date_arrivee"], data["date_depart"],
            data["nb_personnes"], data["notes"], data.get("statut", "RESERVE"),
        )
    )
    if data.get("chambre_id"):
        cur.execute(
            "UPDATE chambres SET etat='Réservée' WHERE id=?",
            (data["chambre_id"],)
        )
    conn.commit()
    conn.close()


def update_reservation(reservation_id, data):
    conn = get_connection()
    cur = conn.cursor()

    ancien = cur.execute(
        "SELECT chambre_id, statut FROM reservations WHERE id=?",
        (reservation_id,)
    ).fetchone()
    ancienne_chambre = ancien["chambre_id"] if ancien else None

    cur.execute(
        """
        UPDATE reservations SET
            nom=?, prenom=?, telephone=?, type_identifiant=?,
            numero_identifiant=?, chambre_id=?, date_arrivee=?,
            date_depart=?, nb_personnes=?, notes=?, statut=?
        WHERE id=?
        """,
        (
            data["nom"], data["prenom"], data["telephone"],
            data["type_identifiant"], data["numero_identifiant"],
            data["chambre_id"], data["date_arrivee"], data["date_depart"],
            data["nb_personnes"], data["notes"], data.get("statut", "RESERVE"),
            reservation_id,
        )
    )

    nouvelle_chambre = data.get("chambre_id")

    if ancienne_chambre and ancienne_chambre != nouvelle_chambre:
        cur.execute(
            "UPDATE chambres SET etat='Libre' WHERE id=?", (ancienne_chambre,)
        )

    if nouvelle_chambre:
        statut = data.get("statut", "RESERVE")
        if statut == "RESERVE":
            cur.execute(
                "UPDATE chambres SET etat='Réservée' WHERE id=?", (nouvelle_chambre,)
            )
        elif statut == "ANNULE":
            cur.execute(
                "UPDATE chambres SET etat='Libre' WHERE id=?", (nouvelle_chambre,)
            )

    conn.commit()
    conn.close()


def delete_reservation(reservation_id):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT chambre_id FROM reservations WHERE id=?", (reservation_id,)
    ).fetchone()
    cur.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
    if row and row["chambre_id"]:
        cur.execute(
            "UPDATE chambres SET etat='Libre' WHERE id=?", (row["chambre_id"],)
        )
    conn.commit()
    conn.close()

