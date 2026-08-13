# -*- coding: utf-8 -*-
"""
Module database.py - Acces aux donnees (SQLite) pour la Gestion d'Hotel.
Extrait automatiquement du fichier unique gestion_hotel.py, sans aucune
modification du code original (seuls les imports necessaires ont ete
ajoutes pour que ce module fonctionne de maniere independante).
"""

import os
import re
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

def validate_identifiant_format(type_identifiant, numero_identifiant):
    patterns = {
        "CIN": r"^\d{8}$",
        "Passeport": r"^[A-Za-z]\d{7}$",
        "Carte de séjour": r"^\d+$",
    }
    pattern = patterns.get(type_identifiant)
    if pattern and not re.match(pattern, numero_identifiant):
        if type_identifiant == "CIN":
            return "Le CIN doit contenir exactement 8 chiffres."
        elif type_identifiant == "Passeport":
            return "Le passeport doit contenir 1 lettre suivie de 7 chiffres (ex: A1234567)."
        elif type_identifiant == "Carte de séjour":
            return "La carte de séjour doit contenir uniquement des chiffres."
    return None


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
            description TEXT DEFAULT '',
            photo TEXT DEFAULT ''
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
            solde REAL DEFAULT 0
        )
        """
    )

    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_numero_identifiant ON clients(numero_identifiant)"
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
        cur.execute("ALTER TABLE factures ADD COLUMN montant_ht REAL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN tva REAL DEFAULT 0")
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
    try:
        cur.execute("ALTER TABLE chambres ADD COLUMN photo TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN type_identifiant TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN numero_identifiant TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN adresse TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN chambre_numero TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN venant_de TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN allant_a TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE chambres ADD COLUMN max_personnes INTEGER DEFAULT 1")
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

    # --- Sejours table (new architecture) ---
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sejours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            chambre_id INTEGER NOT NULL,
            date_entree TEXT NOT NULL,
            date_sortie TEXT DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'En cours',
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
            FOREIGN KEY (chambre_id) REFERENCES chambres(id) ON DELETE SET NULL
        )
        """
    )

    # --- Migration: add client_id to reservations ---
    try:
        cur.execute("ALTER TABLE reservations ADD COLUMN client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL")
        conn.commit()
    except Exception:
        pass

    # --- Migration: add sejour_id to factures ---
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN sejour_id INTEGER REFERENCES sejours(id) ON DELETE SET NULL")
        conn.commit()
    except Exception:
        pass

    # --- Migration: create sejours from existing clients with active rooms ---
    try:
        cur.execute("SELECT COUNT(*) AS n FROM sejours")
        if cur.fetchone()["n"] == 0:
            cur.execute("PRAGMA table_info(clients)")
            existing_cols = {c["name"] for c in cur.fetchall()}
            if "chambre_id" in existing_cols:
                # Get valid room IDs
                valid_rooms = {r["id"] for r in cur.execute("SELECT id FROM chambres").fetchall()}
                # Get columns available for dates
                has_dates = "date_entree" in existing_cols and "date_sortie" in existing_cols
                has_statut = "statut" in existing_cols

                cur.execute("SELECT id, chambre_id" + 
                           (", date_entree, date_sortie" if has_dates else "") +
                           (", statut" if has_statut else "") +
                           " FROM clients WHERE chambre_id IS NOT NULL")
                old_clients = cur.fetchall()
                for oc in old_clients:
                    if oc["chambre_id"] not in valid_rooms:
                        continue
                    st = oc["statut"] if has_statut else "En cours"
                    sejour_statut = "En cours" if st == "En cours" else "Terminé"
                    d_entree = oc["date_entree"] if has_dates else ""
                    d_sortie = oc["date_sortie"] if has_dates else ""
                    cur.execute(
                        "INSERT INTO sejours (client_id, chambre_id, date_entree, date_sortie, statut) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (oc["id"], oc["chambre_id"], d_entree, d_sortie, sejour_statut),
                    )
                conn.commit()
    except Exception:
        pass

    # --- Migration: link existing reservations to clients by numero_identifiant ---
    try:
        cur.execute(
            "SELECT r.id, r.numero_identifiant, c.id AS client_id "
            "FROM reservations r "
            "LEFT JOIN clients c ON c.numero_identifiant = r.numero_identifiant "
            "WHERE r.client_id IS NULL AND c.id IS NOT NULL"
        )
        for row in cur.fetchall():
            cur.execute("UPDATE reservations SET client_id=? WHERE id=?", (row["client_id"], row["id"]))
        conn.commit()
    except Exception:
        pass

    # --- Migration: remove old columns from clients (after migration) ---
    for col in ("chambre_id", "date_entree", "date_sortie", "statut"):
        try:
            cur.execute(f"ALTER TABLE clients DROP COLUMN {col}")
            conn.commit()
        except Exception:
            pass

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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chambre_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chambre_id INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            ordre INTEGER DEFAULT 0,
            FOREIGN KEY (chambre_id) REFERENCES chambres(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reservation_companions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            type_identifiant TEXT DEFAULT 'CIN',
            numero_identifiant TEXT DEFAULT '',
            date_naissance TEXT DEFAULT '',
            lieu_naissance TEXT DEFAULT '',
            adresse TEXT DEFAULT '',
            telephone TEXT DEFAULT '',
            venant_de TEXT DEFAULT '',
            allant_a TEXT DEFAULT '',
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
        )
        """
    )

    # --- Migration: add parent_sejour_id to sejours (group linking) ---
    try:
        cur.execute("ALTER TABLE sejours ADD COLUMN parent_sejour_id INTEGER REFERENCES sejours(id)")
        conn.commit()
    except Exception:
        pass

    # --- Migration: add missing columns to reservations ---
    for col, default in [
        ("date_naissance", ""),
        ("lieu_naissance", ""),
        ("adresse", ""),
        ("venant_de", ""),
        ("allant_a", ""),
    ]:
        try:
            cur.execute(f"ALTER TABLE reservations ADD COLUMN {col} TEXT DEFAULT '{default}'")
            conn.commit()
        except Exception:
            pass

    # --- Migration: add timbre_fiscal to factures ---
    try:
        cur.execute("ALTER TABLE factures ADD COLUMN timbre_fiscal REAL DEFAULT 1.0")
        conn.commit()
    except Exception:
        pass

    conn.commit()

    # Si aucune chambre n'existe, on crée un parc de chambres par défaut
    # Si aucune chambre n'existe, on crée un parc de chambres par défaut
    # 4 étages x 8 chambres = 32 chambres, numérotées "étage-chambre" (ex: 1-3)
    cur.execute("SELECT COUNT(*) AS n FROM chambres")
    if cur.fetchone()["n"] == 0:
        chambres_defaut = []
        for etage in range(1, 5):
            for i in range(1, 9):
                numero = f"{etage}-{i}"
                if i == 1:
                    type_ch, prix, max_p = "Suite", 180.0, 2
                elif i == 2:
                    type_ch, prix, max_p = "Double", 120.0, 2
                else:
                    type_ch, prix, max_p = "Simple", 80.0, 1
                chambres_defaut.append((numero, type_ch, prix, "Libre", "", "", max_p))
        cur.executemany(
            "INSERT INTO chambres (numero, type, prix, etat, description, photo, max_personnes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            chambres_defaut,
        )
        conn.commit()

    # Migration: populate montant_ht and tva for existing factures
    rows = conn.execute(
        "SELECT id, montant_total, remise FROM factures WHERE montant_ht=0 AND montant_total>0"
    ).fetchall()
    for r in rows:
        total = float(r["montant_total"])
        remise = float(r["remise"] or 0)
        ht = round(total - remise * 100 / 107, 3)
        tva_val = round(total - ht, 3)
        if ht < 0:
            ht = 0.0
            tva_val = 0.0
        conn.execute(
            "UPDATE factures SET montant_ht=?, tva=? WHERE id=?",
            (ht, tva_val, r["id"])
        )
    if rows:
        conn.commit()

    # Migration: populate client info on existing factures from JOINs
    rows = conn.execute(
        "SELECT f.id, c.type_identifiant, c.numero_identifiant, c.adresse, "
        "ch.numero AS chambre_numero "
        "FROM factures f "
        "LEFT JOIN clients c ON c.id = f.client_id "
        "LEFT JOIN sejours s ON s.id = f.sejour_id "
        "LEFT JOIN chambres ch ON ch.id = s.chambre_id "
        "WHERE f.chambre_numero = '' OR f.chambre_numero IS NULL "
        "OR f.numero_identifiant = '' OR f.numero_identifiant IS NULL"
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE factures SET type_identifiant=?, numero_identifiant=?, "
            "adresse=?, chambre_numero=? WHERE id=?",
            (r["type_identifiant"] or "", r["numero_identifiant"] or "",
             r["adresse"] or "", r["chambre_numero"] or "", r["id"])
        )
    if rows:
        conn.commit()

    # Migration: populate venant_de/allant_a on existing factures
    rows = conn.execute(
        "SELECT f.id, c.venant_de, c.allant_a "
        "FROM factures f "
        "LEFT JOIN clients c ON c.id = f.client_id "
        "WHERE (f.venant_de = '' OR f.venant_de IS NULL) "
        "AND c.id IS NOT NULL"
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE factures SET venant_de=?, allant_a=? WHERE id=?",
            (r["venant_de"] or "", r["allant_a"] or "", r["id"])
        )
    if rows:
        conn.commit()

    # Migration: set max_personnes based on room type
    type_capacity = {"Simple": 1, "Double": 2, "Suite": 2, "Familiale": 4}
    for type_ch, max_p in type_capacity.items():
        conn.execute(
            "UPDATE chambres SET max_personnes=? WHERE type=? AND (max_personnes=1 OR max_personnes IS NULL)",
            (max_p, type_ch)
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


def add_chambre(numero, type_ch, prix, etat="Libre", description="", photo="", max_personnes=1):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chambres (numero, type, prix, etat, description, photo, max_personnes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (numero, type_ch, prix, etat, description, photo, max_personnes),
    )
    conn.commit()
    conn.close()


def update_chambre(chambre_id, numero, type_ch, prix, etat, description, photo="", max_personnes=1):
    conn = get_connection()
    conn.execute(
        "UPDATE chambres SET numero=?, type=?, prix=?, etat=?, description=?, photo=?, max_personnes=? "
        "WHERE id=?",
        (numero, type_ch, prix, etat, description, photo, max_personnes, chambre_id),
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
# Photos des chambres (multiples)
# ---------------------------------------------------------------------------
def get_chambre_photos(chambre_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chambre_photos WHERE chambre_id=? ORDER BY ordre, id",
        (chambre_id,)
    ).fetchall()
    conn.close()
    return rows


def add_chambre_photo(chambre_id, photo_path, ordre=0):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chambre_photos (chambre_id, photo_path, ordre) VALUES (?, ?, ?)",
        (chambre_id, photo_path, ordre),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def delete_chambre_photo(photo_id):
    conn = get_connection()
    conn.execute("DELETE FROM chambre_photos WHERE id=?", (photo_id,))
    conn.commit()
    conn.close()


def set_chambre_photos(chambre_id, paths):
    """Replace all photos for a room with a new list of paths."""
    conn = get_connection()
    conn.execute("DELETE FROM chambre_photos WHERE chambre_id=?", (chambre_id,))
    for i, p in enumerate(paths):
        conn.execute(
            "INSERT INTO chambre_photos (chambre_id, photo_path, ordre) VALUES (?, ?, ?)",
            (chambre_id, p, i),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
def get_clients():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM clients ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def get_client(client_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM clients WHERE id = ?", (client_id,)
    ).fetchone()
    conn.close()
    return row


def client_exists_by_identifiant(numero_identifiant, exclude_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if exclude_id:
        cur.execute(
            "SELECT COUNT(*) FROM clients WHERE numero_identifiant=? AND id!=?",
            (numero_identifiant, exclude_id),
        )
    else:
        cur.execute(
            "SELECT COUNT(*) FROM clients WHERE numero_identifiant=?",
            (numero_identifiant,),
        )
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def add_client(data):
    """data: dict with personal info keys. Room is managed via sejours."""
    if client_exists_by_identifiant(data["numero_identifiant"]):
        raise ValueError(
            f"Un client avec le numéro d'identifiant '{data['numero_identifiant']}' existe déjà."
        )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clients (
            nom, prenom, type_identifiant, numero_identifiant,
            date_naissance, lieu_naissance, adresse, telephone,
            venant_de, allant_a
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["nom"], data["prenom"], data["type_identifiant"],
            data["numero_identifiant"], data.get("date_naissance", ""),
            data.get("lieu_naissance", ""), data.get("adresse", ""),
            data.get("telephone", ""), data.get("venant_de", ""),
            data.get("allant_a", ""),
        ),
    )
    client_id = cur.lastrowid
    conn.commit()
    conn.close()
    return client_id


def get_client_by_identifiant(numero_identifiant):
    """Lookup existing client by CIN/passport/cart de sejour for auto-fill."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM clients WHERE numero_identifiant=?",
        (numero_identifiant,),
    ).fetchone()
    conn.close()
    return row


