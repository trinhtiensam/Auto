import os, json, tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

# -------------------- Files --------------------
PROFILE_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"

# 11 fields
FIELDS = [
    ("name",       "Tên hồ sơ"),
    ("username",   "Tài khoản"),
    ("password",   "Mật khẩu"),
    ("password2",  "Nhập lại mật khẩu"),
    ("fullname",   "Họ tên"),
    ("phone",      "SĐT"),
    ("email",      "Email"),
    ("birthyear",  "Năm sinh"),
    ("pin",        "PIN"),
    ("bank",       "Ngân hàng"),
    ("branch",     "Chi nhánh"),
]

# -------------------- JSON utils --------------------
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_profiles():
    return load_json(PROFILE_FILE, [])

def save_profiles(data):
    save_json(PROFILE_FILE, data)

def default_field_map():
    # map FIELD_KEY -> list keyword (name/id/placeholder/aria-label)
    return {
        "username":  ["username","user","account","tài khoản","login","tai khoan"],
        "password":  ["password","pass","mật khẩu","pwd","mat khau"],
        "password2": ["confirm","confirm_password","retype","nhập lại","nhap lai"],
        "fullname":  ["fullname","full_name","name","họ tên","ho ten"],
        "phone":     ["phone","tel","mobile","số điện thoại","so dien thoai"],
        "email":     ["email","mail","e-mail"],
        "birthyear": ["birth","dob","birthday","năm sinh","year"],
        "pin":       ["pin","code","mã pin","ma pin","otp"],
        "bank":      ["bank","ngân hàng","ngan hang"],
        "branch":    ["branch","chi nhánh","chi nhanh"],
        # "name" (tên hồ sơ) không autofill
    }

def load_settings():
    return load_json(SETTINGS_FILE, {"field_map": default_field_map()})

def save_settings(data):
    save_json(SETTINGS_FILE, data)

# -------------------- Hidemium scan & connect --------------------
def scan_hidemium_ports(start=0000, end=9999, timeout=0.25):
    found = []
    for port in range(start, end + 1):
        try:
            url = f"http://127.0.0.1:{port}/json/version"
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                browser = data.get("Browser", "")
                product = data.get("Product", "")
                label = browser or product or "Chromium"
                found.append({"port": port, "label": label})
        except Exception:
            continue
    return found

def connect_chrome_by_port(port: int):
    opts = webdriver.ChromeOptions()
    opts.debugger_address = f"127.0.0.1:{port}"
    # Selenium Manager sẽ tự tìm chromedriver tương thích
    driver = webdriver.Chrome(options=opts)
    return driver

# -------------------- Autofill --------------------
def try_fill_element(driver, value, keywords):
    """
    Tìm input/textarea theo danh sách keywords trong thuộc tính
    name, id, placeholder, aria-label. Trả về True nếu đã điền.
    """
    if not value:
        return False
    # gom 1 xpath lớn để thử nhanh (ưu tiên input rồi tới textarea)
    for tag in ("input", "textarea"):
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            xpath = (
                f"//{tag}[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}') or "
                f"contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}') or "
                f"contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}') or "
                f"contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]"
            )
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                try:
                    el.clear()
                except Exception:
                    pass
                try:
                    el.send_keys(value)
                    return True
                except Exception:
                    continue
    return False

def do_autofill(driver, profile, field_map):
    filled_any = False
    for key, _label in FIELDS:
        if key in ("name", "password2"):
            continue
        value = profile.get(key, "")
        kws = field_map.get(key, [])
        if try_fill_element(driver, value, kws):
            filled_any = True
    return filled_any

