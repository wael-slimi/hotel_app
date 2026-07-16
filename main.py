# -*- coding: utf-8 -*-
"""
Module main.py - Point d'entree de l'application Gestion d'Hotel.
Extrait automatiquement du fichier unique gestion_hotel.py, sans aucune
modification du code original (seuls les imports necessaires ont ete
ajoutes pour que ce module fonctionne de maniere independante). sss

Lancement :
    python main.py
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox

from database import init_db, auto_checkout_expired
from tab_chambres import RoomsTab
from tab_clients import ClientsTab
from tab_facturation import FacturationTab
from tab_depenses import DepensesTab
from tab_statistiques import StatsTab
from tab_parametres import ParametresTab
from tab_reservations import ReservationsTab

# ==============================================================================
# Module : main.py
# ==============================================================================

class HotelApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Gestion d'Hôtel - Logiciel de gestion (TND)")
        self.geometry("1280x800")
        self.minsize(1024, 650)

        self._configurer_style()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self.notebook = notebook

        self.tab_chambres = RoomsTab(notebook, self)
        self.tab_clients = ClientsTab(notebook, self)
        self.tab_facturation = FacturationTab(notebook, self)
        self.tab_depenses = DepensesTab(notebook, self)
        self.tab_stats = StatsTab(notebook, self)
        self.tab_parametres = ParametresTab(notebook, self)
        self.tab_reservations = ReservationsTab(notebook, self)

        notebook.add(self.tab_chambres, text="  Chambres  ")
        notebook.add(self.tab_clients, text="  Clients  ")
        notebook.add(self.tab_reservations, text="  Réservations  ")
        notebook.add(self.tab_facturation, text="  Facturation  ")
        notebook.add(self.tab_depenses, text="  Dépenses  ")
        notebook.add(self.tab_stats, text="  Statistiques  ")
        notebook.add(self.tab_parametres, text="  Paramètres  ")

        notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def _configurer_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
        style.configure("TNotebook.Tab", padding=(12, 6),
                        font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    # ------------------------------------------------------------------
    # Méthodes de rafraîchissement croisé entre onglets
    # ------------------------------------------------------------------
    def refresh_rooms_tab(self):
        self.tab_chambres.refresh()

    def refresh_clients_tab(self):
        self.tab_clients.refresh()

    def refresh_stats_tab(self):
        self.tab_stats.refresh()

    def on_tab_changed(self, event):
        selected = event.widget.select()
        widget = event.widget.nametowidget(selected)
        if widget is self.tab_chambres:
            self.tab_chambres.refresh()
        elif widget is self.tab_clients:
            self.tab_clients.refresh()
        elif widget is self.tab_facturation:
            self.tab_facturation.refresh()
        elif widget is self.tab_depenses:
            self.tab_depenses.refresh()
        elif widget is self.tab_stats:
            self.tab_stats.refresh()
        elif widget is self.tab_reservations:
            self.tab_reservations.refresh()
    def refresh_reservations_tab(self):
        self.tab_reservations.refresh()


def main():
    try:
        init_db()
        auto_checkout_expired()
    except Exception as exc:
        # Affiche une fenêtre d'erreur même si le reste de l'UI ne se charge pas
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Erreur de démarrage",
            f"Impossible d'initialiser la base de données :\n{exc}")
        root.destroy()
        sys.exit(1)

    app = HotelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