def update_client(client_id, data):
    if client_exists_by_identifiant(data["numero_identifiant"], exclude_id=client_id):
        raise ValueError(
            f"Un autre client avec le numéro d'identifiant '{data['numero_identifiant']}' existe déjà."
        )
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE clients SET
            nom=?, prenom=?, type_identifiant=?, numero_identifiant=?,
            date_naissance=?, lieu_naissance=?, adresse=?, telephone=?,
            venant_de=?, allant_a=?
        WHERE id=?
        """,
        (
            data["nom"], data["prenom"], data["type_identifiant"],
            data["numero_identifiant"], data.get("date_naissance", ""),
            data.get("lieu_naissance", ""), data.get("adresse", ""),
            data.get("telephone", ""), data.get("venant_de", ""),
            data.get("allant_a", ""),
            client_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_client(client_id):
    conn = get_connection()
    cur = conn.cursor()
    # Free any rooms from active sejours before deleting
    cur.execute(
        "UPDATE chambres SET etat='Libre' WHERE id IN "
        "(SELECT chambre_id FROM sejours WHERE client_id=? AND statut='En cours')",
        (client_id,),
    )
    cur.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Séjours
# ---------------------------------------------------------------------------
def add_sejour(client_id, chambre_id, date_entree, date_sortie=None,
               parent_sejour_id=None):
    """Crée un séjour.

    * parent_sejour_id=None  → séjour principal (seul autorisé si chambre Libre).
    * parent_sejour_id=id    → compagnon du groupe (toujours autorisé si le
      séjour parent est actif dans la même chambre).
    """
    conn = get_connection()
    cur = conn.cursor()

    chambre = cur.execute(
        "SELECT max_personnes, etat FROM chambres WHERE id=?", (chambre_id,)
    ).fetchone()

    if parent_sejour_id is None:
        # --- Séjour principal : la chambre doit être Libre ---
        if chambre and chambre["etat"] != "Libre":
            conn.close()
            raise ValueError(
                f"La chambre est déjà occupée. "
                f"Un groupe ne peut réserver une chambre que lorsqu'elle est Libre.")
    else:
        # --- Compagnon : vérifier que le parent est actif dans la même chambre ---
        parent = cur.execute(
            "SELECT id, chambre_id, statut FROM sejours WHERE id=?",
            (parent_sejour_id,),
        ).fetchone()
        if not parent or parent["statut"] != "En cours":
            conn.close()
            raise ValueError(
                "Le séjour parent n'existe pas ou est déjà terminé.")
        if parent["chambre_id"] != chambre_id:
            conn.close()
            raise ValueError(
                "Le séjour parent n'est pas dans la même chambre.")

    ds = date_sortie or ""
    cur.execute(
        "INSERT INTO sejours (client_id, chambre_id, date_entree, date_sortie, statut, parent_sejour_id) "
        "VALUES (?, ?, ?, ?, 'En cours', ?)",
        (client_id, chambre_id, date_entree, ds, parent_sejour_id),
    )
    sejour_id = cur.lastrowid

    # Mettre la chambre en Occupée si c'est un séjour principal
    if parent_sejour_id is None:
        cur.execute("UPDATE chambres SET etat='Occupée' WHERE id=?", (chambre_id,))

    conn.commit()
    conn.close()
    return sejour_id


def get_sejour(sejour_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT s.*, c.nom, c.prenom, c.numero_identifiant,
               ch.numero AS chambre_numero, ch.prix AS chambre_prix
        FROM sejours s
        LEFT JOIN clients c ON c.id = s.client_id
        LEFT JOIN chambres ch ON ch.id = s.chambre_id
        WHERE s.id = ?
        """,
        (sejour_id,),
    ).fetchone()
    conn.close()
    return row


