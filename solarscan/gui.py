"""
SolarScan desktop interface (tkinter): type an address, press Scan, read the answer.

Layout
  left   inputs: building (address or coordinates, emirate) and the four assumptions as sliders
  right  four key numbers, the roof plan with the modules that fit, the system assumed and a
         payback heat map; buttons to open the PDF/HTML report
Cost and electricity price update the payback at once (no new scan needed). Tilt and edge strip
change the layout, so they take effect on the next scan.

Start:  solarscan gui
"""

import base64
import io
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

from solarscan.cli import DEMO_CASE, demo_kwargs, run_scan
from solarscan.report import _heat, build_report_content, roof_plan_png

NAVY, ACCENT, INK, INK2, LINE, BG, CARD, WARN = ("#14285a", "#1f4e9a", "#14171c", "#59606b", "#d9dee6",
                                                 "#f3f5f8", "#ffffff", "#e07b2a")
EMIRATES = ["(nearest)", "sharjah", "dubai", "abu_dhabi", "ajman", "ras_al_khaimah", "fujairah", "umm_al_quwain"]
OUT_DIR = os.path.join(os.path.expanduser("~"), "SolarScan", "reports")


def _font(size, bold=False):
    return ("Segoe UI", size, "bold") if bold else ("Segoe UI", size)


