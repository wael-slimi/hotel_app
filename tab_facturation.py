# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

import database as db
from database import get_connection
from widgets import DateEntry, date_str_to_iso, iso_to_date_str, _formater_prix
from pdf_facture import generer_facture_pdf, generer_liste_factures_pdf
from num2words_fr import montant_en_lettres

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
NEUTRE_CLAIR = "#F8FAFC"


class FacturationTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.lignes = []
        self.client_map = {}
        self.paiements = {}
        self.facture_id_map = {}
        self.soldes_factures = {}

        self.configure(bg=BG)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Scrollable outer ─────────────────────────────────────────
        canvas = tk.Canvas(self, bg=BG, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=BG)

        self.scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

        container = self.scroll_frame

        # ══════════════════════════════════════════════════════════════
        # CARTE 1 — Client / Séjour
        # ══════════════════════════════════════════════════════════════
        card1 = tk.Frame(container, bg=CARD_BG, bd=0,
                         highlightbackground=CARD_BORDER, highlightthickness=1)
        card1.pack(fill="x", padx=10, pady=(10, 6))

        tk.Label(card1, text="Client / Séjour", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=20, pady=(14, 4))

        c1_grid = tk.Frame(card1, bg=CARD_BG)
        c1_grid.pack(fill="x", padx=20, pady=(0, 14))

        # Row 0: CIN search
        tk.Label(c1_grid, text="Rechercher par CIN", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.cin_search_var = tk.StringVar()
        self.cin_search_var.trace_add("write", lambda *a: self.search_by_cin())
        tk.Entry(c1_grid, textvariable=self.cin_search_var, width=22,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).grid(
            row=0, column=1, sticky="w", pady=4)

        # Row 0: Client dropdown
        tk.Label(c1_grid, text="Client", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=0, column=2, sticky="w", padx=(16, 8), pady=4)
        self.client_var = tk.StringVar()
        self.combo_client = ttk.Combobox(c1_grid, textvariable=self.client_var,
                                         width=55, state="readonly")
        self.combo_client.grid(row=0, column=3, sticky="w", pady=4)
        self.combo_client.bind("<<ComboboxSelected>>", self.on_client_selected)

        # Row 1: Chambre
        tk.Label(c1_grid, text="Chambre", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="w", pady=4)
        self.chambre_label_var = tk.StringVar(value="-")
        tk.Label(c1_grid, textvariable=self.chambre_label_var, bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 9)).grid(
            row=1, column=1, columnspan=2, sticky="w", pady=4)

        # Row 1: Dates
        tk.Label(c1_grid, text="Entrée", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=1, column=3, sticky="e", padx=(0, 8), pady=4)
        self.date_entree = DateEntry(c1_grid, width=12)
        self.date_entree.grid(row=1, column=4, sticky="w", pady=4)

        tk.Label(c1_grid, text="Sortie", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=1, column=5, sticky="e", padx=(0, 8), pady=4)
        self.date_sortie = DateEntry(c1_grid, width=12)
        self.date_sortie.grid(row=1, column=6, sticky="w", pady=4)

        tk.Button(c1_grid, text="Recalculer hébergement", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", command=self.recalculer_hebergement).grid(
            row=1, column=7, padx=(12, 0), pady=4)

        # ══════════════════════════════════════════════════════════════
        # CARTE 2 — Détail de la facture
        # ══════════════════════════════════════════════════════════════
        card2 = tk.Frame(container, bg=CARD_BG, bd=0,
                         highlightbackground=CARD_BORDER, highlightthickness=1)
        card2.pack(fill="x", padx=10, pady=6)

        tk.Label(card2, text="Détail de la facture", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=20, pady=(14, 4))

        # Treeview
        tree_frame = tk.Frame(card2, bg=CARD_BG)
        tree_frame.pack(fill="x", padx=20, pady=(0, 6))

        columns = ("description", "quantite", "prix", "montant", "statut")
        headers = {"description": "DESCRIPTION", "quantite": "QTÉ",
                   "prix": "PRIX UNIT. (TND)", "montant": "MONTANT (TND)",
                   "statut": "STATUT PAIEMENT"}
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 height=6)
        style = ttk.Style()
        style.configure("Fact.Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Fact.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        foreground=TEXT_SECONDARY)
        self.tree.configure(style="Fact.Treeview")

        for c in columns:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=140, anchor="center")
        self.tree.column("description", width=280, anchor="w")
        self.tree.column("quantite", width=60, anchor="center")
        self.tree.column("prix", width=120, anchor="center")
        self.tree.column("montant", width=120, anchor="center")
        self.tree.column("statut", width=200, anchor="center")

        self.tree.tag_configure("odd", background=NEUTRE_CLAIR)
        self.tree.tag_configure("even", background=CARD_BG)
        self.tree.tag_configure("paye", foreground=SUCCES)
        self.tree.tag_configure("non_paye", foreground=DANGER)
        self.tree.tag_configure("partiel", foreground=ATTENTION)

        # Empty state label
        self.empty_label = tk.Label(tree_frame, text="Aucune ligne ajoutée",
                                    bg=CARD_BG, fg=TEXT_SECONDARY,
                                    font=("Segoe UI", 10, "italic"))

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add line form
        add_frame = tk.Frame(card2, bg=CARD_BG)
        add_frame.pack(fill="x", padx=20, pady=(0, 14))

        tk.Label(add_frame, text="Description", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.desc_var = tk.StringVar()
        tk.Entry(add_frame, textvariable=self.desc_var, width=28,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).pack(side="left", padx=(4, 12))

        tk.Label(add_frame, text="Qté", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.qte_var = tk.StringVar(value="1")
        tk.Entry(add_frame, textvariable=self.qte_var, width=6,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).pack(side="left", padx=(4, 12))

        tk.Label(add_frame, text="Prix unit. (TND)", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.prix_var = tk.StringVar(value="0,000")
        self.prix_entry = tk.Entry(add_frame, textvariable=self.prix_var, width=10,
                                   font=("Segoe UI", 9), bd=1, relief="solid",
                                   highlightbackground=CARD_BORDER)
        self.prix_entry.pack(side="left", padx=(4, 12))
        self.prix_entry.bind("<FocusOut>", lambda e: _formater_prix(self.prix_var))

        tk.Button(add_frame, text="+ Ajouter ligne", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", command=self.ajouter_ligne).pack(
            side="left", padx=(0, 8))
        tk.Button(add_frame, text="Supprimer ligne", bg=CARD_BG, fg=DANGER,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground="#FEF2F2", cursor="hand2",
                  command=self.supprimer_ligne).pack(side="left")

        # ══════════════════════════════════════════════════════════════
        # CARTE 3 — Totaux et validation
        # ══════════════════════════════════════════════════════════════
        card3 = tk.Frame(container, bg=CARD_BG, bd=0,
                         highlightbackground=CARD_BORDER, highlightthickness=1)
        card3.pack(fill="x", padx=10, pady=6)

        tk.Label(card3, text="Totaux et validation", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=20, pady=(14, 4))

        c3_inner = tk.Frame(card3, bg=CARD_BG)
        c3_inner.pack(fill="x", padx=20, pady=(0, 14))

        # Row 0: Remise + Mode paiement
        tk.Label(c3_inner, text="Remise (TND)", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.remise_var = tk.StringVar(value="0,000")
        self.remise_var.trace_add("write", lambda *a: self.update_total())
        self.remise_entry = tk.Entry(c3_inner, textvariable=self.remise_var, width=10,
                                     font=("Segoe UI", 9), bd=1, relief="solid",
                                     highlightbackground=CARD_BORDER)
        self.remise_entry.grid(row=0, column=1, sticky="w", pady=4)
        self.remise_entry.bind("<FocusOut>", lambda e: _formater_prix(self.remise_var))

        tk.Label(c3_inner, text="Mode de paiement", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(
            row=0, column=2, sticky="w", padx=(20, 8), pady=4)
        self.mode_var = tk.StringVar(value="Espèces")
        ttk.Combobox(c3_inner, textvariable=self.mode_var,
                     values=["Espèces", "Chèque", "Carte bancaire", "Virement"],
                     width=16, state="readonly").grid(
            row=0, column=3, sticky="w", pady=4)

        # Row 1: Total KPI card + Payer button
        total_card = tk.Frame(c3_inner, bg=PRIMAIRE, bd=0)
        total_card.grid(row=1, column=0, columnspan=2, sticky="w",
                        padx=(0, 12), pady=6, ipadx=16, ipady=8)
        tk.Label(total_card, text="TOTAL", bg=PRIMAIRE, fg="#C7D2FE",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=4, pady=(4, 0))
        self.total_var = tk.StringVar(value="0.000 TND")
        tk.Label(total_card, textvariable=self.total_var, bg=PRIMAIRE, fg="white",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=4, pady=(0, 4))

        tk.Button(c3_inner, text="Payer", bg=SUCCES, fg="white",
                  font=("Segoe UI", 11, "bold"), bd=0,
                  activebackground=SUCCES_HVR, activeforeground="white",
                  cursor="hand2", width=12, command=self.ouvrir_paiement).grid(
            row=1, column=2, columnspan=2, sticky="w", pady=6)

        # Row 2: Montant en lettres
        self.lettres_var = tk.StringVar(value="")
        tk.Label(c3_inner, textvariable=self.lettres_var, bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 9, "italic"),
                 wraplength=700).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(0, 6))

        # Row 3: Facture payée checkbox
        self.paye_var = tk.BooleanVar(value=False)
        self.check_paye = tk.Checkbutton(
            c3_inner, text="Facture payée", variable=self.paye_var,
            bg=CARD_BG, fg=TEXT_PRIMARY, font=("Segoe UI", 9),
            selectcolor=CARD_BG, activebackground=CARD_BG,
            command=self.on_toggle_paye)
        self.check_paye.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)

        # Row 4: Action buttons grouped
        btn_primary = tk.Frame(c3_inner, bg=CARD_BG)
        btn_primary.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        tk.Button(btn_primary, text="Générer la facture", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", command=self.generer_facture).pack(
            side="left", padx=(0, 8))
        tk.Button(btn_primary, text="Réinitialiser", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 10), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=self.reinitialiser).pack(side="left")

        btn_secondary = tk.Frame(c3_inner, bg=CARD_BG)
        btn_secondary.grid(row=4, column=2, columnspan=2, sticky="e", pady=(8, 0))

        tk.Button(btn_secondary, text="Historique des factures", bg=CARD_BG,
                  fg=TEXT_SECONDARY, font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=self.ouvrir_historique).pack(side="left", padx=(0, 8))
        tk.Button(btn_secondary, text="Voir la facture", bg=CARD_BG,
                  fg=TEXT_SECONDARY, font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=self.voir_facture_client).pack(side="left")

    # ------------------------------------------------------------------
    def refresh(self):
        self.client_map = {}
        valeurs = []

        for c in db.get_clients("En cours"):
            if not c["chambre_id"]:
                continue
            texte = (f"[CLIENT] {c['nom']} {c['prenom']} - Chambre "
                     f"{c['chambre_numero']} ({c['numero_identifiant']})")
            self.client_map[texte] = {
                "id": c["id"], "nom": c["nom"], "prenom": c["prenom"],
                "numero_identifiant": c["numero_identifiant"],
                "type_identifiant": c["type_identifiant"],
                "adresse": c["adresse"], "chambre_id": c["chambre_id"],
                "chambre_numero": c["chambre_numero"],
                "chambre_prix": c["chambre_prix"],
                "date_entree": c["date_entree"], "date_sortie": c["date_sortie"],
                "is_reservation": False,
            }
            valeurs.append(texte)

        for r in db.get_reservations("RESERVE"):
            if not r["chambre_id"]:
                continue
            texte = (f"[RÉSERV.] {r['nom']} {r['prenom']} - Chambre "
                     f"{r['chambre_numero']} ({r['numero_identifiant'] or 'sans ID'})")
            self.client_map[texte] = {
                "id": r["id"], "nom": r["nom"], "prenom": r["prenom"],
                "numero_identifiant": r["numero_identifiant"],
                "type_identifiant": r["type_identifiant"],
                "adresse": "", "chambre_id": r["chambre_id"],
                "chambre_numero": r["chambre_numero"],
                "chambre_prix": r["chambre_prix"],
                "date_entree": r["date_arrivee"], "date_sortie": r["date_depart"],
                "is_reservation": True,
            }
            valeurs.append(texte)

        if self.client_var.get() not in valeurs:
            self.client_var.set("")
            self.chambre_label_var.set("-")
        self.combo_client["values"] = valeurs

        self.refresh_historique()

        self.paiements = {}
        self.facture_id_map = {}
        self.soldes_factures = {}
        conn = get_connection()

        factures_payees = conn.execute(
            "SELECT id, client_id, nom_client FROM factures WHERE payee=1"
        ).fetchall()
        factures_partielles = conn.execute(
            "SELECT id, client_id, nom_client, montant_total, montant_paye "
            "FROM factures WHERE payee=0 AND montant_paye>0"
        ).fetchall()
        factures_non_payees = conn.execute(
            "SELECT id, client_id, nom_client FROM factures "
            "WHERE payee=0 AND montant_paye=0"
        ).fetchall()
        conn.close()

        for f in factures_payees:
            for texte, c in self.client_map.items():
                nom_c = f"{c.get('prenom', '')} {c.get('nom', '')}".strip()
                if (not c.get("is_reservation") and c.get("id") and c["id"] == f["client_id"]) \
                   or (f["nom_client"] and f["nom_client"].strip() == nom_c):
                    self.paiements[texte] = True
                    self.facture_id_map[texte] = f["id"]
                    break

        for f in factures_partielles:
            for texte, c in self.client_map.items():
                nom_c = f"{c.get('prenom', '')} {c.get('nom', '')}".strip()
                if (not c.get("is_reservation") and c.get("id") and c["id"] == f["client_id"]) \
                   or (f["nom_client"] and f["nom_client"].strip() == nom_c):
                    self.paiements[texte] = "partiel"
                    self.facture_id_map[texte] = f["id"]
                    self.soldes_factures[texte] = round(
                        f["montant_total"] - f["montant_paye"], 3)
                    break

        for f in factures_non_payees:
            for texte, c in self.client_map.items():
                if texte in self.facture_id_map:
                    continue
                nom_c = f"{c.get('prenom', '')} {c.get('nom', '')}".strip()
                if (not c.get("is_reservation") and c.get("id") and c["id"] == f["client_id"]) \
                   or (f["nom_client"] and f["nom_client"].strip() == nom_c):
                    self.facture_id_map[texte] = f["id"]
                    break

    def search_by_cin(self):
        cin = self.cin_search_var.get().strip()
        if not cin:
            self.combo_client["values"] = list(self.client_map.keys())
            self.client_var.set("")
            self.chambre_label_var.set("-")
            return
        resultats = [texte for texte, c in self.client_map.items()
                     if cin.lower() in str(c.get("numero_identifiant", "")).lower()]
        self.combo_client["values"] = resultats
        if len(resultats) == 1:
            self.client_var.set(resultats[0])
            self.on_client_selected()
        else:
            self.client_var.set("")

    def refresh_historique(self):
        pass

    # ------------------------------------------------------------------
    def on_client_selected(self, event=None):
        texte = self.client_var.get()
        statut = self.paiements.get(texte, False)
        self.paye_var.set(statut is True)
        client = self.client_map.get(texte)
        if not client:
            return

        prefix = "Réservation" if client.get("is_reservation") else "Client"
        prix = f"{client['chambre_prix']:.3f} TND / nuit" if client['chambre_prix'] else "Prix non défini"
        self.chambre_label_var.set(
            f"{prefix} — Chambre {client['chambre_numero']} ({prix})")
        if client["date_entree"]:
            self.date_entree.set(iso_to_date_str(client["date_entree"]))
        else:
            self.date_entree.set_date(date.today())
        if client["date_sortie"]:
            self.date_sortie.set(iso_to_date_str(client["date_sortie"]))
        else:
            self.date_sortie.set_date(date.today())

        texte_client = self.client_var.get()
        facture_id = self.facture_id_map.get(texte_client)
        if facture_id:
            facture, lignes_db = db.get_facture(facture_id)
            self.lignes = [{
                "description": l["description"],
                "quantite": l["quantite"],
                "prix_unitaire": l["prix_unitaire"],
                "auto": True,
            } for l in lignes_db]
            if facture and facture["remise"]:
                self.remise_var.set(f"{facture['remise']:.3f}".replace(".", ","))
            self.refresh_lignes()
        else:
            self.recalculer_hebergement()

    def recalculer_hebergement(self):
        if self.paiements.get(self.client_var.get(), False):
            return
        texte = self.client_var.get()
        client = self.client_map.get(texte)
        if not client:
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner un client.")
            return
        d_entree = self.date_entree.get_date()
        d_sortie = self.date_sortie.get_date()
        if not d_entree or not d_sortie:
            messagebox.showerror("Erreur", "Dates invalides (format JJ/MM/AAAA).")
            return
        nb_nuits = (d_sortie - d_entree).days
        if nb_nuits < 1:
            nb_nuits = 1
        prix_chambre = client["chambre_prix"]
        self.lignes = [l for l in self.lignes if not l.get("auto")]
        description = (f"Hébergement - Chambre {client['chambre_numero']} "
                       f"({nb_nuits} nuit{'s' if nb_nuits > 1 else ''})")
        self.lignes.insert(0, {
            "description": description,
            "quantite": nb_nuits,
            "prix_unitaire": prix_chambre,
            "auto": True,
        })
        self.refresh_lignes()

    # ------------------------------------------------------------------
    def refresh_lignes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Show/hide empty state
        if not self.lignes:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.empty_label.place_forget()

        statut_paiement = self.paiements.get(self.client_var.get(), False)
        if statut_paiement is True:
            statut_texte = "Payée"
            tag = "paye"
        elif statut_paiement == "partiel":
            solde = self.soldes_factures.get(self.client_var.get(), 0.0)
            statut_texte = f"Reste {solde:.3f} TND".replace(".", ",")
            tag = "partiel"
        else:
            statut_texte = "En attente"
            tag = "non_paye"

        last_index = len(self.lignes) - 1
        for index, ligne in enumerate(self.lignes):
            montant = ligne["quantite"] * ligne["prix_unitaire"]
            row_tag = "odd" if index % 2 else "even"
            # Show status only on the last row
            display_statut = statut_texte if index == last_index else ""
            self.tree.insert("", "end", iid=str(index), values=(
                ligne["description"], f"{ligne['quantite']:g}",
                f"{ligne['prix_unitaire']:.3f}".replace(".", ","),
                f"{montant:.3f}".replace(".", ","),
                display_statut,
            ), tags=(row_tag, tag))
        self.update_total()

    def _verifier_paye(self):
        if self.paiements.get(self.client_var.get(), False):
            messagebox.showwarning(
                "Action impossible",
                "Cette facture est déjà marquée comme payée.\n"
                "Aucune modification n'est autorisée.")
            return True
        return False

    def ajouter_ligne(self):
        if self._verifier_paye():
            return
        description = self.desc_var.get().strip()
        if not description:
            messagebox.showerror("Erreur", "La description est obligatoire.")
            return
        try:
            quantite = float(self.qte_var.get().replace(",", "."))
            prix = float(self.prix_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erreur", "Quantité et prix doivent être numériques.")
            return
        self.lignes.append({
            "description": description,
            "quantite": quantite,
            "prix_unitaire": prix,
            "auto": False,
        })
        self.desc_var.set("")
        self.qte_var.set("1")
        self.prix_var.set("0,000")
        self.refresh_lignes()

    def supprimer_ligne(self):
        if self._verifier_paye():
            return
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une ligne.")
            return
        index = int(selection[0])
        del self.lignes[index]
        self.refresh_lignes()

    def update_total(self):
        sous_total = sum(l["quantite"] * l["prix_unitaire"] for l in self.lignes)
        try:
            remise = float(self.remise_var.get().replace(",", "."))
        except ValueError:
            remise = 0.0
        total = round(sous_total - remise, 3)
        if total < 0:
            total = 0.0
        self.total_var.set(f"{total:.3f} TND")
        if total > 0:
            self.lettres_var.set(
                "Arrêtée la présente facture à la somme de : "
                + montant_en_lettres(total))
        else:
            self.lettres_var.set("")

    # ------------------------------------------------------------------
    def reinitialiser(self):
        self.client_var.set("")
        self.chambre_label_var.set("-")
        self.lignes = []
        self.remise_var.set("0,000")
        self.mode_var.set("Espèces")
        self.paye_var.set(False)
        self.refresh_lignes()

    def on_toggle_paye(self):
        if self.paye_var.get():
            confirme = messagebox.askyesno(
                "Confirmer le paiement",
                "Confirmez-vous que cette facture a été payée ?\n"
                "Cette action ne pourra pas être annulée.")
            if not confirme:
                self.paye_var.set(False)
            else:
                self.paiements[self.client_var.get()] = True
                facture_id = self.facture_id_map.get(self.client_var.get())
                if facture_id:
                    db.set_facture_payee(facture_id)
                self.refresh_lignes()
        else:
            messagebox.showwarning(
                "Action impossible",
                "Une facture marquée comme payée ne peut plus être modifiée.")
            self.paye_var.set(True)

    def generer_facture(self):
        texte = self.client_var.get()
        client = self.client_map.get(texte)
        if not client:
            messagebox.showerror("Erreur", "Veuillez sélectionner un client.")
            return

        facture_existante_id = self.facture_id_map.get(texte)
        if facture_existante_id:
            facture, lignes = db.get_facture(facture_existante_id)
            if facture is not None:
                messagebox.showinfo(
                    "Facture déjà générée",
                    f"Une facture (n° {facture['numero']}) a déjà été générée "
                    "pour ce client.\n"
                    "Elle ne peut pas être générée à nouveau ; "
                    "elle va s'ouvrir en consultation.")
                self._afficher_fenetre_facture(facture, lignes, facture_existante_id)
                return

        if not self.lignes:
            messagebox.showerror("Erreur", "Aucune ligne de facturation.")
            return
        d_entree = self.date_entree.get_date()
        d_sortie = self.date_sortie.get_date()
        if not d_entree or not d_sortie:
            messagebox.showerror("Erreur", "Dates invalides (format JJ/MM/AAAA).")
            return
        nb_nuits = max((d_sortie - d_entree).days, 1)
        try:
            remise = float(self.remise_var.get().replace(",", "."))
        except ValueError:
            remise = 0.0

        lignes_db = [(l["description"], l["quantite"], l["prix_unitaire"])
                     for l in self.lignes]
        client_id = None if client.get("is_reservation") else client["id"]
        nom_client = f"{client['prenom']} {client['nom']}".strip()

        facture_id, numero, total = db.create_facture(
            client_id=client_id,
            date_facture=date.today().strftime("%Y-%m-%d"),
            date_entree=date_str_to_iso(self.date_entree.get()),
            date_sortie=date_str_to_iso(self.date_sortie.get()),
            nb_nuits=nb_nuits,
            lignes=lignes_db,
            remise=remise,
            mode_paiement=self.mode_var.get(),
            nom_client=nom_client,
        )

        self.derniere_facture_id = facture_id
        self.derniere_facture_numero = numero
        self.derniere_facture_total = total
        self.facture_id_map[self.client_var.get()] = facture_id
        if self.paye_var.get():
            db.set_facture_payee(facture_id)
            self.paiements[self.client_var.get()] = True

        statut_paiement = "Payée" if self.paye_var.get() else "En attente de paiement"
        messagebox.showinfo(
            "Facture créée",
            f"Facture {numero} créée avec succès.\n"
            f"Total : {total:.3f} TND\n"
            f"Statut : {statut_paiement}")

        self.refresh_historique()
        self.app.refresh_stats_tab()

        if messagebox.askyesno("Export PDF",
                               "Voulez-vous générer le PDF de cette facture ?"):
            self._exporter_pdf(facture_id, numero)

    # ------------------------------------------------------------------
    def _exporter_pdf(self, facture_id, numero):
        nom_fichier_defaut = f"Facture_{numero}.pdf"
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer la facture",
            defaultextension=".pdf",
            initialfile=nom_fichier_defaut,
            filetypes=[("Fichier PDF", "*.pdf")],
        )
        if not chemin:
            return
        try:
            generer_facture_pdf(facture_id, chemin)
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible de générer le PDF : {exc}")
            return
        messagebox.showinfo("Succès", f"Facture exportée : {chemin}")
        try:
            if os.name == "nt":
                os.startfile(chemin)
        except Exception:
            pass

    def ouvrir_historique(self):
        win = tk.Toplevel(self)
        win.title("Historique des factures")
        win.geometry("1100x700")
        win.transient(self)
        win.configure(bg=BG)

        # Filter card
        filtre_card = tk.Frame(win, bg=CARD_BG, bd=0,
                               highlightbackground=CARD_BORDER, highlightthickness=1)
        filtre_card.pack(fill="x", padx=10, pady=10)

        tk.Label(filtre_card, text="Filtres", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=20, pady=(10, 4))

        ff = tk.Frame(filtre_card, bg=CARD_BG)
        ff.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(ff, text="Critère", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).pack(side="left")
        critere_var = tk.StringVar(value="Toutes les factures")
        combo_critere = ttk.Combobox(
            ff, textvariable=critere_var,
            values=["Toutes les factures", "Par date", "Par N° identifiant client"],
            width=25, state="readonly")
        combo_critere.pack(side="left", padx=6)

        lbl_debut = tk.Label(ff, text="Du", bg=CARD_BG, fg=TEXT_PRIMARY,
                             font=("Segoe UI", 9))
        date_debut = DateEntry(ff, width=12)
        lbl_fin = tk.Label(ff, text="Au", bg=CARD_BG, fg=TEXT_PRIMARY,
                           font=("Segoe UI", 9))
        date_fin = DateEntry(ff, width=12)
        date_debut.set_date(date.today().replace(day=1))

        lbl_cin = tk.Label(ff, text="N° identifiant", bg=CARD_BG, fg=TEXT_PRIMARY,
                           font=("Segoe UI", 9))
        cin_var = tk.StringVar()
        entry_cin = tk.Entry(ff, textvariable=cin_var, width=22,
                             font=("Segoe UI", 9), bd=1, relief="solid",
                             highlightbackground=CARD_BORDER)

        def on_critere_change(*args):
            for w in (lbl_debut, date_debut, lbl_fin, date_fin, lbl_cin, entry_cin):
                w.pack_forget()
            c = critere_var.get()
            if c == "Par date":
                lbl_debut.pack(side="left", padx=(12, 4))
                date_debut.pack(side="left")
                lbl_fin.pack(side="left", padx=(12, 4))
                date_fin.pack(side="left")
            elif c == "Par N° identifiant client":
                lbl_cin.pack(side="left", padx=(12, 4))
                entry_cin.pack(side="left")

        critere_var.trace_add("write", on_critere_change)

        # Table card
        table_card = tk.Frame(win, bg=CARD_BG, bd=0,
                              highlightbackground=CARD_BORDER, highlightthickness=1)
        table_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        hist_columns = ("id", "numero", "date", "client", "identifiant",
                        "total", "solde_due", "statut")
        headers_h = {
            "id": "ID", "numero": "N° FACTURE", "date": "DATE",
            "client": "CLIENT", "identifiant": "N° IDENTIFIANT",
            "total": "MONTANT (TND)", "solde_due": "SOLDE DÛ (TND)",
            "statut": "STATUT",
        }
        hist_tree = ttk.Treeview(table_card, columns=hist_columns,
                                 show="headings", height=18)
        hist_style = ttk.Style()
        hist_style.configure("Hist.Treeview", font=("Segoe UI", 9), rowheight=26)
        hist_style.configure("Hist.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                             foreground=TEXT_SECONDARY)
        hist_tree.configure(style="Hist.Treeview")

        for c in hist_columns:
            hist_tree.heading(c, text=headers_h[c])
            hist_tree.column(c, width=100, anchor="center")
        hist_tree.column("client", width=180, anchor="w")
        hist_tree.column("identifiant", width=130, anchor="w")
        hist_tree.column("numero", width=120, anchor="center")
        hist_tree.column("solde_due", width=110, anchor="center")

        hist_tree.tag_configure("odd", background=NEUTRE_CLAIR)
        hist_tree.tag_configure("even", background=CARD_BG)
        hist_tree.tag_configure("paye", foreground=SUCCES)
        hist_tree.tag_configure("non_paye", foreground=DANGER)
        hist_tree.tag_configure("partiel", foreground=ATTENTION)

        scrollbar = ttk.Scrollbar(table_card, orient="vertical",
                                  command=hist_tree.yview)
        hist_tree.configure(yscrollcommand=scrollbar.set)
        hist_tree.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 14), pady=10)

        compteur_var = tk.StringVar()
        tk.Label(table_card, textvariable=compteur_var, bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 9),
                 anchor="e").pack(fill="x", padx=14, pady=(0, 10))

        def appliquer_filtre():
            for item in hist_tree.get_children():
                hist_tree.delete(item)
            c = critere_var.get()
            if c == "Toutes les factures":
                factures = db.get_factures()
            elif c == "Par date":
                debut = date_str_to_iso(date_debut.get()) or "0000-01-01"
                fin = date_str_to_iso(date_fin.get()) or "9999-12-31"
                factures = db.get_factures(debut, fin)
            elif c == "Par N° identifiant client":
                cin = cin_var.get().strip().lower()
                if not cin:
                    messagebox.showwarning(
                        "Attention", "Veuillez saisir un numéro d'identifiant.",
                        parent=win)
                    return
                toutes = db.get_factures()
                conn = get_connection()
                factures = []
                for f in toutes:
                    if f["client_id"]:
                        client_row = conn.execute(
                            "SELECT numero_identifiant FROM clients WHERE id=?",
                            (f["client_id"],)).fetchone()
                        if client_row and cin in str(client_row["numero_identifiant"]).lower():
                            factures.append(f)
                    else:
                        if cin in str(f["nom_client"] or "").lower():
                            factures.append(f)
                conn.close()
            else:
                factures = db.get_factures()

            for i, f in enumerate(factures):
                client_nom = f"{f['prenom'] or ''} {f['nom'] or ''}".strip()
                if not client_nom:
                    client_nom = f["nom_client"] or "—"
                identifiant = "—"
                if f["client_id"]:
                    conn = get_connection()
                    row = conn.execute(
                        "SELECT numero_identifiant FROM clients WHERE id=?",
                        (f["client_id"],)).fetchone()
                    conn.close()
                    if row:
                        identifiant = row["numero_identifiant"]

                est_paye = bool(f["payee"]) if "payee" in f.keys() else False
                montant_paye = float(f["montant_paye"] or 0) if "montant_paye" in f.keys() else 0

                if est_paye:
                    statut_txt = "Payée"
                    solde_txt = ""
                    tag = "paye"
                elif montant_paye > 0:
                    solde = round(f["montant_total"] - montant_paye, 3)
                    solde_txt = f"{solde:.3f}"
                    statut_txt = "Partielle"
                    tag = "partiel"
                else:
                    solde_txt = ""
                    statut_txt = "En attente"
                    tag = "non_paye"

                row_tag = "odd" if i % 2 else "even"
                hist_tree.insert("", "end", iid=str(f["id"]),
                                 tags=(row_tag, tag), values=(
                    f["id"], f["numero"],
                    iso_to_date_str(f["date_facture"]) or f["date_facture"],
                    client_nom, identifiant,
                    f"{f['montant_total']:.3f}",
                    solde_txt, statut_txt,
                ))
            nb = len(hist_tree.get_children())
            compteur_var.set(f"{nb} facture(s) trouvée(s)")

        filtre_btn = tk.Button(ff, text="Filtrer", bg=PRIMAIRE, fg="white",
                               font=("Segoe UI", 9, "bold"), bd=0,
                               activebackground=PRIMAIRE_HVR, activeforeground="white",
                               cursor="hand2",
                               command=appliquer_filtre)
        filtre_btn.pack(side="left", padx=12)

        appliquer_filtre()

        # Bottom buttons
        btn_frame = tk.Frame(win, bg=CARD_BG)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Button(btn_frame, text="Voir la facture", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2",
                  command=lambda: self._voir_depuis_historique(hist_tree)).pack(
            side="left", padx=(14, 8), pady=10)
        tk.Button(btn_frame, text="Payer le solde", bg=SUCCES, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=SUCCES_HVR, activeforeground="white",
                  cursor="hand2",
                  command=lambda: self._payer_solde_depuis_historique(hist_tree)).pack(
            side="left", padx=4, pady=10)
        tk.Button(btn_frame, text="Exporter en PDF", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=lambda: self._exporter_depuis_historique(hist_tree)).pack(
            side="left", padx=4, pady=10)
        tk.Button(btn_frame, text="Imprimer la liste", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=lambda: self._imprimer_liste_factures(hist_tree)).pack(
            side="left", padx=4, pady=10)
        tk.Button(btn_frame, text="Fermer", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=win.destroy).pack(side="right", padx=14, pady=10)

    def _voir_depuis_historique(self, hist_tree):
        selection = hist_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une facture.")
            return
        facture_id = int(selection[0])
        facture, lignes = db.get_facture(facture_id)
        if facture is None:
            messagebox.showerror("Erreur", "Facture introuvable en base.")
            return
        self._afficher_fenetre_facture(facture, lignes, facture_id)

    def _payer_solde_depuis_historique(self, hist_tree):
        selection = hist_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une facture.")
            return
        facture_id = int(selection[0])
        facture, lignes = db.get_facture(facture_id)
        if facture is None:
            messagebox.showerror("Erreur", "Facture introuvable en base.")
            return

        est_paye = bool(facture["payee"]) if "payee" in facture.keys() else False
        montant_paye = float(facture["montant_paye"] or 0) if "montant_paye" in facture.keys() else 0
        total = float(facture["montant_total"])
        reste_du = round(total - montant_paye, 3)

        if est_paye:
            messagebox.showinfo("Information", "Cette facture est entièrement payée.")
            return
        if reste_du <= 0:
            messagebox.showinfo("Information", "Aucun solde restant à payer.")
            return

        self._ouvrir_paiement_solde(facture, reste_du)

    def _ouvrir_paiement_solde(self, facture, reste_du):
        win = tk.Toplevel(self)
        win.title(f"Payer le solde — Facture {facture['numero']}")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.configure(bg=BG)

        header = tk.Frame(win, bg=SUCCES)
        header.pack(fill="x")
        tk.Label(header, text="Payer le solde restant", bg=SUCCES, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(pady=12, padx=16)

        frame = tk.Frame(win, bg=CARD_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        client_nom = f"{facture['prenom'] or ''} {facture['nom'] or ''}".strip()
        if not client_nom:
            client_nom = facture["nom_client"] or "—"

        tk.Label(frame, text="Client", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=(8, 2), padx=16)
        tk.Label(frame, text=client_nom, bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", padx=16, pady=(8, 2))

        tk.Label(frame, text="Facture n°", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=2, padx=16)
        tk.Label(frame, text=facture["numero"], bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=16, pady=2)

        tk.Label(frame, text="Total facture", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=2, padx=16)
        tk.Label(frame, text=f"{total:.3f} TND", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 11)).grid(row=2, column=1, sticky="w", padx=16, pady=2)

        tk.Label(frame, text="Déjà payé", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", pady=2, padx=16)
        deja_paye = round(total - reste_du, 3)
        tk.Label(frame, text=f"{deja_paye:.3f} TND", bg=CARD_BG, fg=SUCCES,
                 font=("Segoe UI", 11, "bold")).grid(row=3, column=1, sticky="w", padx=16, pady=2)

        tk.Label(frame, text="Reste à payer", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", pady=4, padx=16)
        tk.Label(frame, text=f"{reste_du:.3f} TND", bg=CARD_BG, fg=DANGER,
                 font=("Segoe UI", 13, "bold")).grid(row=4, column=1, sticky="w", padx=16, pady=4)

        tk.Label(frame, text="Mode de paiement", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=5, column=0, sticky="w", pady=6, padx=16)
        mode_var = tk.StringVar(value="Espèces")
        ttk.Combobox(frame, textvariable=mode_var,
                     values=["Espèces", "Chèque", "Carte bancaire", "Virement"],
                     width=20, state="readonly").grid(row=5, column=1, sticky="w", padx=16, pady=6)

        tk.Label(frame, text="Montant à payer (TND)", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=6, column=0, sticky="w", pady=6, padx=16)
        recu_var = tk.StringVar(value=f"{reste_du:.3f}".replace(".", ","))
        tk.Entry(frame, textvariable=recu_var, width=15,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).grid(row=6, column=1, sticky="w", padx=16, pady=6)

        monnaie_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=monnaie_var, bg=CARD_BG, fg=SUCCES,
                 font=("Segoe UI", 10, "italic")).grid(
            row=7, column=0, columnspan=2, pady=8, padx=16)

        def calculer_monnaie(*args):
            try:
                recu = float(recu_var.get().replace(",", "."))
                if recu >= reste_du:
                    monnaie = round(recu - reste_du, 3)
                    monnaie_var.set(f"Monnaie à rendre : {monnaie:.3f} TND")
                else:
                    solde = round(reste_du - recu, 3)
                    monnaie_var.set(f"Solde restant après paiement : {solde:.3f} TND")
            except ValueError:
                monnaie_var.set("Montant invalide")

        recu_var.trace_add("write", calculer_monnaie)

        def confirmer_paiement():
            try:
                recu = float(recu_var.get().replace(",", "."))
                if recu <= 0:
                    messagebox.showerror("Erreur", "Le montant doit être positif.", parent=win)
                    return
            except ValueError:
                messagebox.showerror("Erreur", "Montant invalide.", parent=win)
                return

            nouveau_total_paye = round(deja_paye + recu, 3)
            solde_restant = round(total - nouveau_total_paye, 3)
            if solde_restant < 0:
                solde_restant = 0.0

            facture_id = facture["id"]

            # Update montant_paye in DB
            conn = get_connection()
            conn.execute(
                "UPDATE factures SET montant_paye=? WHERE id=?",
                (nouveau_total_paye, facture_id))
            conn.commit()
            conn.close()

            # If fully paid, mark as payee
            if nouveau_total_paye >= total:
                db.set_facture_payee(facture_id)
                # Update client solde if client exists
                if facture["client_id"]:
                    db.set_client_solde(facture["client_id"], 0.0)

            win.destroy()
            messagebox.showinfo(
                "Paiement enregistré",
                f"Montant payé : {recu:.3f} TND\n"
                f"Total payé : {nouveau_total_paye:.3f} TND / {total:.3f} TND\n"
                f"Solde restant : {solde_restant:.3f} TND")

        btn_f = tk.Frame(frame, bg=CARD_BG)
        btn_f.grid(row=8, column=0, columnspan=2, pady=14)
        tk.Button(btn_f, text="Confirmer le paiement", bg=SUCCES, fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  activebackground=SUCCES_HVR, activeforeground="white",
                  cursor="hand2", command=confirmer_paiement).pack(side="left", padx=6)
        tk.Button(btn_f, text="Annuler", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 10), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=win.destroy).pack(side="left", padx=6)

    def _exporter_depuis_historique(self, hist_tree):
        selection = hist_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une facture.")
            return
        facture_id = int(selection[0])
        facture, _ = db.get_facture(facture_id)
        if facture is None:
            return
        if not messagebox.askyesno(
                "Confirmation",
                "Confirmez-vous que cette facture a bien été payée ?"):
            messagebox.showwarning(
                "PDF non disponible",
                "Le PDF ne peut être généré que pour une facture payée.")
            return
        self._exporter_pdf(facture_id, facture["numero"])

    def _imprimer_liste_factures(self, hist_tree):
        items = hist_tree.get_children()
        if not items:
            messagebox.showwarning("Attention", "Aucune facture à imprimer.")
            return
        factures_data = []
        for iid in items:
            valeurs = hist_tree.item(iid)["values"]
            numero, date_f, client, identifiant, total_str, statut = valeurs[1:]
            try:
                montant = float(str(total_str).replace(",", "."))
            except ValueError:
                montant = 0.0
            factures_data.append((numero, date_f, client, identifiant, montant, statut))

        nom_fichier_defaut = f"Liste_factures_{date.today().strftime('%Y%m%d')}.pdf"
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer la liste des factures",
            defaultextension=".pdf",
            initialfile=nom_fichier_defaut,
            filetypes=[("Fichier PDF", "*.pdf")],
        )
        if not chemin:
            return
        try:
            generer_liste_factures_pdf(factures_data, chemin)
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible de générer le PDF : {exc}")
            return
        messagebox.showinfo("Succès", f"Liste exportée : {chemin}")
        try:
            if os.name == "nt":
                os.startfile(chemin)
        except Exception:
            pass

    def ouvrir_paiement(self):
        if not self.client_var.get():
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        if not self.lignes:
            messagebox.showwarning("Attention", "Aucune ligne de facturation.")
            return

        texte = self.client_var.get()
        statut = self.paiements.get(texte, False)
        if statut is True:
            messagebox.showinfo("Information", "Cette facture est entièrement payée.")
            return

        if not self.facture_id_map.get(texte):
            client = self.client_map.get(texte)
            d_entree = self.date_entree.get_date()
            d_sortie = self.date_sortie.get_date()
            if not d_entree or not d_sortie:
                messagebox.showerror("Erreur", "Dates invalides.")
                return
            nb_nuits = max((d_sortie - d_entree).days, 1)
            try:
                remise = float(self.remise_var.get().replace(",", "."))
            except ValueError:
                remise = 0.0
            lignes_db = [(l["description"], l["quantite"], l["prix_unitaire"])
                         for l in self.lignes]
            client_id = None if client.get("is_reservation") else client["id"]
            nom_client = f"{client['prenom']} {client['nom']}".strip()
            facture_id, numero, total = db.create_facture(
                client_id=client_id,
                date_facture=date.today().strftime("%Y-%m-%d"),
                date_entree=date_str_to_iso(self.date_entree.get()),
                date_sortie=date_str_to_iso(self.date_sortie.get()),
                nb_nuits=nb_nuits,
                lignes=lignes_db,
                remise=remise,
                mode_paiement=self.mode_var.get(),
                nom_client=nom_client,
            )
            self.facture_id_map[texte] = facture_id

        win = tk.Toplevel(self)
        win.title("Paiement de la facture")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.configure(bg=BG)

        header = tk.Frame(win, bg=PRIMAIRE)
        header.pack(fill="x")
        tk.Label(header, text="Paiement de la facture", bg=PRIMAIRE, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(pady=12, padx=16)

        frame = tk.Frame(win, bg=CARD_BG)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        sous_total = sum(l["quantite"] * l["prix_unitaire"] for l in self.lignes)
        remise = 0.0
        facture_id = self.facture_id_map.get(texte)
        if facture_id:
            conn = get_connection()
            row = conn.execute(
                "SELECT remise, montant_total, montant_paye FROM factures WHERE id=?",
                (facture_id,)
            ).fetchone()
            conn.close()
            if row:
                remise = float(row["remise"] or 0.0)
                total = round(float(row["montant_total"]), 3)
                deja_paye = round(float(row["montant_paye"] or 0.0), 3)
            else:
                try:
                    remise = float(self.remise_var.get().replace(",", "."))
                except ValueError:
                    remise = 0.0
                total = round(sous_total - remise, 3)
                deja_paye = 0.0
        else:
            try:
                remise = float(self.remise_var.get().replace(",", "."))
            except ValueError:
                remise = 0.0
            total = round(sous_total - remise, 3)
            deja_paye = 0.0

        reste_du = round(total - deja_paye, 3)
        if reste_du < 0:
            reste_du = 0.0

        tk.Label(frame, text="Montant total facture", bg=CARD_BG,
                 fg=TEXT_SECONDARY, font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="w", pady=(8, 2), padx=16)
        tk.Label(frame, text=f"{total:.3f} TND", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 12, "bold")).grid(
            row=0, column=1, sticky="w", padx=16, pady=(8, 2))

        if deja_paye > 0:
            tk.Label(frame, text="Déjà payé", bg=CARD_BG,
                     fg=TEXT_SECONDARY, font=("Segoe UI", 9)).grid(
                row=1, column=0, sticky="w", pady=2, padx=16)
            tk.Label(frame, text=f"{deja_paye:.3f} TND", bg=CARD_BG, fg=SUCCES,
                     font=("Segoe UI", 11, "bold")).grid(
                row=1, column=1, sticky="w", padx=16, pady=2)

            tk.Label(frame, text="Reste à payer", bg=CARD_BG,
                     fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold")).grid(
                row=2, column=0, sticky="w", pady=2, padx=16)
            tk.Label(frame, text=f"{reste_du:.3f} TND", bg=CARD_BG, fg=DANGER,
                     font=("Segoe UI", 12, "bold")).grid(
                row=2, column=1, sticky="w", padx=16, pady=2)
            row_offset = 3
        else:
            row_offset = 1

        tk.Label(frame, text="Mode de paiement", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=row_offset, column=0, sticky="w", pady=6, padx=16)
        mode_var = tk.StringVar(value=self.mode_var.get())
        ttk.Combobox(frame, textvariable=mode_var,
                     values=["Espèces", "Chèque", "Carte bancaire", "Virement"],
                     width=20, state="readonly").grid(
            row=row_offset, column=1, sticky="w", padx=16, pady=6)

        tk.Label(frame, text="Montant à payer (TND)", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 9)).grid(
            row=row_offset + 1, column=0, sticky="w", pady=6, padx=16)
        recu_var = tk.StringVar(value=f"{reste_du:.3f}".replace(".", ","))
        tk.Entry(frame, textvariable=recu_var, width=15,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).grid(
            row=row_offset + 1, column=1, sticky="w", padx=16, pady=6)

        monnaie_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=monnaie_var, bg=CARD_BG, fg=SUCCES,
                 font=("Segoe UI", 10, "italic")).grid(
            row=row_offset + 2, column=0, columnspan=2, pady=8, padx=16)

        def calculer_monnaie(*args):
            try:
                recu = float(recu_var.get().replace(",", "."))
                nouveau_total_paye = round(deja_paye + recu, 3)
                if nouveau_total_paye >= total:
                    monnaie = round(nouveau_total_paye - total, 3)
                    monnaie_var.set(f"Monnaie à rendre : {monnaie:.3f} TND")
                else:
                    solde = round(total - nouveau_total_paye, 3)
                    monnaie_var.set(f"Solde restant après paiement : {solde:.3f} TND")
            except ValueError:
                monnaie_var.set("Montant invalide")

        recu_var.trace_add("write", calculer_monnaie)

        def confirmer_paiement():
            try:
                recu = float(recu_var.get().replace(",", "."))
                if recu <= 0:
                    messagebox.showerror("Erreur",
                        "Le montant doit être positif.", parent=win)
                    return
            except ValueError:
                messagebox.showerror("Erreur", "Montant invalide.", parent=win)
                return

            nouveau_total_paye = round(deja_paye + recu, 3)
            solde_restant = round(total - nouveau_total_paye, 3)
            if solde_restant < 0:
                solde_restant = 0.0

            client = self.client_map.get(texte)

            if nouveau_total_paye >= total:
                self.mode_var.set(mode_var.get())
                self.paye_var.set(True)
                self.paiements[texte] = True
                if facture_id:
                    db.set_facture_paiement_partiel(facture_id, recu)
                    db.set_facture_payee(facture_id)
                if client and not client.get("is_reservation") and client.get("id"):
                    db.set_client_solde(client["id"], 0.0)
                self.refresh_lignes()
                self.app.refresh_clients_tab()
                win.destroy()
                messagebox.showinfo(
                    "Paiement confirmé",
                    f"Montant payé : {recu:.3f} TND\n"
                    f"Total payé : {nouveau_total_paye:.3f} TND / {total:.3f} TND\n"
                    f"Facture entièrement payée.")
            else:
                if facture_id:
                    db.set_facture_paiement_partiel(facture_id, recu)
                if client and not client.get("is_reservation") and client.get("id"):
                    db.set_client_solde(client["id"], solde_restant)
                self.paiements[texte] = "partiel"
                self.soldes_factures[texte] = solde_restant
                self.refresh_lignes()
                self.app.refresh_clients_tab()
                win.destroy()
                messagebox.showinfo(
                    "Paiement enregistré",
                    f"Montant payé : {recu:.3f} TND\n"
                    f"Total payé : {nouveau_total_paye:.3f} TND / {total:.3f} TND\n"
                    f"Solde restant : {solde_restant:.3f} TND\n"
                    f"Vous pourrez payer le solde plus tard.")

        btn_f = tk.Frame(frame, bg=CARD_BG)
        btn_f.grid(row=row_offset + 3, column=0, columnspan=2, pady=14)
        tk.Button(btn_f, text="Confirmer le paiement", bg=SUCCES, fg="white",
                  font=("Segoe UI", 10, "bold"), bd=0,
                  activebackground=SUCCES_HVR, activeforeground="white",
                  cursor="hand2", command=confirmer_paiement).pack(side="left", padx=6)
        tk.Button(btn_f, text="Annuler", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 10), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=win.destroy).pack(side="left", padx=6)

    def voir_facture_client(self):
        texte = self.client_var.get()
        if not texte:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        facture_id = self.facture_id_map.get(texte)
        if not facture_id:
            messagebox.showwarning(
                "Aucune facture",
                "Aucune facture trouvée pour ce client.\n"
                "Générez d'abord la facture.")
            return
        facture, lignes = db.get_facture(facture_id)
        if facture is None:
            messagebox.showerror("Erreur", "Facture introuvable en base.")
            return
        self._afficher_fenetre_facture(facture, lignes, facture_id)

    def _afficher_fenetre_facture(self, facture, lignes, facture_id):
        import tempfile
        import subprocess
        import platform

        nom_fichier = f"Facture_{facture['numero']}.pdf"
        chemin = os.path.join(tempfile.gettempdir(), nom_fichier)
        try:
            generer_facture_pdf(facture_id, chemin)
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible de générer l'aperçu : {exc}")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(chemin)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", chemin])
            else:
                subprocess.Popen(["xdg-open", chemin])
        except Exception as exc:
            messagebox.showerror(
                "Erreur",
                f"Impossible d'ouvrir le PDF automatiquement.\n"
                f"Fichier disponible ici :\n{chemin}")
