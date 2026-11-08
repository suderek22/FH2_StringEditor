import os
import tempfile
import tkinter as tk
import zipfile
from pathlib import Path
from struct import error as struct_error
from tkinter import filedialog, ttk

from strtable import StrTable
from theme import Dialogs, apply_theme


class Editor:
    def __init__(self, root):
        self.root = root
        self.table = StrTable()
        self.path = None
        self.label = "Untitled"
        self.dirty = False
        self.selected = None
        self.loading = False
        root.geometry("850x560")
        root.minsize(650, 400)
        apply_theme(root)
        self.dialogs = Dialogs(root)
        bar = ttk.Frame(root, padding=8)
        bar.pack(fill="x")
        for label, action in [("New", self.new), ("Open .str / ZIP", self.open),
                              ("Save", self.save), ("Save As", lambda: self.save(True)),
                              ("Add entry", self.add)]:
            ttk.Button(bar, text=label, command=action).pack(side="left", padx=2)
        self.search = tk.StringVar()
        ttk.Entry(bar, textvariable=self.search, width=24).pack(side="right")
        ttk.Label(bar, text="Search: ").pack(side="right")
        self.search.trace_add("write", lambda *_: self.refresh())
        pane = ttk.Panedwindow(root, orient="vertical")
        pane.pack(fill="both", expand=True, padx=8)
        listing = ttk.Frame(pane)
        self.tree = ttk.Treeview(listing, columns=("hex", "dec", "text"), show="headings")
        for col, title, width in [("hex", "ID (hex)", 90), ("dec", "ID (decimal)", 100),
                                  ("text", "Content", 580)]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, stretch=col == "text")
        scroll = ttk.Scrollbar(listing, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.select)
        pane.add(listing, weight=3)
        edit = ttk.Frame(pane)
        self.entry_label = ttk.Label(edit, text="Select an entry to edit its text.")
        self.entry_label.pack(anchor="w", pady=4)
        self.text = tk.Text(edit, height=7, wrap="word", undo=True)
        self.text.pack(fill="both", expand=True)
        self.text.bind("<<Modified>>", self.changed)
        pane.add(edit, weight=1)
        self.status = ttk.Label(root, padding=8)
        self.status.pack(fill="x")
        root.protocol("WM_DELETE_WINDOW", self.close)
        for shortcut, action in [("<Control-o>", self.open), ("<Control-n>", self.new),
                                 ("<Control-s>", self.save)]:
            root.bind(shortcut, lambda event, fn=action: fn())
        self.refresh()

    def refresh(self):
        self.loading = True
        self.tree.delete(*self.tree.get_children())
        query = self.search.get().casefold()
        for key, value in sorted(self.table.strings.items()):
            if query in f"{key} 0x{key:04X} {value}".casefold():
                self.tree.insert("", "end", iid=str(key),
                                 values=(f"0x{key:04X}", key, value.replace("\n", " ⏎ ")))
        if self.selected is not None and self.tree.exists(str(self.selected)):
            self.tree.selection_set(str(self.selected))
        self.loading = False
        self.update_status()

    def update_status(self):
        self.root.title(f"FH2 STR Editor — {self.label}{' *' if self.dirty else ''}")
        self.status.config(text=f"{len(self.table.strings)} entries | FH2 LSB2 0x200 | "
                                "Text edits apply immediately; Save writes the file.")

    def select(self, event=None):
        if self.loading:
            return
        selection = self.tree.selection()
        if not selection:
            return
        self.selected = int(selection[0])
        self.loading = True
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.table.strings[self.selected])
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.loading = False
        self.entry_label.config(text=f"Editing ID 0x{self.selected:04X} ({self.selected})")

    def changed(self, event=None):
        if self.text.edit_modified():
            if not self.loading and self.selected is not None:
                value = self.text.get("1.0", "end-1c")
                self.table.strings[self.selected] = value
                self.dirty = True
                if self.tree.exists(str(self.selected)):
                    self.tree.set(str(self.selected), "text", value.replace("\n", " ⏎ "))
                self.update_status()
            self.text.edit_modified(False)

    def confirm(self):
        if not self.dirty:
            return True
        answer = self.dialogs.askyesnocancel("Unsaved changes", "Save your changes first?")
        return self.save() if answer else answer is not None

    def reset(self, table, path, label):
        self.table, self.path, self.label = table, path, label
        self.selected, self.dirty = None, False
        self.loading = True
        self.text.delete("1.0", "end")
        self.text.edit_modified(False)
        self.loading = False
        self.entry_label.config(text="Select an entry to edit its text.")
        self.search.set("")
        self.refresh()

    def new(self):
        if self.confirm():
            self.reset(StrTable(), None, "Untitled")
            self.dirty = True
            self.update_status()

    def open(self):
        if not self.confirm():
            return
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("FH2 tables / language archives", "*.str *.zip"),
                                                     ("All files", "*.*")])
        if not path:
            return
        try:
            source = Path(path)
            if source.suffix.lower() == ".zip":
                with zipfile.ZipFile(source) as archive:
                    names = sorted(n for n in archive.namelist() if n.lower().endswith(".str"))
                    if not names:
                        raise ValueError("The ZIP contains no .str tables.")
                    name = self.choose_table(names)
                    if name is None:
                        return
                    table = StrTable.read(archive.read(name))
                self.reset(table, None, name)
            else:
                self.reset(StrTable.read(source.read_bytes()), source, source.name)
        except (OSError, ValueError, struct_error, zipfile.BadZipFile, KeyError) as error:
            self.dialogs.showerror("Cannot open table", str(error))

    def choose_table(self, names):
        dialog = self.dialogs.create("Choose a table from the ZIP")
        dialog.geometry("380x400")
        box = tk.Listbox(dialog)
        box.pack(fill="both", expand=True, padx=8, pady=8)
        for name in names:
            box.insert("end", name)
        result = []

        def accept(event=None):
            if box.curselection():
                result.append(names[box.curselection()[0]])
                dialog.destroy()

        ttk.Button(dialog, text="Open", command=accept).pack(pady=8)
        box.bind("<Double-1>", accept)
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        self.dialogs.wait(dialog)
        return result[0] if result else None

    def add(self):
        raw = self.dialogs.askstring("Add entry", "Numeric ID (decimal or 0x hexadecimal).\n"
                                    "Allowed: 0–65535. Existing IDs cannot be reused.")
        if raw is None:
            return
        try:
            key = int(raw, 16 if raw.strip().lower().startswith("0x") else 10)
            if not 0 <= key <= 65535 or key in self.table.strings:
                raise ValueError("ID is out of range or already exists.")
        except ValueError as error:
            self.dialogs.showerror("Invalid ID", str(error))
            return
        self.table.strings[key] = ""
        self.selected, self.dirty = key, True
        self.search.set("")
        self.refresh()
        self.tree.selection_set(str(key))
        self.tree.see(str(key))
        self.select()
        self.text.focus_set()

    def save(self, save_as=False):
        path = self.path
        if save_as or path is None:
            chosen = filedialog.asksaveasfilename(parent=self.root, defaultextension=".str",
                                                initialfile=Path(self.label).name,
                                                filetypes=[("FH2 string table", "*.str")])
            if not chosen:
                return False
            path = Path(chosen)
        temporary = None
        try:
            data = self.table.write()
            StrTable.read(data)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            os.replace(temporary, path)
            temporary = None
        except (OSError, ValueError, struct_error) as error:
            self.dialogs.showerror("Cannot save table", str(error))
            return False
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.path, self.label, self.dirty = path, path.name, False
        self.update_status()
        return True

    def close(self):
        if self.confirm():
            self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    Editor(window)
    window.mainloop()
