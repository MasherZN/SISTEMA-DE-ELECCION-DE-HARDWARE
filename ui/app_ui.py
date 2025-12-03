import tkinter as tk
from tkinter import ttk, messagebox
import requests
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import ImageGrab
import datetime


API_URL = "http://127.0.0.1:8000/recommend"


# ============================================================
#       ESTILO OSCURO
# ============================================================
def apply_dark_theme(style):
    style.theme_create("darkmode", parent="clam", settings={
        ".": {
            "configure": {
                "background": "#0e1117",
                "foreground": "#d9e6ff",
                "fieldbackground": "#0e1117",
                "font": ("Segoe UI", 10)
            }
        },
        "TLabel": {"configure": {"background": "#0e1117", "foreground": "#d9e6ff"}},
        "TFrame": {"configure": {"background": "#0e1117"}},
        "TButton": {
            "configure": {
                "background": "#1f6feb",
                "foreground": "white",
                "padding": 6,
                "font": ("Segoe UI", 10, "bold"),
                "borderwidth": 0
            },
            "map": {"background": [("active", "#388bfd")]}
        },
        "TEntry": {
            "configure": {
                "fieldbackground": "#161b22",
                "foreground": "white",
                "insertcolor": "white"
            }
        },
        "Treeview": {
            "configure": {
                "background": "#161b22",
                "fieldbackground": "#161b22",
                "foreground": "white",
                "rowheight": 28,
                "bordercolor": "#0e1117",
                "borderwidth": 0
            },
            "map": {
                "background": [("selected", "#1f6feb")],
                "foreground": [("selected", "white")]
            }
        }
    })
    style.theme_use("darkmode")


