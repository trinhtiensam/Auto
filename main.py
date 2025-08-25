import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.simpledialog import askstring
from selenium import webdriver
from selenium.webdriver.common.by import By
import psutil
import win32gui
import win32process
from PIL import Image, ImageTk
import win32ui
import win32con

PROFILES_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"

# ======================= JSON Helper =======================
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ======================= Browser Detection =======================
def get_window_icon(hwnd):
    try:
        hicon = win32gui.SendMessage(hwnd, win32con.WM_GETICON, 1, 0)
        if hicon == 0:
            hicon = win32gui.GetClassLong(hwnd, win32con.GCL_HICON)
        if hicon:
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, 32, 32)
            hdc = hdc.CreateCompatibleDC()
            hdc.SelectObject(hbmp)
            win32gui.DrawIconEx(hdc.GetHandleOutput(), 0, 0, hicon, 32, 32, 0, 0, win32con.DI_NORMAL)
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
            return ImageTk.PhotoImage(img)
    except Exception:
        return None
    return None


def enum_browser_windows():
    browsers = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                p = psutil.Process(pid)
                exe = p.name().lower()
                if any(b in exe for b in ["chrome", "brave", "msedge", "hidemium"]):
                    title = win32gui.GetWindowText(hwnd)
                    icon = get_window_icon(hwnd)
                    browsers.append({"hwnd": hwnd, "title": title, "exe": exe, "icon": icon})
            except Exception:
                pass

    win32gui.EnumWindows(callback, None)
    return browsers


# ======================= Autofill =======================
def find_input_for_field(driver, keywords):
    inputs = driver.find_elements(By.XPATH, "//input | //textarea")
    for inp in inputs:
        attrs = [
            inp.get_attribute("name") or "",
            inp.get_attribute("id") or "",
            inp.get_attribute("placeholder") or "",
            inp.get_attribute("aria-label") or "",
            inp.get_attribute("autocomplete") or "",
            inp.get_attribute("ng-model") or ""
        ]
        combined = " ".join(a.lower() for a in attrs if a)
        for kw in keywords:
            if kw.lower() in combined:
                return inp
    return None


def autofill_profile(driver, profile, settings):
    for field, keywords in settings.items():
        value = profile.get(field, "")
        if not value:
            continue
        inp = find_input_for_field(driver, keywords)
        if inp:
            try:
                inp.clear()
                inp.send_keys(value)
            except Exception:
                pass


