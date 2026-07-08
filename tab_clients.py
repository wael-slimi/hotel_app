# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import database as db
from database import TYPES_IDENTIFIANT
from widgets import DateEntry, date_str_to_iso, iso_to_date_str
from pdf_facture import generer_fiche_police

# ── Design system palette ──────────────────────────────────────────
BG          = "#F1F3F6"
CARD_BG     = "#FFFFFF"
CARD_BORDER = "#E2E5EA"
TEXT_PRIMARY = "#1E293B"
TEXT_SECONDARY = "#64748B"
PRIMAIRE     = "#4F46E5"
PRIMAIRE_HVR = "#4338CA"
SUCCES       = "#10B981"
ATTENTION    = "#F59E0B"
DANGER       = "#EF4444"
NEUTRE_CLAIR = "#F8FAFC"


class ClientsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.selected_client_id = None
        self.configure(bg=BG)

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Left panel: form card ────────────────────────────────────
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="y", padx=8, pady=8)

        form_card = tk.Frame(left, bg=CARD_BG, bd=0,
                             highlightbackground=CARD_BORDER, highlightthickness=1)
        form_card.pack(fill="y", expand=True)

        tk.Label(form_card, text="Fiche client", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(14, 4))

        self.vars = {}
        r = 0

        # ── Section: Identité ───────────────────────────────────────
        self._section_header(form_card, "Identité", r); r += 1

        self._add_field(form_card, r, "Nom *", "nom"); r += 1
        self._add_field(form_card, r, "Prénom *", "prenom"); r += 1

        tk.Label(form_card, text="Type d'identifiant *", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.vars["type_identifiant"] = tk.StringVar(value=TYPES_IDENTIFIANT[0])
        ttk.Combobox(form_card, textvariable=self.vars["type_identifiant"],
                     values=TYPES_IDENTIFIANT, width=21,
                     state="readonly").grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        self._add_field(form_card, r, "N° identifiant *", "numero_identifiant"); r += 1

        tk.Label(form_card, text="Date de naissance", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.date_naissance = DateEntry(form_card, width=12)
        self.date_naissance.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        self._add_field(form_card, r, "Lieu de naissance", "lieu_naissance"); r += 1

        # ── Section: Coordonnées ────────────────────────────────────
        self._section_header(form_card, "Coordonnées", r); r += 1

        self._add_field(form_card, r, "Adresse", "adresse", width=28); r += 1
        self._add_field(form_card, r, "Téléphone", "telephone"); r += 1
        self._add_field(form_card, r, "Venant de", "venant_de"); r += 1
        self._add_field(form_card, r, "Allant à", "allant_a"); r += 1

        # ── Section: Séjour ─────────────────────────────────────────
        self._section_header(form_card, "Séjour", r); r += 1

        tk.Label(form_card, text="Chambre réservée", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.chambre_var = tk.StringVar()
        self.combo_chambres = ttk.Combobox(
            form_card, textvariable=self.chambre_var, width=21, state="readonly")
        self.combo_chambres.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        tk.Label(form_card, text="Date d'entrée", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.date_entree = DateEntry(form_card, width=12)
        self.date_entree.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        tk.Label(form_card, text="Date de sortie", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.date_sortie = DateEntry(form_card, width=12)
        self.date_sortie.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        tk.Label(form_card, text="Statut", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.statut_var = tk.StringVar(value="En cours")
        ttk.Combobox(form_card, textvariable=self.statut_var,
                     values=["En cours", "Sorti"], width=21,
                     state="readonly").grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        # ── Buttons ─────────────────────────────────────────────────
        btn_frame = tk.Frame(form_card, bg=CARD_BG)
        btn_frame.grid(row=r, column=0, columnspan=2, pady=(12, 14))

        tk.Button(btn_frame, text="Nouveau", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  width=10, command=self.nouveau).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Enregistrer", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", width=10, command=self.enregistrer).pack(
            side="left", padx=3)
        tk.Button(btn_frame, text="Supprimer", bg=DANGER, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground="#DC2626", activeforeground="white",
                  cursor="hand2", width=10, command=self.supprimer).pack(
            side="left", padx=3)

        btn_frame2 = tk.Frame(form_card, bg=CARD_BG)
        btn_frame2.grid(row=r + 1, column=0, columnspan=2, pady=(0, 14))

        tk.Button(btn_frame2, text="Check-out", bg=ATTENTION, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground="#D97706", activeforeground="white",
                  cursor="hand2", width=10, command=self.checkout).pack(
            side="left", padx=3)
        tk.Button(btn_frame2, text="Fiche Police", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  width=10, command=self.imprimer_fiche_police).pack(
            side="left", padx=3)

        # ── Right panel: table card ──────────────────────────────────
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        table_card = tk.Frame(right, bg=CARD_BG, bd=0,
                              highlightbackground=CARD_BORDER, highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        # Search + filter bar
        toolbar = tk.Frame(table_card, bg=CARD_BG)
        toolbar.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(toolbar, text="Recherche", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        search_ent = tk.Entry(toolbar, textvariable=self.search_var, width=22,
                              font=("Segoe UI", 9), bd=1, relief="solid",
                              highlightbackground=CARD_BORDER)
        search_ent.pack(side="left", padx=(4, 12))

        tk.Label(toolbar, text="Filtre", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.filtre_statut = tk.StringVar(value="Tous")
        ttk.Combobox(toolbar, textvariable=self.filtre_statut,
                     values=["Tous", "En cours", "Sorti"], width=12,
                     state="readonly").pack(side="left", padx=4)
        self.filtre_statut.trace_add("write", lambda *a: self.refresh())

        # Treeview
        tree_frame = tk.Frame(table_card, bg=CARD_BG)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        columns = ("id", "nom", "prenom", "identifiant", "chambre",
                   "entree", "sortie", "statut", "solde")
        headers = {
            "id": "ID", "nom": "NOM", "prenom": "PRÉNOM",
            "identifiant": "IDENTIFIANT", "chambre": "CHAMBRE",
            "entree": "ENTRÉE", "sortie": "SORTIE", "statut": "STATUT",
            "solde": "SOLDE (TND)",
        }
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 height=22)
        style = ttk.Style()
        style.configure("Clients.Treeview", font=("Segoe UI", 9), rowheight=28)
        style.configure("Clients.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        foreground=TEXT_SECONDARY)
        self.tree.configure(style="Clients.Treeview")

        for c in columns:
            self.tree.heading(c, text=headers[c])
            width = 50 if c == "id" else 90 if c in ("chambre", "statut") else 100
            self.tree.column(c, width=width, anchor="center")
        self.tree.column("nom", width=110, anchor="w")
        self.tree.column("prenom", width=110, anchor="w")
        self.tree.column("identifiant", width=110, anchor="w")
        self.tree.column("entree", width=85, anchor="center")
        self.tree.column("sortie", width=85, anchor="center")
        self.tree.column("solde", width=110, anchor="center")

        # Zebra striping tags
        self.tree.tag_configure("odd", background=NEUTRE_CLAIR)
        self.tree.tag_configure("even", background=CARD_BG)
        self.tree.tag_configure("en_cours", foreground=SUCCES)
        self.tree.tag_configure("sorti", foreground=TEXT_SECONDARY)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def _section_header(self, parent, title, row):
        lbl = tk.Label(parent, text=title, bg=NEUTRE_CLAIR, fg=PRIMAIRE,
                       font=("Segoe UI", 10, "bold"), anchor="w")
        lbl.grid(row=row, column=0, columnspan=2, sticky="ew",
                 padx=14, pady=(10, 2), ipady=3)
        # Extend background
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

    def _add_field(self, parent, row, label, key, width=24):
        tk.Label(parent, text=label, bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(
            row=row, column=0, sticky="w", padx=18, pady=3)
        var = tk.StringVar()
        widget = tk.Entry(parent, textvariable=var, width=width,
                          font=("Segoe UI", 9), bd=1, relief="solid",
                          highlightbackground=CARD_BORDER)
        widget.grid(row=row, column=1, sticky="w", padx=4, pady=3)
        self.vars[key] = var
        return widget

    # ------------------------------------------------------------------
    def refresh(self):
        chambres = db.get_chambres()
        self.chambres_map = {"": None}
        valeurs = [""]
        current_chambre_id = self._get_current_chambre_id()
        for ch in chambres:
            if ch["etat"] == "Libre" or ch["id"] == current_chambre_id:
                texte = f"{ch['numero']} - {ch['type']} ({ch['prix']} TND)"
                self.chambres_map[texte] = ch["id"]
                valeurs.append(texte)
        self.combo_chambres["values"] = valeurs
        if self.chambre_var.get() not in valeurs:
            self.chambre_var.set("")

        for item in self.tree.get_children():
            self.tree.delete(item)

        statut_filtre = self.filtre_statut.get()
        if statut_filtre == "Tous":
            clients = db.get_clients()
        else:
            clients = db.get_clients(statut_filtre)

        recherche = self.search_var.get().strip().lower()

        for i, c in enumerate(clients):
            ligne = (c["nom"], c["prenom"], c["numero_identifiant"],
                     c["chambre_numero"] or "")
            if recherche and not any(recherche in str(v).lower() for v in ligne):
                continue

            # Status badge text
            statut = c["statut"]
            if statut == "En cours":
                statut_txt = "En cours"
            else:
                statut_txt = "Sorti"

            solde_val = c["solde"] or 0.0
            solde_txt = f"{solde_val:.3f}" if solde_val else "0.000"

            row_tag = "odd" if i % 2 else "even"
            statut_tag = "en_cours" if statut == "En cours" else "sorti"

            self.tree.insert("", "end", iid=str(c["id"]),
                             tags=(row_tag, statut_tag), values=(
                c["id"], c["nom"], c["prenom"], c["numero_identifiant"],
                c["chambre_numero"] or "-",
                iso_to_date_str(c["date_entree"]) or c["date_entree"],
                iso_to_date_str(c["date_sortie"]) or c["date_sortie"],
                statut_txt, solde_txt,
            ))

    def _get_current_chambre_id(self):
        if not self.selected_client_id:
            return None
        client = db.get_client(self.selected_client_id)
        return client["chambre_id"] if client else None

    def on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        client_id = int(selection[0])
        self.selected_client_id = client_id
        client = db.get_client(client_id)
        if not client:
            return

        self.vars["nom"].set(client["nom"])
        self.vars["prenom"].set(client["prenom"])
        self.vars["type_identifiant"].set(client["type_identifiant"])
        self.vars["numero_identifiant"].set(client["numero_identifiant"])
        self.vars["lieu_naissance"].set(client["lieu_naissance"])
        self.vars["adresse"].set(client["adresse"])
        self.vars["telephone"].set(client["telephone"])
        self.vars["venant_de"].set(client["venant_de"])
        self.vars["allant_a"].set(client["allant_a"])
        self.statut_var.set(client["statut"])

        if client["date_naissance"]:
            self.date_naissance.set(iso_to_date_str(client["date_naissance"]))
        else:
            self.date_naissance.set("")
        if client["date_entree"]:
            self.date_entree.set(iso_to_date_str(client["date_entree"]))
        if client["date_sortie"]:
            self.date_sortie.set(iso_to_date_str(client["date_sortie"]))

        self.refresh_chambre_combo(client)

    def refresh_chambre_combo(self, client):
        chambres = db.get_chambres()
        valeurs = [""]
        self.chambres_map = {"": None}
        for ch in chambres:
            if ch["etat"] == "Libre" or ch["id"] == client["chambre_id"]:
                texte = f"{ch['numero']} - {ch['type']} ({ch['prix']} TND)"
                self.chambres_map[texte] = ch["id"]
                valeurs.append(texte)
        self.combo_chambres["values"] = valeurs
        if client["chambre_id"]:
            for texte, cid in self.chambres_map.items():
                if cid == client["chambre_id"]:
                    self.chambre_var.set(texte)
                    return
        self.chambre_var.set("")

    def nouveau(self):
        self.selected_client_id = None
        for var in self.vars.values():
            var.set("")
        self.vars["type_identifiant"].set(TYPES_IDENTIFIANT[0])
        self.date_naissance.set("")
        self.date_entree.set_date(date.today())
        self.date_sortie.set_date(date.today())
        self.statut_var.set("En cours")
        self.chambre_var.set("")
        self.refresh()
        self.tree.selection_remove(self.tree.selection())

    def _collect_form_data(self):
        nom = self.vars["nom"].get().strip()
        prenom = self.vars["prenom"].get().strip()
        numero_id = self.vars["numero_identifiant"].get().strip()

        if not nom or not prenom or not numero_id:
            messagebox.showerror(
                "Champs manquants",
                "Les champs Nom, Prénom et N° d'identifiant sont obligatoires.")
            return None

        erreur_format = db.validate_identifiant_format(
            self.vars["type_identifiant"].get(), numero_id
        )
        if erreur_format:
            messagebox.showerror("Erreur", erreur_format)
            return None

        date_naissance_iso = date_str_to_iso(self.date_naissance.get())
        date_entree_iso = date_str_to_iso(self.date_entree.get())
        date_sortie_iso = date_str_to_iso(self.date_sortie.get())

        today = date.today().isoformat()

        if date_naissance_iso and date_naissance_iso > today:
            messagebox.showerror("Erreur", "La date de naissance ne peut pas être dans le futur.")
            return None

        if date_entree_iso and date_entree_iso < today:
            messagebox.showerror("Erreur", "La date d'entrée ne peut pas être dans le passé.")
            return None

        if date_entree_iso and date_sortie_iso and date_sortie_iso < date_entree_iso:
            messagebox.showerror(
                "Erreur", "La date de sortie doit être après la date d'entrée."
            )
            return None

        chambre_texte = self.chambre_var.get()
        chambre_id = self.chambres_map.get(chambre_texte)

        data = {
            "nom": nom,
            "prenom": prenom,
            "type_identifiant": self.vars["type_identifiant"].get(),
            "numero_identifiant": numero_id,
            "date_naissance": date_naissance_iso,
            "lieu_naissance": self.vars["lieu_naissance"].get().strip(),
            "adresse": self.vars["adresse"].get().strip(),
            "telephone": self.vars["telephone"].get().strip(),
            "venant_de": self.vars["venant_de"].get().strip(),
            "allant_a": self.vars["allant_a"].get().strip(),
            "chambre_id": chambre_id,
            "date_entree": date_entree_iso,
            "date_sortie": date_sortie_iso,
            "statut": self.statut_var.get(),
        }
        return data

    def enregistrer(self):
        data = self._collect_form_data()
        if data is None:
            return

        try:
            if self.selected_client_id:
                db.update_client(self.selected_client_id, data)
                messagebox.showinfo("Succès", "Client mis à jour avec succès.")
            else:
                new_id = db.add_client(data)
                self.selected_client_id = new_id
                messagebox.showinfo("Succès", "Client ajouté avec succès.")
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))
            return

        self.refresh()
        self.app.refresh_rooms_tab()

    def supprimer(self):
        if not self.selected_client_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        if not messagebox.askyesno(
                "Confirmation",
                "Voulez-vous vraiment supprimer ce client ? "
                "Sa chambre sera libérée."):
            return
        db.delete_client(self.selected_client_id)
        self.nouveau()
        self.refresh()
        self.app.refresh_rooms_tab()

    def checkout(self):
        if not self.selected_client_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        client = db.get_client(self.selected_client_id)
        if not client:
            return
        if client["statut"] == "Sorti":
            messagebox.showinfo("Information", "Ce client est déjà sorti.")
            return

        if not messagebox.askyesno(
                "Confirmation",
                f"Confirmer la sortie de {client['prenom']} {client['nom']} "
                f"et libérer la chambre {client['chambre_numero'] or ''} ?"):
            return

        data = dict(client)
        data["statut"] = "Sorti"
        data["date_sortie"] = date.today().strftime("%Y-%m-%d")
        db.update_client(self.selected_client_id, data)
        self.refresh()
        self.app.refresh_rooms_tab()
        messagebox.showinfo("Succès", "Le client est marqué comme sorti et la chambre est libérée.")

    def imprimer_fiche_police(self):
        if not self.selected_client_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        client = db.get_client(self.selected_client_id)
        if not client:
            messagebox.showerror("Erreur", "Client introuvable.")
            return
        try:
            chemin = generer_fiche_police(dict(client))
            messagebox.showinfo("Succès", f"Fiche Police générée :\n{chemin}")
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Impossible de générer la fiche :\n{e}")