class App:
    def __init__(self, root):
        self.root, self.data, self.q = root, None, queue.Queue()
        root.title("SolarScan – rooftop solar screening")
        root.configure(bg=BG)
        root.geometry("1240x800")
        root.minsize(1100, 720)
        st = ttk.Style(root)
        st.theme_use("clam")
        st.configure("TCombobox", padding=4)
        st.configure("Horizontal.TScale", background=CARD)
        st.configure("TProgressbar", troughcolor=LINE, background=ACCENT, thickness=4)

        head = tk.Frame(root, bg=NAVY, height=56)
        head.pack(fill="x")
        tk.Label(head, text="SolarScan", fg="white", bg=NAVY, font=_font(17, True)).pack(side="left", padx=18, pady=10)
        tk.Label(head, text="How much solar fits on this roof, and does it pay back?", fg="#c9d4ea", bg=NAVY,
                 font=_font(11)).pack(side="left", pady=12)

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)
        self._sidebar(body)
        self._main(body)

        bar = tk.Frame(root, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        bar.pack(fill="x", side="bottom")
        self.status = tk.Label(bar, text="Enter an address, or run the demo building.", bg=CARD, fg=INK2,
                               font=_font(9), anchor="w")
        self.status.pack(side="left", padx=12, pady=5)
        self.prog = ttk.Progressbar(bar, mode="indeterminate", length=160)
        root.after(100, self._poll)

    # ------------------------------------------------------------ inputs
    def _card(self, parent, title, **pack):
        f = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        f.pack(fill="x", pady=(0, 12), **pack)
        tk.Label(f, text=title, bg=CARD, fg=INK, font=_font(11, True)).pack(anchor="w", padx=14, pady=(10, 4))
        return f

    def _sidebar(self, body):
        side = tk.Frame(body, bg=BG, width=300)
        side.pack(side="left", fill="y", padx=(0, 16))
        side.pack_propagate(False)

        self.building_card = self._card(side, "1  Building")
        self.addr = tk.StringVar()
        self.entry = tk.Entry(self.building_card, textvariable=self.addr, font=_font(11), relief="solid", bd=1, highlightthickness=0)
        self.entry.pack(fill="x", padx=14, ipady=5)
        self.entry.bind("<Return>", lambda _: self.scan())
        tk.Label(self.building_card, text="Address, place name, or  lat, lon", bg=CARD, fg=INK2, font=_font(8)).pack(anchor="w", padx=14)
        row = tk.Frame(self.building_card, bg=CARD)
        row.pack(fill="x", padx=14, pady=(8, 12))
        tk.Label(row, text="Emirate", bg=CARD, fg=INK2, font=_font(9)).pack(side="left")
        self.emirate = ttk.Combobox(row, values=EMIRATES, state="readonly", width=17)
        self.emirate.current(0)
        self.emirate.pack(side="right")

        self.assumptions_card = self._card(side, "2  Assumptions")
        self.cost = self._slider(self.assumptions_card, "Installed cost", 2000, 5000, 3000, 100, "{:,.0f} AED/kWp", live=True)
        self.price = self._slider(self.assumptions_card, "Electricity price", 0.20, 0.60, 0.38, 0.01, "{:.2f} AED/kWh", live=True)
        self.tilt = self._slider(self.assumptions_card, "Module tilt", 5, 30, 15, 1, "{:.0f}°")
        self.edge = self._slider(self.assumptions_card, "Edge strip", 0.5, 3.0, 1.5, 0.5, "{:.1f} m")
        tk.Frame(self.assumptions_card, bg=CARD, height=6).pack()

        self.go = tk.Button(side, text="Scan roof", command=self.scan, bg=ACCENT, fg="white", activebackground=NAVY,
                            activeforeground="white", relief="flat", font=_font(12, True), cursor="hand2")
        self.go.pack(fill="x", ipady=8)
        self.demo_btn = tk.Button(side, text="Try the demo building", command=self.demo, bg=CARD, fg=ACCENT, relief="flat",
                                  font=_font(10), cursor="hand2", highlightthickness=1, highlightbackground=LINE
                                  )
        self.demo_btn.pack(fill="x", pady=(8, 0), ipady=5)

    def _slider(self, parent, label, lo, hi, val, step, fmt, live=False):
        var = tk.DoubleVar(value=val)
        f = tk.Frame(parent, bg=CARD)
        f.pack(fill="x", padx=14, pady=(4, 2))
        tk.Label(f, text=label, bg=CARD, fg=INK2, font=_font(9)).pack(side="left")
        out = tk.Label(f, text=fmt.format(val), bg=CARD, fg=INK, font=_font(9, True))
        out.pack(side="right")

        def moved(_=None):
            v = round(round(var.get() / step) * step, 2)
            var.set(v)
            out.config(text=fmt.format(v))
            if live:
                self._refresh_money()
        sc = ttk.Scale(parent, from_=lo, to=hi, variable=var, command=moved)
        sc.pack(fill="x", padx=14)
        var.scale = sc
        return var

    # ------------------------------------------------------------ results
    def _main(self, body):
        main = tk.Frame(body, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.tiles_frame = tk.Frame(main, bg=BG)
        self.tiles_frame.pack(fill="x")
        self.tiles = []
        for i, name in enumerate(["System size", "Energy per year", "Investment", "Payback"]):
            t = tk.Frame(self.tiles_frame, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            t.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            self.tiles_frame.columnconfigure(i, weight=1)
            tk.Label(t, text=name, bg=CARD, fg=INK2, font=_font(9)).pack(anchor="w", padx=12, pady=(8, 0))
            v = tk.Label(t, text="–", bg=CARD, fg=ACCENT, font=_font(20, True))
            v.pack(anchor="w", padx=12)
            s = tk.Label(t, text=" ", bg=CARD, fg=INK2, font=_font(8))
            s.pack(anchor="w", padx=12, pady=(0, 8))
            self.tiles.append((v, s))

        lower = tk.Frame(main, bg=BG)
        lower.pack(fill="both", expand=True, pady=(12, 0))
        self.plan_frame = tk.Frame(lower, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.plan_frame.pack(side="left", fill="both", expand=True)
        tk.Label(self.plan_frame, text="Roof plan", bg=CARD, fg=INK, font=_font(11, True)).pack(anchor="w", padx=14, pady=(10, 0))
        self.plan = tk.Label(self.plan_frame, bg=CARD, text="The roof and the modules that fit\nwill appear here.",
                             fg=INK2, font=_font(10))
        self.plan.pack(fill="both", expand=True, padx=8, pady=8)

        right = tk.Frame(lower, bg=BG, width=380)
        right.pack(side="left", fill="y", padx=(12, 0))
        right.pack_propagate(False)
        self.sys_frame = tk.Frame(right, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.sys_frame.pack(fill="x")
        tk.Label(self.sys_frame, text="System assumed", bg=CARD, fg=INK, font=_font(11, True)).pack(anchor="w", padx=14, pady=(10, 4))
        self.sys_rows = tk.Frame(self.sys_frame, bg=CARD)
        self.sys_rows.pack(fill="x", padx=14, pady=(0, 10))

        self.heat_frame = tk.Frame(right, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        self.heat_frame.pack(fill="both", expand=True, pady=(12, 0))
        tk.Label(self.heat_frame, text="Payback (years)", bg=CARD, fg=INK, font=_font(11, True)).pack(anchor="w", padx=14, pady=(10, 0))
        tk.Label(self.heat_frame, text="rows: cost, AED/kWp | columns: price, AED/kWh", bg=CARD, fg=INK2,
                 font=_font(8)).pack(anchor="w", padx=14)
        self.heat = tk.Canvas(self.heat_frame, bg=CARD, highlightthickness=0, height=170)
        self.heat.pack(fill="x", padx=14, pady=6)

        btns = tk.Frame(right, bg=BG)
        btns.pack(fill="x", pady=(12, 0))
        self.open_pdf = tk.Button(btns, text="Open PDF report", state="disabled", command=lambda: self._open("pdf"),
                                  bg=ACCENT, fg="white", relief="flat", font=_font(10, True), cursor="hand2",
                                  disabledforeground="#9fb3d6")
        self.open_pdf.pack(side="left", fill="x", expand=True, ipady=5)
        self.open_html = tk.Button(btns, text="Open web report", state="disabled", command=lambda: self._open("html"),
                                   bg=CARD, fg=ACCENT, relief="flat", font=_font(10), cursor="hand2",
                                   highlightthickness=1, highlightbackground=LINE)
        self.open_html.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=5)

    # ------------------------------------------------------------ actions
    def demo(self):
        self.addr.set(DEMO_CASE["address"])
        self.emirate.set(DEMO_CASE["emirate"])
        kw = demo_kwargs()
        kw.pop("emirate")  # taken from the emirate box
        self._start(kw)

    def scan(self):
        text = self.addr.get().strip()
        if not text:
            self._say("Enter an address or coordinates first.", warn=True)
            return
        kw = dict(address=text)
        parts = [p.strip() for p in text.split(",")]
        if len(parts) == 2:
            try:
                kw.update(lat=float(parts[0]), lon=float(parts[1]))
            except ValueError:
                pass
        self._start(kw)

    def _start(self, kw):
        em = self.emirate.get()
        kw.update(tilt=self.tilt.get(), setback=self.edge.get(), rate_aed=self.price.get(),
                  cost_per_kw=self.cost.get(), emirate=None if em.startswith("(") else em,
                  out_dir=OUT_DIR, fmt="both", return_data=True)
        self.go.config(state="disabled", text="Scanning…")
        self._say("Finding the building and laying out the modules…")
        self.prog.pack(side="right", padx=12)
        self.prog.start(12)
        threading.Thread(target=self._work, args=(kw,), daemon=True).start()

    def _work(self, kw):
        try:
            self.q.put(("ok", run_scan(**kw)))
        except Exception as e:  # shown in the status bar
            self.q.put(("err", str(e) or e.__class__.__name__))

    def _poll(self):
        try:
            kind, val = self.q.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll)
            return
        self.prog.stop(); self.prog.pack_forget()
        self.go.config(state="normal", text="Scan roof")
        if kind == "ok":
            self.data = val
            self._show()
            self._say(f"Done. Reports saved in {OUT_DIR}")
        else:
            self._say(f"Could not scan: {val}", warn=True)
        self.root.after(100, self._poll)

    def _say(self, text, warn=False):
        self.status.config(text=text, fg=WARN if warn else INK2)

    def _open(self, kind):
        if self.data and self.data.get(kind):
            webbrowser.open("file:///" + os.path.abspath(self.data[kind]).replace("\\", "/"))

    # ------------------------------------------------------------ drawing
    def _show(self):
        d = self.data
        buf = io.BytesIO()
        h = max(self.plan.winfo_height() - 16, 360)
        roof_plan_png(d, buf, width_in=h / 100 / 1.22, dpi=100)
        self._img = tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
        self.plan.config(image=self._img, text="")
        c = build_report_content(d)
        for w in self.sys_rows.winfo_children():
            w.destroy()
        for i, (k, v) in enumerate(c["system"][:6]):
            tk.Label(self.sys_rows, text=k, bg=CARD, fg=INK2, font=_font(9)).grid(row=i, column=0, sticky="nw", pady=1)
            tk.Label(self.sys_rows, text=v, bg=CARD, fg=INK, font=_font(9), wraplength=270, justify="left"
                     ).grid(row=i, column=1, sticky="w", padx=(10, 0), pady=1)
        self.open_pdf.config(state="normal")
        self.open_html.config(state="normal")
        self._refresh_money()

    def _refresh_money(self):
        d = self.data
        if not d:
            return
        d = dict(d, cost_per_kw=self.cost.get(), rate_aed=self.price.get())
        kwp, kwh = d["dc_capacity_kw"], d["annual_kwh"]
        d["payback_years"] = (kwp * d["cost_per_kw"]) / (kwh * d["rate_aed"]) if kwh > 0 else float("inf")
        c = build_report_content(d)
        for (v, s), (_, val, sub) in zip(self.tiles, c["key"]):
            v.config(text=val)
            s.config(text=sub)
        self._draw_heat(c)

    def _draw_heat(self, c):
        cv = self.heat
        cv.delete("all")
        cv.update_idletasks()
        W = max(cv.winfo_width(), 340)
        x0, cw, ch, y0 = 62, (W - 64) / 4, 32, 22
        vals = [v for row in c["grid"] for v in row]
        lo, hi = min(vals), max(vals)
        for j, r in enumerate(c["tariffs"]):
            cv.create_text(x0 + cw * (j + 0.5), y0 / 2, text=f"{r:.2f}", fill=INK2, font=_font(9, True))
        for i, (cost, row) in enumerate(zip(c["costs"], c["grid"])):
            y = y0 + i * ch
            cv.create_text(x0 - 8, y + ch / 2, text=f"{cost:,.0f}", anchor="e", fill=INK2, font=_font(9, True))
            for j, v in enumerate(row):
                bg, fg = _heat(v, lo, hi)
                x = x0 + j * cw
                cv.create_rectangle(x + 1, y + 1, x + cw - 1, y + ch - 1, fill=bg, outline="")
                cv.create_text(x + cw / 2, y + ch / 2, text=f"{v:.1f}", fill=fg,
                               font=_font(10, (i, j) == c["base"]))
        bi, bj = c["base"]
        cv.create_rectangle(x0 + bj * cw + 1, y0 + bi * ch + 1, x0 + (bj + 1) * cw - 1, y0 + (bi + 1) * ch - 1,
                            outline=WARN, width=2.5)
        cv.config(height=y0 + 4 * ch + 4)


def _dpi_aware():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def main(screenshot=None):
    """Open the window. With screenshot=path: run the demo, save a picture of the window, and close."""
    _dpi_aware()
    root = tk.Tk()
    app = App(root)
    if screenshot:
        def grab():
            if app.data is None:
                root.after(300, grab)
                return
            root.after(900, shoot)

        def shoot():
            root.lift(); root.attributes("-topmost", True); root.update()
            from PIL import ImageGrab
            x, y = root.winfo_rootx(), root.winfo_rooty()
            ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height())).save(screenshot)
            root.destroy()
        root.after(400, app.demo)
        root.after(1500, grab)
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