# -------------------- Settings editor (per-field keywords) --------------------
class FieldMapEditor(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Cài đặt nhận dạng trường")
        self.geometry("520x360")
        self.resizable(False, False)

        self.settings = load_settings()
        self.field_map = self.settings.get("field_map", default_field_map())

        # List fields
        left = tk.Frame(self)
        left.pack(side="left", fill="y", padx=8, pady=8)
        tk.Label(left, text="Chọn trường").pack(anchor="w")
        self.listbox = tk.Listbox(left, height=15)
        self.listbox.pack(fill="y")
        for key, label in FIELDS:
            if key == "name":  # không edit keyword cho 'Tên hồ sơ'
                continue
            self.listbox.insert(tk.END, f"{label} ({key})")
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Editor
        right = tk.Frame(self)
        right.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        tk.Label(right, text="Từ khóa (phân tách bởi dấu phẩy):").pack(anchor="w")
        self.txt = tk.Text(right, height=10)
        self.txt.pack(fill="both", expand=True)

        btns = tk.Frame(right)
        btns.pack(fill="x", pady=6)
        tk.Button(btns, text="Lưu", command=self.save_current).pack(side="left")
        tk.Button(btns, text="Đóng", command=self.on_close).pack(side="right")

        # chọn mục đầu
        if self.listbox.size() > 0:
            self.listbox.selection_set(0)
            self.on_select()

    def _current_key(self):
        sel = self.listbox.curselection()
        if not sel:
            return None, None
        text = self.listbox.get(sel[0])  # "Họ tên (fullname)"
        key = text.split("(")[-1].rstrip(")")
        label = text.split(" (")[0]
        return key, label

    def on_select(self, _evt=None):
        key, _label = self._current_key()
        if not key:
            return
        kws = self.field_map.get(key, [])
        self.txt.delete("1.0", tk.END)
        self.txt.insert("1.0", ", ".join(kws))

    def save_current(self):
        key, label = self._current_key()
        if not key:
            return
        raw = self.txt.get("1.0", tk.END).strip()
        kws = [x.strip() for x in raw.split(",") if x.strip()]
        self.field_map[key] = kws
        self.settings["field_map"] = self.field_map
        save_settings(self.settings)
        messagebox.showinfo("Đã lưu", f"Đã lưu từ khóa cho '{label}'")

    def on_close(self):
        self.destroy()

# -------------------- Main App --------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Autofill Hidemium")
        self.geometry("880x640")
        self.resizable(True, True)

        self.driver = None
        self.hidemium_list = []   # [{port, label}]
        self.entries = {}

        # Menu
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        m_profile = tk.Menu(menubar, tearoff=0)
        m_profile.add_command(label="Import JSON...", command=self.import_profiles)
        m_profile.add_command(label="Export JSON...", command=self.export_profiles)
        menubar.add_cascade(label="Hồ sơ", menu=m_profile)

        m_settings = tk.Menu(menubar, tearoff=0)
        m_settings.add_command(label="Nhận dạng trường...", command=self.open_field_map)
        menubar.add_cascade(label="Cài đặt", menu=m_settings)

        # Top row: scan + combobox + connect
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Button(top, text="Quét Hidemium", command=self.scan_hidemium).pack(side="left")
        ttk.Label(top, text="Chọn phiên Hidemium:").pack(side="left", padx=(12, 4))
        self.cbo = ttk.Combobox(top, state="readonly", width=50)
        self.cbo.pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Kết nối", command=self.connect_selected).pack(side="left")
        ttk.Button(top, text="Autofill", command=self.autofill_current).pack(side="left", padx=(8,0))

        # Form 11 fields
        frm = ttk.Frame(self)
        frm.pack(side="left", fill="y", padx=10, pady=6)
        for i, (key, label) in enumerate(FIELDS):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=2)
            show = "*" if key in ("password", "password2", "pin") else None
            e = ttk.Entry(frm, show=show, width=32)
            e.grid(row=i, column=1, sticky="w", pady=2, padx=(6,0))
            self.entries[key] = e
        ttk.Button(frm, text="Lưu/Update hồ sơ", command=self.save_profile).grid(
            row=len(FIELDS), column=0, columnspan=2, pady=8, sticky="we"
        )

        # Table profiles
        right = ttk.Frame(self)
        right.pack(side="right", fill="both", expand=True, padx=10, pady=6)
        cols = ("Tên hồ sơ", "Tài khoản", "Email", "SĐT")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=150)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_pick_profile)

        btn_bar = ttk.Frame(right)
        btn_bar.pack(fill="x", pady=6)
        ttk.Button(btn_bar, text="Xóa hồ sơ", command=self.delete_profile).pack(side="left")

        self.refresh_table()

    # ---------- Profiles ----------
    def current_profile_from_form(self):
        return {k: self.entries[k].get().strip() for k, _ in FIELDS}

    def save_profile(self):
        p = self.current_profile_from_form()
        if not p["name"]:
            messagebox.showerror("Lỗi", "Vui lòng nhập Tên hồ sơ")
            return
        if p["password"] != p["password2"]:
            messagebox.showerror("Lỗi", "Mật khẩu nhập lại không khớp")
            return
        data = load_profiles()
        for i, old in enumerate(data):
            if old.get("name") == p["name"]:
                data[i] = p
                break
        else:
            data.append(p)
        save_profiles(data)
        self.refresh_table()
        messagebox.showinfo("OK", "Đã lưu hồ sơ")

    def refresh_table(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for p in load_profiles():
            self.tree.insert("", "end", values=(p.get("name",""), p.get("username",""), p.get("email",""), p.get("phone","")))

    def on_pick_profile(self, _evt=None):
        item = self.tree.focus()
        if not item:
            return
        vals = self.tree.item(item, "values")
        name = vals[0]
        for p in load_profiles():
            if p.get("name") == name:
                for k, _ in FIELDS:
                    self.entries[k].delete(0, tk.END)
                    self.entries[k].insert(0, p.get(k, ""))
                break

    def delete_profile(self):
        item = self.tree.focus()
        if not item:
            return
        vals = self.tree.item(item, "values")
        name = vals[0]
        data = [p for p in load_profiles() if p.get("name") != name]
        save_profiles(data)
        self.refresh_table()

    def import_profiles(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            data = load_json(path, [])
            if isinstance(data, list):
                save_profiles(data)
                self.refresh_table()
                messagebox.showinfo("OK", "Import thành công")
            else:
                messagebox.showerror("Lỗi", "File không đúng định dạng (expect list)")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không import được: {e}")

    def export_profiles(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            save_json(path, load_profiles())
            messagebox.showinfo("OK", "Export thành công")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không export được: {e}")

    # ---------- Settings ----------
    def open_field_map(self):
        FieldMapEditor(self)

    # ---------- Hidemium ----------
    def scan_hidemium(self):
        self.hidemium_list = scan_hidemium_ports()
        if not self.hidemium_list:
            self.cbo["values"] = []
            messagebox.showwarning("Không thấy", "Không phát hiện Hidemium (hãy mở Hidemium với --remote-debugging-port)")
            return
        show = [f"Port {i['port']} — {i['label']}" for i in self.hidemium_list]
        self.cbo["values"] = show
        self.cbo.current(0)

    def connect_selected(self):
        if not self.hidemium_list:
            messagebox.showerror("Lỗi", "Hãy bấm 'Quét Hidemium' trước")
            return
        idx = self.cbo.current()
        if idx < 0:
            messagebox.showerror("Lỗi", "Chưa chọn phiên Hidemium")
            return
        port = self.hidemium_list[idx]["port"]
        try:
            self.driver = connect_chrome_by_port(port)
            messagebox.showinfo("Kết nối", f"Đã kết nối Hidemium port {port}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Kết nối thất bại: {e}")

    def autofill_current(self):
        if not self.driver:
            messagebox.showwarning("Chưa kết nối", "Hãy kết nối Hidemium trước")
            return
        name = self.entries["name"].get().strip()
        if not name:
            messagebox.showwarning("Thiếu tên hồ sơ", "Nhập hoặc chọn hồ sơ trước")
            return
        data = load_profiles()
        prof = next((p for p in data if p.get("name") == name), None)
        if not prof:
            messagebox.showerror("Lỗi", "Không tìm thấy hồ sơ")
            return
        settings = load_settings()
        field_map = settings.get("field_map", default_field_map())
        ok = do_autofill(self.driver, prof, field_map)
        if ok:
            messagebox.showinfo("Xong", "Autofill thành công")
        else:
            messagebox.showwarning("Chưa điền được", "Không tìm thấy ô nhập phù hợp theo từ khóa")

# -------------------- Run --------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
