# FH2 STR Editor

Small standalone Windows editor for Forza Horizon 2 **LSB2 version 0x200** string tables.
No Python installation is required to run the packaged EXE.

Uses CarPackStudio's charcoal palette and blue buttons, with a custom document
icon for the EXE, main window and app dialogs. App dialogs are dark; native
Windows open/save pickers retain the operating system's appearance.

- Open a `.str` file or select a table directly from a language ZIP.
- Search by numeric ID or text; select a row and edit the multiline text below it.
- Add an entry with a unique decimal or hexadecimal 16-bit ID.
- Create an empty table with **New**.
- Save or Save As writes a standalone `.str` file, never modifies a ZIP.
- Ctrl+O opens, Ctrl+N creates, Ctrl+S saves. Text edits apply immediately.

Existing symbolic-name, comment and key-order sections are preserved unchanged,
following FH2 Mod Platform's text-patching approach. Newly added entries use numeric
IDs; this tool does not generate symbolic `IDS_` names or database references.
Unmodified tables are saved byte-for-byte. Invalid formats are rejected.

Back up your originals. Use the game's mediaoverride mechanism rather than
overwriting stock game media. A new table alone does not make the game load it:
the game must already reference that table and the IDs you add.
Editing a language ZIP's table saves an extracted `.str`; repacking/installing it
is separate. The game reads string tables at startup.

## Build

Python 3.12 with Tkinter and PyInstaller:

```powershell
python -m unittest -v
python -m PyInstaller --noconfirm --clean --onefile --windowed --name FH2StrEditor --icon icon.ico --add-data "icon.ico;." app.py
```

Output: `dist\FH2StrEditor.exe`.
