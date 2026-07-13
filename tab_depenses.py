# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

import database as db
from database import CATEGORIES_DEPENSE
from widgets import DateEntry, date_str_to_iso, iso_to_date_str
from pdf_facture import generer_liste_depenses_pdf

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

# Category colors for badges
CAT_COLORS = {
    "Maintenance":        {"bg": "#FFF7ED", "fg": "#EA580C"},
    "Ménage":             {"bg": "#ECFDF5", "fg": "#059669"},
    "STEG (Électricité)": {"bg": "#FFFBEB", "fg": "#D97706"},
    "SONEDE (Eau)":       {"bg": "#EFF6FF", "fg": "#2563EB"},
    "Internet / Télécom": {"bg": "#F5F3FF", "fg": "#7C3AED"},
    "Fournitures":        {"bg": "#EFF6FF", "fg": "#2563EB"},
    "Salaires":           {"bg": "#ECFDF5", "fg": "#059669"},
    "Impôts / Taxes":     {"bg": "#FEF2F2", "fg": "#DC2626"},
    "Autre":              {"bg": NEUTRE_CLAIR, "fg": TEXT_SECONDARY},
}


class DepensesTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.selected_depense_id = None
        self.configure(bg=BG)

        self._build_ui()
        self.refresh()

    def _formater_montant(self, event=None):
        valeur = self.montant_var.get().replace(",", ".").strip()
        try:
            self.montant_var.set(f"{float(valeur):.3f}".replace(".", ","))
        except ValueError:
            pass

    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Left panel: form + summary ───────────────────────────────
        left = tk.Frame(self, bg=BG)
        left.pack(side="left", fill="y", padx=8, pady=8)

        # Form card
        form_card = tk.Frame(left, bg=CARD_BG, bd=0,
                             highlightbackground=CARD_BORDER, highlightthickness=1)
        form_card.pack(fill="x")

        tk.Label(form_card, text="Nouvelle dépense", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=18, pady=(14, 4))

        form_grid = tk.Frame(form_card, bg=CARD_BG)
        form_grid.pack(fill="x", padx=18, pady=(0, 14))

        # Date
        tk.Label(form_grid, text="Date *", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=4)
        self.date_entry = DateEntry(form_grid, width=12)
        self.date_entry.grid(row=0, column=1, sticky="w", padx=(4, 0), pady=4)

        # Catégorie
        tk.Label(form_grid, text="Catégorie *", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4)
        self.categorie_var = tk.StringVar(value=CATEGORIES_DEPENSE[0])
        ttk.Combobox(form_grid, textvariable=self.categorie_var,
                     values=CATEGORIES_DEPENSE, width=22,
                     state="readonly").grid(row=1, column=1, sticky="w",
                                            padx=(4, 0), pady=4)

        # Description
        tk.Label(form_grid, text="Description", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=4)
        self.description_var = tk.StringVar()
        tk.Entry(form_grid, textvariable=self.description_var, width=24,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).grid(
            row=2, column=1, sticky="w", padx=(4, 0), pady=4)

        # Montant
        tk.Label(form_grid, text="Montant (TND) *", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", pady=4)
        self.montant_var = tk.StringVar()
        self.montant_entry = tk.Entry(form_grid, textvariable=self.montant_var,
                                      width=24, font=("Segoe UI", 9), bd=1,
                                      relief="solid",
                                      highlightbackground=CARD_BORDER)
        self.montant_entry.grid(row=3, column=1, sticky="w", padx=(4, 0), pady=4)
        self.montant_entry.bind("<FocusOut>", self._formater_montant)

        # Mode de paiement
        tk.Label(form_grid, text="Mode de paiement", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=4, column=0, sticky="w", pady=4)
        self.mode_var = tk.StringVar(value="Espèces")
        ttk.Combobox(form_grid, textvariable=self.mode_var,
                     values=["Espèces", "Chèque", "Carte bancaire", "Virement"],
                     width=22, state="readonly").grid(row=4, column=1, sticky="w",
                                                      padx=(4, 0), pady=4)

        # Buttons
        btn_frame = tk.Frame(form_grid, bg=CARD_BG)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        tk.Button(btn_frame, text="Nouveau", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  width=9, command=self.nouveau).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Enregistrer", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", width=9, command=self.enregistrer).pack(
            side="left", padx=3)
        tk.Button(btn_frame, text="Modifier", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  width=9, command=self.modifier).pack(side="left", padx=3)
        tk.Button(btn_frame, text="Supprimer", bg=DANGER, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground="#DC2626", activeforeground="white",
                  cursor="hand2", width=9, command=self.supprimer).pack(
            side="left", padx=3)

        # ── Summary card ─────────────────────────────────────────────
        summary_card = tk.Frame(left, bg=CARD_BG, bd=0,
                                highlightbackground=CARD_BORDER, highlightthickness=1)
        summary_card.pack(fill="x", pady=(6, 0))

        tk.Label(summary_card, text="Résumé du mois", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=18, pady=(12, 4))

        self.summary_frame = tk.Frame(summary_card, bg=CARD_BG)
        self.summary_frame.pack(fill="x", padx=18, pady=(0, 12))

        # ── Right panel: table ───────────────────────────────────────
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        # Table card
        table_card = tk.Frame(right, bg=CARD_BG, bd=0,
                              highlightbackground=CARD_BORDER, highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        # Toolbar
        toolbar = tk.Frame(table_card, bg=CARD_BG)
        toolbar.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(toolbar, text="Du", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.filtre_debut = DateEntry(toolbar, width=10)
        self.filtre_debut.pack(side="left", padx=(4, 8))
        self.filtre_debut.set("01/01/2000")

        tk.Label(toolbar, text="Au", bg=CARD_BG, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.filtre_fin = DateEntry(toolbar, width=10)
        self.filtre_fin.pack(side="left", padx=(4, 12))

        tk.Button(toolbar, text="Filtrer", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", command=self.refresh).pack(side="left", padx=(0, 6))
        tk.Button(toolbar, text="Tout afficher", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=self.reset_filtre).pack(side="left", padx=(0, 6))
        tk.Button(toolbar, text="Imprimer", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  command=self.imprimer_liste).pack(side="left")

        # Treeview
        tree_frame = tk.Frame(table_card, bg=CARD_BG)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        columns = ("id", "date", "categorie", "description", "montant", "mode")
        headers = {
            "id": "ID", "date": "DATE", "categorie": "CATÉGORIE",
            "description": "DESCRIPTION", "montant": "MONTANT (TND)",
            "mode": "MODE DE PAIEMENT",
        }
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 height=20)
        style = ttk.Style()
        style.configure("Dep.Treeview", font=("Segoe UI", 9), rowheight=28)
        style.configure("Dep.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        foreground=TEXT_SECONDARY)
        self.tree.configure(style="Dep.Treeview")

        for c in columns:
            self.tree.heading(c, text=headers[c])
            w = 50 if c == "id" else 140 if c == "montant" else 120
            self.tree.column(c, width=w, anchor="center")
        self.tree.column("description", width=220, anchor="w")
        self.tree.column("categorie", width=160, anchor="w")

        self.tree.tag_configure("odd", background=NEUTRE_CLAIR)
        self.tree.tag_configure("even", background=CARD_BG)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Empty state
        self.empty_label = tk.Label(tree_frame, text="Aucune dépense sur cette période",
                                    bg=CARD_BG, fg=TEXT_SECONDARY,
                                    font=("Segoe UI", 10, "italic"))

        # Total card
        total_card = tk.Frame(table_card, bg=PRIMAIRE, bd=0)
        total_card.pack(fill="x", padx=14, pady=(0, 14))

        total_inner = tk.Frame(total_card, bg=PRIMAIRE)
        total_inner.pack(fill="x", padx=16, pady=10)
        tk.Label(total_inner, text="TOTAL DÉPENSES", bg=PRIMAIRE, fg="#C7D2FE",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.total_var = tk.StringVar(value="0.000 TND")
        tk.Label(total_inner, textvariable=self.total_var, bg=PRIMAIRE, fg="white",
                 font=("Segoe UI", 14, "bold")).pack(side="right")

    # ------------------------------------------------------------------
    def _refresh_summary(self):
        for w in self.summary_frame.winfo_children():
            w.destroy()

        today = date.today()
        debut = f"{today.year}-{today.month:02d}-01"
        if today.month == 12:
            fin = f"{today.year + 1}-01-01"
        else:
            fin = f"{today.year}-{today.month + 1:02d}-01"

        depenses = db.get_depenses(debut, fin)
        totaux = {}
        for d in depenses:
            cat = d["categorie"]
            totaux[cat] = totaux.get(cat, 0.0) + d["montant"]

        if not totaux:
            tk.Label(self.summary_frame, text="Aucune dépense ce mois",
                     bg=CARD_BG, fg=TEXT_SECONDARY,
                     font=("Segoe UI", 9, "italic")).pack(anchor="w")
            return

        for cat, montant in sorted(totaux.items(), key=lambda x: -x[1]):
            colors = CAT_COLORS.get(cat, {"bg": NEUTRE_CLAIR, "fg": TEXT_SECONDARY})
            row = tk.Frame(self.summary_frame, bg=CARD_BG)
            row.pack(fill="x", pady=1)

            badge = tk.Label(row, text=f" {cat} ", bg=colors["bg"], fg=colors["fg"],
                             font=("Segoe UI", 8, "bold"), bd=0)
            badge.pack(side="left")

            tk.Label(row, text=f"{montant:.3f} TND", bg=CARD_BG, fg=TEXT_PRIMARY,
                     font=("Segoe UI", 9)).pack(side="right")

    # ------------------------------------------------------------------
    def reset_filtre(self):
        self.filtre_debut.set("01/01/2000")
        self.filtre_fin.set_date(date.today())
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        debut = date_str_to_iso(self.filtre_debut.get()) or "0000-01-01"
        fin = date_str_to_iso(self.filtre_fin.get()) or "9999-12-31"

        depenses = db.get_depenses(debut, fin)
        total = 0.0

        if not depenses:
            self.empty_label.place(relx=0.5, rely=0.4, anchor="center")
        else:
            self.empty_label.place_forget()

        for i, d in enumerate(depenses):
            total += d["montant"]
            row_tag = "odd" if i % 2 else "even"
            self.tree.insert("", "end", iid=str(d["id"]), tags=(row_tag,), values=(
                d["id"], iso_to_date_str(d["date"]) or d["date"],
                f"  {d['categorie']}  ", d["description"],
                f"{d['montant']:.3f}", d["mode_paiement"],
            ))

        self.total_var.set(f"{total:.3f} TND")
        self._refresh_summary()

    def imprimer_liste(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Attention", "Aucune dépense à imprimer.")
            return

        depenses_data = []
        for iid in items:
            valeurs = self.tree.item(iid)["values"]
            date_d, categorie, description, montant_str, mode = valeurs[1:]
            try:
                montant = float(str(montant_str).replace(",", "."))
            except ValueError:
                montant = 0.0
            depenses_data.append((date_d, categorie.strip(), description, montant, mode))

        nom_fichier_defaut = f"Liste_depenses_{date.today().strftime('%Y%m%d')}.pdf"
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer la liste des dépenses",
            defaultextension=".pdf",
            initialfile=nom_fichier_defaut,
            filetypes=[("Fichier PDF", "*.pdf")],
        )
        if not chemin:
            return
        try:
            generer_liste_depenses_pdf(depenses_data, chemin)
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible de générer le PDF : {exc}")
            return
        messagebox.showinfo("Succès", f"Liste exportée : {chemin}")
        try:
            if os.name == "nt":
                os.startfile(chemin)
        except Exception:
            pass

    def on_select(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        depense_id = int(selection[0])
        self.selected_depense_id = depense_id

        depenses = db.get_depenses()
        for d in depenses:
            if d["id"] == depense_id:
                self.date_entry.set(iso_to_date_str(d["date"]) or d["date"])
                self.categorie_var.set(d["categorie"])
                self.description_var.set(d["description"])
                self.montant_var.set(f"{d['montant']:.3f}")
                self.mode_var.set(d["mode_paiement"])
                break

    def nouveau(self):
        self.selected_depense_id = None
        self.date_entry.set_date(date.today())
        self.categorie_var.set(CATEGORIES_DEPENSE[0])
        self.description_var.set("")
        self.montant_var.set("")
        self.mode_var.set("Espèces")
        self.tree.selection_remove(self.tree.selection())
        self.refresh()

    def enregistrer(self):
        date_iso = date_str_to_iso(self.date_entry.get())
        if not date_iso:
            messagebox.showerror("Erreur", "La date est invalide (format JJ/MM/AAAA).")
            return
        if date_iso > date.today().isoformat():
            messagebox.showerror("Erreur", "La date de dépense ne peut pas être dans le futur.")
            return
        try:
            montant = float(self.montant_var.get().replace(",", "."))
            if montant <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Le montant doit être un nombre positif.")
            return

        categorie = self.categorie_var.get()
        description = self.description_var.get().strip()
        mode = self.mode_var.get()

        if self.selected_depense_id:
            db.update_depense(self.selected_depense_id, date_iso, categorie,
                              description, montant, mode)
            messagebox.showinfo("Succès", "Dépense mise à jour.")
        else:
            db.add_depense(date_iso, categorie, description, montant, mode)
            messagebox.showinfo("Succès", "Dépense ajoutée.")

        self.refresh()
        self.app.refresh_stats_tab()

    def modifier(self):
        if not self.selected_depense_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner une dépense dans la liste.")
            return

        win = tk.Toplevel(self)
        win.title("Modifier la dépense")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.configure(bg=BG)

        card = tk.Frame(win, bg=CARD_BG, bd=0,
                        highlightbackground=CARD_BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(card, text="Modifier la dépense", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=18, pady=(14, 4))

        fg = tk.Frame(card, bg=CARD_BG)
        fg.pack(fill="x", padx=18, pady=(0, 14))

        tk.Label(fg, text="Date *", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=4)
        date_entry = DateEntry(fg, width=12)
        date_entry.grid(row=0, column=1, sticky="w", padx=(4, 0), pady=4)
        date_entry.set(self.date_entry.get())

        tk.Label(fg, text="Catégorie *", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4)
        categorie_var = tk.StringVar(value=self.categorie_var.get())
        ttk.Combobox(fg, textvariable=categorie_var,
                     values=CATEGORIES_DEPENSE, width=22,
                     state="readonly").grid(row=1, column=1, sticky="w",
                                            padx=(4, 0), pady=4)

        tk.Label(fg, text="Description", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=4)
        description_var = tk.StringVar(value=self.description_var.get())
        tk.Entry(fg, textvariable=description_var, width=24,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).grid(
            row=2, column=1, sticky="w", padx=(4, 0), pady=4)

        tk.Label(fg, text="Montant (TND) *", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", pady=4)
        montant_var = tk.StringVar(value=self.montant_var.get())
        tk.Entry(fg, textvariable=montant_var, width=24,
                 font=("Segoe UI", 9), bd=1, relief="solid",
                 highlightbackground=CARD_BORDER).grid(
            row=3, column=1, sticky="w", padx=(4, 0), pady=4)

        tk.Label(fg, text="Mode de paiement", bg=CARD_BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).grid(row=4, column=0, sticky="w", pady=4)
        mode_var = tk.StringVar(value=self.mode_var.get())
        ttk.Combobox(fg, textvariable=mode_var,
                     values=["Espèces", "Chèque", "Carte bancaire", "Virement"],
                     width=22, state="readonly").grid(row=4, column=1, sticky="w",
                                                      padx=(4, 0), pady=4)

        def confirmer():
            d_iso = date_str_to_iso(date_entry.get())
            if not d_iso:
                messagebox.showerror("Erreur", "Date invalide (format JJ/MM/AAAA).")
                return
            if d_iso > date.today().isoformat():
                messagebox.showerror("Erreur",
                                     "La date de dépense ne peut pas être dans le futur.")
                return
            try:
                mt = float(montant_var.get().replace(",", "."))
                if mt <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erreur", "Le montant doit être un nombre positif.")
                return
            db.update_depense(
                self.selected_depense_id, d_iso, categorie_var.get(),
                description_var.get().strip(), mt, mode_var.get())
            win.destroy()
            self.refresh()
            self.app.refresh_stats_tab()
            messagebox.showinfo("Succès", "Dépense modifiée avec succès.")

        btn = tk.Frame(fg, bg=CARD_BG)
        btn.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        tk.Button(btn, text="Confirmer", bg=PRIMAIRE, fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  activebackground=PRIMAIRE_HVR, activeforeground="white",
                  cursor="hand2", width=10, command=confirmer).pack(side="left", padx=4)
        tk.Button(btn, text="Annuler", bg=CARD_BG, fg=TEXT_PRIMARY,
                  font=("Segoe UI", 9), bd=1, relief="solid",
                  activebackground=NEUTRE_CLAIR, cursor="hand2",
                  width=10, command=win.destroy).pack(side="left", padx=4)

    def supprimer(self):
        if not self.selected_depense_id:
            messagebox.showwarning("Attention",
                                   "Veuillez sélectionner une dépense.")
            return
        if not messagebox.askyesno("Confirmation", "Supprimer cette dépense ?"):
            return
        db.delete_depense(self.selected_depense_id)
        self.nouveau()
        self.refresh()
        self.app.refresh_stats_tab()