def get_sejours_client(client_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
        FROM sejours s
        LEFT JOIN chambres ch ON ch.id = s.chambre_id
        WHERE s.client_id = ?
        ORDER BY s.date_entree DESC
        """,
        (client_id,),
    ).fetchall()
    conn.close()
    return rows


def get_sejours_actifs():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.*, c.nom, c.prenom, c.numero_identifiant,
               c.type_identifiant, c.adresse, c.venant_de, c.allant_a,
               ch.numero AS chambre_numero, ch.prix AS chambre_prix
        FROM sejours s
        LEFT JOIN clients c ON c.id = s.client_id
        LEFT JOIN chambres ch ON ch.id = s.chambre_id
        WHERE s.statut = 'En cours'
        ORDER BY s.date_entree DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_sejour_actif_client(client_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT s.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix
        FROM sejours s
        LEFT JOIN chambres ch ON ch.id = s.chambre_id
        WHERE s.client_id = ? AND s.statut = 'En cours'
        ORDER BY s.date_entree DESC LIMIT 1
        """,
        (client_id,),
    ).fetchone()
    conn.close()
    return row


def checkout_sejour(sejour_id, date_sortie=None):
    if not date_sortie:
        date_sortie = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.cursor()
    sejour = cur.execute("SELECT chambre_id FROM sejours WHERE id=?", (sejour_id,)).fetchone()
    cur.execute(
        "UPDATE sejours SET statut='Terminé', date_sortie=? WHERE id=?",
        (date_sortie, sejour_id),
    )
    if sejour:
        other_active = cur.execute(
            "SELECT 1 FROM sejours WHERE chambre_id=? AND statut='En cours' AND id!=? LIMIT 1",
            (sejour["chambre_id"], sejour_id)
        ).fetchone()
        if not other_active:
            cur.execute("UPDATE chambres SET etat='Libre' WHERE id=?", (sejour["chambre_id"],))
    conn.commit()
    conn.close()