# ============================================================
# POPUP ENCUESTA
# ============================================================
class SurveyPopup(tk.Toplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback = callback

        self.title("Encuesta del Usuario")
        self.geometry("420x620")
        self.configure(bg="#0e1117")
        self.resizable(False, False)

        container = tk.Frame(self, bg="#0e1117")
        container.pack(padx=20, pady=20, fill="both", expand=True)

        title = tk.Label(container, text="Encuesta del Sistema Experto",
                         bg="#0e1117", fg="white",
                         font=("Segoe UI", 16, "bold"))
        title.pack(pady=10)

        # Variables
        self.q_jugar = tk.BooleanVar()
        self.q_editar = tk.BooleanVar()
        self.q_programar = tk.BooleanVar()
        self.q_trabajar = tk.BooleanVar()
        self.q_stream = tk.BooleanVar()
        self.q_viajar = tk.BooleanVar()

        opts = [
            ("¿Juegas videojuegos?", self.q_jugar),
            ("¿Editas fotos/video?", self.q_editar),
            ("¿Programas?", self.q_programar),
            ("¿Trabajas en oficina?", self.q_trabajar),
            ("¿Haces streaming?", self.q_stream),
            ("¿Viajas frecuentemente?", self.q_viajar)
        ]

        for text, var in opts:
            ttk.Checkbutton(container, text=text, variable=var).pack(anchor="w", pady=4)

        # RENDIMIENTO
        tk.Label(container, text="\nNivel de rendimiento deseado:",
                 bg="#0e1117", fg="white",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self.performance_var = tk.StringVar(value="medio")
        for label, value in [("Bajo", "bajo"), ("Medio", "medio"), ("Alto", "alto")]:
            ttk.Radiobutton(container, text=label, variable=self.performance_var,
                            value=value).pack(anchor="w")

        # TIPO DE EQUIPO
        tk.Label(container, text="\n¿Qué tipo de equipo deseas?",
                 bg="#0e1117", fg="white",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self.device_var = tk.StringVar(value="pc_escritorio")
        ttk.Radiobutton(container, text="PC de escritorio",
                        variable=self.device_var, value="pc_escritorio").pack(anchor="w")
        ttk.Radiobutton(container, text="Laptop",
                        variable=self.device_var, value="laptop").pack(anchor="w")

        # PRESUPUESTO
        tk.Label(container, text="\nPresupuesto (MXN):",
                 bg="#0e1117", fg="white",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self.budget_entry = ttk.Entry(container)
        self.budget_entry.insert(0, "20000")
        self.budget_entry.pack(fill="x", pady=4)

        ttk.Button(container, text="Enviar", command=self.submit).pack(pady=20)

    def submit(self):
        try:
            budget = float(self.budget_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Presupuesto inválido")
            return

        data = {
            "juegas": self.q_jugar.get(),
            "editas": self.q_editar.get(),
            "programas": self.q_programar.get(),
            "trabajas": self.q_trabajar.get(),
            "streamer": self.q_stream.get(),
            "viajas": self.q_viajar.get(),
            "performance": self.performance_var.get()
        }

        self.callback(data, budget, self.device_var.get())
        self.destroy()


# ============================================================
# VENTANA PRINCIPAL
# ============================================================
class ModernUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Sistema Experto en Hardware")
        self.geometry("1150x780")
        self.configure(bg="#0e1117")

        self.survey_data = None
        self.device_type = None
        self.budget = None

        self._create_style()
        self._build_interface()

        self.after(350, self.open_survey_popup)

    def _create_style(self):
        style = ttk.Style()
        apply_dark_theme(style)

    def _build_interface(self):
        header = ttk.Label(self, text="Sistema Experto en Hardware",
                           font=("Segoe UI", 22, "bold"))
        header.pack(pady=15)

        self.profile_label = ttk.Label(self, text="Perfil detectado: ---",
                                       font=("Segoe UI", 14, "bold"))
        self.profile_label.pack(pady=(0, 20))

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        # =====================================================
        # TABLA IZQUIERDA
        # =====================================================
        left = ttk.Frame(container)
        left.grid(row=0, column=0, sticky="nsew", padx=10)

        cols = ("Componente", "Nombre", "Precio")
        self.tree = ttk.Treeview(left, columns=cols, show="headings")

        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=180)

        self.tree.pack(fill="both", expand=True)

        # =====================================================
        # DERECHA — RAZONAMIENTO + ADVERTENCIAS + GRÁFICA
        # =====================================================
        right = ttk.Frame(container)
        right.grid(row=0, column=1, sticky="nsew", padx=10)

        ttk.Label(right, text="Razonamiento:",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self.reasoning_box = tk.Text(
            right, height=10, bg="#161b22", fg="#d9e6ff",
            bd=0, highlightthickness=0, wrap="word"
        )
        self.reasoning_box.pack(fill="x", pady=8)

        ttk.Label(right, text="Advertencias:",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self.warnings_box = tk.Text(
            right, height=5, bg="#161b22", fg="#ffb3b3",
            bd=0, highlightthickness=0, wrap="word"
        )
        self.warnings_box.pack(fill="x", pady=8)

        self.chart_frame = ttk.Frame(right)
        self.chart_frame.pack(fill="both", expand=True)

        # =====================================================
        # BOTONES INFERIORES
        # =====================================================
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=12)

        ttk.Button(
            button_frame,
            text="Volver a realizar encuesta",
            command=self.reset_and_open_survey
        ).pack(side="left", padx=10)

        ttk.Button(
            button_frame,
            text="Tomar Screenshot",
            command=self.take_screenshot
        ).pack(side="left", padx=10)

    # ============================================================
    # Abrir encuesta
    # ============================================================
    def open_survey_popup(self):
        SurveyPopup(self, self.on_survey_complete)

    def reset_and_open_survey(self):
        # Reset visual
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.reasoning_box.delete("1.0", tk.END)
        self.warnings_box.delete("1.0", tk.END)

        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        self.open_survey_popup()

    def take_screenshot(self):
        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty()
            w = x + self.winfo_width()
            h = y + self.winfo_height()

            filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img = ImageGrab.grab(bbox=(x, y, w, h))
            img.save(filename)

            messagebox.showinfo("Screenshot guardado",
                                f"Guardado como:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo tomar screenshot:\n{e}")

    # ============================================================
    # Llamar API
    # ============================================================
    def on_survey_complete(self, survey_data, budget, device_type):
        self.survey_data = survey_data
        self.budget = budget
        self.device_type = device_type
        self.get_recommendation()

    def get_recommendation(self):
        payload = {
            "survey": self.survey_data,
            "budget": self.budget,
            "device_type": self.device_type
        }

        try:
            response = requests.post(API_URL, json=payload, timeout=8)
        except Exception:
            messagebox.showerror("Error", "No se pudo conectar con la API.")
            return

        if response.status_code != 200:
            messagebox.showerror("Error API", f"Código {response.status_code}")
            return

        self.display(response.json())

    # ============================================================
    # Mostrar resultados
    # ============================================================
    def display(self, data):
        # Limpiar UI
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.reasoning_box.delete("1.0", tk.END)
        self.warnings_box.delete("1.0", tk.END)

        for w in self.chart_frame.winfo_children():
            w.destroy()

        # PERFIL
        profile = data.get("profile_description", "---")
        self.profile_label.config(text=f"Perfil detectado: {profile}")

        # Tabla
        comps = data.get("components", {})
        for key, comp in comps.items():
            name = comp.get("name", "N/A")
            price = comp.get("price", 0)
            self.tree.insert("", "end", values=(key, name, f"${price}"))

        total = data.get("total_price_estimate", 0)
        self.tree.insert("", "end", values=("TOTAL", "", f"${total}"))

        # Razonamiento
        for line in data.get("reasoning", []):
            self.reasoning_box.insert(tk.END, f"• {line}\n")

        # Advertencias
        for w in data.get("warnings", []):
            self.warnings_box.insert(tk.END, f"⚠ {w}\n")

        # Gráfica
        allocation = data.get("allocation_estimate", {})
        labels = list(allocation.keys())
        values = [allocation[k] for k in labels]

        if labels and sum(values) > 0:
            fig = Figure(figsize=(4, 3), facecolor="#0e1117")
            ax = fig.add_subplot(111)

            ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=140)
            ax.set_title("Distribución del presupuesto", color="white")

            fig.patch.set_facecolor("#0e1117")
            ax.patch.set_facecolor("#0e1117")

            for text in ax.texts:
                text.set_color("white")

            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    app = ModernUI()
    app.mainloop()
