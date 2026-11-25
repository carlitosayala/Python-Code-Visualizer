import ast
import importlib.util
import os
import tkinter as tk
import tkinter.font as tkfont
from collections import defaultdict
from tkinter import filedialog, messagebox, scrolledtext, ttk

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def node_to_name(node):
    """Return a readable name for an AST node."""
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = node_to_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    try:
        return ast.unparse(node)
    except (AttributeError, TypeError):
        return node.__class__.__name__


def _collect_target_names(target):
    names = []

    if isinstance(target, ast.Name):
        names.append(target.id)

    elif isinstance(target, (ast.Tuple, ast.List)):
        for item in target.elts:
            names.extend(_collect_target_names(item))

    return names


def extract_class_attributes(class_node):
    attributes = set()

    # Class-level attributes
    for item in class_node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                attributes.update(_collect_target_names(target))

        elif isinstance(item, ast.AnnAssign):
            attributes.update(_collect_target_names(item.target))

    # Instance attributes such as self.name
    for item in class_node.body:
        if not isinstance(
            item,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        for node in ast.walk(item):
            targets = []

            if isinstance(node, ast.Assign):
                targets.extend(node.targets)

            elif isinstance(node, ast.AnnAssign):
                targets.append(node.target)

            elif isinstance(node, ast.AugAssign):
                targets.append(node.target)

            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    attributes.add(target.attr)

    return sorted(attributes)


def extract_classes(tree):
    classes = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        bases = [
            node_to_name(base)
            for base in node.bases
        ]

        methods = [
            item.name
            for item in node.body
            if isinstance(
                item,
                (ast.FunctionDef, ast.AsyncFunctionDef)
            )
        ]

        classes[node.name] = {
            "bases": bases,
            "methods": methods,
            "attrs": extract_class_attributes(node),
        }

    return classes


def build_call_graph(tree):
    class CallGraphVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_scope = "<module>"
            self.class_stack = []
            self.calls = defaultdict(set)
            self.functions = set()

        def visit_ClassDef(self, node):
            self.class_stack.append(node.name)

            for item in node.body:
                self.visit(item)

            self.class_stack.pop()

        def _function_scope_name(self, node):
            if self.class_stack:
                return f"{self.class_stack[-1]}.{node.name}"

            if self.current_scope != "<module>":
                return f"{self.current_scope}.{node.name}"

            return node.name

        def visit_FunctionDef(self, node):
            previous_scope = self.current_scope
            scope_name = self._function_scope_name(node)

            self.current_scope = scope_name
            self.functions.add(scope_name)
            self.calls.setdefault(scope_name, set())

            for statement in node.body:
                self.visit(statement)

            self.current_scope = previous_scope

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_Call(self, node):
            called_name = node_to_name(node.func)

            if called_name:
                self.calls[self.current_scope].add(called_name)

            self.generic_visit(node)

    visitor = CallGraphVisitor()
    visitor.visit(tree)

    return {
        "calls": {
            scope: set(callees)
            for scope, callees in visitor.calls.items()
        },
        "functions": set(visitor.functions),
    }


def extract_dependencies(tree):
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                alias.name
                for alias in node.names
            )

        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            module = node.module or ""
            imports.append(prefix + module)

    return sorted(set(imports))


def module_exists(name):
    if not name or name.startswith("."):
        return True

    try:
        return importlib.util.find_spec(name) is not None

    except (
        ImportError,
        ModuleNotFoundError,
        AttributeError,
        ValueError,
    ):
        return False


