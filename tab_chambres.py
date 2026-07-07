# -*- coding: utf-8 -*-
import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageTk, ImageDraw

import database as db
from database import ETATS_CHAMBRE, get_connection
from widgets import iso_to_date_str, _formater_prix

PHOTOS_DIR = Path(__file__).parent / "photos_chambres"
PHOTOS_DIR.mkdir(exist_ok=True)

THUMB_SIZE = (150, 90)
NB_COLONNES = 4

COULEURS_ETAT = {
    "Libre": "#4CAF50",
    "Occupée": "#E53935",
    "Réservée": "#FB8C00",
    "Maintenance": "#9E9E9E",
}


def _placeholder_thumbnail():
    img = Image.new("RGB", THUMB_SIZE, "#d9d9d9")
    draw = ImageDraw.Draw(img)
    text = "Pas de photo"
    bbox = draw.textbbox((0, 0), text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((THUMB_SIZE[0] - tw) / 2, (THUMB_SIZE[1] - th) / 2),
        text, fill="#888888",
    )
    return img


def _load_thumbnail(photo_path):
    if photo_path:
        p = Path(photo_path)
        if p.is_file():
            try:
                img = Image.open(p)
                img = img.convert("RGB")
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                canvas = Image.new("RGB", THUMB_SIZE, "#ececec")
                x = (THUMB_SIZE[0] - img.width) // 2
                y = (THUMB_SIZE[1] - img.height) // 2
                canvas.paste(img, (x, y))
                return canvas
            except Exception:
                pass
    return _placeholder_thumbnail()


class RoomsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.selected_chambre_id = None
        self._thumb_cache = {}

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        legend_frame = ttk.Frame(self)
        legend_frame.pack(fill="x", padx=8, pady=(8, 0))

        ttk.Label(legend_frame, text="Légende :",
                  font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        for etat, couleur in COULEURS_ETAT.items():
            carre = tk.Label(legend_frame, text="  ", bg=couleur)
            carre.pack(side="left", padx=(0, 4))
            ttk.Label(legend_frame, text=etat).pack(side="left", padx=(0, 12))

        ttk.Button(legend_frame, text="+ Ajouter une chambre",
                   command=self.ajouter_chambre).pack(side="right")

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(canvas_frame, bg="#F5F5F5",
                                 highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                        command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.grid_frame = tk.Frame(self.canvas, bg="#F5F5F5")
        self.grid_window = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw")

        self.grid_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.recap_var = tk.StringVar()
        ttk.Label(self, textvariable=self.recap_var,
                  font=("Segoe UI", 10, "bold")).pack(pady=(0, 8))

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.grid_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------
    def refresh(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._thumb_cache.clear()

        chambres = db.get_chambres()

        row_index = 0
        col = 0
        etage_courant = None

        for ch in chambres:
            etage = ch["numero"].split("-")[0] if "-" in ch["numero"] else "?"

            if etage != etage_courant:
                etage_courant = etage
                if row_index > 0:
                    row_index += 1
                lbl_etage = tk.Label(
                    self.grid_frame, text=f"Étage {etage_courant}",
                    bg="#F5F5F5", fg="#1F4E79",
                    font=("Segoe UI", 12, "bold"), anchor="w")
                lbl_etage.grid(row=row_index, column=0, columnspan=NB_COLONNES,
                                sticky="w", padx=4, pady=(10, 4))
                row_index += 1
                col = 0

            self._creer_tile(ch, row_index, col)
            col += 1
            if col >= NB_COLONNES:
                col = 0
                row_index += 1

        for c in range(NB_COLONNES):
            self.grid_frame.grid_columnconfigure(c, weight=1)

        occ, total = db.taux_occupation()
        libre = total - occ
        self.recap_var.set(
            f"Total chambres : {total}   |   Occupées : {occ}   |   "
            f"Libres : {libre}   |   Taux d'occupation : "
            f"{(occ / total * 100) if total else 0:.1f} %"
        )

    # ------------------------------------------------------------------
    def _creer_tile(self, chambre, row, col):
        couleur = COULEURS_ETAT.get(chambre["etat"], "#BDBDBD")

        tile = tk.Frame(self.grid_frame, bg="white", bd=1, relief="solid",
                        width=200, height=170, cursor="hand2")
        tile.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        tile.grid_propagate(False)

        pil_img = _load_thumbnail(chambre.get("photo", ""))
        tk_img = ImageTk.PhotoImage(pil_img)
        self._thumb_cache[chambre["id"]] = tk_img

        lbl_photo = tk.Label(tile, image=tk_img, bg="white")
        lbl_photo.pack(pady=(6, 4))

        lbl_numero = tk.Label(tile, text=f"Chambre {chambre['numero']}",
                               font=("Segoe UI", 10, "bold"), bg="white")
        lbl_numero.pack()

        statut_frame = tk.Frame(tile, bg="white")
        statut_frame.pack(pady=(2, 6))

        dot = tk.Canvas(statut_frame, width=12, height=12, bg="white",
                         highlightthickness=0)
        dot.create_oval(2, 2, 12, 12, fill=couleur, outline=couleur)
        dot.pack(side="left", padx=(0, 4))

        lbl_etat = tk.Label(statut_frame, text=chambre["etat"],
                             font=("Segoe UI", 8), fg="#555555", bg="white")
        lbl_etat.pack(side="left")

        for widget in (tile, lbl_photo, lbl_numero, statut_frame, dot, lbl_etat):
            widget.bind("<Button-1>",
                        lambda e, c=chambre: self.afficher_occupant(c))
            widget.bind("<Button-3>",
                        lambda e, c=chambre: self.ouvrir_details(c))

    # ------------------------------------------------------------------
    def afficher_occupant(self, chambre):
        win = tk.Toplevel(self)
        win.title(f"Chambre {chambre['numero']} — Détails occupation")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        BLEU = "#2C3E6B"
        header = tk.Frame(win, bg=BLEU)
        header.pack(fill="x")
        tk.Label(
            header,
            text=f"Chambre {chambre['numero']} — {chambre['etat']}",
            bg=BLEU, fg="white",
            font=("Segoe UI", 13, "bold")
        ).pack(pady=12, padx=16)

        frame = ttk.Frame(win)
        frame.pack(padx=16, pady=12)

        def ligne(label, valeur, row):
            ttk.Label(frame, text=label,
                      font=("Segoe UI", 9, "bold")).grid(
                row=row, column=0, sticky="w", padx=6, pady=3)
            ttk.Label(frame, text=valeur or "—").grid(
                row=row, column=1, sticky="w", padx=6, pady=3)

        if chambre["etat"] == "Occupée":
            conn = get_connection()
            client = conn.execute(
                """
                SELECT c.*, ch.numero AS chambre_numero
                FROM clients c
                JOIN chambres ch ON ch.id = c.chambre_id
                WHERE c.chambre_id = ? AND c.statut = 'En cours'
                ORDER BY c.id DESC LIMIT 1
                """, (chambre["id"],)
            ).fetchone()
            conn.close()

            if client:
                ligne("Nom", f"{client['prenom']} {client['nom']}", 0)
                ligne("Identifiant",
                      f"{client['type_identifiant']} : {client['numero_identifiant']}", 1)
                ligne("Téléphone", client["telephone"], 2)
                ligne("Venant de", client["venant_de"], 3)
                ligne("Allant à", client["allant_a"], 4)
                ligne("Date d'entrée",
                      iso_to_date_str(client["date_entree"]) or client["date_entree"], 5)
                ligne("Date de sortie prévue",
                      iso_to_date_str(client["date_sortie"]) or client["date_sortie"], 6)
                try:
                    sortie = datetime.strptime(client["date_sortie"], "%Y-%m-%d").date()
                    restant = (sortie - date.today()).days
                    texte = f"{restant} nuit(s)" if restant > 0 else "Départ prévu aujourd'hui"
                    ligne("Nuits restantes", texte, 7)
                except Exception:
                    pass
            else:
                ttk.Label(frame, text="Aucun client trouvé.").grid(
                    row=0, column=0, columnspan=2, pady=8)

        elif chambre["etat"] == "Réservée":
            conn = get_connection()
            rez = conn.execute(
                """
                SELECT * FROM reservations
                WHERE chambre_id = ? AND statut = 'RESERVE'
                ORDER BY date_arrivee ASC LIMIT 1
                """, (chambre["id"],)
            ).fetchone()
            conn.close()

            if rez:
                ligne("Nom", f"{rez['prenom']} {rez['nom']}", 0)
                ligne("Téléphone", rez["telephone"], 1)
                ligne("Identifiant",
                      f"{rez['type_identifiant']} : {rez['numero_identifiant']}", 2)
                ligne("Nb. personnes", str(rez["nb_personnes"]), 3)
                ligne("Date d'arrivée",
                      iso_to_date_str(rez["date_arrivee"]) or rez["date_arrivee"], 4)
                ligne("Date de départ",
                      iso_to_date_str(rez["date_depart"]) or rez["date_depart"], 5)
                ligne("Notes", rez["notes"], 6)
                try:
                    arrivee = datetime.strptime(rez["date_arrivee"], "%Y-%m-%d").date()
                    jours = (arrivee - date.today()).days
                    if jours > 0:
                        texte = f"Dans {jours} jour(s)"
                    elif jours == 0:
                        texte = "Aujourd'hui"
                    else:
                        texte = f"En retard de {abs(jours)} jour(s)"
                    ligne("Arrivée prévue", texte, 7)
                except Exception:
                    pass
            else:
                ttk.Label(frame, text="Aucune réservation trouvée.").grid(
                    row=0, column=0, columnspan=2, pady=8)

        ttk.Button(win, text="Fermer", command=win.destroy).pack(pady=10)

    # ------------------------------------------------------------------
    def ajouter_chambre(self):
        self._formulaire_chambre(None)

    def ouvrir_details(self, chambre):
        self._formulaire_chambre(chambre)

    # ------------------------------------------------------------------
    def _formulaire_chambre(self, chambre):
        est_edition = chambre is not None
        win = tk.Toplevel(self)
        win.title("Chambre" if not est_edition else f"Chambre {chambre['numero']}")
        win.resizable(False, False)
        win.transient(self)
        win.wait_visibility()
        win.grab_set()

        pad = {"padx": 10, "pady": 6}

        # --- Numéro ---
        tk.Label(win, text="N° de chambre *").grid(row=0, column=0, sticky="e", **pad)
        numero_var = tk.StringVar(value=chambre["numero"] if est_edition else "")
        tk.Entry(win, textvariable=numero_var, width=25).grid(
            row=0, column=1, columnspan=2, sticky="w", **pad)

        # --- Type ---
        tk.Label(win, text="Type").grid(row=1, column=0, sticky="e", **pad)
        type_var = tk.StringVar(value=chambre["type"] if est_edition else "Simple")
        ttk.Combobox(win, textvariable=type_var,
                     values=["Simple", "Double", "Suite", "Familiale"],
                     width=22, state="normal").grid(
            row=1, column=1, columnspan=2, sticky="w", **pad)

        # --- Prix ---
        tk.Label(win, text="Prix / nuit (TND) *").grid(row=2, column=0, sticky="e", **pad)
        prix_var = tk.StringVar(
            value=f"{chambre['prix']:.3f}".replace(".", ",") if est_edition else "0,000"
        )
        prix_entry = tk.Entry(win, textvariable=prix_var, width=25)
        prix_entry.grid(row=2, column=1, columnspan=2, sticky="w", **pad)
        prix_entry.bind("<FocusOut>", lambda e: _formater_prix(prix_var))

        # --- État ---
        tk.Label(win, text="État").grid(row=3, column=0, sticky="e", **pad)
        etat_var = tk.StringVar(value=chambre["etat"] if est_edition else "Libre")
        ttk.Combobox(win, textvariable=etat_var, values=db.ETATS_CHAMBRE,
                     width=22, state="readonly").grid(
            row=3, column=1, columnspan=2, sticky="w", **pad)

        # --- Description ---
        tk.Label(win, text="Description").grid(row=4, column=0, sticky="ne", **pad)
        desc_var = tk.StringVar(value=chambre["description"] if est_edition else "")
        tk.Entry(win, textvariable=desc_var, width=25).grid(
            row=4, column=1, columnspan=2, sticky="w", **pad)

        # ------------------------------------------------------------
        # Photo
        # ------------------------------------------------------------
        tk.Label(win, text="Image").grid(row=5, column=0, sticky="ne", **pad)

        preview_label = tk.Label(win, bg="#ececec", bd=1, relief="solid")
        preview_label.grid(row=5, column=1, sticky="w", padx=10, pady=6)

        photo_var = tk.StringVar(
            value=chambre.get("photo", "") if est_edition else ""
        )
        preview_ref = {"img": None}

        def rafraichir_preview():
            pil_img = _load_thumbnail(photo_var.get())
            tk_img = ImageTk.PhotoImage(pil_img)
            preview_ref["img"] = tk_img
            preview_label.configure(image=tk_img)

        rafraichir_preview()

        def choisir_fichier():
            path = filedialog.askopenfilename(
                title="Choisir une image",
                filetypes=[("Images", "*.jpg *.jpeg *.png"), ("Tous", "*.*")]
            )
            if not path:
                return
            src = Path(path)
            try:
                dest = PHOTOS_DIR / src.name
                if dest.exists() and dest.resolve() != src.resolve():
                    dest = PHOTOS_DIR / f"{src.stem}_{numero_var.get() or 'chambre'}{src.suffix}"
                shutil.copy2(src, dest)
                photo_var.set(str(dest))
                rafraichir_preview()
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de copier l'image :\n{e}")

        def coller_chemin():
            saisie = filedialog.askopenfilename(
                title="Coller le chemin ou sélectionner une image",
                filetypes=[("Images", "*.jpg *.jpeg *.png"), ("Tous", "*.*")]
            )
            if saisie:
                photo_var.set(saisie)
                rafraichir_preview()

        btn_frame = tk.Frame(win)
        btn_frame.grid(row=5, column=2, sticky="w", padx=10, pady=6)
        tk.Button(btn_frame, text="Parcourir...", command=choisir_fichier).pack(fill="x", pady=(0, 4))
        tk.Button(btn_frame, text="Coller chemin", command=coller_chemin).pack(fill="x")

        # ------------------------------------------------------------
        # Actions
        # ------------------------------------------------------------
        def enregistrer():
            numero = numero_var.get().strip()
            if not numero:
                messagebox.showerror("Erreur", "Le numéro de chambre est obligatoire.")
                return
            try:
                prix = float(prix_var.get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Erreur", "Le prix doit être un nombre valide.")
                return

            try:
                if not est_edition:
                    db.add_chambre(numero, type_var.get(), prix, etat_var.get(),
                                   desc_var.get(), photo_var.get())
                else:
                    db.update_chambre(chambre["id"], numero, type_var.get(),
                                       prix, etat_var.get(), desc_var.get(),
                                       photo_var.get())
            except Exception as exc:
                messagebox.showerror("Erreur", f"Impossible d'enregistrer : {exc}")
                return

            win.destroy()
            self.refresh()
            self.app.refresh_clients_tab()

        def supprimer():
            if not est_edition:
                return
            if not messagebox.askyesno(
                    "Confirmation",
                    f"Supprimer la chambre {chambre['numero']} ?"):
                return
            try:
                db.delete_chambre(chambre["id"])
            except Exception as exc:
                messagebox.showerror("Erreur", f"Impossible de supprimer : {exc}")
                return
            win.destroy()
            self.refresh()
            self.app.refresh_clients_tab()

        action_frame = tk.Frame(win)
        action_frame.grid(row=6, column=0, columnspan=3, pady=(10, 12))
        tk.Button(action_frame, text="Enregistrer", width=12,
                  command=enregistrer).pack(side="left", padx=6)
        if est_edition:
            tk.Button(action_frame, text="Supprimer", width=12,
                      command=supprimer).pack(side="left", padx=6)
        tk.Button(action_frame, text="Annuler", width=12,
                  command=win.destroy).pack(side="left", padx=6)
