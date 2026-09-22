import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tkfont
import ast
import os
from collections import defaultdict

# Pillow (needed for PNG export)
try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False


class UMLCanvasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python UML Visualizer")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f4f4f4")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Modern.TButton",
                        font=("Segoe UI", 10, "bold"),
                        padding=7)

        # Top controls
        top = tk.Frame(root, bg="#f4f4f4")
        top.pack(fill="x", pady=8)

        ttk.Button(top, text="Select Python File", style="Modern.TButton",
                   command=self.load_file).pack(side="left", padx=10)

        ttk.Button(top, text="Generate Call Graph", style="Modern.TButton",
                   command=self.generate_call_graph).pack(side="left", padx=10)

        ttk.Button(top, text="Generate Text Class Diagram", style="Modern.TButton",
                   command=self.generate_text_class_diagram).pack(side="left", padx=10)

        ttk.Button(top, text="Generate UML Canvas", style="Modern.TButton",
                   command=self.parse_and_draw).pack(side="left", padx=10)

        ttk.Button(top, text="Save UML as PNG", style="Modern.TButton",
                   command=self.save_canvas_png).pack(side="left", padx=10)

        ttk.Button(top, text="View Module Dependencies", style="Modern.TButton",
                   command=self.generate_dependencies).pack(side="left", padx=10)

        self.file_label = tk.Label(top, text="No file selected",
                                   bg="#f4f4f4", fg="#333")
        self.file_label.pack(side="left", padx=15)

        # Main layout — left canvas, right text
        container = tk.Frame(root)
        container.pack(fill="both", expand=True)

        # Scrollable canvas area
        canvas_frame = tk.Frame(container)
        canvas_frame.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Scrollbars
        self.vbar = ttk.Scrollbar(canvas_frame, orient="vertical",
                                  command=self.canvas.yview)
        self.vbar.pack(side="right", fill="y")

        self.hbar = ttk.Scrollbar(container, orient="horizontal",
                                  command=self.canvas.xview)
        self.hbar.pack(side="bottom", fill="x")

        self.canvas.configure(xscrollcommand=self.hbar.set,
                              yscrollcommand=self.vbar.set)

        # Right side text output
        right = tk.Frame(container, width=300, bg="#f4f4f4")
        right.pack(side="right", fill="y")

        tk.Label(right, text="Output", bg="#f4f4f4", fg="#333",
                 font=("Segoe UI", 11, "bold")).pack(pady=6)

        self.output = scrolledtext.ScrolledText(right, width=36, height=40,
                                                font=("Consolas", 10))
        self.output.pack(padx=8, pady=8, fill="y")

        # Data storage
        self.file_path = None
        self.classes = {}
        self.positions = {}
        self.colors = ["#FFDDC1", "#CDECF6", "#E6E6FA", "#E8F6E7", "#FFF3B0"]

        self.font = tkfont.Font(family="Consolas", size=10)
        self.title_font = tkfont.Font(family="Consolas", size=11, weight="bold")

        # Enable canvas panning (middle mouse or right-click)
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.pan)
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.pan)

        # Mousewheel scroll support
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)

    # ========== Movement / Scrolling ==========
    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    # ========== File Loading ==========
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if path:
            self.file_path = path
            self.file_label.config(text=os.path.basename(path))
            self.output.insert(tk.END, f"Loaded file: {path}\n\n")
        else:
            messagebox.showinfo("No file", "Select a valid Python file.")

    def parse_safely(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return ast.parse(f.read())
        except SyntaxError:
            messagebox.showerror("Syntax Error",
                                 "Syntax error detected. Cannot parse file.")
            return None

    # ========== TEST CASE: Call Graph ==========
    def generate_call_graph(self):
        tree = self.parse_safely()
        if tree is None:
            return

        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)

        self.output.insert(tk.END, "📞 Call Graph:\n")
        if calls:
            for c in sorted(set(calls)):
                self.output.insert(tk.END, f" - {c}()\n")
        else:
            self.output.insert(tk.END, "No function calls found.\n")
        self.output.insert(tk.END, "\n")

    # ========== TEST CASE: Textual Class Diagram ==========
    def generate_text_class_diagram(self):
        tree = self.parse_safely()
        if tree is None:
            return

        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        if not classes:
            messagebox.showwarning("No Classes", "No classes detected.")
            return

        self.output.insert(tk.END, "🏛️ Class Diagram:\n")
        for cls in classes:
            bases = [b.id for b in cls.bases if isinstance(b, ast.Name)]
            methods = [m.name for m in cls.body if isinstance(m, ast.FunctionDef)]
            attrs = [
                a.targets[0].id for a in cls.body
                if isinstance(a, ast.Assign) and isinstance(a.targets[0], ast.Name)
            ]

            self.output.insert(tk.END,
                               f"\nClass: {cls.name}\n"
                               f"  Inherits: {bases}\n"
                               f"  Methods: {methods}\n"
                               f"  Attributes: {attrs}\n")

    # ========== TEST CASES 03–06: UML Canvas ==========
    def parse_and_draw(self):
        tree = self.parse_safely()
        if tree is None:
            return

        self._extract_classes(tree)
        if not self.classes:
            messagebox.showwarning("No Classes", "No classes detected.")
            return

        self._layout_classes()
        self._draw_canvas()
        self._print_info()

    def _extract_classes(self, tree):
        self.classes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                name = node.name
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                attrs = [
                    a.targets[0].id for a in node.body
                    if isinstance(a, ast.Assign) and isinstance(a.targets[0], ast.Name)
                ]
                self.classes[name] = {
                    "bases": bases,
                    "methods": methods,
                    "attrs": attrs
                }

    def _layout_classes(self):
        self.positions = {}
        x = 50
        y = 50
        for i, cname in enumerate(self.classes):
            w = 220
            h = 140
            self.positions[cname] = (x, y, w, h)
            x += 300
            if x > 1500:
                x = 50
                y += 220

    def _draw_canvas(self):
        self.canvas.delete("all")

        # Draw boxes
        for i, (cname, data) in enumerate(self.classes.items()):
            x, y, w, h = self.positions[cname]
            color = self.colors[i % len(self.colors)]

            self.canvas.create_rectangle(x, y, x+w, y+h, fill=color, outline="black", width=2)
            self.canvas.create_rectangle(x, y, x+w, y+28, fill="white", outline="black")
            self.canvas.create_text(x+10, y+14, text=cname, anchor="w",
                                    font=self.title_font)

            # Attributes
            yy = y + 38
            for attr in data["attrs"]:
                self.canvas.create_text(x+10, yy, anchor="w", text=attr,
                                        font=self.font)
                yy += 18

            # Methods
            yy += 8
            for method in data["methods"]:
                self.canvas.create_text(x+10, yy, anchor="w",
                                        text=method + "()", font=self.font)
                yy += 18

        # Draw inheritance arrows
        for child, data in self.classes.items():
            cx, cy, cw, ch = self.positions[child]
            for base in data["bases"]:
                if base in self.positions:
                    bx, by, bw, bh = self.positions[base]
                    self.canvas.create_line(
                        bx + bw / 2, by + bh,
                        cx + cw / 2, cy,
                        width=2,
                        arrow=tk.LAST
                    )

        # Update scrollregion
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.config(scrollregion=(bbox[0] - 50, bbox[1] - 50,
                                             bbox[2] + 50, bbox[3] + 50))

    def _print_info(self):
        self.output.delete("1.0", tk.END)
        for cname, data in self.classes.items():
            self.output.insert(tk.END,
                               f"Class: {cname}\n"
                               f"  Bases: {data['bases']}\n"
                               f"  Attrs: {data['attrs']}\n"
                               f"  Methods: {data['methods']}\n\n")

    # ========== TEST CASE 06: Missing Imports Detection ==========
    def generate_dependencies(self):
        tree = self.parse_safely()
        if tree is None:
            return

        imports = []
        unresolved = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.append(a.name)
                    if not self._module_exists(a.name):
                        unresolved.append(a.name)

            if isinstance(node, ast.ImportFrom):
                imports.append(node.module)
                if not self._module_exists(node.module):
                    unresolved.append(node.module)

        self.output.insert(tk.END, "📦 Module Dependencies:\n")
        for imp in sorted(set(imports)):
            flag = " (missing!)" if imp in unresolved else ""
            self.output.insert(tk.END, f" - {imp}{flag}\n")
        self.output.insert(tk.END, "\n")

        if unresolved:
            messagebox.showwarning("Unresolved Imports",
                                   f"Missing modules detected:\n{', '.join(unresolved)}")

    def _module_exists(self, name):
        try:
            __import__(name)
            return True
        except:
            return False

    # ========== Save UML Diagram ==========
    def save_canvas_png(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("Pillow Missing",
                                 "Install Pillow: pip install pillow")
            return

        self.root.update()
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))

        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")]
        )
        if save_path:
            img.save(save_path)
            messagebox.showinfo("Saved", f"Diagram saved to\n{save_path}")


if __name__ == "__main__":
    root = tk.Tk()
    UMLCanvasApp(root)
    root.mainloop()
