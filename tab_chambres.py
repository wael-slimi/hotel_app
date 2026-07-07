# -*- coding: utf-8 -*-
import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageTk, ImageDraw, ImageFont

import database as db
from database import ETATS_CHAMBRE, get_connection, get_chambre_photos, set_chambre_photos
from widgets import iso_to_date_str, _formater_prix

PHOTOS_DIR = Path(__file__).parent / "photos_chambres"
PHOTOS_DIR.mkdir(exist_ok=True)

THUMB_SIZE = (180, 135)  # for form previews
CARD_SIZE = (200, 170)   # full tile card
NB_COLONNES = 6

FONT_BOLD = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/TTF/DejaVuSans.ttf"

COULEURS_ETAT = {
    "Libre": "#4CAF50",
    "Occupée": "#E53935",
    "Réservée": "#FB8C00",
    "Maintenance": "#9E9E9E",
}


def _arrondir_coins(img, radius=6, composite_on_white=True):
    img_rgba = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    img_rgba.putalpha(mask)
    if composite_on_white:
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img_rgba, mask=img_rgba.split()[3])
        return bg
    return img_rgba


def _exact_thumb(img):
    w, h = img.size
    tw, th = THUMB_SIZE
    r_img = tw / th
    r_src = w / h
    if r_src > r_img:
        nh = h
        nw = int(h * r_img)
    else:
        nw = w
        nh = int(w / r_img)
    x = (w - nw) // 2
    y = (h - nh) // 2
    return img.crop((x, y, x + nw, y + nh)).resize(THUMB_SIZE, Image.LANCZOS)