def auto_checkout_expired():
    """Terminate sejours whose date_sortie has passed and free their rooms."""
    today = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.cursor()
    expired = cur.execute(
        "SELECT id, chambre_id FROM sejours "
        "WHERE statut='En cours' AND date_sortie != '' AND date_sortie <= ?",
        (today,),
    ).fetchall()
    for s in expired:
        cur.execute(
            "UPDATE sejours SET statut='Terminé' WHERE id=?", (s["id"],))
        other_active = cur.execute(
            "SELECT 1 FROM sejours WHERE chambre_id=? AND statut='En cours' AND id!=? LIMIT 1",
            (s["chambre_id"], s["id"])
        ).fetchone()
        if not other_active:
            cur.execute("UPDATE chambres SET etat='Libre' WHERE id=?", (s["chambre_id"],))
    conn.commit()
    conn.close()
    return len(expired)


def auto_cancel_expired_reservations():
    """Auto-cancel RESERVE reservations where date_arrivee has passed."""
    today = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.cursor()
    expired = cur.execute(
        "SELECT id, chambre_id FROM reservations "
        "WHERE statut='RESERVE' AND date_arrivee != '' AND date_arrivee < ?",
        (today,),
    ).fetchall()
    for r in expired:
        cur.execute(
            "UPDATE reservations SET statut='EXPIRE' WHERE id=?", (r["id"],))
        if r["chambre_id"]:
            has_active = cur.execute(
                "SELECT 1 FROM sejours WHERE chambre_id=? AND statut='En cours' LIMIT 1",
                (r["chambre_id"],),
            ).fetchone()
            if not has_active:
                cur.execute(
                    "UPDATE chambres SET etat='Libre' WHERE id=?",
                    (r["chambre_id"],))
    conn.commit()
    conn.close()
    return len(expired)