class UMLCanvasApp:
    BG = "#f3f5f8"
    PANEL = "#ffffff"
    TEXT = "#1f2937"
    MUTED = "#64748b"
    ACCENT = "#2563eb"
    BORDER = "#d7dde5"

    CLASS_COLORS = [
        "#e8f0ff",
        "#eaf8ef",
        "#fff4db",
        "#f3eafe",
        "#fdecec",
    ]

    def __init__(self, root):
        self.root = root

        self.root.title("Python Code Visualizer")
        self.root.geometry("1280x820")
        self.root.minsize(1000, 650)
        self.root.configure(bg=self.BG)

        self.file_path = None
        self.classes = {}
        self.positions = {}

        self.font = tkfont.Font(
            family="Consolas",
            size=10,
        )

        self.title_font = tkfont.Font(
            family="Segoe UI",
            size=11,
            weight="bold",
        )

        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()
        self._set_analysis_enabled(False)

    # ==========================================================
    # GUI
    # ==========================================================

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Toolbar.TButton",
            font=("Segoe UI", 9),
            padding=(10, 7),
            background="#eef2f7",
            foreground=self.TEXT,
        )

        style.map(
            "Toolbar.TButton",
            background=[
                ("active", "#e2e8f0")
            ],
        )

        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold"),
            padding=(12, 7),
            background=self.ACCENT,
            foreground="white",
        )

        style.map(
            "Primary.TButton",
            background=[
                ("active", "#1d4ed8")
            ],
            foreground=[
                ("disabled", "#e2e8f0")
            ],
        )

        style.configure(
            "Header.TLabel",
            background=self.BG,
            foreground=self.TEXT,
            font=("Segoe UI", 18, "bold"),
        )

        style.configure(
            "Subheader.TLabel",
            background=self.BG,
            foreground=self.MUTED,
            font=("Segoe UI", 9),
        )

        style.configure(
            "Status.TLabel",
            background=self.PANEL,
            foreground=self.MUTED,
            font=("Segoe UI", 9),
        )

    def _build_ui(self):
        # Header
        header = tk.Frame(
            self.root,
            bg=self.BG,
        )

        header.pack(
            fill="x",
            padx=18,
            pady=(14, 8),
        )

        title_area = tk.Frame(
            header,
            bg=self.BG,
        )

        title_area.pack(side="left")

        ttk.Label(
            title_area,
            text="Python Code Visualizer",
            style="Header.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            title_area,
            text=(
                "Inspect calls, classes, UML relationships, "
                "and module dependencies."
            ),
            style="Subheader.TLabel",
        ).pack(
            anchor="w",
            pady=(2, 0),
        )

        self.file_label = tk.Label(
            header,
            text="No file selected",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        )

        self.file_label.pack(
            side="right",
            padx=(20, 0),
            pady=(8, 0),
        )

        # Toolbar
        toolbar = tk.Frame(
            self.root,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )

        toolbar.pack(
            fill="x",
            padx=18,
            pady=(0, 10),
        )

        ttk.Button(
            toolbar,
            text="Open Python File",
            style="Primary.TButton",
            command=self.load_file,
        ).pack(
            side="left",
            padx=(10, 6),
            pady=9,
        )

        self.analysis_buttons = []

        button_specs = [
            (
                "Call Graph",
                self.generate_call_graph,
            ),
            (
                "Class Diagram",
                self.generate_text_class_diagram,
            ),
            (
                "UML Canvas",
                self.parse_and_draw,
            ),
            (
                "Dependencies",
                self.generate_dependencies,
            ),
        ]

        for text, command in button_specs:
            button = ttk.Button(
                toolbar,
                text=text,
                style="Toolbar.TButton",
                command=command,
            )

            button.pack(
                side="left",
                padx=4,
                pady=9,
            )

            self.analysis_buttons.append(button)

        self.save_button = ttk.Button(
            toolbar,
            text="Save UML as PNG",
            style="Toolbar.TButton",
            command=self.save_canvas_png,
        )

        self.save_button.pack(
            side="left",
            padx=4,
            pady=9,
        )

        self.save_button.state(["disabled"])

        ttk.Button(
            toolbar,
            text="Clear",
            style="Toolbar.TButton",
            command=self.clear_view,
        ).pack(
            side="right",
            padx=10,
            pady=9,
        )

        # Main split view
        main = ttk.Panedwindow(
            self.root,
            orient=tk.HORIZONTAL,
        )

        main.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 10),
        )

        canvas_panel = tk.Frame(
            main,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )

        output_panel = tk.Frame(
            main,
            bg=self.PANEL,
            width=360,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )

        main.add(
            canvas_panel,
            weight=3,
        )

        main.add(
            output_panel,
            weight=1,
        )

        # Canvas heading
        tk.Label(
            canvas_panel,
            text="UML Canvas",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(
            fill="x",
            padx=12,
            pady=(10, 6),
        )

        # Canvas
        canvas_frame = tk.Frame(
            canvas_panel,
            bg=self.PANEL,
        )

        canvas_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )

        self.canvas = tk.Canvas(
            canvas_frame,
            bg="#fbfcfe",
            highlightthickness=0,
        )

        self.canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.vbar = ttk.Scrollbar(
            canvas_frame,
            orient="vertical",
            command=self.canvas.yview,
        )

        self.vbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.hbar = ttk.Scrollbar(
            canvas_frame,
            orient="horizontal",
            command=self.canvas.xview,
        )

        self.hbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        canvas_frame.rowconfigure(
            0,
            weight=1,
        )

        canvas_frame.columnconfigure(
            0,
            weight=1,
        )

        self.canvas.configure(
            xscrollcommand=self.hbar.set,
            yscrollcommand=self.vbar.set,
        )

        # Output panel
        tk.Label(
            output_panel,
            text="Analysis Output",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(
            fill="x",
            padx=12,
            pady=(10, 6),
        )

        self.output = scrolledtext.ScrolledText(
            output_panel,
            width=42,
            wrap="word",
            font=("Consolas", 10),
            bg="#fbfcfe",
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            padx=10,
            pady=10,
        )

        self.output.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )

        # Status bar
        status_frame = tk.Frame(
            self.root,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1,
        )

        status_frame.pack(
            fill="x",
            side="bottom",
        )

        self.status_var = tk.StringVar(
            value="Ready"
        )

        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).pack(
            side="left",
            padx=12,
            pady=6,
        )

        # Canvas controls
        self.canvas.bind(
            "<ButtonPress-2>",
            self.start_pan,
        )

        self.canvas.bind(
            "<B2-Motion>",
            self.pan,
        )

        self.canvas.bind(
            "<ButtonPress-3>",
            self.start_pan,
        )

        self.canvas.bind(
            "<B3-Motion>",
            self.pan,
        )

        self.canvas.bind(
            "<MouseWheel>",
            self._on_mousewheel,
        )

        self.canvas.bind(
            "<Shift-MouseWheel>",
            self._on_shift_mousewheel,
        )

    def _bind_shortcuts(self):
        self.root.bind(
            "<Control-o>",
            lambda event: self.load_file(),
        )

        self.root.bind(
            "<Control-l>",
            lambda event: self.clear_view(),
        )

    def _set_analysis_enabled(self, enabled):
        for button in getattr(
            self,
            "analysis_buttons",
            [],
        ):
            if enabled:
                button.state(["!disabled"])
            else:
                button.state(["disabled"])

    def _set_status(self, text):
        self.status_var.set(text)

    def _set_output(self, title, lines):
        self.output.delete(
            "1.0",
            tk.END,
        )

        self.output.insert(
            tk.END,
            f"{title}\n",
        )

        self.output.insert(
            tk.END,
            "=" * len(title) + "\n\n",
        )

        for line in lines:
            self.output.insert(
                tk.END,
                f"{line}\n",
            )

    def clear_view(self):
        self.output.delete(
            "1.0",
            tk.END,
        )

        self.canvas.delete("all")

        self.classes = {}
        self.positions = {}

        self.save_button.state(
            ["disabled"]
        )

        self._set_status(
            "View cleared"
        )

    # ==========================================================
    # Canvas Movement
    # ==========================================================

    def start_pan(self, event):
        self.canvas.scan_mark(
            event.x,
            event.y,
        )

    def pan(self, event):
        self.canvas.scan_dragto(
            event.x,
            event.y,
            gain=1,
        )

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(
            int(
                -1 * (
                    event.delta / 120
                )
            ),
            "units",
        )

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(
            int(
                -1 * (
                    event.delta / 120
                )
            ),
            "units",
        )

    # ==========================================================
    # File Loading
    # ==========================================================

    def load_file(self):
        path = filedialog.askopenfilename(
            title="Select a Python file",
            filetypes=[
                (
                    "Python Files",
                    "*.py",
                )
            ],
        )

        if not path:
            return

        self.file_path = path

        self.file_label.config(
            text=os.path.basename(path)
        )

        self._set_analysis_enabled(True)

        self.save_button.state(
            ["disabled"]
        )

        self.canvas.delete("all")

        self._set_output(
            "File Loaded",
            [
                os.path.basename(path),
                "",
                (
                    "Choose an analysis option "
                    "from the toolbar."
                ),
            ],
        )

        self._set_status(
            f"Loaded {os.path.basename(path)}"
        )

    def parse_safely(self):
        if not self.file_path:
            messagebox.showinfo(
                "No File",
                "Select a Python file first.",
            )

            return None

        try:
            with open(
                self.file_path,
                "r",
                encoding="utf-8",
            ) as file:
                source = file.read()

            return ast.parse(
                source,
                filename=self.file_path,
            )

        except SyntaxError as error:
            if error.lineno:
                location = (
                    f"line {error.lineno}"
                )
            else:
                location = "unknown line"

            messagebox.showerror(
                "Syntax Error",
                (
                    "Cannot parse the selected "
                    "file.\n\n"
                    f"{error.msg} ({location})"
                ),
            )

            self._set_status(
                "Syntax error detected"
            )

            return None

        except (
            OSError,
            UnicodeError,
        ) as error:
            messagebox.showerror(
                "File Error",
                (
                    "Could not read the selected "
                    f"file.\n\n{error}"
                ),
            )

            self._set_status(
                "Could not read file"
            )

            return None

    # ==========================================================
    # Call Graph
    # ==========================================================

    def generate_call_graph(self):
        tree = self.parse_safely()

        if tree is None:
            return

        graph = build_call_graph(tree)

        calls = graph["calls"]
        functions = graph["functions"]

        lines = []

        module_calls = sorted(
            calls.get(
                "<module>",
                set(),
            )
        )

        if module_calls:
            for callee in module_calls:
                lines.append(
                    f"<module> -> {callee}()"
                )
        else:
            lines.append(
                "<module> -> no calls"
            )

        for function_name in sorted(
            functions
        ):
            callees = sorted(
                calls.get(
                    function_name,
                    set(),
                )
            )

            if callees:
                for callee in callees:
                    lines.append(
                        f"{function_name}() "
                        f"-> {callee}()"
                    )

            else:
                lines.append(
                    f"{function_name}() "
                    "-> no calls"
                )

        self._set_output(
            "Call Graph",
            lines,
        )

        self._set_status(
            "Call graph generated"
        )

    # ==========================================================
    # Text Class Diagram
    # ==========================================================

    def generate_text_class_diagram(self):
        tree = self.parse_safely()

        if tree is None:
            return

        classes = extract_classes(tree)

        if not classes:
            messagebox.showwarning(
                "No Classes",
                "No classes were detected.",
            )

            self._set_output(
                "Class Diagram",
                [
                    "No classes detected."
                ],
            )

            self._set_status(
                "No classes detected"
            )

            return

        lines = []

        for class_name, data in classes.items():
            lines.extend(
                [
                    f"Class: {class_name}",
                    (
                        "  Inherits: "
                        f"{data['bases'] or 'None'}"
                    ),
                    (
                        "  Attributes: "
                        f"{data['attrs'] or 'None'}"
                    ),
                    (
                        "  Methods: "
                        f"{data['methods'] or 'None'}"
                    ),
                    "",
                ]
            )

        self._set_output(
            "Class Diagram",
            lines,
        )

        self._set_status(
            f"Found {len(classes)} class(es)"
        )

    # ==========================================================
    # UML Canvas
    # ==========================================================

    def parse_and_draw(self):
        tree = self.parse_safely()

        if tree is None:
            return

        self.classes = extract_classes(tree)

        if not self.classes:
            messagebox.showwarning(
                "No Classes",
                "No classes were detected.",
            )

            self.canvas.delete("all")

            self.save_button.state(
                ["disabled"]
            )

            self._set_status(
                "No classes detected"
            )

            return

        self._layout_classes()
        self._draw_canvas()
        self._print_info()

        self.save_button.state(
            ["!disabled"]
        )

        self._set_status(
            (
                "UML canvas generated for "
                f"{len(self.classes)} class(es)"
            )
        )

    def _box_height(self, data):
        content_lines = (
            max(
                1,
                len(data["attrs"]),
            )
            +
            max(
                1,
                len(data["methods"]),
            )
        )

        return max(
            160,
            92 + (
                content_lines * 20
            ),
        )

    def _layout_classes(self):
        self.positions = {}

        x = 50
        y = 50
        row_max_height = 0

        for class_name, data in self.classes.items():
            width = 240
            height = self._box_height(data)

            self.positions[class_name] = (
                x,
                y,
                width,
                height,
            )

            row_max_height = max(
                row_max_height,
                height,
            )

            x += 300

            if x > 1100:
                x = 50

                y += (
                    row_max_height
                    + 70
                )

                row_max_height = 0

    def _draw_canvas(self):
        self.canvas.delete("all")

        for index, (
            class_name,
            data,
        ) in enumerate(
            self.classes.items()
        ):
            x, y, width, height = (
                self.positions[class_name]
            )

            color = self.CLASS_COLORS[
                index
                % len(
                    self.CLASS_COLORS
                )
            ]

            # Main class box
            self.canvas.create_rectangle(
                x,
                y,
                x + width,
                y + height,
                fill=color,
                outline=self.BORDER,
                width=2,
            )

            # Header
            self.canvas.create_rectangle(
                x,
                y,
                x + width,
                y + 34,
                fill=self.PANEL,
                outline=self.BORDER,
                width=1,
            )

            self.canvas.create_text(
                x + 12,
                y + 17,
                text=class_name,
                anchor="w",
                fill=self.TEXT,
                font=self.title_font,
            )

            # Attributes
            attribute_y = y + 48

            if data["attrs"]:
                for attribute in data["attrs"]:
                    self.canvas.create_text(
                        x + 12,
                        attribute_y,
                        text=f"+ {attribute}",
                        anchor="w",
                        fill=self.TEXT,
                        font=self.font,
                    )

                    attribute_y += 20

            else:
                self.canvas.create_text(
                    x + 12,
                    attribute_y,
                    text="(no attributes)",
                    anchor="w",
                    fill=self.MUTED,
                    font=self.font,
                )

                attribute_y += 20

            # Divider
            separator_y = (
                attribute_y + 4
            )

            self.canvas.create_line(
                x,
                separator_y,
                x + width,
                separator_y,
                fill=self.BORDER,
            )

            # Methods
            method_y = separator_y + 16

            if data["methods"]:
                for method in data["methods"]:
                    self.canvas.create_text(
                        x + 12,
                        method_y,
                        text=f"+ {method}()",
                        anchor="w",
                        fill=self.TEXT,
                        font=self.font,
                    )

                    method_y += 20

            else:
                self.canvas.create_text(
                    x + 12,
                    method_y,
                    text="(no methods)",
                    anchor="w",
                    fill=self.MUTED,
                    font=self.font,
                )

        self._draw_inheritance_arrows()

        self.canvas.update_idletasks()

        bbox = self.canvas.bbox("all")

        if bbox:
            self.canvas.config(
                scrollregion=(
                    bbox[0] - 50,
                    bbox[1] - 50,
                    bbox[2] + 50,
                    bbox[3] + 50,
                )
            )

    def _draw_inheritance_arrows(self):
        for child, data in self.classes.items():
            if child not in self.positions:
                continue

            child_box = (
                self.positions[child]
            )

            for base in data["bases"]:
                base_name = (
                    base.split(".")[-1]
                )

                if base_name not in self.positions:
                    continue

                base_box = (
                    self.positions[
                        base_name
                    ]
                )

                (
                    start_x,
                    start_y,
                    end_x,
                    end_y,
                ) = self._connection_points(
                    child_box,
                    base_box,
                )

                self.canvas.create_line(
                    start_x,
                    start_y,
                    end_x,
                    end_y,
                    fill=self.MUTED,
                    width=2,
                    arrow=tk.LAST,
                    arrowshape=(
                        12,
                        14,
                        6,
                    ),
                )

    @staticmethod
    def _connection_points(
        source_box,
        target_box,
    ):
        sx, sy, sw, sh = source_box
        tx, ty, tw, th = target_box

        source_center_x = (
            sx + sw / 2
        )

        source_center_y = (
            sy + sh / 2
        )

        target_center_x = (
            tx + tw / 2
        )

        target_center_y = (
            ty + th / 2
        )

        dx = (
            target_center_x
            - source_center_x
        )

        dy = (
            target_center_y
            - source_center_y
        )

        if abs(dx) >= abs(dy):
            if dx >= 0:
                start = (
                    sx + sw,
                    source_center_y,
                )

                end = (
                    tx,
                    target_center_y,
                )

            else:
                start = (
                    sx,
                    source_center_y,
                )

                end = (
                    tx + tw,
                    target_center_y,
                )

        else:
            if dy >= 0:
                start = (
                    source_center_x,
                    sy + sh,
                )

                end = (
                    target_center_x,
                    ty,
                )

            else:
                start = (
                    source_center_x,
                    sy,
                )

                end = (
                    target_center_x,
                    ty + th,
                )

        return (
            *start,
            *end,
        )

    def _print_info(self):
        lines = []

        for class_name, data in self.classes.items():
            lines.extend(
                [
                    f"Class: {class_name}",
                    (
                        "  Bases: "
                        f"{data['bases'] or 'None'}"
                    ),
                    (
                        "  Attributes: "
                        f"{data['attrs'] or 'None'}"
                    ),
                    (
                        "  Methods: "
                        f"{data['methods'] or 'None'}"
                    ),
                    "",
                ]
            )

        self._set_output(
            "UML Canvas",
            lines,
        )

    # ==========================================================
    # Dependencies
    # ==========================================================

    def generate_dependencies(self):
        tree = self.parse_safely()

        if tree is None:
            return

        imports = extract_dependencies(
            tree
        )

        unresolved = []
        lines = []

        if not imports:
            lines.append(
                "No imports detected."
            )

        else:
            for module_name in imports:
                if module_name.startswith("."):
                    lines.append(
                        (
                            f"{module_name} "
                            "(relative import)"
                        )
                    )

                    continue

                exists = module_exists(
                    module_name
                )

                if exists:
                    lines.append(
                        f"{module_name} (found)"
                    )

                else:
                    lines.append(
                        f"{module_name} (missing)"
                    )

                    unresolved.append(
                        module_name
                    )

        self._set_output(
            "Module Dependencies",
            lines,
        )

        if unresolved:
            messagebox.showwarning(
                "Unresolved Imports",
                (
                    "Missing modules detected:\n"
                    + ", ".join(unresolved)
                ),
            )

            self._set_status(
                (
                    f"{len(unresolved)} "
                    "unresolved import(s)"
                )
            )

        else:
            self._set_status(
                "Dependency check complete"
            )

    # ==========================================================
    # Save UML
    # ==========================================================

    def save_canvas_png(self):
        if not PIL_AVAILABLE:
            messagebox.showerror(
                "Pillow Missing",
                (
                    "Pillow is required for "
                    "PNG export.\n\n"
                    "Install it with:\n"
                    "python -m pip install pillow"
                ),
            )

            return

        if not self.canvas.find_all():
            messagebox.showinfo(
                "No UML Diagram",
                (
                    "Generate the UML canvas "
                    "before saving."
                ),
            )

            return

        self.root.update()

        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()

        width = (
            self.canvas.winfo_width()
        )

        height = (
            self.canvas.winfo_height()
        )

        image = ImageGrab.grab(
            bbox=(
                x,
                y,
                x + width,
                y + height,
            )
        )

        save_path = (
            filedialog.asksaveasfilename(
                title="Save UML diagram",
                defaultextension=".png",
                filetypes=[
                    (
                        "PNG Image",
                        "*.png",
                    )
                ],
            )
        )

        if not save_path:
            return

        try:
            image.save(save_path)

            messagebox.showinfo(
                "Saved",
                (
                    "Diagram saved to:\n"
                    f"{save_path}"
                ),
            )

            self._set_status(
                (
                    "Saved "
                    f"{os.path.basename(save_path)}"
                )
            )

        except OSError as error:
            messagebox.showerror(
                "Save Error",
                (
                    "Could not save the image."
                    f"\n\n{error}"
                ),
            )

            self._set_status(
                "Could not save UML image"
            )


if __name__ == "__main__":
    root = tk.Tk()

    UMLCanvasApp(root)

    root.mainloop()