def _placeholder_thumbnail():
    img = Image.new("RGB", THUMB_SIZE, "#E8E8E8")
    draw = ImageDraw.Draw(img)
    # Bed icon as simple shape
    cx, cy = THUMB_SIZE[0] // 2, THUMB_SIZE[1] // 2
    bw, bh = 36, 18
    draw.rounded_rectangle(
        [cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2],
        radius=4, fill="#BBBBBB"
    )
    draw.rounded_rectangle(
        [cx - 14, cy - bh // 2 - 6, cx - 8, cy - bh // 2 + 2],
        radius=2, fill="#BBBBBB"
    )
    draw.rounded_rectangle(
        [cx + 8, cy - bh // 2 - 6, cx + 14, cy - bh // 2 + 2],
        radius=2, fill="#BBBBBB"
    )
    draw.text((cx - 12, cy + 12), "Chambre", fill="#BBBBBB", font=None)
    return img


def _cover_fill(img, target_size):
    tw, th = target_size
    w, h = img.size
    r_t = tw / th
    r_s = w / h
    if r_s > r_t:
        nw = int(h * r_t)
        x = (w - nw) // 2
        return img.crop((x, 0, x + nw, h)).resize(target_size, Image.LANCZOS)
    else:
        nh = int(w / r_t)
        y = (h - nh) // 2
        return img.crop((0, y, w, y + nh)).resize(target_size, Image.LANCZOS)


def _placeholder_card(card_size):
    W, H = card_size
    img = Image.new("RGBA", card_size, "#E8E8E8")
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2 - 10
    bw, bh = 40, 20
    draw.rounded_rectangle([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2],
                           radius=4, fill="#BBBBBB")
    draw.rounded_rectangle([cx - 16, cy - bh // 2 - 8, cx - 9, cy - bh // 2 + 2],
                           radius=2, fill="#BBBBBB")
    draw.rounded_rectangle([cx + 9, cy - bh // 2 - 8, cx + 16, cy - bh // 2 + 2],
                           radius=2, fill="#BBBBBB")
    draw.text((cx - 14, cy + 14), "Chambre", fill="#BBBBBB", font=None)
    return _arrondir_coins(img, 12, composite_on_white=False)


def _render_card(card_size, photo_path, chambre, prix, rtype):
    W, H = card_size
    if photo_path and Path(photo_path).is_file():
        try:
            img = Image.open(photo_path).convert("RGBA")
        except Exception:
            return _placeholder_card(card_size)
    else:
        return _placeholder_card(card_size)

    img = _cover_fill(img, card_size)

    # Gradient overlay at bottom 35%
    gh = int(H * 0.38)
    gradient = Image.new("RGBA", (W, gh), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    for y in range(gh):
        a = int(200 * (y / gh))
        gdraw.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    img.paste(gradient, (0, H - gh), gradient)

    # Text on gradient
    draw = ImageDraw.Draw(img)
    try:
        fb = ImageFont.truetype(FONT_BOLD, 11)
        fr = ImageFont.truetype(FONT_REG, 8)
        fp = ImageFont.truetype(FONT_BOLD, 10)
    except Exception:
        fb = fr = fp = ImageFont.load_default()

    lx, ly = 10, H - 50
    draw.text((lx, ly), f"Chambre {chambre['numero']}", font=fb, fill="white")
    ly += 16
    draw.text((lx, ly), rtype, font=fr, fill=(255, 255, 255, 200))
    ly += 14
    draw.text((lx, ly), f"{prix:.0f} TND / nuit", font=fp, fill="#E65100")

    img = _arrondir_coins(img, 12, composite_on_white=False)
    return img


def _load_thumbnail(photo_path):
    if photo_path:
        p = Path(photo_path)
        if p.is_file():
            try:
                img = Image.open(p).convert("RGB")
                return _exact_thumb(img)
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

        self.canvas = tk.Canvas(canvas_frame, bg="#F0F2F5",
                                 highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                        command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.grid_frame = tk.Frame(self.canvas, bg="#F0F2F5")
        self.grid_window = self.canvas.create_window(
            (0, 0), window=self.grid_frame, anchor="nw")

        self.grid_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Hint row
        hint_frame = ttk.Frame(self)
        hint_frame.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Label(
            hint_frame,
            text="Clic gauche : Photo suivante  |  Clic droit : Modifier  |  Double-clic : Occupant",
            font=("Segoe UI", 8), foreground="#888888"
        ).pack(side="left")

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
                    bg="#F0F2F5", fg="#1F4E79",
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

        tile = tk.Frame(self.grid_frame, bg=self.grid_frame.cget("bg"),
                        bd=0, highlightthickness=0,
                        width=CARD_SIZE[0], height=CARD_SIZE[1],
                        cursor="hand2")
        tile.grid(row=row, column=col, padx=5, pady=5)
        tile.grid_propagate(False)

        # Load photos
        photos_rows = get_chambre_photos(chambre["id"])
        paths = [r["photo_path"] for r in photos_rows]
        if not paths and chambre.get("photo"):
            paths = [chambre["photo"]]
        tile.photo_paths = paths
        tile.photo_index = 0

        # Card background image (covers full tile)
        lbl = tk.Label(tile, bg=self.grid_frame.cget("bg"))
        lbl.place(x=0, y=0, width=CARD_SIZE[0], height=CARD_SIZE[1])

        # Counter badge (defined before render_and_set references it)
        counter = tk.Label(tile, text="",
                           bg="#333333", fg="white",
                           font=("Segoe UI", 7), padx=3, pady=0)
        if len(paths) > 1:
            counter.place(relx=1.0, rely=1.0, anchor="se", x=-5, y=-5)

        # Render initial card image
        def render_and_set(idx):
            p = paths[idx] if idx < len(paths) else ""
            prix = chambre["prix"]
            rtype = chambre["type"]
            img = _render_card(CARD_SIZE, p, chambre, prix, rtype)
            tk_img = ImageTk.PhotoImage(img)
            self._thumb_cache[f"{chambre['id']}_{idx}"] = tk_img
            lbl.configure(image=tk_img)
            if len(paths) > 1:
                counter.configure(text=f"{idx+1}/{len(paths)}")

        render_and_set(0)

        # Status pill
        pill = tk.Label(tile, text=chambre["etat"],
                        bg=couleur, fg="white",
                        font=("Segoe UI", 7, "bold"), padx=5, pady=1)
        pill.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)

        # Auto-slideshow every 2.5s
        slideshow_id = [None]

        def auto_next():
            if len(paths) > 1:
                nxt = (tile.photo_index + 1) % len(paths)
                tile.photo_index = nxt
                render_and_set(nxt)
                slideshow_id[0] = tile.after(2500, auto_next)

        def stop_slideshow():
            if slideshow_id[0] is not None:
                tile.after_cancel(slideshow_id[0])
                slideshow_id[0] = None

        def restart_slideshow():
            stop_slideshow()
            if len(paths) > 1:
                slideshow_id[0] = tile.after(2500, auto_next)

        if len(paths) > 1:
            slideshow_id[0] = tile.after(2500, auto_next)

        # Photo cycling
        def cycle(n):
            if len(paths) > 1:
                idx = (tile.photo_index + n) % len(paths)
                tile.photo_index = idx
                render_and_set(idx)
                restart_slideshow()

        # Bindings on the full card surface
        for w in (lbl, tile, pill, counter):
            w.bind("<Button-1>",
                   lambda e, c=chambre: (
                       cycle(1), self.afficher_occupant(c)
                   )[-1])
            w.bind("<Button-3>",
                   lambda e, c=chambre: self.ouvrir_details(c))

        # Separate double-click for occupant
        for w in (lbl, tile, pill, counter):
            w.bind("<Double-Button-1>",
                   lambda e, c=chambre: self.afficher_occupant(c))

    # ------------------------------------------------------------------
    def afficher_occupant(self, chambre):
        win = tk.Toplevel(self)
        win.title(f"Chambre {chambre['numero']} — Détails occupation")
        win.resizable(False, False)
        win.transient(self)
        win.wait_visibility()
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
        # Photos (multiples)
        # ------------------------------------------------------------
        tk.Label(win, text="Photos").grid(row=5, column=0, sticky="ne", **pad)

        photos_list = []  # list of (path, label_widget, btn_widget)

        photos_container = tk.Frame(win, bd=1, relief="solid", bg="white")
        photos_container.grid(row=5, column=1, columnspan=2, sticky="ew",
                              padx=10, pady=6, ipady=4)

        def rebuild_photos_ui():
            for w in photos_container.winfo_children():
                w.destroy()
            if not photos_list:
                tk.Label(photos_container, text="Aucune photo",
                         fg="#999999", bg="white",
                         font=("Segoe UI", 8)).pack(pady=10)
                return
            row_frame = tk.Frame(photos_container, bg="white")
            row_frame.pack(padx=4, pady=4)
            for idx, (path, _, _) in enumerate(photos_list):
                cell = tk.Frame(row_frame, bg="white", bd=1, relief="solid")
                cell.grid(row=0, column=idx, padx=3)

                pil = _load_thumbnail(path)
                tk_img = ImageTk.PhotoImage(pil)
                self._thumb_cache[f"form_{path}"] = tk_img

                lbl = tk.Label(cell, image=tk_img, bg="white")
                lbl.pack()
                lbl.image = tk_img

                def make_del(i):
                    def del_photo():
                        nonlocal photos_list
                        if i < len(photos_list):
                            photos_list.pop(i)
                            rebuild_photos_ui()
                    return del_photo

                tk.Button(cell, text="X", font=("Segoe UI", 6, "bold"),
                          fg="white", bg="#E53935", bd=0,
                          command=make_del(idx)).place(relx=1.0, rely=0.0,
                                                       anchor="ne")

        def ajouter_photo():
            path = filedialog.askopenfilename(
                title="Choisir une image",
                filetypes=[("Images", "*.jpg *.jpeg *.png"), ("Tous", "*.*")]
            )
            if not path:
                return
            src = Path(path)
            try:
                dest = PHOTOS_DIR / src.name
                if dest.exists():
                    if dest.resolve() == src.resolve():
                        photos_list.append((str(dest), None, None))
                        rebuild_photos_ui()
                        return
                    stem = numero_var.get().strip() or "chambre"
                    dest = PHOTOS_DIR / f"{src.stem}_{stem}{src.suffix}"
                shutil.copy2(str(src), str(dest))
                photos_list.append((str(dest), None, None))
                rebuild_photos_ui()
            except Exception as e:
                messagebox.showerror("Erreur",
                                     f"Impossible de copier l'image :\n{e}")

        if est_edition:
            for p in get_chambre_photos(chambre["id"]):
                photos_list.append((p["photo_path"], None, None))

        rebuild_photos_ui()

        tk.Button(win, text="+ Ajouter une photo",
                  command=ajouter_photo).grid(
            row=6, column=1, sticky="w", padx=10, pady=(0, 6))

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
                                   desc_var.get(), "")
                    # Get the new room's ID
                    nouvelles = db.get_chambres()
                    new_id = None
                    for nv in nouvelles:
                        if nv["numero"] == numero:
                            new_id = nv["id"]
                            break
                    if new_id:
                        paths = [p[0] for p in photos_list]
                        set_chambre_photos(new_id, paths)
                else:
                    db.update_chambre(chambre["id"], numero, type_var.get(),
                                       prix, etat_var.get(), desc_var.get(), "")
                    paths = [p[0] for p in photos_list]
                    set_chambre_photos(chambre["id"], paths)
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
        action_frame.grid(row=7, column=0, columnspan=3, pady=(10, 12))
        tk.Button(action_frame, text="Enregistrer", width=12,
                  command=enregistrer).pack(side="left", padx=6)
        if est_edition:
            tk.Button(action_frame, text="Supprimer", width=12,
                      command=supprimer).pack(side="left", padx=6)
        tk.Button(action_frame, text="Annuler", width=12,
                  command=win.destroy).pack(side="left", padx=6)
