"""
INTERFAZ GRAFICA - COMPILADOR PASCAL-LIKE
──────────────────────────────────────────────────────────────
Interfaz simple con Tkinter (viene incluido con Python, no
requiere instalar nada extra). Reutiliza la funcion compilar()
de main.py tal cual, capturando su salida por consola y
mostrandola con un poco de color para que sea mas legible.

Incluye numeracion de lineas en el editor, al estilo de un
compilador/IDE: la columna izquierda se actualiza automaticamente
al escribir, borrar, pegar texto o hacer scroll.

Para ejecutar:  python interfaz.py
(Debe estar en la misma carpeta que main.py, Modelo.py, Lexico.py,
 Sintactico.py y Semantico.py)
"""

import io
import contextlib
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from Main import compilar  # reutiliza tu logica existente, sin duplicarla


class TextConNumeros(ttk.Frame):
    """
    Envoltorio de un tk.Text que agrega, a la izquierda, una columna
    con el numero de linea correspondiente (como en cualquier editor
    de codigo/compilador). Se actualiza sola con cada cambio de texto,
    scroll o redimension de la ventana.
    """

    def __init__(self, master, ancho_numeros=44, **kwargs_text):
        super().__init__(master)

        self.canvas_numeros = tk.Canvas(
            self, width=ancho_numeros, bg="#252526", highlightthickness=0
        )
        self.canvas_numeros.pack(side=tk.LEFT, fill=tk.Y)

        self.text = tk.Text(self, **kwargs_text)

        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._on_scrollbar)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=self._on_textscroll)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Eventos que pueden cambiar que lineas son visibles o cuantas hay
        for evento in ("<KeyRelease>", "<ButtonRelease>", "<Configure>",
                       "<<Paste>>", "<<Cut>>", "<<Undo>>", "<<Redo>>"):
            self.text.bind(evento, self._actualizar_numeros)

        self.text.bind("<MouseWheel>", lambda e: self.after_idle(self._actualizar_numeros))
        self.text.bind("<Button-4>", lambda e: self.after_idle(self._actualizar_numeros))
        self.text.bind("<Button-5>", lambda e: self.after_idle(self._actualizar_numeros))

        self._actualizar_numeros()

    # ---------- scroll sincronizado ----------

    def _on_scrollbar(self, *args):
        self.text.yview(*args)
        self._actualizar_numeros()

    def _on_textscroll(self, *args):
        self.scrollbar.set(*args)
        self._actualizar_numeros()

    # ---------- dibujo de la columna de numeros ----------

    def _actualizar_numeros(self, event=None):
        self.canvas_numeros.delete("all")

        indice = self.text.index("@0,0")
        while True:
            info_linea = self.text.dlineinfo(indice)
            if info_linea is None:
                break
            y = info_linea[1]
            numero = str(indice).split(".")[0]
            self.canvas_numeros.create_text(
                self.canvas_numeros.winfo_width() - 6, y,
                anchor="ne", text=numero,
                fill="#858585", font=("Consolas", 10),
            )
            indice = self.text.index(f"{indice}+1line")

    # ---------- atajos convenientes, delegan al Text interno ----------

    def get(self, *args, **kwargs):
        return self.text.get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        resultado = self.text.delete(*args, **kwargs)
        self._actualizar_numeros()
        return resultado

    def insert(self, *args, **kwargs):
        resultado = self.text.insert(*args, **kwargs)
        self._actualizar_numeros()
        return resultado


class CompiladorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Compilador Pascal-like")
        self.root.geometry("1000x650")
        self.archivo_actual = None

        self._construir_toolbar()
        self._construir_paneles()
        self._construir_statusbar()

    # ---------- construccion de la UI ----------

    def _construir_toolbar(self):
        barra = ttk.Frame(self.root, padding=6)
        barra.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(barra, text="Abrir", command=self.abrir_archivo).pack(side=tk.LEFT, padx=3)
        ttk.Button(barra, text="Guardar", command=self.guardar_archivo).pack(side=tk.LEFT, padx=3)
        ttk.Button(barra, text="Limpiar", command=self.limpiar_editor).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            barra, text="▶  Compilar", command=self.compilar_codigo
        ).pack(side=tk.RIGHT, padx=3)

    def _construir_paneles(self):
        panel = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        panel.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Editor de codigo (izquierda), con numeracion de lineas
        marco_editor = ttk.Frame(panel)
        ttk.Label(marco_editor, text="Codigo fuente").pack(anchor="w")
        self.editor = TextConNumeros(
            marco_editor,
            font=("Consolas", 11), undo=True, wrap="none",
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        panel.add(marco_editor, weight=1)

        # Salida del compilador (derecha)
        marco_salida = ttk.Frame(panel)
        ttk.Label(marco_salida, text="Resultado de la compilacion").pack(anchor="w")
        self.salida = tk.Text(
            marco_salida, font=("Consolas", 10), state="disabled", wrap="word",
            bg="#0c0c0c", fg="#dddddd",
        )
        self.salida.pack(fill=tk.BOTH, expand=True)
        panel.add(marco_salida, weight=1)

        # Tags de color para resaltar la salida
        self.salida.tag_configure("ok", foreground="#4caf50")
        self.salida.tag_configure("error", foreground="#f44336")
        self.salida.tag_configure("fase", foreground="#569cd6", font=("Consolas", 10, "bold"))

    def _construir_statusbar(self):
        self.status = tk.StringVar(value="Listo")
        barra = ttk.Label(self.root, textvariable=self.status, anchor="w", padding=4)
        barra.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = barra

    # ---------- acciones ----------

    def abrir_archivo(self):
        ruta = filedialog.askopenfilename(
            filetypes=[("Archivos de texto", "*.txt *.pas *.pl"), ("Todos", "*.*")]
        )
        if not ruta:
            return
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", contenido)
        self.archivo_actual = ruta
        self.status.set(f"Archivo abierto: {ruta}")

    def guardar_archivo(self):
        ruta = self.archivo_actual
        if not ruta:
            ruta = filedialog.asksaveasfilename(
                defaultextension="",  # no forzar ninguna extension fija
                filetypes=[
                    ("Codigo Pascal-like", "*.pas"),
                    ("Archivo de texto", "*.txt"),
                    ("Todos los archivos", "*.*"),
                ],
            )
            if not ruta:
                return
            # Si el usuario no escribio ninguna extension, usamos .pas por defecto
            if not Path(ruta).suffix:
                ruta += ".pas"

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.editor.get("1.0", tk.END))
        self.archivo_actual = ruta
        self.status.set(f"Guardado en: {ruta}")

    def limpiar_editor(self):
        self.editor.delete("1.0", tk.END)
        self._set_salida("")
        self.status.set("Listo")

    def compilar_codigo(self):
        codigo = self.editor.get("1.0", tk.END)
        if not codigo.strip():
            messagebox.showwarning("Sin codigo", "Escribe o abre un archivo con codigo antes de compilar.")
            return

        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                compilar(codigo, nombre=self.archivo_actual or "(editor)")
        except Exception as e:
            messagebox.showerror("Error al compilar", f"Ocurrio un error inesperado:\n{e}")
            return

        texto = buffer.getvalue()
        self._set_salida(texto)

        if "COMPILACION EXITOSA" in texto:
            self.status.set("✅ Compilacion exitosa")
        else:
            self.status.set("❌ Se encontraron errores")

    # ---------- utilidades de presentacion ----------

    def _set_salida(self, texto: str):
        self.salida.configure(state="normal")
        self.salida.delete("1.0", tk.END)
        for linea in texto.splitlines(keepends=True):
            tag = None
            if "✅" in linea or "✓" in linea:
                tag = "ok"
            elif "❌" in linea or "ERROR" in linea.upper():
                tag = "error"
            elif linea.strip().startswith("FASE"):
                tag = "fase"
            self.salida.insert(tk.END, linea, tag)
        self.salida.configure(state="disabled")


def main_gui():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    CompiladorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main_gui()