def delete_sejour(sejour_id):
    conn = get_connection()
    cur = conn.cursor()
    sejour = cur.execute("SELECT chambre_id FROM sejours WHERE id=?", (sejour_id,)).fetchone()
    cur.execute("DELETE FROM sejours WHERE id=?", (sejour_id,))
    if sejour:
        cur.execute("UPDATE chambres SET etat='Libre' WHERE id=?", (sejour["chambre_id"],))
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
                    nom_client="", sejour_id=None,
                    type_identifiant="", numero_identifiant="",
                    adresse="", chambre_numero="",
                    venant_de="", allant_a="",
                    timbre_fiscal=1.0):
    """
    lignes: liste de tuples (description, quantite, prix_unitaire)
    Retourne (facture_id, numero, montant_total)
    remise: pourcentage (%) appliqué sur le sous-total
    TVA = 7% appliquée après remise
    TTC = HT + TVA + timbre_fiscal
    """
    sous_total = 0.0
    lignes_calc = []
    for description, quantite, prix_unitaire in lignes:
        montant = round(float(quantite) * float(prix_unitaire), 3)
        sous_total += montant
        lignes_calc.append((description, quantite, prix_unitaire, montant))
    remise_pct = float(remise or 0)
    remise_amount = round(sous_total * remise_pct / 100, 3) if remise_pct else 0.0
    montant_ht = round(sous_total - remise_amount, 3)
    if montant_ht < 0:
        montant_ht = 0.0
    tva = round(montant_ht * 0.07, 3)
    tf = float(timbre_fiscal or 0)
    montant_total = round(montant_ht + tva + tf, 3)

    numero = get_next_numero_facture()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO factures (numero, client_id, nom_client, date_facture,
                               date_entree, date_sortie, nb_nuits, montant_total,
                               remise, mode_paiement, sejour_id, montant_ht, tva,
                               type_identifiant, numero_identifiant, adresse,
                               chambre_numero, venant_de, allant_a, timbre_fiscal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (numero, client_id, nom_client, date_facture, date_entree, date_sortie,
         nb_nuits, montant_total, remise_pct, mode_paiement, sejour_id,
         montant_ht, tva, type_identifiant, numero_identifiant, adresse,
         chambre_numero, venant_de, allant_a, tf),
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
        SELECT f.*,
               c.nom AS nom, c.prenom AS prenom,
               COALESCE(NULLIF(f.numero_identifiant, ''), c.numero_identifiant, '') AS numero_identifiant,
               COALESCE(NULLIF(f.type_identifiant, ''), c.type_identifiant, '') AS type_identifiant,
               COALESCE(NULLIF(f.adresse, ''), c.adresse, '') AS adresse,
               COALESCE(NULLIF(f.chambre_numero, ''), ch.numero, '') AS chambre_numero,
               ch.prix AS chambre_prix
        FROM factures f
        LEFT JOIN clients c ON c.id = f.client_id
        LEFT JOIN sejours s ON s.id = f.sejour_id
        LEFT JOIN chambres ch ON ch.id = s.chambre_id
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
    row = conn.execute(
        "SELECT montant_paye FROM factures WHERE id=?", (facture_id,)
    ).fetchone()
    ancien = row["montant_paye"] if row else 0.0
    nouveau_total = round(ancien + montant_paye, 3)
    conn.execute(
        "UPDATE factures SET montant_paye=? WHERE id=?",
        (nouveau_total, facture_id)
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
            SELECT r.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix,
                   c.nom AS client_nom, c.prenom AS client_prenom
            FROM reservations r
            LEFT JOIN chambres ch ON ch.id = r.chambre_id
            LEFT JOIN clients c ON c.id = r.client_id
            WHERE r.statut = ?
            ORDER BY r.date_arrivee ASC
            """, (statut,)
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT r.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix,
                   c.nom AS client_nom, c.prenom AS client_prenom
            FROM reservations r
            LEFT JOIN chambres ch ON ch.id = r.chambre_id
            LEFT JOIN clients c ON c.id = r.client_id
            ORDER BY r.date_arrivee ASC
            """
        ).fetchall()
    conn.close()
    return rows


def get_reservation(reservation_id):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT r.*, ch.numero AS chambre_numero, ch.prix AS chambre_prix,
               c.nom AS client_nom, c.prenom AS client_prenom
        FROM reservations r
        LEFT JOIN chambres ch ON ch.id = r.chambre_id
        LEFT JOIN clients c ON c.id = r.client_id
        WHERE r.id = ?
        """, (reservation_id,)
    ).fetchone()
    conn.close()
    return row


def check_reservation_overlap(chambre_id, date_arrivee, date_depart, exclude_id=None):
    """Check if a reservation overlaps with existing ones for the same room."""
    conn = get_connection()
    query = (
        "SELECT id, nom, prenom, date_arrivee, date_depart FROM reservations "
        "WHERE chambre_id=? AND statut='RESERVE' "
        "AND date_arrivee <= ? AND date_depart >= ?"
    )
    params = [chambre_id, date_depart, date_arrivee]
    if exclude_id:
        query += " AND id!=?"
        params.append(exclude_id)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def add_reservation(data):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reservations (
            nom, prenom, telephone, type_identifiant, numero_identifiant,
            date_naissance, lieu_naissance, adresse, venant_de, allant_a,
            chambre_id, date_arrivee, date_depart, nb_personnes, notes, statut,
            client_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["nom"], data["prenom"], data["telephone"],
            data["type_identifiant"], data["numero_identifiant"],
            data.get("date_naissance", ""), data.get("lieu_naissance", ""),
            data.get("adresse", ""), data.get("venant_de", ""),
            data.get("allant_a", ""),
            data["chambre_id"], data["date_arrivee"], data["date_depart"],
            data["nb_personnes"], data["notes"], data.get("statut", "RESERVE"),
            data.get("client_id"),
        )
    )
    if data.get("chambre_id"):
        has_other_rez = cur.execute(
            "SELECT 1 FROM reservations WHERE chambre_id=? AND statut='RESERVE' AND id!=? LIMIT 1",
            (data["chambre_id"], cur.lastrowid)
        ).fetchone()
        has_active_sejour = cur.execute(
            "SELECT 1 FROM sejours WHERE chambre_id=? AND statut='En cours' LIMIT 1",
            (data["chambre_id"],)
        ).fetchone()
        if not has_other_rez and not has_active_sejour:
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
            numero_identifiant=?, date_naissance=?, lieu_naissance=?,
            adresse=?, venant_de=?, allant_a=?,
            chambre_id=?, date_arrivee=?,
            date_depart=?, nb_personnes=?, notes=?, statut=?, client_id=?
        WHERE id=?
        """,
        (
            data["nom"], data["prenom"], data["telephone"],
            data["type_identifiant"], data["numero_identifiant"],
            data.get("date_naissance", ""), data.get("lieu_naissance", ""),
            data.get("adresse", ""), data.get("venant_de", ""),
            data.get("allant_a", ""),
            data["chambre_id"], data["date_arrivee"], data["date_depart"],
            data["nb_personnes"], data["notes"], data.get("statut", "RESERVE"),
            data.get("client_id"),
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


# --- Reservation companions ------------------------------------------------

def add_reservation_companion(reservation_id, data):
    conn = get_connection()
    conn.execute(
        "INSERT INTO reservation_companions "
        "(reservation_id, nom, prenom, type_identifiant, numero_identifiant, "
        "date_naissance, lieu_naissance, adresse, telephone, venant_de, allant_a) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            reservation_id,
            data["nom"], data["prenom"],
            data.get("type_identifiant", "CIN"),
            data.get("numero_identifiant", ""),
            data.get("date_naissance", ""),
            data.get("lieu_naissance", ""),
            data.get("adresse", ""),
            data.get("telephone", ""),
            data.get("venant_de", ""),
            data.get("allant_a", ""),
        ),
    )
    conn.commit()
    conn.close()


def get_reservation_companions(reservation_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM reservation_companions WHERE reservation_id=?",
        (reservation_id,),
    ).fetchall()
    conn.close()
    return rows


def delete_reservation_companions(reservation_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM reservation_companions WHERE reservation_id=?",
        (reservation_id,),
    )
    conn.commit()
    conn.close()

