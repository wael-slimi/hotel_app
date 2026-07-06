# -*- coding: utf-8 -*-
"""
Module tab_parametres.py - Onglet "Parametres" pour la Gestion d'Hotel.
Extrait automatiquement du fichier unique gestion_hotel.py, sans aucune
modification du code original (seuls les imports necessaires ont ete
ajoutes pour que ce module fonctionne de maniere independante).
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db

# ==============================================================================
# Module : tab_parametres.py
# ==============================================================================

class ParametresTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        frame = ttk.LabelFrame(self, text="Informations de l'hôtel (en-tête de facture)")
        frame.pack(padx=16, pady=16, anchor="nw")

        self.vars = {}
        champs = [
            ("nom_hotel", "Nom de l'hôtel"),
            ("adresse_hotel", "Adresse"),
            ("telephone_hotel", "Téléphone"),
            ("matricule_fiscal", "Matricule fiscal"),
        ]
        for i, (cle, label) in enumerate(champs):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w",
                                                padx=8, pady=6)
            var = tk.StringVar(value=db.get_parametre(cle, ""))
            self.vars[cle] = var
            ttk.Entry(frame, textvariable=var, width=50).grid(
                row=i, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(frame, text="Prochain numéro de facture").grid(
            row=len(champs), column=0, sticky="w", padx=8, pady=6)
        self.vars["prochain_numero_facture"] = tk.StringVar(
            value=db.get_parametre("prochain_numero_facture", "1"))
        ttk.Entry(frame, textvariable=self.vars["prochain_numero_facture"],
                  width=15).grid(row=len(champs), column=1, sticky="w",
                                  padx=8, pady=6)

        ttk.Button(frame, text="Enregistrer",
                   command=self.enregistrer).grid(
            row=len(champs) + 1, column=0, columnspan=2, pady=12)

        # Informations sur la base de données
        info_frame = ttk.LabelFrame(self, text="À propos")
        info_frame.pack(padx=16, pady=16, anchor="nw", fill="x")
        ttk.Label(info_frame, text=(
            "Logiciel de gestion d'hôtel\n"
            "Base de données SQLite : hotel.db (dans le dossier de l'application)\n"
            "Devise utilisée : Dinar Tunisien (TND), 1 TND = 1000 millimes"
        ), justify="left").pack(padx=8, pady=8, anchor="w")

    def enregistrer(self):
        try:
            int(self.vars["prochain_numero_facture"].get())
        except ValueError:
            messagebox.showerror("Erreur", "Le prochain numéro de facture doit être un entier.")
            return

        for cle, var in self.vars.items():
            db.set_parametre(cle, var.get())

        messagebox.showinfo("Succès", "Paramètres enregistrés.")