# ======================= GUI =======================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Autofill Manager")
        self.root.geometry("1000x600")

        # Load data
        self.profiles = load_json(PROFILES_FILE, [])
        self.settings = load_json(SETTINGS_FILE, {
            "Tên hồ sơ": ["profile", "name", "tên hồ sơ"],
            "Tài khoản": ["account", "username", "user", "tài khoản"],
            "Pass": ["password", "pass", "mật khẩu"],
            "Nhập lại pass": ["confirm", "password_confirmation", "nhập lại mật khẩu"],
            "Họ tên": ["fullname", "name", "họ tên"],
            "SĐT": ["phone", "tel", "sdt", "số điện thoại"],
            "Email": ["email", "mail"],
            "Năm sinh": ["birth", "dob", "birthday", "năm sinh"],
            "PIN": ["pin", "mã pin"],
            "Ngân hàng": ["bank", "ngân hàng"],
            "Chi nhánh": ["branch", "chi nhánh"]
        })

        self.selected_browser = None
        self.setup_ui()

    def setup_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Profiles
        tab1 = tk.Frame(nb)
        nb.add(tab1, text="Quản lý Hồ sơ")

        cols = ["Tên hồ sơ", "Tài khoản", "Email", "SĐT"]
        self.tree = ttk.Treeview(tab1, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=180)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.refresh_profiles()

        btn_frame = tk.Frame(tab1)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="Thêm hồ sơ", command=self.add_profile).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(btn_frame, text="Sửa hồ sơ", command=self.edit_profile).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(btn_frame, text="Xóa hồ sơ", command=self.delete_profile).pack(side=tk.LEFT, padx=5, pady=5)

        # Tab 2: Browser
        tab2 = tk.Frame(nb)
        nb.add(tab2, text="Browser")

        tk.Button(tab2, text="Quét Browser", command=self.select_browser).pack(pady=10)
        self.browser_label = tk.Label(tab2, text="Chưa chọn Browser", font=("Arial", 12))
        self.browser_label.pack(pady=5)
        tk.Button(tab2, text="Autofill", command=self.do_autofill).pack(pady=10)

        # Tab 3: Settings
        tab3 = tk.Frame(nb)
        nb.add(tab3, text="Cấu hình từ khóa")

        self.settings_list = tk.Listbox(tab3, width=80, height=20)
        self.settings_list.pack(fill=tk.BOTH, expand=True)

        self.refresh_settings()

        btn_frame2 = tk.Frame(tab3)
        btn_frame2.pack(fill=tk.X)
        tk.Button(btn_frame2, text="Sửa từ khóa", command=self.edit_setting).pack(side=tk.LEFT, padx=5, pady=5)

    def refresh_profiles(self):
        self.tree.delete(*self.tree.get_children())
        for p in self.profiles:
            self.tree.insert("", tk.END, values=(p.get("Tên hồ sơ"), p.get("Tài khoản"), p.get("Email"), p.get("SĐT")))

    def refresh_settings(self):
        self.settings_list.delete(0, tk.END)
        for k, v in self.settings.items():
            self.settings_list.insert(tk.END, f"{k} → {', '.join(v)}")

    def add_profile(self):
        profile = {}
        for field in self.settings.keys():
            val = askstring("Nhập thông tin", f"{field}:")
            profile[field] = val if val else ""
        self.profiles.append(profile)
        save_json(PROFILES_FILE, self.profiles)
        self.refresh_profiles()

    def edit_profile(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        profile = self.profiles[idx]
        for field in self.settings.keys():
            val = askstring("Sửa thông tin", f"{field}:", initialvalue=profile.get(field, ""))
            profile[field] = val if val else ""
        self.profiles[idx] = profile
        save_json(PROFILES_FILE, self.profiles)
        self.refresh_profiles()

    def delete_profile(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        del self.profiles[idx]
        save_json(PROFILES_FILE, self.profiles)
        self.refresh_profiles()

    def select_browser(self):
        self.browsers = enum_browser_windows()
        if not self.browsers:
            messagebox.showerror("Lỗi", "Không tìm thấy browser nào đang mở!")
            return

        win = tk.Toplevel(self.root)
        win.title("Chọn Browser")

        frame = tk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True)

        lb = tk.Listbox(frame, width=80, height=15)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame, orient="vertical", command=lb.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        lb.config(yscrollcommand=scrollbar.set)

        self.browser_map = {}
        for i, b in enumerate(self.browsers):
            text = f"{b['exe']} | {b['title']}"
            lb.insert(i, text)
            self.browser_map[i] = b

        def on_select():
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            self.selected_browser = self.browser_map[idx]
            self.browser_label.config(text=f"Đã chọn: {self.selected_browser['exe']} - {self.selected_browser['title']}")
            win.destroy()

        tk.Button(win, text="Chọn", command=on_select).pack(pady=5)

    def do_autofill(self):
        if not self.selected_browser:
            messagebox.showerror("Lỗi", "Chưa chọn browser!")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Lỗi", "Chưa chọn hồ sơ!")
            return

        idx = self.tree.index(sel[0])
        profile = self.profiles[idx]

        try:
            options = webdriver.ChromeOptions()
            options.debugger_address = "127.0.0.1:9222"
            driver = webdriver.Chrome(options=options)
            autofill_profile(driver, profile, self.settings)
            messagebox.showinfo("Thành công", "Đã autofill xong!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể autofill: {e}")

    def edit_setting(self):
        sel = self.settings_list.curselection()
        if not sel:
            return
        idx = sel[0]
        field = list(self.settings.keys())[idx]
        current = ", ".join(self.settings[field])
        val = askstring("Sửa từ khóa", f"Từ khóa cho {field} (cách nhau dấu phẩy):", initialvalue=current)
        if val is not None:
            self.settings[field] = [v.strip() for v in val.split(",") if v.strip()]
            save_json(SETTINGS_FILE, self.settings)
            self.refresh_settings()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
