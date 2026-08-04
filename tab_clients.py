# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
        # ── Left panel: scrollable form card ─────────────────────────
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="y", padx=8, pady=8)

        canvas = tk.Canvas(left, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(left, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=BG)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _on_button4(event):
            canvas.yview_scroll(-1, "units")
        def _on_button5(event):
            canvas.yview_scroll(1, "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_button4)
        canvas.bind("<Button-5>", _on_button5)
        self.scroll_frame.bind("<MouseWheel>", _on_mousewheel)
        self.scroll_frame.bind("<Button-4>", _on_button4)
        self.scroll_frame.bind("<Button-5>", _on_button5)

        form_card = tk.Frame(self.scroll_frame, bg=CARD_BG, bd=0,
                             highlightbackground=CARD_BORDER, highlightthickness=1)
        form_card.pack(fill="both", expand=True)

        tk.Label(form_card, text="Fiche client", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(14, 4))

        form_grid = tk.Frame(form_card, bg=CARD_BG)
        form_grid.pack(fill="both", expand=True)

        self.vars = {}
        r = 0

        # ── Section: Identité ───────────────────────────────────────
        self._section_header(form_grid, "Identité", r); r += 1

        self._add_field(form_grid, r, "Nom *", "nom"); r += 1
        self._add_field(form_grid, r, "Prénom *", "prenom"); r += 1

        tk.Label(form_grid, text="Type d'identifiant *", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.vars["type_identifiant"] = tk.StringVar(value=TYPES_IDENTIFIANT[0])
        ttk.Combobox(form_grid, textvariable=self.vars["type_identifiant"],
                     values=TYPES_IDENTIFIANT, width=21,
                     state="readonly").grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        self._add_field(form_grid, r, "N° identifiant *", "numero_identifiant"); r += 1

        tk.Label(form_grid, text="Date de naissance", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.date_naissance = DateEntry(form_grid, width=12)
        self.date_naissance.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        self._add_field(form_grid, r, "Lieu de naissance", "lieu_naissance"); r += 1

        # ── Section: Coordonnées ────────────────────────────────────
        self._section_header(form_grid, "Coordonnées", r); r += 1

        self._add_field(form_grid, r, "Adresse", "adresse", width=28); r += 1
        self._add_field(form_grid, r, "Téléphone", "telephone"); r += 1
        self._add_field(form_grid, r, "Venant de", "venant_de"); r += 1
        self._add_field(form_grid, r, "Allant à", "allant_a"); r += 1

        # ── Section: Chambre ────────────────────────────────────────
        self._section_header(form_grid, "Chambre", r); r += 1

        tk.Label(form_grid, text="Assigner une chambre", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.chambre_var = tk.StringVar(value="— Aucune —")
        self.chambre_map = {"— Aucune —": None}
        self.chambre_combo = ttk.Combobox(
            form_grid, textvariable=self.chambre_var,
            values=["— Aucune —"], width=28, state="readonly")
        self.chambre_combo.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        self.chambre_var.trace_add("write", lambda *a: self._update_comp_max())
        self._refresh_chambre_combo()
        r += 1

        tk.Label(form_grid, text="Date d'entrée *", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.date_entree = DateEntry(form_grid, width=12)
        self.date_entree.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        tk.Label(form_grid, text="Date de sortie *", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.date_sortie = DateEntry(form_grid, width=12)
        self.date_sortie.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        r += 1

        self.cin_hint = tk.Label(form_grid, text="", bg=CARD_BG,
                                 fg=TEXT_SECONDARY, font=("Segoe UI", 9, "italic"))
        self.cin_hint.grid(row=r, column=0, columnspan=2, sticky="w",
                           padx=18, pady=2)
        r += 1

        # CIN auto-fill trace
        def _on_cin_change(*_args):
            if self.selected_client_id:
                return
            cin = self.vars["numero_identifiant"].get().strip()
            if len(cin) < 3:
                self.cin_hint.config(text="", fg=TEXT_SECONDARY)
                return
            existing = db.get_client_by_identifiant(cin)
            if existing:
                self.vars["nom"].set(existing["nom"])
                self.vars["prenom"].set(existing["prenom"])
                self.vars["type_identifiant"].set(existing["type_identifiant"])
                self.vars["lieu_naissance"].set(existing["lieu_naissance"] or "")
                self.vars["adresse"].set(existing["adresse"] or "")
                self.vars["telephone"].set(existing["telephone"] or "")
                if existing["date_naissance"]:
                    self.date_naissance.set(
                        iso_to_date_str(existing["date_naissance"]))
                self.cin_hint.config(
                    text=f"Client existant trouvé: {existing['prenom']} {existing['nom']}",
                    fg=SUCCES)
            else:
                self.cin_hint.config(text="Nouveau client", fg=TEXT_SECONDARY)

        self.vars["numero_identifiant"].trace_add("write", _on_cin_change)

        # ── Section: Compagnons ─────────────────────────────────────
        self._section_header(form_grid, "Compagnons (même chambre)", r); r += 1

        tk.Label(form_grid, text="Nombre d'accompagnants", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=r, column=0, sticky="w", padx=18, pady=3)
        self.comp_count_var = tk.StringVar(value="0")
        self.comp_count_combo = ttk.Combobox(
            form_grid, textvariable=self.comp_count_var,
            values=["0", "1", "2", "3"], width=21, state="readonly")
        self.comp_count_combo.grid(row=r, column=1, sticky="w", padx=4, pady=3)
        self.comp_count_var.trace_add("write", lambda *a: self._rebuild_compagnon_forms())
        r += 1

        self.comp_container = tk.Frame(form_grid, bg=CARD_BG)
        self.comp_container.grid(row=r, column=0, columnspan=2, sticky="ew",
                                 padx=14, pady=(0, 6))
        self.comp_forms = []  # list of dicts with var references
        r += 1

        # ── Section: Séjours ────────────────────────────────────────
        self._section_header(form_grid, "Séjours du client", r); r += 1

        sejours_frame = tk.Frame(form_grid, bg=CARD_BG)
        sejours_frame.grid(row=r, column=0, columnspan=2, sticky="ew",
                           padx=14, pady=(0, 6))

        sejours_cols = ("id", "chambre", "entree", "sortie", "statut")
        sejours_headers = {
            "id": "ID", "chambre": "CHAMBRE",
            "entree": "ENTRÉE", "sortie": "SORTIE", "statut": "STATUT",
        }
        self.sejours_tree = ttk.Treeview(
            sejours_frame, columns=sejours_cols, show="headings",
            height=4)
        style_s = ttk.Style()
        style_s.configure("Sejours.Treeview", font=("Segoe UI", 8), rowheight=22)
        style_s.configure("Sejours.Treeview.Heading", font=("Segoe UI", 8, "bold"),
                          foreground=TEXT_SECONDARY)
        self.sejours_tree.configure(style="Sejours.Treeview")

        for c in sejours_cols:
            self.sejours_tree.heading(c, text=sejours_headers[c])
            w = 35 if c == "id" else 70 if c == "chambre" else 80
            self.sejours_tree.column(c, width=w, anchor="center")

        self.sejours_tree.tag_configure("en_cours", foreground=SUCCES)
        self.sejours_tree.tag_configure("termine", foreground=TEXT_SECONDARY)

        sejours_scroll = ttk.Scrollbar(sejours_frame, orient="vertical",
                                        command=self.sejours_tree.yview)
        self.sejours_tree.configure(yscrollcommand=sejours_scroll.set)
        self.sejours_tree.pack(side="left", fill="both", expand=True)
        sejours_scroll.pack(side="right", fill="y")
        r += 1

        # ── Buttons ─────────────────────────────────────────────────
        btn_frame = tk.Frame(form_grid, bg=CARD_BG)
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

        btn_frame2 = tk.Frame(form_grid, bg=CARD_BG)
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
        tk.Button(btn_frame2, text="Ajouter Compagnon", bg=SUCCES, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground="#059669", activeforeground="white",
                  cursor="hand2", width=14, command=self.ajouter_compagnon).pack(
            side="left", padx=3)

        # ── Right panel: table card ──────────────────────────────────
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        table_card = tk.Frame(right, bg=CARD_BG, bd=0,
                              highlightbackground=CARD_BORDER, highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        # Search bar (no statut filter needed)
        toolbar = tk.Frame(table_card, bg=CARD_BG)
        toolbar.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(toolbar, text="Recherche (nom, prénom, CIN…)", bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 9)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        search_ent = tk.Entry(toolbar, textvariable=self.search_var, width=22,
                              font=("Segoe UI", 9), bd=1, relief="solid",
                              highlightbackground=CARD_BORDER)
        search_ent.pack(side="left", padx=(4, 12))

        # Treeview — client list
        tree_frame = tk.Frame(table_card, bg=CARD_BG)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        columns = ("id", "nom", "prenom", "identifiant", "solde")
        headers = {
            "id": "ID", "nom": "NOM", "prenom": "PRÉNOM",
            "identifiant": "IDENTIFIANT", "solde": "SOLDE (TND)",
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
            width = 50 if c == "id" else 110 if c in ("nom", "prenom", "identifiant") else 100
            self.tree.column(c, width=width, anchor="center")
        self.tree.column("nom", width=110, anchor="w")
        self.tree.column("prenom", width=110, anchor="w")
        self.tree.column("identifiant", width=110, anchor="w")
        self.tree.column("solde", width=110, anchor="center")

        # Zebra striping tags
        self.tree.tag_configure("odd", background=NEUTRE_CLAIR)
        self.tree.tag_configure("even", background=CARD_BG)

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

    def _rebuild_compagnon_forms(self):
        for w in self.comp_container.winfo_children():
            w.destroy()
        self.comp_forms = []

        try:
            nb = int(self.comp_count_var.get())
        except ValueError:
            nb = 0

        for i in range(nb):
            frame = tk.LabelFrame(self.comp_container,
                                  text=f"Compagnon {i + 1}",
                                  bg=CARD_BG, fg=PRIMAIRE,
                                  font=("Segoe UI", 10, "bold"),
                                  bd=1, relief="groove")
            frame.pack(fill="x", padx=4, pady=4)

            form_vars = {}
            row = 0

            # Nom
            tk.Label(frame, text="Nom *", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=24, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["nom"] = v; row += 1

            # Prénom
            tk.Label(frame, text="Prénom *", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=24, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["prenom"] = v; row += 1

            # Type identifiant
            tk.Label(frame, text="Type d'identifiant *", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar(value=TYPES_IDENTIFIANT[0])
            ttk.Combobox(frame, textvariable=v, values=TYPES_IDENTIFIANT,
                         width=21, state="readonly"
                         ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["type_identifiant"] = v; row += 1

            # N° identifiant
            tk.Label(frame, text="N° identifiant *", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=24, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["numero_identifiant"] = v; row += 1

            # Date de naissance
            tk.Label(frame, text="Date de naissance", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            de = DateEntry(frame, width=12)
            de.grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["date_naissance"] = de; row += 1

            # Lieu de naissance
            tk.Label(frame, text="Lieu de naissance", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=24, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["lieu_naissance"] = v; row += 1

            # Adresse
            tk.Label(frame, text="Adresse", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=28, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["adresse"] = v; row += 1

            # Téléphone
            tk.Label(frame, text="Téléphone", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=24, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["telephone"] = v; row += 1

            # Venant de
            tk.Label(frame, text="Venant de", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=24, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["venant_de"] = v; row += 1

            # Allant à
            tk.Label(frame, text="Allant à", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=18, pady=3)
            v = tk.StringVar()
            tk.Entry(frame, textvariable=v, width=24, font=("Segoe UI", 9),
                     bd=1, relief="solid", highlightbackground=CARD_BORDER
                     ).grid(row=row, column=1, sticky="w", padx=4, pady=3)
            form_vars["allant_a"] = v; row += 1

            self.comp_forms.append(form_vars)

    def _refresh_chambre_combo(self):
        self.chambre_map = {"— Aucune —": None}
        self.chambre_cap = {}  # chambre_id -> max_personnes
        vals = ["— Aucune —"]
        sejours_actifs = db.get_sejours_actifs()
        occ_count = {}
        for s in sejours_actifs:
            occ_count[s["chambre_id"]] = occ_count.get(s["chambre_id"], 0) + 1
        for ch in db.get_chambres():
            if ch["etat"] in ("Libre", "Occupée"):
                nb = occ_count.get(ch["id"], 0)
                cap = ch["max_personnes"] or 1
                self.chambre_cap[ch["id"]] = cap
                suffix = f" ({nb}/{cap})" if nb > 0 else ""
                txt = f"{ch['numero']} - {ch['type']} ({ch['prix']} TND){suffix}"
                self.chambre_map[txt] = ch["id"]
                vals.append(txt)
        self.chambre_combo["values"] = vals
        if self.chambre_var.get() not in vals:
            self.chambre_var.set("— Aucune —")
        self._update_comp_max()

    def _update_comp_max(self):
        if not hasattr(self, "comp_count_combo"):
            return
        ch_text = self.chambre_var.get()
        ch_id = self.chambre_map.get(ch_text)
        if ch_id is None:
            max_comp = 3
        else:
            cap = self.chambre_cap.get(ch_id, 1)
            sejours_actifs = db.get_sejours_actifs()
            occ = sum(1 for s in sejours_actifs if s["chambre_id"] == ch_id)
            max_comp = min(cap - occ, 3)
            if max_comp < 0:
                max_comp = 0
        allowed = [str(i) for i in range(max_comp + 1)]
        self.comp_count_combo["values"] = allowed
        cur = self.comp_count_var.get()
        if cur not in allowed:
            self.comp_count_var.set("0")
            self._rebuild_compagnon_forms()

    # ------------------------------------------------------------------
    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        clients = db.get_clients()
        recherche = self.search_var.get().strip().lower()

        for i, c in enumerate(clients):
            ligne = (c["nom"], c["prenom"], c["numero_identifiant"])
            if recherche and not any(recherche in str(v).lower() for v in ligne):
                continue

            solde_val = c["solde"] or 0.0
            solde_txt = f"{solde_val:.3f}" if solde_val else "0.000"

            row_tag = "odd" if i % 2 else "even"

            self.tree.insert("", "end", iid=str(c["id"]),
                             tags=(row_tag,), values=(
                c["id"], c["nom"], c["prenom"], c["numero_identifiant"],
                solde_txt,
            ))

    def _load_sejours(self, client_id):
        for item in self.sejours_tree.get_children():
            self.sejours_tree.delete(item)

        sejours = db.get_sejours_client(client_id)
        for s in sejours:
            statut = s["statut"]
            tag = "en_cours" if statut == "En cours" else "termine"
            self.sejours_tree.insert("", "end", iid=str(s["id"]),
                                     tags=(tag,), values=(
                s["id"],
                s["chambre_numero"] or "-",
                iso_to_date_str(s["date_entree"]) or s["date_entree"],
                iso_to_date_str(s["date_sortie"]) or "-",
                statut,
            ))

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

        if client["date_naissance"]:
            self.date_naissance.set(iso_to_date_str(client["date_naissance"]))
        else:
            self.date_naissance.set("")

        self.cin_hint.config(text="", fg=TEXT_SECONDARY)
        self._refresh_chambre_combo()
        self._load_sejours(client_id)

        # Detect companions in the same room
        self.comp_count_var.set("0")
        self._rebuild_compagnon_forms()
        active = db.get_sejour_actif_client(client_id)
        if active:
            ch_id = active["chambre_id"]
            sejours_actifs = db.get_sejours_actifs()
            comp_list = [s for s in sejours_actifs
                         if s["chambre_id"] == ch_id and s["client_id"] != client_id]
            if comp_list:
                self.comp_count_var.set(str(len(comp_list)))
                self._rebuild_compagnon_forms()
                for i, cs in enumerate(comp_list):
                    if i < len(self.comp_forms):
                        c = db.get_client(cs["client_id"])
                        if c:
                            self.comp_forms[i]["nom"].set(c["nom"])
                            self.comp_forms[i]["prenom"].set(c["prenom"])
                            self.comp_forms[i]["type_identifiant"].set(c["type_identifiant"])
                            self.comp_forms[i]["numero_identifiant"].set(c["numero_identifiant"])
                            if c["date_naissance"]:
                                self.comp_forms[i]["date_naissance"].set(
                                    iso_to_date_str(c["date_naissance"]))
                            self.comp_forms[i]["lieu_naissance"].set(c["lieu_naissance"] or "")
                            self.comp_forms[i]["adresse"].set(c["adresse"] or "")
                            self.comp_forms[i]["telephone"].set(c["telephone"] or "")
                            self.comp_forms[i]["venant_de"].set(c["venant_de"] or "")
                            self.comp_forms[i]["allant_a"].set(c["allant_a"] or "")

    def nouveau(self):
        self.selected_client_id = None
        for var in self.vars.values():
            var.set("")
        self.vars["type_identifiant"].set(TYPES_IDENTIFIANT[0])
        self.date_naissance.set("")
        self.date_entree.set("")
        self.date_sortie.set("")
        self.chambre_var.set("— Aucune —")
        self.comp_count_var.set("0")
        self._rebuild_compagnon_forms()
        self.cin_hint.config(text="", fg=TEXT_SECONDARY)
        self._refresh_chambre_combo()
        for item in self.sejours_tree.get_children():
            self.sejours_tree.delete(item)
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

        today = date.today().isoformat()

        if date_naissance_iso and date_naissance_iso > today:
            messagebox.showerror("Erreur", "La date de naissance ne peut pas être dans le futur.")
            return None

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
        }
        return data

    def enregistrer(self):
        data = self._collect_form_data()
        if data is None:
            return

        chambre_id = self.chambre_map.get(self.chambre_var.get())

        d_entree = date_str_to_iso(self.date_entree.get())
        d_sortie = date_str_to_iso(self.date_sortie.get())

        if chambre_id:
            if not d_entree or not d_sortie:
                messagebox.showerror(
                    "Erreur",
                    "Les dates d'entrée et de sortie sont obligatoires "
                    "lors de l'assignation d'une chambre.")
                return
            if d_sortie < d_entree:
                messagebox.showerror(
                    "Erreur",
                    "La date de sortie doit être après ou égale à la date d'entrée.")
                return

        try:
            if self.selected_client_id:
                db.update_client(self.selected_client_id, data)
                if chambre_id:
                    active = db.get_sejour_actif_client(self.selected_client_id)
                    if active:
                        messagebox.showwarning(
                            "Attention",
                            "Ce client a déjà un séjour actif. "
                            "Termez-le d'abord avant d'assigner une nouvelle chambre.")
                    else:
                        db.add_sejour(self.selected_client_id, chambre_id, d_entree, d_sortie)
                messagebox.showinfo("Succès", "Client mis à jour avec succès.")
            else:
                new_id = db.add_client(data)
                self.selected_client_id = new_id
                if chambre_id:
                    db.add_sejour(new_id, chambre_id, d_entree, d_sortie)
                messagebox.showinfo("Succès", "Client ajouté avec succès.")
        except ValueError as e:
            messagebox.showwarning("Attention", str(e))

        # Create companions from dynamic forms
        nb_comp = 0
        for comp in self.comp_forms:
            cn = comp["nom"].get().strip()
            cp = comp["prenom"].get().strip()
            cti = comp["type_identifiant"].get()
            cnum = comp["numero_identifiant"].get().strip()
            if not (cn and cp and cnum):
                continue
            if not chambre_id:
                continue
            cde = comp["date_naissance"].get_date().strftime("%Y-%m-%d") if hasattr(comp["date_naissance"], "get_date") else ""
            cln = comp["lieu_naissance"].get().strip()
            cad = comp["adresse"].get().strip()
            ctel = comp["telephone"].get().strip()
            cvd = comp["venant_de"].get().strip()
            caa = comp["allant_a"].get().strip()
            existing = db.get_client_by_identifiant(cnum)
            if existing:
                comp_id = existing["id"]
            else:
                comp_data = {
                    "nom": cn, "prenom": cp,
                    "type_identifiant": cti,
                    "numero_identifiant": cnum,
                    "date_naissance": cde,
                    "lieu_naissance": cln,
                    "adresse": cad,
                    "telephone": ctel,
                    "venant_de": cvd,
                    "allant_a": caa,
                }
                comp_id = db.add_client(comp_data)
            active_comp = db.get_sejour_actif_client(comp_id)
            if not active_comp:
                try:
                    db.add_sejour(comp_id, chambre_id, d_entree, d_sortie)
                    nb_comp += 1
                except ValueError as e:
                    messagebox.showwarning("Compagnon",
                        f"{cp['prenom']} {cn}: {e}")

        if nb_comp > 0:
            messagebox.showinfo("Compagnons", f"{nb_comp} compagnon(s) ajouté(s).")

        self._refresh_chambre_combo()
        self.refresh()
        self.app.refresh_rooms_tab()
        if self.selected_client_id:
            self._load_sejours(self.selected_client_id)

    def supprimer(self):
        if not self.selected_client_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        if not messagebox.askyesno(
                "Confirmation",
                "Voulez-vous vraiment supprimer ce client ? "
                "Ses séjours actifs seront terminés et les chambres libérées."):
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

        sejour = db.get_sejour_actif_client(self.selected_client_id)
        if not sejour:
            messagebox.showinfo("Information", "Ce client n'a pas de séjour actif.")
            return

        chambre = db.get_chambre(sejour["chambre_id"])
        today = date.today().strftime("%Y-%m-%d")
        early = sejour["date_sortie"] and today < sejour["date_sortie"]
        nb_nuits = max((date.fromisoformat(today) - date.fromisoformat(sejour["date_entree"])).days, 1)

        if early:
            nb_prevues = max((date.fromisoformat(sejour["date_sortie"]) - date.fromisoformat(sejour["date_entree"])).days, 1)
            msg = (f"Départ anticipé ?\n\n"
                   f"Le séjour prévoit une sortie le "
                   f"{iso_to_date_str(sejour['date_sortie'])}.\n"
                   f"Nuits passées : {nb_nuits} / {nb_prevues}\n\n"
                   f"Confirmer le départ anticipé ?")
        else:
            msg = (f"Confirmer la sortie de {client['prenom']} {client['nom']} "
                   f"et libérer la chambre {chambre['numero'] if chambre else ''} ?")

        if not messagebox.askyesno("Confirmation", msg):
            return

        db.checkout_sejour(sejour["id"], date_sortie=today)
        self.refresh()
        self._load_sejours(self.selected_client_id)
        self.app.refresh_rooms_tab()

        prix = float(chambre["prix"]) if chambre else 0.0
        lignes = [(f"Nuit chambre {chambre['numero']}", nb_nuits, prix)]
        nom_client = f"{client['prenom']} {client['nom']}".strip()
        fid, numero, total = db.create_facture(
            client_id=client["id"],
            date_facture=today,
            date_entree=sejour["date_entree"],
            date_sortie=today,
            nb_nuits=nb_nuits,
            lignes=lignes,
            mode_paiement="Espèces",
            nom_client=nom_client,
            sejour_id=sejour["id"],
            type_identifiant=client.get("type_identifiant", ""),
            numero_identifiant=client.get("numero_identifiant", ""),
            adresse=client.get("adresse", ""),
            chambre_numero=chambre["numero"] if chambre else "",
            venant_de=client.get("venant_de", ""),
            allant_a=client.get("allant_a", ""),
        )
        if messagebox.askyesno(
                "Facture générée",
                f"Facture {numero} créée.\n"
                f"Nuits : {nb_nuits} × {prix:.3f} = {total:.3f} TND\n"
                f"TVA 7% incluse.\n\n"
                f"Générer le PDF ?"):
            try:
                from pdf_facture import generer_facture_pdf
                nom_fichier_defaut = f"Facture_{numero}.pdf"
                chemin = filedialog.asksaveasfilename(
                    title="Enregistrer la facture",
                    defaultextension=".pdf",
                    initialfile=nom_fichier_defaut,
                    filetypes=[("Fichier PDF", "*.pdf")],
                )
                if chemin:
                    generer_facture_pdf(fid, chemin)
                    messagebox.showinfo("PDF", f"Facture enregistrée :\n{chemin}")
            except Exception as e:
                messagebox.showerror("Erreur PDF", str(e))
        self.app.refresh_stats_tab()

    def imprimer_fiche_police(self):
        if not self.selected_client_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        client = db.get_client(self.selected_client_id)
        if not client:
            messagebox.showerror("Erreur", "Client introuvable.")
            return
        try:
            data = dict(client)
            sejour = db.get_sejour_actif_client(self.selected_client_id)
            if sejour:
                data["chambre_numero"] = sejour["chambre_numero"]
                data["date_entree"] = sejour["date_entree"]
                data["date_sortie"] = sejour["date_sortie"]
                data["statut"] = sejour["statut"]
            chemin = generer_fiche_police(data)
            messagebox.showinfo("Succès", f"Fiche Police générée :\n{chemin}")
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Impossible de générer la fiche :\n{e}")

    def ajouter_compagnon(self):
        if not self.selected_client_id:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        sejour = db.get_sejour_actif_client(self.selected_client_id)
        if not sejour:
            messagebox.showwarning("Attention", "Ce client n'a pas de séjour actif.")
            return

        win = tk.Toplevel(self)
        win.title("Ajouter un compagnon")
        win.resizable(False, False)
        win.transient(self)
        win.wait_visibility()
        win.grab_set()
        win.configure(bg=CARD_BG)

        tk.Label(win, text=f"Ajouter un compagnon dans la chambre {sejour['chambre_numero']}",
                 bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 11, "bold")).pack(pady=(14, 8), padx=16)

        form = tk.Frame(win, bg=CARD_BG)
        form.pack(padx=16, pady=8)

        def _row(label, row):
            tk.Label(form, text=label, bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=6, pady=4)
            var = tk.StringVar()
            tk.Entry(form, textvariable=var, width=25, font=("Segoe UI", 9),
                     bd=1, relief="solid",
                     highlightbackground=CARD_BORDER).grid(row=row, column=1, sticky="w", padx=4, pady=4)
            return var

        nom_var = _row("Nom *", 0)
        prenom_var = _row("Prénom *", 1)

        tk.Label(form, text="Type identifiant", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", padx=6, pady=4)
        type_id_var = tk.StringVar(value=TYPES_IDENTIFIANT[0])
        ttk.Combobox(form, textvariable=type_id_var, values=TYPES_IDENTIFIANT,
                     width=22, state="readonly").grid(row=2, column=1, sticky="w", padx=4, pady=4)

        cin_var = _row("N° identifiant *", 3)
        tel_var = _row("Téléphone", 4)

        def _save():
            c_nom = nom_var.get().strip()
            c_prenom = prenom_var.get().strip()
            c_cin = cin_var.get().strip()
            if not c_nom or not c_prenom or not c_cin:
                messagebox.showerror("Erreur", "Nom, prénom et N° identifiant sont obligatoires.", parent=win)
                return
            existing = db.get_client_by_identifiant(c_cin)
            if existing:
                comp_id = existing["id"]
            else:
                comp_id = db.add_client({
                    "nom": c_nom, "prenom": c_prenom,
                    "type_identifiant": type_id_var.get(),
                    "numero_identifiant": c_cin,
                    "date_naissance": "", "lieu_naissance": "",
                    "adresse": "", "telephone": tel_var.get().strip(),
                    "venant_de": "", "allant_a": "",
                })
            active = db.get_sejour_actif_client(comp_id)
            if active:
                messagebox.showwarning("Attention", f"{c_prenom} {c_nom} a déjà un séjour actif.", parent=win)
                return
            db.add_sejour(comp_id, sejour["chambre_id"], sejour["date_entree"], sejour["date_sortie"])
            messagebox.showinfo("Succès", f"{c_prenom} {c_nom} ajouté dans la chambre {sejour['chambre_numero']}.", parent=win)
            win.destroy()
            self.refresh()
            self.app.refresh_rooms_tab()

        btn_frame = tk.Frame(win, bg=CARD_BG)
        btn_frame.pack(pady=12)
        tk.Button(btn_frame, text="Ajouter", bg=SUCCES, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2",
                  width=12, command=_save).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Annuler", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid", cursor="hand2",
                  width=12, command=win.destroy).pack(side="left", padx=6)
