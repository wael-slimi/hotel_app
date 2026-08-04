# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import database as db
from database import TYPES_IDENTIFIANT, get_connection
from widgets import DateEntry, date_str_to_iso, iso_to_date_str

# ── Design system palette ──────────────────────────────────────────
BG          = "#F1F3F6"
CARD_BG     = "#FFFFFF"
CARD_BORDER = "#E2E5EA"
TEXT_PRIMARY = "#1E293B"
TEXT_SECONDARY = "#64748B"
PRIMAIRE     = "#4F46E5"
PRIMAIRE_HVR = "#4338CA"
SUCCES       = "#10B981"
SUCCES_HVR   = "#059669"
ATTENTION    = "#F59E0B"
DANGER       = "#EF4444"
DANGER_HVR   = "#DC2626"
NEUTRE_CLAIR = "#F8FAFC"

STATUTS_RESERVATION = ["RESERVE", "ANNULE", "EXPIRE"]

BADGE_COLORS = {
    "RESERVE": {"bg": "#EEF2FF", "fg": PRIMAIRE, "label": "Réservé"},
    "ANNULE":  {"bg": "#FEF2F2", "fg": DANGER,  "label": "Annulé"},
    "EXPIRE":  {"bg": "#F3F4F6", "fg": "#6B7280", "label": "Expirée"},
}


class ReservationsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.selected_reservation_id = None
        self.configure(bg=BG)

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Left panel: table card ───────────────────────────────────
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        # ── Header card ─────────────────────────────────────────────
        header_card = tk.Frame(left, bg=CARD_BG, bd=0,
                               highlightbackground=CARD_BORDER, highlightthickness=1)
        header_card.pack(fill="x", pady=(0, 6))

        hdr_inner = tk.Frame(header_card, bg=CARD_BG)
        hdr_inner.pack(fill="x", padx=20, pady=14)

        self.total_var = tk.StringVar(value="0 réservations")
        tk.Label(hdr_inner, text="Réservations", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(hdr_inner, textvariable=self.total_var, bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 10)).pack(
            side="left", padx=(12, 0))

        # ── Table card ──────────────────────────────────────────────
        table_card = tk.Frame(left, bg=CARD_BG, bd=0,
                              highlightbackground=CARD_BORDER, highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        # Toolbar: search + filter
        toolbar = tk.Frame(table_card, bg=CARD_BG)
        toolbar.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(toolbar, text="Recherche (nom, prénom, CIN…)", bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 9)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        tk.Entry(toolbar, textvariable=self.search_var, width=22,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).pack(side="left", padx=(4, 12))

        tk.Label(toolbar, text="Filtre", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.filtre_statut = tk.StringVar(value="Tous")
        ttk.Combobox(toolbar, textvariable=self.filtre_statut,
                     values=["Tous"] + STATUTS_RESERVATION, width=12,
                     state="readonly").pack(side="left", padx=4)
        self.filtre_statut.trace_add("write", lambda *a: self.refresh())

        # Treeview
        tree_frame = tk.Frame(table_card, bg=CARD_BG)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        columns = ("id", "nom", "prenom", "telephone", "chambre",
                   "arrivee", "depart", "nb_personnes", "statut")
        headers = {
            "id": "ID", "nom": "NOM", "prenom": "PRÉNOM",
            "telephone": "TÉLÉPHONE", "chambre": "CHAMBRE",
            "arrivee": "ARRIVÉE", "depart": "DÉPART",
            "nb_personnes": "PERS.", "statut": "STATUT",
        }
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 height=20)
        style = ttk.Style()
        style.configure("Rez.Treeview", font=("Segoe UI", 9), rowheight=28)
        style.configure("Rez.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        foreground=TEXT_SECONDARY)
        self.tree.configure(style="Rez.Treeview")

        for c in columns:
            self.tree.heading(c, text=headers[c])
            w = 46 if c == "id" else 90 if c in ("chambre", "statut") else 100
            self.tree.column(c, width=w, anchor="center")
        self.tree.column("nom", width=120, anchor="w")
        self.tree.column("prenom", width=120, anchor="w")
        self.tree.column("telephone", width=110, anchor="w")
        self.tree.column("arrivee", width=85, anchor="center")
        self.tree.column("depart", width=85, anchor="center")
        self.tree.column("nb_personnes", width=50, anchor="center")
        self.tree.column("statut", width=90, anchor="center")

        # Zebra striping
        self.tree.tag_configure("odd", background=NEUTRE_CLAIR)
        self.tree.tag_configure("even", background=CARD_BG)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Status bar
        self.status_var = tk.StringVar()
        tk.Label(table_card, textvariable=self.status_var, bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 9),
                 anchor="w").pack(fill="x", padx=14, pady=(0, 10))

        # ── Right panel: action buttons card ─────────────────────────
        right = tk.Frame(self, bg=BG)
        right.pack(side="right", fill="y", padx=(0, 8), pady=8)

        btn_card = tk.Frame(right, bg=CARD_BG, bd=0,
                            highlightbackground=CARD_BORDER, highlightthickness=1)
        btn_card.pack(fill="y", expand=True)

        tk.Label(btn_card, text="Actions", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=16, pady=(14, 10))

        self._make_btn(btn_card, "+ Nouvelle\nréservation",
                       PRIMAIRE, PRIMAIRE_HVR, "white",
                       self.nouvelle_reservation, bold=True)
        self._make_btn(btn_card, "Check-in",
                       SUCCES, SUCCES_HVR, "white",
                       self.checkin_reservation, bold=True)
        self._make_btn(btn_card, "Modifier",
                       CARD_BG, NEUTRE_CLAIR, TEXT_PRIMARY,
                       self.modifier_reservation, border=True)
        self._make_btn(btn_card, "Supprimer",
                       DANGER, DANGER_HVR, "white",
                       self.supprimer_reservation, bold=True)

        tk.Frame(btn_card, bg=CARD_BG, height=10).pack()
        self._make_btn(btn_card, "Annuler",
                       ATTENTION, "#D97706", "white",
                       self.annuler_reservation, bold=True)

    def _make_btn(self, parent, text, bg, active, fg, command,
                  bold=False, border=False):
        weight = "bold" if bold else "normal"
        font = ("Segoe UI", 10, weight)
        relief = "solid" if border else "flat"
        bd = 1 if border else 0
        btn = tk.Button(parent, text=text, bg=bg, fg=fg,
                        font=font, bd=bd, relief=relief,
                        activebackground=active, activeforeground=fg,
                        cursor="hand2", width=18, command=command)
        btn.pack(padx=12, pady=4, fill="x")
        return btn

    # ------------------------------------------------------------------
    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        statut = self.filtre_statut.get()
        reservations = db.get_reservations(
            None if statut == "Tous" else statut)

        recherche = self.search_var.get().strip().lower()
        total = 0
        for i, r in enumerate(reservations):
            ligne = (r["nom"], r["prenom"], r["telephone"],
                     r["chambre_numero"] or "", r["numero_identifiant"] or "")
            if recherche and not any(
                    recherche in str(v).lower() for v in ligne):
                continue

            statut_val = r["statut"]
            badge = BADGE_COLORS.get(statut_val, None)
            if badge:
                statut_display = f"  {badge['label']}  "
            else:
                statut_display = statut_val

            row_tag = "odd" if i % 2 else "even"

            self.tree.insert("", "end", iid=str(r["id"]), tags=(row_tag,), values=(
                r["id"],
                r["nom"], r["prenom"], r["telephone"],
                r["chambre_numero"] or "—",
                iso_to_date_str(r["date_arrivee"]) or r["date_arrivee"],
                iso_to_date_str(r["date_depart"]) or r["date_depart"],
                r["nb_personnes"],
                statut_display,
            ))
            total += 1

        self.total_var.set(f"{total} réservation(s)")
        self.status_var.set(f"{total} réservation(s) affichée(s)")

    def _on_select(self, event=None):
        selection = self.tree.selection()
        if selection:
            self.selected_reservation_id = int(selection[0])

    # ------------------------------------------------------------------
    def _ouvrir_formulaire(self, reservation=None):
        win = tk.Toplevel(self)
        win.title("Nouvelle réservation" if reservation is None
                  else f"Modifier réservation #{reservation['id']}")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.configure(bg=BG)

        outer = tk.Frame(win, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
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
        scroll_frame.bind("<MouseWheel>", _on_mousewheel)
        scroll_frame.bind("<Button-4>", _on_button4)
        scroll_frame.bind("<Button-5>", _on_button5)

        def _cleanup():
            canvas.unbind("<MouseWheel>")
            canvas.unbind("<Button-4>")
            canvas.unbind("<Button-5>")
            scroll_frame.unbind("<MouseWheel>")
            scroll_frame.unbind("<Button-4>")
            scroll_frame.unbind("<Button-5>")
        win.bind("<Destroy>", lambda e: _cleanup() if e.widget == win else None)

        form_card = tk.Frame(scroll_frame, bg=CARD_BG, bd=0,
                             highlightbackground=CARD_BORDER, highlightthickness=1)
        form_card.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(form_card, text="Nouvelle réservation" if reservation is None
                 else f"Réservation #{reservation['id']}",
                 bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=18, pady=(14, 4))

        form_grid = tk.Frame(form_card, bg=CARD_BG)
        form_grid.pack(fill="both", expand=True)

        def row(r, label, widget_fn, required=False):
            txt = label + (" *" if required else "")
            tk.Label(form_grid, text=txt, bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).grid(
                row=r, column=0, sticky="w", padx=18, pady=4)
            w = widget_fn(form_grid)
            w.grid(row=r, column=1, sticky="w", padx=4, pady=4)
            return w

        def entry(parent, var, width=24):
            return tk.Entry(parent, textvariable=var, width=width,
                            font=("Segoe UI", 9), bd=1, relief="solid",
                            highlightbackground=CARD_BORDER)

        nom_var = tk.StringVar(value=reservation["nom"] if reservation else "")
        prenom_var = tk.StringVar(
            value=reservation["prenom"] if reservation else "")
        tel_var = tk.StringVar(
            value=reservation["telephone"] if reservation else "")
        type_id_var = tk.StringVar(
            value=reservation["type_identifiant"] if reservation
            else TYPES_IDENTIFIANT[0])
        num_id_var = tk.StringVar(
            value=reservation["numero_identifiant"] if reservation else "")
        notes_var = tk.StringVar(
            value=reservation["notes"] if reservation else "")
        statut_var = tk.StringVar(
            value=reservation["statut"] if reservation else "RESERVE")

        _linked_client_id = [None]

        def _on_cin_change(*_args):
            cin = num_id_var.get().strip()
            if len(cin) < 3 or reservation is not None:
                hint_lbl.config(text="", fg=TEXT_SECONDARY)
                _linked_client_id[0] = None
                return
            existing = db.get_client_by_identifiant(cin)
            if existing:
                nom_var.set(existing["nom"])
                prenom_var.set(existing["prenom"])
                tel_var.set(existing["telephone"] or "")
                type_id_var.set(existing["type_identifiant"])
                _linked_client_id[0] = existing["id"]
                hint_lbl.config(
                    text=f"Client existant trouvé: {existing['prenom']} {existing['nom']}",
                    fg=SUCCES)
            else:
                _linked_client_id[0] = None
                hint_lbl.config(text="Nouveau client", fg=TEXT_SECONDARY)

        num_id_var.trace_add("write", _on_cin_change)

        # ── Section: Client ─────────────────────────────────────────
        tk.Label(form_grid, text="Informations client", bg=NEUTRE_CLAIR,
                 fg=PRIMAIRE, font=("Segoe UI", 10, "bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=14,
            pady=(10, 2), ipady=3)
        form_grid.grid_columnconfigure(0, weight=1)
        form_grid.grid_columnconfigure(1, weight=1)

        row(1, "Nom", lambda p: entry(p, nom_var), required=True)
        row(2, "Prénom", lambda p: entry(p, prenom_var), required=True)
        row(3, "Téléphone", lambda p: entry(p, tel_var))

        tk.Label(form_grid, text="Type d'identifiant", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=4, column=0, sticky="w", padx=18, pady=4)
        ttk.Combobox(form_grid, textvariable=type_id_var,
                     values=TYPES_IDENTIFIANT, width=22,
                     state="readonly").grid(row=4, column=1, sticky="w",
                                            padx=4, pady=4)

        row(5, "N° identifiant", lambda p: entry(p, num_id_var))

        hint_lbl = tk.Label(form_grid, text="", bg=CARD_BG,
                            fg=TEXT_SECONDARY, font=("Segoe UI", 9, "italic"))
        hint_lbl.grid(row=5, column=2, sticky="w", padx=4, pady=4)

        # ── Section: Séjour ─────────────────────────────────────────
        tk.Label(form_grid, text="Détails du séjour", bg=NEUTRE_CLAIR,
                 fg=PRIMAIRE, font=("Segoe UI", 10, "bold"), anchor="w").grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=14,
            pady=(10, 2), ipady=3)

        # Chambre combo
        tk.Label(form_grid, text="Chambre", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(
            row=7, column=0, sticky="w", padx=18, pady=4)
        chambres = db.get_chambres()
        chambre_map = {"— Aucune —": None}
        chambre_vals = ["— Aucune —"]
        for ch in chambres:
            if ch["etat"] != "Maintenance":
                occ = db.get_sejours_actifs()
                nb_occ = sum(1 for s in occ if s["chambre_id"] == ch["id"])
                suffix = f" ({nb_occ} occupant(s))" if nb_occ > 0 else ""
                texte = f"{ch['numero']} - {ch['type']} ({ch['prix']} TND){suffix}"
                chambre_map[texte] = ch["id"]
                chambre_vals.append(texte)

        chambre_var = tk.StringVar(value="— Aucune —")
        if reservation and reservation["chambre_id"]:
            for t, cid in chambre_map.items():
                if cid == reservation["chambre_id"]:
                    chambre_var.set(t)
                    break

        ttk.Combobox(form_grid, textvariable=chambre_var, values=chambre_vals,
                     width=28, state="readonly").grid(
            row=7, column=1, sticky="w", padx=4, pady=4)

        # Dates
        tk.Label(form_grid, text="Date d'arrivée *", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=8, column=0, sticky="w", padx=18, pady=4)
        date_arrivee = DateEntry(form_grid, width=12)
        date_arrivee.grid(row=8, column=1, sticky="w", padx=4, pady=4)
        if reservation and reservation["date_arrivee"]:
            date_arrivee.set(iso_to_date_str(reservation["date_arrivee"]))

        tk.Label(form_grid, text="Date de départ *", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=9, column=0, sticky="w", padx=18, pady=4)
        date_depart = DateEntry(form_grid, width=12)
        date_depart.grid(row=9, column=1, sticky="w", padx=4, pady=4)
        if reservation and reservation["date_depart"]:
            date_depart.set(iso_to_date_str(reservation["date_depart"]))

        row(10, "Notes", lambda p: entry(p, notes_var, width=30))

        # ── Section: Compagnons ──────────────────────────────────────
        tk.Label(form_grid, text="Compagnons (même chambre)", bg=NEUTRE_CLAIR,
                 fg=PRIMAIRE, font=("Segoe UI", 10, "bold"), anchor="w").grid(
            row=11, column=0, columnspan=2, sticky="ew", padx=14,
            pady=(10, 2), ipady=3)

        tk.Label(form_grid, text="Nombre d'accompagnants", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=12, column=0, sticky="w", padx=18, pady=4)
        comp_count_var = tk.StringVar(value="0")
        comp_count_combo = ttk.Combobox(
            form_grid, textvariable=comp_count_var,
            values=["0", "1", "2", "3"], width=22, state="readonly")
        comp_count_combo.grid(row=12, column=1, sticky="w", padx=4, pady=4)

        comp_container = tk.Frame(form_grid, bg=CARD_BG)
        comp_container.grid(row=13, column=0, columnspan=2, sticky="ew",
                            padx=14, pady=(0, 6))
        comp_forms = []

        # ── Capacity data for companion limit ───────────────────────
        chambre_cap = {}
        sejours_actifs = db.get_sejours_actifs()
        occ_count = {}
        for s in sejours_actifs:
            occ_count[s["chambre_id"]] = occ_count.get(s["chambre_id"], 0) + 1
        for ch in db.get_chambres():
            cap = ch["max_personnes"] or 1
            occ = occ_count.get(ch["id"], 0)
            chambre_cap[ch["id"]] = (cap, occ)

        def _rebuild_compagnon_forms():
            for w in comp_container.winfo_children():
                w.destroy()
            comp_forms.clear()
            try:
                nb = int(comp_count_var.get())
            except ValueError:
                nb = 0
            for i in range(nb):
                frame = tk.LabelFrame(comp_container,
                                      text=f"Compagnon {i + 1}",
                                      bg=CARD_BG, fg=PRIMAIRE,
                                      font=("Segoe UI", 10, "bold"),
                                      bd=1, relief="groove")
                frame.pack(fill="x", padx=4, pady=4)
                form_vars = {}
                r = 0

                def _entry(parent, width=24):
                    v = tk.StringVar()
                    tk.Entry(parent, textvariable=v, width=width,
                             font=("Segoe UI", 9), bd=1, relief="solid",
                             highlightbackground=CARD_BORDER).grid(
                        row=r, column=1, sticky="w", padx=4, pady=3)
                    return v

                def _label(text):
                    tk.Label(frame, text=text, bg=CARD_BG, fg=TEXT_PRIMARY,
                             font=("Segoe UI", 9)).grid(
                        row=r, column=0, sticky="w", padx=18, pady=3)

                _label("Nom *")
                form_vars["nom"] = _entry(frame); r += 1
                _label("Prénom *")
                form_vars["prenom"] = _entry(frame); r += 1

                _label("Type d'identifiant *")
                v = tk.StringVar(value=TYPES_IDENTIFIANT[0])
                ttk.Combobox(frame, textvariable=v, values=TYPES_IDENTIFIANT,
                             width=22, state="readonly").grid(
                    row=r, column=1, sticky="w", padx=4, pady=3)
                form_vars["type_identifiant"] = v; r += 1

                _label("N° identifiant *")
                form_vars["numero_identifiant"] = _entry(frame); r += 1

                _label("Date de naissance")
                de = DateEntry(frame, width=12)
                de.grid(row=r, column=1, sticky="w", padx=4, pady=3)
                form_vars["date_naissance"] = de; r += 1

                _label("Lieu de naissance")
                form_vars["lieu_naissance"] = _entry(frame); r += 1

                _label("Adresse")
                form_vars["adresse"] = _entry(frame, width=28); r += 1

                _label("Téléphone")
                form_vars["telephone"] = _entry(frame); r += 1

                _label("Venant de")
                form_vars["venant_de"] = _entry(frame); r += 1

                _label("Allant à")
                form_vars["allant_a"] = _entry(frame); r += 1

                comp_forms.append(form_vars)

        def _update_comp_max():
            ch_text = chambre_var.get()
            ch_id = chambre_map.get(ch_text)
            if ch_id is None:
                max_comp = 3
            else:
                cap, occ = chambre_cap.get(ch_id, (1, 0))
                max_comp = min(cap - occ, 3)
                if max_comp < 0:
                    max_comp = 0
            allowed = [str(i) for i in range(max_comp + 1)]
            comp_count_combo["values"] = allowed
            cur = comp_count_var.get()
            if cur not in allowed:
                comp_count_var.set("0")
                _rebuild_compagnon_forms()

        comp_count_var.trace_add("write", lambda *a: _rebuild_compagnon_forms())
        chambre_var.trace_add("write", lambda *a: _update_comp_max())
        _update_comp_max()
        if reservation:
            companions = db.get_reservation_companions(reservation["id"])
            if companions:
                comp_count_var.set(str(len(companions)))
                _rebuild_compagnon_forms()
                for i, cp in enumerate(companions):
                    if i < len(comp_forms):
                        comp_forms[i]["nom"].set(cp["nom"])
                        comp_forms[i]["prenom"].set(cp["prenom"])
                        comp_forms[i]["type_identifiant"].set(cp["type_identifiant"])
                        comp_forms[i]["numero_identifiant"].set(cp["numero_identifiant"])
                        if cp["date_naissance"]:
                            comp_forms[i]["date_naissance"].set(
                                iso_to_date_str(cp["date_naissance"]))
                        comp_forms[i]["lieu_naissance"].set(cp["lieu_naissance"] or "")
                        comp_forms[i]["adresse"].set(cp["adresse"] or "")
                        comp_forms[i]["telephone"].set(cp["telephone"] or "")
                        comp_forms[i]["venant_de"].set(cp["venant_de"] or "")
                        comp_forms[i]["allant_a"].set(cp["allant_a"] or "")

        tk.Label(form_grid, text="Statut", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(
            row=14, column=0, sticky="w", padx=18, pady=4)
        ttk.Combobox(form_grid, textvariable=statut_var,
                     values=STATUTS_RESERVATION, width=22,
                     state="readonly").grid(row=14, column=1, sticky="w",
                                            padx=4, pady=4)

        # ── Buttons ─────────────────────────────────────────────────
        btn_frame = tk.Frame(form_grid, bg=CARD_BG)
        btn_frame.grid(row=15, column=0, columnspan=2, pady=(12, 14))

        def enregistrer():
            nom = nom_var.get().strip()
            prenom = prenom_var.get().strip()
            if not nom or not prenom:
                messagebox.showerror(
                    "Erreur", "Nom et Prénom sont obligatoires.", parent=win)
                return

            d_arr = date_str_to_iso(date_arrivee.get())
            d_dep = date_str_to_iso(date_depart.get())
            if not d_arr or not d_dep:
                messagebox.showerror(
                    "Erreur", "Dates invalides (format JJ/MM/AAAA).",
                    parent=win)
                return
            if d_dep < d_arr:
                messagebox.showerror(
                    "Erreur",
                    "La date de départ doit être après ou égale à la date d'arrivée.",
                    parent=win)
                return
            if d_arr < date.today().isoformat():
                messagebox.showerror(
                    "Erreur",
                    "La date d'arrivée ne peut pas être dans le passé.",
                    parent=win)
                return

            erreur_format = db.validate_identifiant_format(
                type_id_var.get(), num_id_var.get().strip()
            )
            if erreur_format:
                messagebox.showerror("Erreur", erreur_format, parent=win)
                return

            # Count valid companions for nb_personnes
            nb_comp = 0
            for comp in comp_forms:
                cn = comp["nom"].get().strip()
                cp = comp["prenom"].get().strip()
                cnum = comp["numero_identifiant"].get().strip()
                if cn and cp and cnum:
                    nb_comp += 1
            nb_personnes = 1 + nb_comp

            data = {
                "nom": nom, "prenom": prenom,
                "telephone": tel_var.get().strip(),
                "type_identifiant": type_id_var.get(),
                "numero_identifiant": num_id_var.get().strip(),
                "chambre_id": chambre_map.get(chambre_var.get()),
                "date_arrivee": d_arr, "date_depart": d_dep,
                "nb_personnes": nb_personnes,
                "notes": notes_var.get().strip(),
                "statut": statut_var.get(),
                "client_id": _linked_client_id[0],
            }

            chambre_id = data["chambre_id"]
            if chambre_id:
                overlaps = db.check_reservation_overlap(
                    chambre_id, d_arr, d_dep,
                    exclude_id=reservation["id"] if reservation else None)
                if overlaps:
                    noms = ", ".join(f"{o['prenom']} {o['nom']}" for o in overlaps)
                    if not messagebox.askyesno(
                            "Chambre déjà réservée",
                            f"La chambre est déjà réservée par: {noms}\n"
                            "Voulez-vous quand même réserver (partage de chambre) ?",
                            parent=win):
                        return

            if reservation is None:
                db.add_reservation(data)
                new_res = db.get_reservations()
                res_id = new_res[-1]["id"] if new_res else None
                messagebox.showinfo("Succès", "Réservation ajoutée.", parent=win)
            else:
                res_id = reservation["id"]
                db.update_reservation(res_id, data)
                messagebox.showinfo("Succès", "Réservation modifiée.", parent=win)

            # Save companions to DB
            if res_id:
                db.delete_reservation_companions(res_id)
                for comp in comp_forms:
                    cn = comp["nom"].get().strip()
                    cp = comp["prenom"].get().strip()
                    cnum = comp["numero_identifiant"].get().strip()
                    if not (cn and cp and cnum):
                        continue
                    cde = ""
                    try:
                        cde = comp["date_naissance"].get_date().strftime("%Y-%m-%d")
                    except Exception:
                        pass
                    db.add_reservation_companion(res_id, {
                        "nom": cn, "prenom": cp,
                        "type_identifiant": comp["type_identifiant"].get(),
                        "numero_identifiant": cnum,
                        "date_naissance": cde,
                        "lieu_naissance": comp["lieu_naissance"].get().strip(),
                        "adresse": comp["adresse"].get().strip(),
                        "telephone": comp["telephone"].get().strip(),
                        "venant_de": comp["venant_de"].get().strip(),
                        "allant_a": comp["allant_a"].get().strip(),
                    })

            win.destroy()
            self.refresh()
            self.app.refresh_rooms_tab()

        tk.Button(btn_frame, text="Enregistrer", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", width=14, command=enregistrer).pack(
            side="left", padx=4)
        tk.Button(btn_frame, text="Annuler", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 10), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  width=14, command=win.destroy).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    def nouvelle_reservation(self):
        self._ouvrir_formulaire(None)

    def modifier_reservation(self):
        if not self.selected_reservation_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner une réservation.")
            return
        r = db.get_reservation(self.selected_reservation_id)
        if r:
            self._ouvrir_formulaire(dict(r))

    def supprimer_reservation(self):
        if not self.selected_reservation_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner une réservation.")
            return
        r = db.get_reservation(self.selected_reservation_id)
        if not r:
            return
        if not messagebox.askyesno(
                "Confirmation",
                f"Supprimer la réservation de {r['prenom']} {r['nom']} ?"):
            return
        db.delete_reservation(self.selected_reservation_id)
        self.selected_reservation_id = None
        self.refresh()
        self.app.refresh_rooms_tab()

    def annuler_reservation(self):
        if not self.selected_reservation_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner une réservation.")
            return
        r = db.get_reservation(self.selected_reservation_id)
        if not r:
            return
        if r["statut"] == "ANNULE":
            messagebox.showinfo("Info", "Cette réservation est déjà annulée.")
            return
        if not messagebox.askyesno(
                "Confirmation",
                f"Annuler la réservation de {r['prenom']} {r['nom']} ?"):
            return
        data = dict(r)
        data["statut"] = "ANNULE"
        db.update_reservation(self.selected_reservation_id, data)
        self.refresh()
        self.app.refresh_rooms_tab()

    def checkin_reservation(self):
        if not self.selected_reservation_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner une réservation.")
            return
        r = db.get_reservation(self.selected_reservation_id)
        if not r:
            return
        if r["statut"] == "ANNULE":
            messagebox.showerror("Erreur",
                                 "Impossible de faire le check-in d'une réservation annulée.")
            return
        if not r["chambre_id"]:
            messagebox.showerror("Erreur",
                                 "Aucune chambre associée à cette réservation.")
            return

        client = None
        try:
            cid = r["client_id"]
        except (IndexError, KeyError):
            cid = None
        if cid:
            client = db.get_client(cid)
        if not client:
            try:
                num_id = r["numero_identifiant"]
            except (IndexError, KeyError):
                num_id = None
            if num_id:
                client = db.get_client_by_identifiant(num_id)

        if not client:
            client_id = db.add_client({
                "nom": r["nom"],
                "prenom": r["prenom"],
                "type_identifiant": r["type_identifiant"],
                "numero_identifiant": r["numero_identifiant"] or "",
                "date_naissance": "",
                "lieu_naissance": "",
                "adresse": "",
                "telephone": r["telephone"] or "",
                "venant_de": "",
                "allant_a": "",
            })
            client = db.get_client(client_id)

        active = db.get_sejour_actif_client(client["id"])
        if active:
            messagebox.showerror("Erreur",
                                 f"{client['prenom']} {client['nom']} a déjà "
                                 f"un séjour actif en chambre {active['chambre_numero']}.")
            return

        if not messagebox.askyesno(
                "Confirmer le Check-in",
                f"Confirmer l'arrivée de {client['prenom']} {client['nom']} "
                f"en chambre {r['chambre_numero']} ?"):
            return

        # Pre-validate: count primary + valid companions vs room capacity
        companions = db.get_reservation_companions(r["id"])
        valid_companions = []
        for cp in companions:
            cn = cp["nom"].strip()
            cnum = cp["numero_identifiant"].strip()
            if cn and cnum:
                valid_companions.append(cp)
        total_needed = 1 + len(valid_companions)

        chambre = db.get_chambre(r["chambre_id"])
        max_p = chambre["max_personnes"] if chambre else 1
        sejours_actifs = db.get_sejours_actifs()
        nb_actuels = sum(1 for s in sejours_actifs if s["chambre_id"] == r["chambre_id"])
        if nb_actuels + total_needed > max_p:
            messagebox.showerror(
                "Erreur capacité",
                f"La chambre {r['chambre_numero']} ne peut accueillir que {max_p} "
                f"personne(s). Vous essayez d'en placer {total_needed} "
                f"(client + {len(valid_companions)} compagnon(s)), "
                f"mais il y a déjà {nb_actuels} occupant(s).")
            return

        try:
            db.add_sejour(client["id"], r["chambre_id"],
                          date.today().strftime("%Y-%m-%d"),
                          r["date_depart"])
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return

        # Create companion clients + sejours (capacity already validated)
        nb_comp_created = 0
        for cp in valid_companions:
            cnum = cp["numero_identifiant"].strip()
            existing = db.get_client_by_identifiant(cnum)
            if existing:
                comp_id = existing["id"]
            else:
                comp_id = db.add_client({
                    "nom": cp["nom"], "prenom": cp["prenom"],
                    "type_identifiant": cp["type_identifiant"],
                    "numero_identifiant": cnum,
                    "date_naissance": cp["date_naissance"],
                    "lieu_naissance": cp["lieu_naissance"],
                    "adresse": cp["adresse"],
                    "telephone": cp["telephone"],
                    "venant_de": cp["venant_de"],
                    "allant_a": cp["allant_a"],
                })
            active_comp = db.get_sejour_actif_client(comp_id)
            if not active_comp:
                db.add_sejour(comp_id, r["chambre_id"],
                              date.today().strftime("%Y-%m-%d"),
                              r["date_depart"],
                              skip_capacity_check=True)
                nb_comp_created += 1

        update_data = dict(r)
        update_data["statut"] = "CHECKED_IN"
        update_data["client_id"] = client["id"]
        db.update_reservation(self.selected_reservation_id, update_data)

        msg = (f"{client['prenom']} {client['nom']} est maintenant enregistré(e) "
               f"en chambre {r['chambre_numero']}.")
        if nb_comp_created > 0:
            msg += f"\n\n{nb_comp_created} compagnon(s) ajouté(s)."

        self.selected_reservation_id = None
        self.refresh()
        self.app.refresh_rooms_tab()
        self.app.refresh_clients_tab()
        messagebox.showinfo("Check-in effectué", msg)
