# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
from datetime import date, datetime, timedelta

import database as db
from widgets import DateEntry, date_str_to_iso

# ── Design system palette ──────────────────────────────────────────
BG          = "#F1F3F6"
CARD_BG     = "#FFFFFF"
CARD_BORDER = "#E2E5EA"
TEXT_PRIMARY = "#1E293B"
TEXT_SECONDARY = "#64748B"
PRIMAIRE     = "#4F46E5"
SUCCES       = "#10B981"
DANGER       = "#EF4444"
NEUTRE_CLAIR = "#F8FAFC"

PERIODES = {
    "Jour": "day",
    "Mois": "month",
    "Année": "year",
}


class StatsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.configure(bg=BG)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        filtre_frame = tk.Frame(self, bg=BG)
        filtre_frame.pack(fill="x", padx=8, pady=8)

        tk.Label(filtre_frame, text="Du :", bg=BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).pack(side="left")
        self.date_debut = DateEntry(filtre_frame, width=12)
        self.date_debut.pack(side="left", padx=4)
        debut_defaut = date.today() - timedelta(days=365)
        self.date_debut.set_date(debut_defaut)

        tk.Label(filtre_frame, text="Au :", bg=BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))
        self.date_fin = DateEntry(filtre_frame, width=12)
        self.date_fin.pack(side="left", padx=4)

        tk.Label(filtre_frame, text="Regrouper par :", bg=BG, fg=TEXT_PRIMARY,
                 font=("Segoe UI", 9)).pack(side="left", padx=(12, 0))
        self.periode_var = tk.StringVar(value="Mois")
        ttk.Combobox(filtre_frame, textvariable=self.periode_var,
                     values=list(PERIODES.keys()), width=10,
                     state="readonly").pack(side="left", padx=4)

        ttk.Button(filtre_frame, text="Actualiser",
                   command=self.refresh).pack(side="left", padx=12)

        ttk.Button(filtre_frame, text="Aujourd'hui",
                   command=self.raccourci_jour).pack(side="left", padx=2)
        ttk.Button(filtre_frame, text="Ce mois",
                   command=self.raccourci_mois).pack(side="left", padx=2)
        ttk.Button(filtre_frame, text="Cette année",
                   command=self.raccourci_annee).pack(side="left", padx=2)

        kpi_frame = tk.Frame(self, bg=BG)
        kpi_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.kpi_recettes = self._creer_kpi(kpi_frame, "Recettes", SUCCES)
        self.kpi_depenses = self._creer_kpi(kpi_frame, "Dépenses", DANGER)
        self.kpi_benefice = self._creer_kpi(kpi_frame, "Bénéfice", PRIMAIRE)
        self.kpi_occupation = self._creer_kpi(kpi_frame, "Taux d'occupation", "#8E44AD")

        main_frame = tk.Frame(self, bg=BG)
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        table_card = tk.Frame(main_frame, bg=CARD_BG, bd=0,
                              highlightbackground=CARD_BORDER, highlightthickness=1)
        table_card.pack(side="left", fill="both", expand=False, padx=(0, 8))

        tk.Label(table_card, text="Récapitulatif par période", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=14, pady=(10, 4))

        columns = ("periode", "recettes", "depenses", "benefice")
        headers = {"periode": "Période", "recettes": "Recettes (TND)",
                   "depenses": "Dépenses (TND)", "benefice": "Bénéfice (TND)"}
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings",
                                  height=18)
        style = ttk.Style()
        style.configure("Stats.Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Stats.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        foreground=TEXT_SECONDARY)
        self.tree.configure(style="Stats.Treeview")
        for c in columns:
            self.tree.heading(c, text=headers[c])
            w = 90 if c == "periode" else 110
            self.tree.column(c, width=w, anchor="center")
        self.tree.tag_configure("odd", background=NEUTRE_CLAIR)
        self.tree.tag_configure("even", background=CARD_BG)
        self.tree.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        graph_card = tk.Frame(main_frame, bg=CARD_BG, bd=0,
                              highlightbackground=CARD_BORDER, highlightthickness=1)
        graph_card.pack(side="left", fill="both", expand=True)

        tk.Label(graph_card, text="Graphiques", bg=CARD_BG,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=14, pady=(10, 4))

        self.canvas = tk.Canvas(graph_card, bg=CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.canvas.bind("<Configure>", lambda e: self._redraw())

        self._last_data = {}

    def _creer_kpi(self, parent, titre, couleur):
        frame = tk.Frame(parent, bg=couleur, bd=0)
        frame.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        tk.Label(frame, text=titre, bg=couleur, fg="white",
                 font=("Segoe UI", 10, "bold")).pack(pady=(8, 0))
        var = tk.StringVar(value="--")
        tk.Label(frame, textvariable=var, bg=couleur, fg="white",
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 8))
        return var

    def raccourci_jour(self):
        today = date.today()
        self.date_debut.set_date(today)
        self.date_fin.set_date(today)
        self.periode_var.set("Jour")
        self.refresh()

    def raccourci_mois(self):
        today = date.today()
        self.date_debut.set_date(date(today.year, today.month, 1))
        self.date_fin.set_date(today)
        self.periode_var.set("Jour")
        self.refresh()

    def raccourci_annee(self):
        today = date.today()
        self.date_debut.set_date(date(today.year, 1, 1))
        self.date_fin.set_date(today)
        self.periode_var.set("Mois")
        self.refresh()

    def refresh(self):
        debut = date_str_to_iso(self.date_debut.get())
        fin = date_str_to_iso(self.date_fin.get())
        if not debut or not fin:
            return

        group_by = PERIODES.get(self.periode_var.get(), "month")

        recettes = {r["periode"]: r["total"] or 0.0
                    for r in db.recap_recettes(debut, fin, group_by)}
        depenses = {r["periode"]: r["total"] or 0.0
                    for r in db.recap_depenses(debut, fin, group_by)}

        periodes = sorted(set(recettes.keys()) | set(depenses.keys()))

        for item in self.tree.get_children():
            self.tree.delete(item)

        total_recettes = 0.0
        total_depenses = 0.0
        for i, p in enumerate(periodes):
            r = recettes.get(p, 0.0)
            d = depenses.get(p, 0.0)
            benefice = r - d
            total_recettes += r
            total_depenses += d
            tag = "odd" if i % 2 else "even"
            self.tree.insert("", "end", tags=(tag,), values=(
                self._formatter_periode(p, group_by),
                f"{r:.3f}", f"{d:.3f}", f"{benefice:.3f}",
            ))

        total_benefice = total_recettes - total_depenses
        occ, total_chambres = db.taux_occupation()
        taux = (occ / total_chambres * 100) if total_chambres else 0

        self.kpi_recettes.set(f"{total_recettes:.3f} TND")
        self.kpi_depenses.set(f"{total_depenses:.3f} TND")
        self.kpi_benefice.set(f"{total_benefice:.3f} TND")
        self.kpi_occupation.set(f"{taux:.1f} %  ({occ}/{total_chambres})")

        self._last_data = {
            "periodes": periodes, "recettes": recettes,
            "depenses": depenses, "group_by": group_by,
        }
        self._redraw()

    def _formatter_periode(self, periode, group_by):
        try:
            if group_by == "day":
                return datetime.strptime(periode, "%Y-%m-%d").strftime("%d/%m/%Y")
            if group_by == "month":
                return datetime.strptime(periode, "%Y-%m").strftime("%m/%Y")
            return periode
        except ValueError:
            return periode

    def _redraw(self):
        self.canvas.delete("all")
        data = self._last_data
        if not data or not data.get("periodes"):
            self.canvas.create_text(
                0, 0, text="Aucune donnée pour cette période",
                fill=TEXT_SECONDARY, font=("Segoe UI", 11),
                anchor="center", tags="empty")
            self.canvas.update_idletasks()
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            self.canvas.coords("empty", w // 2, h // 2)
            return

        periodes = data["periodes"]
        recettes = data["recettes"]
        depenses = data["depenses"]
        group_by = data["group_by"]
        labels = [self._formatter_periode(p, group_by) for p in periodes]
        vals_r = [recettes.get(p, 0.0) for p in periodes]
        vals_d = [depenses.get(p, 0.0) for p in periodes]
        benefices = [r - d for r, d in zip(vals_r, vals_d)]

        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), 300)
        ch = max(self.canvas.winfo_height(), 300)

        chart_h = (ch - 40) // 2
        pad_l, pad_r, pad_t = 60, 20, 10
        chart_w = cw - pad_l - pad_r

        self._draw_bar_chart(0, pad_t, chart_w, chart_h,
                             labels, vals_r, vals_d, "Recettes vs Dépenses")
        self._draw_line_chart(0, pad_t + chart_h + 20, chart_w, chart_h,
                              labels, benefices, "Évolution du bénéfice")

    def _draw_bar_chart(self, x0, y0, w, h, labels, vals_r, vals_d, title):
        c = self.canvas
        n = len(labels)
        if n == 0:
            return

        max_val = max(max(vals_r, default=0), max(vals_d, default=0), 1)
        bar_area_top = y0 + 25
        bar_area_bot = y0 + h - 25
        bar_area_h = bar_area_bot - bar_area_top
        c.create_text(x0 + w // 2, y0 + 5, text=title,
                      fill=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"))

        c.create_line(x0 + 10, bar_area_bot, x0 + w - 10, bar_area_bot,
                      fill=CARD_BORDER, width=1)

        slot_w = w / n if n else 1
        bar_w = slot_w * 0.35

        for i in range(n):
            x_center = x0 + 20 + slot_w * i + slot_w / 2
            r_h = (vals_r[i] / max_val) * bar_area_h if max_val else 0
            d_h = (vals_d[i] / max_val) * bar_area_h if max_val else 0

            x_r = x_center - bar_w - 2
            c.create_rectangle(x_r, bar_area_bot - r_h, x_r + bar_w, bar_area_bot,
                               fill=SUCCES, outline="", tags="bar")
            x_d = x_center + 2
            c.create_rectangle(x_d, bar_area_bot - d_h, x_d + bar_w, bar_area_bot,
                               fill=DANGER, outline="", tags="bar")

            lbl = labels[i]
            if len(lbl) > 7:
                lbl = lbl[:6] + "…"
            c.create_text(x_center, bar_area_bot + 12, text=lbl,
                          fill=TEXT_SECONDARY, font=("Segoe UI", 7),
                          angle=45, anchor="ne")

        for i in range(5):
            val = max_val * i / 4
            y = bar_area_bot - (bar_area_h * i / 4)
            c.create_text(x0 + 8, y, text=f"{val:.0f}",
                          fill=TEXT_SECONDARY, font=("Segoe UI", 7),
                          anchor="e")
            if i > 0:
                c.create_line(x0 + 12, y, x0 + w - 10, y,
                              fill=NEUTRE_CLAIR, width=1, dash=(3, 3))

        lx = x0 + w - 120
        ly = y0 + 22
        c.create_rectangle(lx, ly, lx + 10, ly + 10, fill=SUCCES, outline="")
        c.create_text(lx + 14, ly + 5, text="Recettes", fill=TEXT_SECONDARY,
                      font=("Segoe UI", 8), anchor="w")
        c.create_rectangle(lx + 70, ly, lx + 80, ly + 10, fill=DANGER, outline="")
        c.create_text(lx + 84, ly + 5, text="Dépenses", fill=TEXT_SECONDARY,
                      font=("Segoe UI", 8), anchor="w")

    def _draw_line_chart(self, x0, y0, w, h, labels, values, title):
        c = self.canvas
        n = len(labels)
        if n == 0:
            return

        chart_top = y0 + 25
        chart_bot = y0 + h - 25
        chart_h = chart_bot - chart_top
        c.create_text(x0 + w // 2, y0 + 5, text=title,
                      fill=TEXT_PRIMARY, font=("Segoe UI", 10, "bold"))

        c.create_line(x0 + 10, chart_bot, x0 + w - 10, chart_bot,
                      fill=CARD_BORDER, width=1)

        v_min = min(values, default=0)
        v_max = max(values, default=0)
        v_range = max(abs(v_min), abs(v_max), 1)
        zero_y = chart_top + chart_h * (v_max / (v_range * 2)) if v_range else chart_top + chart_h / 2

        c.create_line(x0 + 10, zero_y, x0 + w - 10, zero_y,
                      fill=TEXT_SECONDARY, width=1, dash=(4, 4))

        points = []
        slot_w = w / n if n else 1
        for i in range(n):
            x = x0 + 20 + slot_w * i + slot_w / 2
            ratio = (values[i] - (-v_range)) / (v_range * 2) if v_range else 0.5
            y = chart_bot - ratio * chart_h
            points.append((x, y))

            lbl = labels[i]
            if len(lbl) > 7:
                lbl = lbl[:6] + "…"
            c.create_text(x, chart_bot + 12, text=lbl,
                          fill=TEXT_SECONDARY, font=("Segoe UI", 7),
                          angle=45, anchor="ne")

        if len(points) > 1:
            flat = [coord for p in points for coord in p]
            c.create_line(*flat, fill=PRIMAIRE, width=2, smooth=True)

        for x, y in points:
            c.create_oval(x - 4, y - 4, x + 4, y + 4,
                          fill=PRIMAIRE, outline=CARD_BG, width=2)

        for i in range(5):
            val = v_min + (v_max - v_min) * i / 4 if v_max != v_min else 0
            y = chart_bot - chart_h * i / 4
            c.create_text(x0 + 8, y, text=f"{val:.0f}",
                          fill=TEXT_SECONDARY, font=("Segoe UI", 7), anchor="e")

        c.create_text(x0 + w - 60, y0 + 22, text="Bénéfice",
                      fill=PRIMAIRE, font=("Segoe UI", 8, "bold"))
