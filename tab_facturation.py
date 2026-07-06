# -*- coding: utf-8 -*-
"""
Module tab_facturation.py - Onglet "Facturation" pour la Gestion d'Hotel.
Extrait automatiquement du fichier unique gestion_hotel.py, sans aucune
modification du code original (seuls les imports necessaires ont ete
ajoutes pour que ce module fonctionne de maniere independante).
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

import database as db
from database import get_connection
from widgets import DateEntry, date_str_to_iso, iso_to_date_str, _formater_prix
from pdf_facture import generer_facture_pdf, generer_liste_factures_pdf
from num2words_fr import montant_en_lettres

# ==============================================================================
# Module : tab_facturation.py
# ==============================================================================

class FacturationTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.lignes = []  # liste de dicts: description, quantite, prix_unitaire
        self.client_map = {}
        self.paiements = {}
        self.facture_id_map = {}
        self.soldes_factures = {}

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        # ----- Partie haute : sélection client -----
        top_frame = ttk.LabelFrame(self, text="Client / Séjour")
        top_frame.pack(fill="x", padx=8, pady=8)

        ttk.Label(top_frame, text="Rechercher par CIN :").grid(
            row=0, column=0, sticky="w", padx=4, pady=4)
        self.cin_search_var = tk.StringVar()
        self.cin_search_var.trace_add("write", lambda *a: self.search_by_cin())
        cin_entry = ttk.Entry(top_frame, textvariable=self.cin_search_var, width=22)
        cin_entry.grid(row=0, column=1, padx=4, pady=4, sticky="w")

        self.client_var = tk.StringVar()
        self.combo_client = ttk.Combobox(top_frame, textvariable=self.client_var,
                                        width=70, state="readonly")
        self.combo_client.grid(row=0, column=2, padx=4, pady=4, sticky="w")
        self.combo_client.bind("<<ComboboxSelected>>", self.on_client_selected)

        ttk.Label(top_frame, text="Chambre :").grid(row=1, column=0, sticky="w",
                                                      padx=4, pady=4)
        self.chambre_label_var = tk.StringVar(value="-")
        ttk.Label(top_frame, textvariable=self.chambre_label_var).grid(
            row=1, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(top_frame, text="Date d'entrée :").grid(row=2, column=0, sticky="w",
                                                            padx=4, pady=4)
        self.date_entree = DateEntry(top_frame, width=12)
        self.date_entree.grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(top_frame, text="Date de sortie :").grid(row=3, column=0, sticky="w",
                                                             padx=4, pady=4)
        self.date_sortie = DateEntry(top_frame, width=12)
        self.date_sortie.grid(row=3, column=1, sticky="w", padx=4, pady=4)

        ttk.Button(top_frame, text="Recalculer hébergement",
                   command=self.recalculer_hebergement).grid(
            row=2, column=2, rowspan=2, padx=8)

        # ----- Partie centrale : lignes de facturation -----
        mid_frame = ttk.LabelFrame(self, text="Détail de la facture")
        mid_frame.pack(fill="both", expand=False, padx=8, pady=4)

        columns = ("description", "quantite", "prix", "montant", "statut")
        headers = {"description": "Description", "quantite": "Quantité",
                "prix": "Prix unitaire (TND)", "montant": "Montant (TND)",
                "statut": "Statut paiement"}
        self.tree = ttk.Treeview(mid_frame, columns=columns, show="headings",
                                height=6)
        for c in columns:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=150, anchor="center")
        self.tree.column("description", width=260, anchor="w")
        self.tree.column("quantite", width=60, anchor="center")
        self.tree.column("statut", width=240, anchor="center")
        self.tree.tag_configure("paye", foreground="#1F8A4C")
        self.tree.tag_configure("non_paye", foreground="#C0392B")
        self.tree.tag_configure("partiel", foreground="#E67E22")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        # Ajout d'une ligne (service supplémentaire)
        add_frame = ttk.Frame(mid_frame)
        add_frame.pack(fill="x", padx=4, pady=4)

        ttk.Label(add_frame, text="Description").pack(side="left")
        self.desc_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.desc_var, width=30).pack(
            side="left", padx=4)

        ttk.Label(add_frame, text="Qté").pack(side="left")
        self.qte_var = tk.StringVar(value="1")
        ttk.Entry(add_frame, textvariable=self.qte_var, width=6).pack(
            side="left", padx=4)

        ttk.Label(add_frame, text="Prix unit. (TND)").pack(side="left")
        self.prix_var = tk.StringVar(value="0,000")
        self.prix_entry = ttk.Entry(add_frame, textvariable=self.prix_var, width=10)
        self.prix_entry.pack(side="left", padx=4)
        self.prix_entry.bind("<FocusOut>", lambda e: _formater_prix(self.prix_var))

        ttk.Button(add_frame, text="Ajouter ligne",
                   command=self.ajouter_ligne).pack(side="left", padx=8)
        ttk.Button(add_frame, text="Supprimer ligne sélectionnée",
                   command=self.supprimer_ligne).pack(side="left", padx=4)

        # ----- Partie basse : totaux + actions -----
        # ----- Partie basse : totaux + actions -----
        bottom_frame = ttk.LabelFrame(self, text="Totaux et validation")
        bottom_frame.pack(fill="x", padx=8, pady=8)

        # Ligne 0 : Remise + Mode paiement + Total
        ttk.Label(bottom_frame, text="Remise (TND) :").grid(
            row=0, column=0, sticky="w", padx=4, pady=4)
        self.remise_var = tk.StringVar(value="0,000")
        self.remise_var.trace_add("write", lambda *a: self.update_total())
        self.remise_entry = ttk.Entry(bottom_frame, textvariable=self.remise_var, width=10)
        self.remise_entry.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.remise_entry.bind("<FocusOut>", lambda e: _formater_prix(self.remise_var))

        ttk.Label(bottom_frame, text="Mode de paiement :").grid(
            row=0, column=2, sticky="w", padx=4, pady=4)
        self.mode_var = tk.StringVar(value="Espèces")
        ttk.Combobox(bottom_frame, textvariable=self.mode_var,
                     values=["Espèces", "Chèque", "Carte bancaire", "Virement"],
                     width=15, state="readonly").grid(row=0, column=3, padx=4, pady=4)

        self.total_var = tk.StringVar(value="Total : 0.000 TND")
        ttk.Label(bottom_frame, textvariable=self.total_var,
                font=("Segoe UI", 12, "bold")).grid(
            row=0, column=4, padx=20, pady=4)
        ttk.Button(bottom_frame, text="💰 Payer",
                command=self.ouvrir_paiement).grid(
            row=0, column=5, padx=8, pady=4)

        # Ligne 1 : Montant en lettres
        self.lettres_var = tk.StringVar(value="")
        ttk.Label(bottom_frame, textvariable=self.lettres_var,
                  wraplength=700, font=("Segoe UI", 9, "italic")).grid(
            row=1, column=0, columnspan=5, sticky="w", padx=4, pady=2)

        # Ligne 2 : Case à cocher "Facture payée"
        self.paye_var = tk.BooleanVar(value=False)
        self.check_paye = ttk.Checkbutton(
            bottom_frame, text="✅ Facture payée",
            variable=self.paye_var,
            command=self.on_toggle_paye
        )
        self.check_paye.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=4)

        # Ligne 3 : Boutons
        action_frame = ttk.Frame(bottom_frame)
        action_frame.grid(row=3, column=0, columnspan=5, pady=8)
        ttk.Button(action_frame, text="Générer la facture",
                   command=self.generer_facture).pack(side="left", padx=4)
        ttk.Button(action_frame, text="Réinitialiser",
                   command=self.reinitialiser).pack(side="left", padx=4)
        ttk.Button(action_frame, text="📋 Historique des factures",
                   command=self.ouvrir_historique).pack(side="left", padx=4)
        ttk.Button(action_frame, text="👁️ Voir la facture",          # ← AJOUTER
                   command=self.voir_facture_client).pack(side="left", padx=4)

        # ----- Historique des factures -----
        

    # ------------------------------------------------------------------
    def refresh(self):
        self.client_map = {}
        valeurs = []

        # Clients en cours
        for c in db.get_clients("En cours"):
            if not c["chambre_id"]:
                continue
            texte = (f"[CLIENT] {c['nom']} {c['prenom']} - Chambre "
                     f"{c['chambre_numero']} ({c['numero_identifiant']})")
            self.client_map[texte] = {
                "id": c["id"],
                "nom": c["nom"],
                "prenom": c["prenom"],
                "numero_identifiant": c["numero_identifiant"],
                "type_identifiant": c["type_identifiant"],
                "adresse": c["adresse"],
                "chambre_id": c["chambre_id"],
                "chambre_numero": c["chambre_numero"],
                "chambre_prix": c["chambre_prix"],
                "date_entree": c["date_entree"],
                "date_sortie": c["date_sortie"],
                "is_reservation": False,
            }
            valeurs.append(texte)

        # Réservations actives
        for r in db.get_reservations("RESERVE"):
            if not r["chambre_id"]:
                continue
            texte = (f"[RÉSERV.] {r['nom']} {r['prenom']} - Chambre "
                     f"{r['chambre_numero']} ({r['numero_identifiant'] or 'sans ID'})")
            self.client_map[texte] = {
                "id": r["id"],
                "nom": r["nom"],
                "prenom": r["prenom"],
                "numero_identifiant": r["numero_identifiant"],
                "type_identifiant": r["type_identifiant"],
                "adresse": "",
                "chambre_id": r["chambre_id"],
                "chambre_numero": r["chambre_numero"],
                "chambre_prix": r["chambre_prix"],
                "date_entree": r["date_arrivee"],
                "date_sortie": r["date_depart"],
                "is_reservation": True,
            }
            valeurs.append(texte)

        if self.client_var.get() not in valeurs:
            self.client_var.set("")
            self.chambre_label_var.set("-")
        self.combo_client["values"] = valeurs  # ← AJOUTER CETTE LIGNE

        self.refresh_historique()
        

        # Recharger les paiements depuis la base
        # Recharger les paiements depuis la base
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
            self.combo_client["values"] = []
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
    def _filtrer_clients(self):
        recherche = self.search_client_var.get().strip().lower()
        if not recherche:
            # Afficher tous les clients/réservations
            self.combo_client["values"] = list(self.client_map.keys())
            return

        filtres = [
            texte for texte, c in self.client_map.items()
            if recherche in str(c.get("numero_identifiant", "")).lower()
        ]
        self.combo_client["values"] = filtres

        # Sélectionner automatiquement si un seul résultat
        if len(filtres) == 1:
            self.client_var.set(filtres[0])
            self.on_client_selected()
        elif len(filtres) == 0:
            self.client_var.set("")
            self.chambre_label_var.set("-")

    def refresh_historique(self):
        pass  # plus utilisé, l'historique est dans une fenêtre séparée

    # ------------------------------------------------------------------
    def on_client_selected(self, event=None):
        texte = self.client_var.get()
        statut = self.paiements.get(texte, False)
        self.paye_var.set(statut is True)
        client = self.client_map.get(texte)
        if not client:
            return

        prefix = "📋 Réservation" if client.get("is_reservation") else "👤 Client"
        self.chambre_label_var.set(
            f"{prefix} — Chambre {client['chambre_numero']} "
            f"({client['chambre_prix']:.3f} TND / nuit)")

        if client["date_entree"]:
            self.date_entree.set(iso_to_date_str(client["date_entree"]))
        else:
            self.date_entree.set_date(date.today())

        if client["date_sortie"]:
            self.date_sortie.set(iso_to_date_str(client["date_sortie"]))
        else:
            self.date_sortie.set_date(date.today())

        # Charger les lignes depuis la base si facture existante
        texte_client = self.client_var.get()
        facture_id = self.facture_id_map.get(texte_client)
        if facture_id:
            _, lignes_db = db.get_facture(facture_id)
            self.lignes = [{
                "description": l["description"],
                "quantite": l["quantite"],
                "prix_unitaire": l["prix_unitaire"],
                "auto": True,
            } for l in lignes_db]
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

        # Supprimer toute ligne d'hébergement existante (générée auto)
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

        statut_paiement = self.paiements.get(self.client_var.get(), False)

        if statut_paiement == True:
            statut_texte = "✅ Payée"
            tag = "paye"
        elif statut_paiement == "partiel":
            solde = self.soldes_factures.get(self.client_var.get(), 0.0)
            statut_texte = f"⚠️ Partiellement payée - Reste {solde:.3f} TND".replace(".", ",")
            tag = "partiel"
        else:
            statut_texte = "⏳ En attente"
            tag = "non_paye"

        for index, ligne in enumerate(self.lignes):
            montant = ligne["quantite"] * ligne["prix_unitaire"]
            self.tree.insert("", "end", iid=str(index), values=(
                ligne["description"], f"{ligne['quantite']:g}",
                f"{ligne['prix_unitaire']:.3f}".replace(".", ","),
                f"{montant:.3f}".replace(".", ","),
                statut_texte,
            ), tags=(tag,))
        self.update_total()
    def _verifier_paye(self):
        """Retourne True si la facture est payée (action bloquée)."""
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
        self.total_var.set(f"Total : {total:.3f} TND")
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
        self.paye_var.set(False)   # ← ajouter cette ligne
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
                # Sauvegarder en base
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

        # Une facture ne peut être générée qu'une seule fois pour un même
        # client/séjour. Si une facture existe déjà, on ne la recrée pas :
        # on l'affiche simplement en lecture seule.
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

        # Si c'est une réservation, on passe client_id=None
        # (pas encore de client créé dans la table clients)
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

        statut_paiement = "✅ Payée" if self.paye_var.get() else "⏳ En attente de paiement"
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

        # Ouvrir automatiquement le PDF si possible (Windows)
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

        # ----- Barre de filtres -----
        filtre_frame = ttk.LabelFrame(win, text="Filtres")
        filtre_frame.pack(fill="x", padx=8, pady=8)

        ttk.Label(filtre_frame, text="Critère :").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        critere_var = tk.StringVar(value="Toutes les factures")
        combo_critere = ttk.Combobox(
            filtre_frame, textvariable=critere_var,
            values=["Toutes les factures", "Par date", "Par N° identifiant client"],
            width=25, state="readonly"
        )
        combo_critere.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        lbl_debut = ttk.Label(filtre_frame, text="Du :")
        date_debut = DateEntry(filtre_frame, width=12)
        lbl_fin = ttk.Label(filtre_frame, text="Au :")
        date_fin = DateEntry(filtre_frame, width=12)
        date_debut.set_date(date.today().replace(day=1))

        lbl_cin = ttk.Label(filtre_frame, text="N° identifiant :")
        cin_var = tk.StringVar()
        entry_cin = ttk.Entry(filtre_frame, textvariable=cin_var, width=22)

        ttk.Button(
            filtre_frame, text="🔍 Filtrer",
            command=lambda: appliquer_filtre()
        ).grid(row=0, column=6, padx=12, pady=6)

        def on_critere_change(*args):
            for w in (lbl_debut, date_debut, lbl_fin, date_fin, lbl_cin, entry_cin):
                w.grid_remove()

            c = critere_var.get()
            if c == "Par date":
                lbl_debut.grid(row=0, column=2, padx=4, pady=6, sticky="w")
                date_debut.grid(row=0, column=3, padx=4, pady=6, sticky="w")
                lbl_fin.grid(row=0, column=4, padx=4, pady=6, sticky="w")
                date_fin.grid(row=0, column=5, padx=4, pady=6, sticky="w")
            elif c == "Par N° identifiant client":
                lbl_cin.grid(row=0, column=2, padx=4, pady=6, sticky="w")
                entry_cin.grid(row=0, column=3, padx=4, pady=6, sticky="w")

        critere_var.trace_add("write", on_critere_change)

        # ----- Tableau des factures -----
        hist_columns = ("id", "numero", "date", "client", "identifiant", "total", "statut")
        headers_h = {
            "id": "ID", "numero": "N° Facture", "date": "Date",
            "client": "Client", "identifiant": "N° Identifiant",
            "total": "Montant (TND)", "statut": "Statut"
        }

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=4)

        hist_tree = ttk.Treeview(frame, columns=hist_columns, show="headings", height=18)
        for c in hist_columns:
            hist_tree.heading(c, text=headers_h[c])
            hist_tree.column(c, width=100, anchor="center")
        hist_tree.column("client", width=180, anchor="w")
        hist_tree.column("identifiant", width=130, anchor="w")
        hist_tree.column("numero", width=120, anchor="center")
        hist_tree.tag_configure("paye", foreground="#1F8A4C")
        hist_tree.tag_configure("non_paye", foreground="#C0392B")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=hist_tree.yview)
        hist_tree.configure(yscrollcommand=scrollbar.set)
        hist_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        compteur_var = tk.StringVar()
        ttk.Label(win, textvariable=compteur_var,
                font=("Segoe UI", 9, "italic")).pack(anchor="e", padx=8)

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
                        "Attention", "Veuillez saisir un numéro d'identifiant.", parent=win)
                    return
                toutes = db.get_factures()
                conn = get_connection()
                factures = []
                for f in toutes:
                    if f["client_id"]:
                        client_row = conn.execute(
                            "SELECT numero_identifiant FROM clients WHERE id=?",
                            (f["client_id"],)
                        ).fetchone()
                        if client_row and cin in str(client_row["numero_identifiant"]).lower():
                            factures.append(f)
                    else:
                        if cin in str(f["nom_client"] or "").lower():
                            factures.append(f)
                conn.close()
            else:
                factures = db.get_factures()

            for f in factures:
                client_nom = f"{f['prenom'] or ''} {f['nom'] or ''}".strip()
                if not client_nom:
                    client_nom = f["nom_client"] or "—"

                identifiant = "—"
                if f["client_id"]:
                    conn = get_connection()
                    row = conn.execute(
                        "SELECT numero_identifiant FROM clients WHERE id=?",
                        (f["client_id"],)
                    ).fetchone()
                    conn.close()
                    if row:
                        identifiant = row["numero_identifiant"]

                est_paye = bool(f["payee"]) if "payee" in f.keys() else False
                statut_txt = "✅ Payée" if est_paye else "⏳ En attente"
                tag = "paye" if est_paye else "non_paye"

                hist_tree.insert("", "end", iid=str(f["id"]), tags=(tag,), values=(
                    f["id"], f["numero"],
                    iso_to_date_str(f["date_facture"]) or f["date_facture"],
                    client_nom, identifiant,
                    f"{f['montant_total']:.3f}",
                    statut_txt,
                ))

            nb = len(hist_tree.get_children())
            compteur_var.set(f"{nb} facture(s) trouvée(s)")

        appliquer_filtre()

        # ----- Boutons bas -----
        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=6)
        ttk.Button(
            btn_frame, text="👁️ Voir la facture",
            command=lambda: self._voir_depuis_historique(hist_tree)
        ).pack(side="left", padx=4)
        ttk.Button(
            btn_frame, text="📄 Exporter en PDF",
            command=lambda: self._exporter_depuis_historique(hist_tree)
        ).pack(side="left", padx=4)
        ttk.Button(
            btn_frame, text="🖨️ Imprimer la liste",
            command=lambda: self._imprimer_liste_factures(hist_tree)
        ).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Fermer",
                command=win.destroy).pack(side="left", padx=4)
    def _voir_depuis_historique(self, hist_tree):
        selection = hist_tree.selection()
        if not selection:
            messagebox.showwarning("Attention",
                                "Veuillez sélectionner une facture.")
            return
        facture_id = int(selection[0])
        facture, lignes = db.get_facture(facture_id)
        if facture is None:
            messagebox.showerror("Erreur", "Facture introuvable en base.")
            return

        # Vérifier si la facture est payée
        est_paye = bool(facture["payee"]) if "payee" in facture.keys() else False
        self._afficher_fenetre_facture(facture, lignes, facture_id)


    def _exporter_depuis_historique(self, hist_tree):
        selection = hist_tree.selection()
        if not selection:
            messagebox.showwarning("Attention",
                                "Veuillez sélectionner une facture.")
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
            # valeurs = (id, numero, date, client, identifiant, total, statut)
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
        if self.paiements.get(self.client_var.get(), False):
            messagebox.showinfo("Information", "Cette facture est déjà payée.")
            return

        # Générer la facture automatiquement si pas encore fait
        if not self.facture_id_map.get(self.client_var.get()):
            texte = self.client_var.get()
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
            lignes_db = [(l["description"], l["quantite"], l["prix_unitaire"]) for l in self.lignes]
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
            self.facture_id_map[self.client_var.get()] = facture_id

        win = tk.Toplevel(self)
        win.title("💰 Paiement de la facture")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        BLEU = "#1F4E79"
        header = tk.Frame(win, bg=BLEU)
        header.pack(fill="x")
        tk.Label(header, text="Paiement de la facture", bg=BLEU, fg="white",
                font=("Segoe UI", 13, "bold")).pack(pady=12, padx=16)

        frame = ttk.Frame(win)
        frame.pack(padx=20, pady=12)

        sous_total = sum(l["quantite"] * l["prix_unitaire"] for l in self.lignes)
        try:
            remise = float(self.remise_var.get().replace(",", "."))
        except ValueError:
            remise = 0.0
        total = round(sous_total - remise, 3)

        ttk.Label(frame, text="Montant total à payer :",
                font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=6)
        ttk.Label(frame, text=f"{total:.3f} TND",
                font=("Segoe UI", 12, "bold"),
                foreground="#1F4E79").grid(row=0, column=1, sticky="w", padx=12, pady=6)

        ttk.Label(frame, text="Mode de paiement :").grid(row=1, column=0, sticky="w", pady=6)
        mode_var = tk.StringVar(value=self.mode_var.get())
        ttk.Combobox(frame, textvariable=mode_var,
                    values=["Espèces", "Chèque", "Carte bancaire", "Virement"],
                    width=20, state="readonly").grid(row=1, column=1, sticky="w", padx=12, pady=6)

        ttk.Label(frame, text="Montant reçu (TND) :").grid(row=2, column=0, sticky="w", pady=6)
        recu_var = tk.StringVar(value=f"{total:.3f}".replace(".", ","))
        ttk.Entry(frame, textvariable=recu_var, width=15).grid(
            row=2, column=1, sticky="w", padx=12, pady=6)

        monnaie_var = tk.StringVar(value="Monnaie à rendre : 0.000 TND")
        ttk.Label(frame, textvariable=monnaie_var,
                font=("Segoe UI", 10, "italic"),
                foreground="#1F8A4C").grid(row=3, column=0, columnspan=2, pady=6)

        def calculer_monnaie(*args):
            try:
                recu = float(recu_var.get().replace(",", "."))
                if recu >= total:
                    monnaie = round(recu - total, 3)
                    monnaie_var.set(f"Monnaie à rendre : {monnaie:.3f} TND")
                else:
                    solde = round(total - recu, 3)
                    monnaie_var.set(f"⚠️ Paiement partiel — Solde restant : {solde:.3f} TND")
            except ValueError:
                monnaie_var.set("Montant reçu invalide")

        recu_var.trace_add("write", calculer_monnaie)

        def confirmer_paiement():
            try:
                recu = float(recu_var.get().replace(",", "."))
                if recu <= 0:
                    messagebox.showerror("Erreur",
                        "Le montant reçu doit être positif.", parent=win)
                    return
            except ValueError:
                messagebox.showerror("Erreur", "Montant reçu invalide.", parent=win)
                return

            facture_id = self.facture_id_map.get(self.client_var.get())
            texte = self.client_var.get()
            client = self.client_map.get(texte)

            if recu >= total:
                # ----- Paiement complet -----
                self.mode_var.set(mode_var.get())
                self.paye_var.set(True)
                self.paiements[texte] = True

                if facture_id:
                    db.set_facture_payee(facture_id)

                if client and not client.get("is_reservation") and client.get("id"):
                    db.set_client_solde(client["id"], 0.0)

                self.refresh_lignes()
                self.app.refresh_clients_tab()
                win.destroy()
                messagebox.showinfo(
                    "Paiement confirmé",
                    f"Paiement complet de {total:.3f} TND confirmé.\n"
                    f"Mode : {mode_var.get()}\n"
                    f"Monnaie rendue : {round(recu - total, 3):.3f} TND")

            else:
                # ----- Paiement partiel -----
                solde_restant = round(total - recu, 3)

                if facture_id:
                    db.set_facture_paiement_partiel(facture_id, recu)

                if client and not client.get("is_reservation") and client.get("id"):
                    db.set_client_solde(client["id"], solde_restant)

                self.paiements[texte] = "partiel"

                self.refresh_lignes()
                self.app.refresh_clients_tab()
                win.destroy()
                messagebox.showinfo(
                    "Paiement partiel enregistré",
                    f"Montant reçu : {recu:.3f} TND\n"
                    f"Solde restant : {solde_restant:.3f} TND\n"
                    f"Le solde a été ajouté à la fiche client.")

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="✅ Confirmer le paiement",
                command=confirmer_paiement).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Annuler",
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

        # Générer le PDF dans un dossier temporaire
        nom_fichier = f"Facture_{facture['numero']}.pdf"
        chemin = os.path.join(tempfile.gettempdir(), nom_fichier)

        try:
            generer_facture_pdf(facture_id, chemin)
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible de générer l'aperçu : {exc}")
            return

        # Ouvrir le PDF avec le lecteur par défaut du système
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
