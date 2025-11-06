import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests, json, os
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

API_URL = "http://127.0.0.1:8000/recommend"

class ModernUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("💻 Sistema Experto en Hardware")
        self.geometry("1000x800")
        self.configure(bg="#0e0e0e")
        self.minsize(900, 700)
        self._create_style()
        self._build_interface()

    def _create_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#121212")
        style.configure("TLabel", background="#121212", foreground="white", font=("Segoe UI", 11))
        style.configure("TButton", background="#00ADEF", foreground="white", font=("Segoe UI", 11, "bold"))
        style.map("TButton", background=[("active", "#00C6FF")])

    def _build_interface(self):
        header = tk.Frame(self, bg="#1f1f1f", height=80)
        header.pack(fill="x")
        tk.Label(header, text="🧠 Sistema Experto en Hardware",
                 font=("Segoe UI Semibold", 20), bg="#1f1f1f", fg="#00C6FF").pack(pady=10)
        tk.Label(header, text="Asistente inteligente para configurar tu PC ideal",
                 font=("Segoe UI", 11), bg="#1f1f1f", fg="#BBBBBB").pack()

        form = ttk.Frame(self)
        form.pack(fill="x", pady=15)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Perfil del usuario:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.profile_cb = ttk.Combobox(form, values=["ofimatico","estudiante","programador","gamer","disenador","ninguno"], state="readonly")
        self.profile_cb.set("gamer")
        self.profile_cb.grid(row=0, column=1, padx=10, pady=10, sticky="we")

        ttk.Label(form, text="Presupuesto (MXN):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.budget_entry = ttk.Entry(form)
        self.budget_entry.insert(0, "25000")
        self.budget_entry.grid(row=1, column=1, padx=10, pady=10, sticky="we")

        self.use_min_btn = tk.Button(form, text="💡 Usar presupuesto mínimo sugerido",
                                     bg="#444", fg="white", relief="flat",
                                     command=self.use_suggested_budget)
        self.use_min_btn.grid(row=2, column=1, pady=5, sticky="e")

        btn_frame = tk.Frame(self, bg="#0e0e0e")
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="🔍 Generar Recomendación", bg="#00ADEF", fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", command=self.get_recommendation).pack(side="left", expand=True, padx=20)

        content_frame = tk.Frame(self, bg="#0e0e0e")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        content_frame.columnconfigure(0, weight=2)
        content_frame.columnconfigure(1, weight=1)

        self.result_box = tk.Text(content_frame, bg="#101010", fg="#EAEAEA", font=("Consolas", 10),
                                  relief="flat", wrap="word", padx=15, pady=15)
        self.result_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.chart_frame = tk.Frame(content_frame, bg="#0e0e0e")
        self.chart_frame.grid(row=0, column=1, sticky="nsew")

        self.note_label = tk.Label(self, bg="#0e0e0e", fg="#00C6FF", font=("Segoe UI", 10, "italic"))
        self.note_label.pack(pady=(0, 10))

    # ------------------- API -------------------
    def get_recommendation(self):
        try:
            budget_value = float(self.budget_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "⚠️ El presupuesto debe ser numérico.")
            return
        payload = {"profile": self.profile_cb.get(), "budget": budget_value}
        try:
            res = requests.post(API_URL, json=payload)
            if res.status_code == 200:
                self.show_result(res.json())
            else:
                messagebox.showerror("Error API", f"Código {res.status_code}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------- Mostrar resultado -------------------
    def show_result(self, data):
        self.result_box.delete("1.0", tk.END)

        if "error" in data:
            self.result_box.insert(tk.END, f"❌ {data['error']}\n\n")
            if "minimum_required" in data:
                self.result_box.insert(tk.END, f"💸 Monto mínimo estimado: ${data['minimum_required']}\n\n")
                self.last_min_budget = data["minimum_required"]
            if "debug" in data:
                self.result_box.insert(tk.END, f"🔍 Info técnica:\n{json.dumps(data['debug'], indent=2)}\n")

            self.note_label.config(text="")
            for w in self.chart_frame.winfo_children():
                w.destroy()
            img_path = os.path.join(os.path.dirname(__file__), "presupuesto.jpg")
            if os.path.exists(img_path):
                img = Image.open(img_path).resize((400, 300))
                self.img_tk = ImageTk.PhotoImage(img)
                tk.Label(self.chart_frame, image=self.img_tk, bg="#0e0e0e").pack(expand=True)
            else:
                tk.Label(self.chart_frame, text="(No se encontró la imagen 'presupuesto.jpg')",
                         bg="#0e0e0e", fg="gray").pack(expand=True)
            return

        # Resultado normal
        self.result_box.insert(tk.END, f"👤 Perfil: {data['profile']}\n")
        self.result_box.insert(tk.END, f"💰 Presupuesto: ${data['budget_input']}\n\n")
        for k, v in data["components"].items():
            self.result_box.insert(tk.END, f"• {k:<12}: {v['name']} (${v['price']})\n")
        self.result_box.insert(tk.END, f"\n💵 TOTAL: ${data['total_price_estimate']}\n")

        if data.get("note"):
            self.note_label.config(text=f"⚙️ {data['note']}")
        else:
            self.note_label.config(text="")

        self._show_chart(data["allocation_estimate"])

    def _show_chart(self, allocation):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        labels, values = list(allocation.keys()), list(allocation.values())
        fig = Figure(figsize=(4, 3), facecolor="#0e0e0e")
        ax = fig.add_subplot(111)
        ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=140,
               colors=["#00C6FF", "#00ADEF", "#3399FF", "#66B2FF"], textprops={'color': "white"})
        ax.set_title("Distribución del presupuesto", color="white")
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def use_suggested_budget(self):
        if hasattr(self, "last_min_budget"):
            self.budget_entry.delete(0, tk.END)
            self.budget_entry.insert(0, str(self.last_min_budget))
        else:
            messagebox.showinfo("Aviso", "Primero genera una recomendación con error para obtener el mínimo sugerido.")

if __name__ == "__main__":
    app = ModernUI()
    app.mainloop()
