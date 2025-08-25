# autofill_app.py
# Simple Python autofill application
# - Reads profiles.json
# - Lets user select multiple profiles
# - Can autofill into a target window by focusing it (by title) or giving user a countdown to click in the target
# - Uses pyautogui to type and press Tab between fields

"""
Files included in this single document (copy each to separate files):

1) autofill_app.py  (this file)
2) profiles.json    (sample data file)
3) requirements.txt
4) README (packaging & usage instructions)

Save them in the same folder.
"""

import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui

# Optional: Use pygetwindow for window activation (Windows, macOS minimal)
try:
    import pygetwindow as gw
    HAVE_PYGETWINDOW = True
except Exception:
    HAVE_PYGETWINDOW = False

APP_TITLE = 'Autofill - Simple App'

# --------------------------
# Helper: load profiles
# --------------------------

def load_profiles(path='profiles.json'):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Expecting a list of profiles: [{"name":"Alice","fields":["alice","p@ss","Alice Nguyen",...]}, ...]
    return data

# --------------------------
# Autofill logic
# --------------------------

def autofill_profile(profile, press_tab=True, interval=0.05):
    """Type the fields of a single profile. If press_tab True, sends TAB after each field.
    profile: dict with keys 'name' and 'fields' (list of strings)
    """
    fields = profile.get('fields', [])
    for i, val in enumerate(fields):
        # Give tiny pause between characters to mimic human typing
        pyautogui.write(str(val), interval=interval)
        if press_tab and i < len(fields) - 0:
            pyautogui.press('tab')
            time.sleep(0.05)

# --------------------------
# Background worker
# --------------------------

def run_autofill(profiles, mode, countdown, activate_title, interval, press_tab=True):
    """mode: 'countdown' or 'title'
    countdown: seconds before start
    activate_title: window title to activate if mode == 'title'
    """
    if mode == 'title' and HAVE_PYGETWINDOW:
        # try to activate the window first
        try:
            wins = gw.getWindowsWithTitle(activate_title)
            if not wins:
                raise Exception('No window matching title found')
            wins[0].activate()
            time.sleep(0.3)
        except Exception as e:
            print('Could not activate window by title:', e)
            # fallback to countdown
            mode = 'countdown'

    if mode == 'countdown':
        for i in range(countdown, 0, -1):
            print(f'Starting in {i} s...')
            time.sleep(1)

    # now type all selected profiles (one after another)
    for p in profiles:
        print('Filling profile:', p.get('name'))
        autofill_profile(p, press_tab=press_tab, interval=interval)
        # optional small delay between profiles
        time.sleep(0.3)

# --------------------------
# GUI
# --------------------------

class AutofillApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('640x480')

        self.profiles = []
        self.check_vars = []

        self.create_widgets()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)

        top = ttk.Frame(frm)
        top.pack(fill='x')

        ttk.Button(top, text='Open profiles.json', command=self.open_profiles).pack(side='left')
        ttk.Button(top, text='Reload', command=self.reload_profiles).pack(side='left')
        ttk.Button(top, text='Save as...', command=self.save_profiles_as).pack(side='left')

        # Profiles list area with checkboxes
        self.canvas = tk.Canvas(frm)
        self.scroll = ttk.Scrollbar(frm, orient='vertical', command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0,0), window=self.inner, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scroll.pack(side='right', fill='y')

        # Options
        opt = ttk.LabelFrame(self, text='Options', padding=8)
        opt.pack(fill='x', padx=12, pady=8)

        self.start_mode = tk.StringVar(value='countdown')
        ttk.Radiobutton(opt, text='Countdown (click target manually)', variable=self.start_mode, value='countdown').grid(row=0, column=0, sticky='w')
        ttk.Radiobutton(opt, text='Activate window by title (requires pygetwindow)', variable=self.start_mode, value='title').grid(row=0, column=1, sticky='w')

        ttk.Label(opt, text='Countdown (s):').grid(row=1, column=0, sticky='e')
        self.countdown_var = tk.IntVar(value=5)
        ttk.Entry(opt, textvariable=self.countdown_var, width=6).grid(row=1, column=1, sticky='w')

        ttk.Label(opt, text='Window title (for title mode):').grid(row=2, column=0, sticky='e')
        self.title_var = tk.StringVar()
        ttk.Entry(opt, textvariable=self.title_var, width=40).grid(row=2, column=1, sticky='w')

        ttk.Label(opt, text='Typing interval (s/char):').grid(row=3, column=0, sticky='e')
        self.interval_var = tk.DoubleVar(value=0.02)
        ttk.Entry(opt, textvariable=self.interval_var, width=6).grid(row=3, column=1, sticky='w')

        self.press_tab_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text='Press TAB after each field', variable=self.press_tab_var).grid(row=4, column=0, sticky='w')

        # Action buttons
        actions = ttk.Frame(self)
        actions.pack(fill='x', padx=12, pady=8)
        ttk.Button(actions, text='Start Autofill', command=self.start_autofill).pack(side='left')
        ttk.Button(actions, text='Stop (kill threads)', command=self.stop_autofill).pack(side='left')

        # Status
        self.status = tk.StringVar(value='Ready')
        ttk.Label(self, textvariable=self.status).pack(fill='x', padx=12)

    def open_profiles(self):
        path = filedialog.askopenfilename(filetypes=[('JSON files','*.json')], initialfile='profiles.json')
        if path:
            try:
                self.profiles = load_profiles(path)
                self.profiles_path = path
                self.populate_profiles()
                self.status.set(f'Loaded {len(self.profiles)} profiles from {path}')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to load profiles: {e}')

    def reload_profiles(self):
        try:
            self.profiles = load_profiles(getattr(self, 'profiles_path', 'profiles.json'))
            self.populate_profiles()
            self.status.set(f'Reloaded {len(self.profiles)} profiles')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to reload profiles: {e}')

    def save_profiles_as(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files','*.json')])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
            self.status.set(f'Saved profiles to {path}')

    def populate_profiles(self):
        # clear
        for child in self.inner.winfo_children():
            child.destroy()
        self.check_vars = []

        for i, p in enumerate(self.profiles):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(self.inner, text=f"{p.get('name','(no name)')}", variable=var)
            cb.grid(row=i, column=0, sticky='w', padx=4, pady=2)
            # show a small preview
            ttk.Label(self.inner, text=', '.join(map(str, p.get('fields', [])[:3])) + (', ...' if len(p.get('fields', []))>3 else '')).grid(row=i, column=1, sticky='w')
            self.check_vars.append(var)

    def start_autofill(self):
        sel = [p for p, v in zip(self.profiles, self.check_vars) if v.get()]
        if not sel:
            messagebox.showinfo('No selection', 'Please select at least one profile to autofill.')
            return
        mode = self.start_mode.get()
        countdown = int(self.countdown_var.get())
        title = self.title_var.get()
        interval = float(self.interval_var.get())
        press_tab = self.press_tab_var.get()

        self.status.set('Starting autofill...')
        # run in thread to avoid blocking UI
        self.worker = threading.Thread(target=self._worker_thread, args=(sel, mode, countdown, title, interval, press_tab), daemon=True)
        self.worker.start()

    def _worker_thread(self, sel, mode, countdown, title, interval, press_tab):
        try:
            run_autofill(sel, mode, countdown, title, interval, press_tab)
            self.status.set('Autofill finished')
        except Exception as e:
            self.status.set(f'Error: {e}')

    def stop_autofill(self):
        # In this simple app we cannot gracefully stop pyautogui typing; user can move mouse to corner to trigger fail-safe.
        # Inform user how to stop
        messagebox.showinfo('Stop', 'To stop pyautogui typing you can move your mouse to the top-left corner to trigger PyAutoGUI fail-safe (or close the script).')


if __name__ == '__main__':
    # Try to load default profiles.json if present
    try:
        profiles = load_profiles('profiles.json')
    except Exception:
        profiles = []

    app = AutofillApp()
    app.profiles = profiles
    if profiles:
        app.populate_profiles()
    app.mainloop()


# --------------------------
# Sample profiles.json content (save as profiles.json in same folder):
# [
#   {
#     "name": "Test Account 1",
#     "fields": ["username1", "password123", "Nguyen Van A", "0123456789", "a@example.com"]
#   },
#   {
#     "name": "Test Account 2",
#     "fields": ["anotheruser", "p@ssw0rd", "Tran Thi B", "0987654321", "b@example.com"]
#   }
# ]

# --------------------------
# requirements.txt
# pyautogui
# pygetwindow   # optional but recommended on Windows/macOS
# pillow        # pyautogui dependency

# --------------------------
# README (quick start)
# 1) Install Python 3.8+ and pip
# 2) pip install -r requirements.txt
# 3) Save profiles.json next to autofill_app.py
# 4) python autofill_app.py
# 5) Select profiles, choose mode, click Start. If using Countdown, click into the target window before the timer ends.
#
# Packaging to EXE (PyInstaller):
# pip install pyinstaller
# pyinstaller --onefile --windowed autofill_app.py
# The EXE will be in dist/autofill_app.exe
# Note: If pygetwindow is used, you may need additional hooks for Windows; test the EXE thoroughly.
#
# Safety notes:
# - Do NOT use this tool to autofill content into sites without permission.
# - Move the mouse to the screen corner to trigger PyAutoGUI fail-safe if something goes wrong.
# --------------------------
