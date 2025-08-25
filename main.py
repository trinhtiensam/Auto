import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import psutil
import win32gui
import win32process
from PIL import Image, ImageTk
import base64
import io

SETTINGS_FILE = "settings.json"
PROFILES_FILE = "profiles.json"

# -------------------------
# Utils
# -------------------------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# -------------------------
# Browser scanning
# -------------------------
def enum_windows_callback(hwnd, result):
    if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            p = psutil.Process(pid)
            exe = p.name().lower()
            if exe in ["chrome.exe", "brave.exe", "msedge.exe"]:
                result.append((exe, hwnd, win32gui.GetWindowText(hwnd)))
        except psutil.NoSuchProcess:
            pass

def scan_browsers():
    result = []
    win32gui.EnumWindows(enum_windows_callback, result)
    return result

def get_icon_from_hwnd(hwnd):
    try:
        hicon = win32gui.SendMessage(hwnd, 0x7F, 1, 0)  # WM_GETICON, ICON_SMALL
        if hicon == 0:
            hicon = win32gui.GetClassLong(hwnd, -14)  # GCL_HICONSM
        if hicon:
            # Không lấy icon gốc vì hơi phức tạp, tạm trả None
            return None
    except Exception:
        return None
    return None

# -------------------------
# Autofill
# -------------------------
def autofill(driver, profile, settings):
    for field, keywords in settings.items():
        value = profile.get(field, "")
        if not value:
            continue
        try:
            for kw in keywords:
                xpath = (
                    f"//*[@name='{kw}' or @id='{kw}' or "
                    f"contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}') or "
                    f"contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}') or "
                    f"contains(translate(@ng-model,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}') or "
                    f"contains(translate(@formcontrolname,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}') or "
                    f"contains(translate(@autocomplete,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]"
                )
                elems = driver.find_elements(By.XPATH, xpath)
                if elems:
                    elems[0].clear()
                    elems[0].send_keys(value)
                    break
        except Exception as e:
            print("Autofill error:", e)

# -------------------------
# GUI
# -------------------------
class AutofillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Autofill App")

        self.settings = load_json(SETTINGS_FILE, {
            "Tên hồ sơ": ["profile", "name"],
            "Tài khoản": ["account", "username", "user"],
            "Pass": ["password", "pass"],
            "Nhập lại pass": ["confirm", "password_confirmation"],
            "Họ tên": ["fullname", "name"],
            "SĐT": ["phone", "tel", "số điện thoại"],
            "Email": ["email", "mail"],
            "Năm sinh": ["birth", "dob", "ngaysinh"],
            "PIN": ["pin", "mã pin"],
            "Ngân hàng": ["bank", "nganhang"],
            "Chi nhánh": ["branch", "chinhanh"]
        })
        self.profiles = load_json(PROFILES_FILE, [])

        self.build_ui()

    def build_ui(self):
        # Browser section
        ttk.Label(self.root, text="Browser đang chạy:").pack(anchor="w", padx=5, pady=2)
        self.browser_list = tk.Listbox(self.root, height=5)
        self.browser_list.pack(fill="x", padx=5, pady=2)
        ttk.Button(self.root, text="Quét Browser", command=self.update_browsers).pack(pady=3)

        # Profile table
        cols = ["Tên hồ sơ", "Tài khoản", "Email"]
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=5)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.pack(fill="x", padx=5, pady=5)
        self.update_profiles()

        # Action buttons
        frame = ttk.Frame(self.root)
        frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(frame, text="Thêm", command=self.add_profile).pack(side="left", padx=3)
        ttk.Button(frame, text="Sửa", command=self.edit_profile).pack(side="left", padx=3)
        ttk.Button(frame, text="Xóa", command=self.delete_profile).pack(side="left", padx=3)

    def update_browsers(self):
        self.browser_list.delete(0, tk.END)
        for exe, hwnd, title in scan_browsers():
            self.browser_list.insert(tk.END, f"{exe} | {title}")

    def update_profiles(self):
        self.tree.delete(*self.tree.get_children())
        for p in self.profiles:
            self.tree.insert("", "end", values=(p.get("Tên hồ sơ"), p.get("Tài khoản"), p.get("Email")))

    def add_profile(self):
        self.profile_form()

    def edit_profile(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Chọn hồ sơ để sửa")
            return
        idx = self.tree.index(selected)
        self.profile_form(self.profiles[idx], idx)

    def delete_profile(self):
        selected = self.tree.focus()
        if not selected:
            return
        idx = self.tree.index(selected)
        del self.profiles[idx]
        save_json(PROFILES_FILE, self.profiles)
        self.update_profiles()

    def profile_form(self, profile=None, index=None):
        top = tk.Toplevel(self.root)
        top.title("Thông tin hồ sơ")

        entries = {}
        for field in self.settings.keys():
            frame = ttk.Frame(top)
            frame.pack(fill="x", padx=5, pady=2)
            ttk.Label(frame, text=field, width=15).pack(side="left")
            ent = ttk.Entry(frame)
            ent.pack(fill="x", expand=True)
            if profile:
                ent.insert(0, profile.get(field, ""))
            entries[field] = ent

        def save():
            new_profile = {f: e.get() for f, e in entries.items()}
            if index is None:
                self.profiles.append(new_profile)
            else:
                self.profiles[index] = new_profile
            save_json(PROFILES_FILE, self.profiles)
            self.update_profiles()
            top.destroy()

        ttk.Button(top, text="Lưu", command=save).pack(pady=5)

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = AutofillApp(root)
    root.mainloop()
