import os, json, re, psutil, requests, sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.simpledialog import askstring
from PIL import Image, ImageTk
import win32gui, win32process, win32con, win32ui

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# =============== Files & Defaults ===============
PROFILES_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"

FIELDS = [
    "Tên hồ sơ", "Tài khoản", "Mật khẩu", "Nhập lại mật khẩu", "Họ tên",
    "SĐT", "Email", "Năm sinh", "PIN", "Ngân hàng", "Chi nhánh"
]

DEFAULT_FIELD_KEYWORDS = {
    "Tên hồ sơ": ["profile_name", "ten_ho_so"],
    "Tài khoản": ["username", "user", "account", "login", "tai_khoan"],
    "Mật khẩu": ["password", "pass", "pwd", "mat_khau"],
    "Nhập lại mật khẩu": ["confirm", "confirm_password", "retype", "nhap_lai"],
    "Họ tên": ["fullname", "full_name", "name", "ho_ten"],
    "SĐT": ["phone", "mobile", "tel", "so_dien_thoai", "sdt"],
    "Email": ["email", "mail", "e-mail"],
    "Năm sinh": ["dob", "birth", "birthday", "ngay_sinh", "nam_sinh"],
    "PIN": ["pin", "security_code", "ma_pin"],
    "Ngân hàng": ["bank", "ten_ngan_hang"],
    "Chi nhánh": ["branch", "branch_name", "chi_nhanh"]
}

# =============== IO Helpers ===============
def ensure_file_json(path: str, default_obj):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_obj, f, indent=2, ensure_ascii=False)
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default_obj

def save_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

# =============== Windows helpers (title + icon) ===============
def get_window_title_from_pid(pid: int) -> str:
    titles = []

    def callback(hwnd, _):
        try:
            tid, current_pid = win32process.GetWindowThreadProcessId(hwnd)
            if current_pid == pid and win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title.strip():
                    titles.append(title)
        except Exception:
            pass

    win32gui.EnumWindows(callback, None)
    return titles[0] if titles else ""

def get_icon_from_exe(exe_path: str, size: int = 20):
    try:
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        hicon = (small[0] if small else (large[0] if large else None))
        if not hicon:
            return None

        hdc_screen = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc_screen, size, size)

        memdc = hdc_screen.CreateCompatibleDC()
        memdc.SelectObject(hbmp)
        win32gui.DrawIconEx(memdc.GetHandleOutput(), 0, 0, hicon, size, size, 0, None, win32con.DI_NORMAL)

        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)

        from PIL import Image  # already imported Pillow; keep local import for clarity
        img = Image.frombuffer("RGB",
                               (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                               bmpstr, "raw", "BGRX", 0, 1)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# =============== Browser scan (Chromium-based) ===============
BROWSER_KEYWORDS = ["chrome", "msedge", "brave", "hidemium"]

def find_running_browsers():
    """Return list of dicts: {pid, name, exe, port, title, icon} for processes that expose remote-debugging-port."""
    found = []
    for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            name = (p.info["name"] or "").lower()
            if not any(k in name for k in BROWSER_KEYWORDS):
                continue

            cmdline = " ".join(p.info.get("cmdline") or [])
            m = re.search(r"--remote-debugging-port=(\d+)", cmdline)
            if not m:
                continue
            port = m.group(1)

            # Validate the endpoint is active
            try:
                requests.get(f"http://127.0.0.1:{port}/json/version", timeout=0.8)
            except Exception:
                continue

            title = get_window_title_from_pid(p.info["pid"]) or ""
            icon = get_icon_from_exe(p.info.get("exe") or "")  # may be None

            found.append({
                "pid": p.info["pid"],
                "name": p.info["name"],
                "exe": p.info.get("exe") or "",
                "port": port,
                "title": title,
                "icon": icon
            })
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    return found

# =============== Dialogs ===============
class ProfileForm(tk.Toplevel):
    """Add / Edit profile"""
    def __init__(self, master, initial=None):
        super().__init__(master)
        self.title("Hồ sơ")
        self.resizable(False, False)
        self.result = None

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        self.vars = {}
        for i, field in enumerate(FIELDS):
            ttk.Label(frm, text=field).grid(row=i, column=0, sticky="w", padx=4, pady=3)
            var = tk.StringVar(value=(initial.get(field, "") if initial else ""))
            ent = ttk.Entry(frm, textvariable=var, width=36, show="*" if "khẩu" in field.upper() or field == "PIN" else "")
            ent.grid(row=i, column=1, sticky="w", padx=4, pady=3)
            self.vars[field] = var

        btns = ttk.Frame(frm)
        btns.grid(row=len(FIELDS), column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btns, text="Lưu", command=self.on_ok).pack(side="left", padx=5)
        ttk.Button(btns, text="Huỷ", command=self.destroy).pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self.on_ok())
        self.grab_set()
        self.transient(master)
        self.focus()

    def on_ok(self):
        data = {f: self.vars[f].get() for f in FIELDS}
        if not data["Tên hồ sơ"].strip():
            messagebox.showerror("Lỗi", "Tên hồ sơ không được để trống.")
            return
        self.result = data
        self.destroy()

class FieldMapEditor(tk.Toplevel):
    """Edit settings.json: field -> keywords list"""
    def __init__(self, master, settings: dict):
        super().__init__(master)
        self.title("Cài đặt nhận dạng trường")
        self.geometry("580x400")
        self.settings = {k: list(v) for k, v in settings.items()}
        self.result = None

        left = ttk.Frame(self, padding=6); left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=6); right.pack(side="right", fill="both", expand=True)

        ttk.Label(left, text="Trường").pack(anchor="w")
        self.list_fields = tk.Listbox(left, height=20)
        self.list_fields.pack(fill="y", expand=False)
        for f in FIELDS:
            self.list_fields.insert("end", f)
        self.list_fields.bind("<<ListboxSelect>>", self.on_select_field)
        self.list_fields.selection_set(0)

        ttk.Label(right, text="Từ khoá (mỗi dòng một từ)").pack(anchor="w")
        self.txt_keywords = tk.Text(right, height=15)
        self.txt_keywords.pack(fill="both", expand=True)

        btns = ttk.Frame(right); btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Lưu thay đổi", command=self.save_current).pack(side="left", padx=4)
        ttk.Button(btns, text="Đóng", command=self.on_close).pack(side="left", padx=4)

        self.on_select_field(None)
        self.grab_set(); self.transient(master)

    def on_select_field(self, _):
        idx = self.list_fields.curselection()
        if not idx: return
        field = self.list_fields.get(idx[0])
        kw = "\n".join(self.settings.get(field, []))
        self.txt_keywords.delete("1.0", "end")
        self.txt_keywords.insert("1.0", kw)

    def save_current(self):
        idx = self.list_fields.curselection()
        if not idx: return
        field = self.list_fields.get(idx[0])
        raw = self.txt_keywords.get("1.0", "end").strip()
        arr = [x.strip() for x in raw.splitlines() if x.strip()]
        self.settings[field] = arr
        messagebox.showinfo("Đã lưu", f"Đã cập nhật từ khoá cho '{field}'.")

    def on_close(self):
        # lưu lần cuối trường đang mở
        self.save_current()
        self.result = self.settings
        self.destroy()

# =============== Main App ===============
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Autofill App")
        self.geometry("1000x620")

        # Data
        self.profiles = ensure_file_json(PROFILES_FILE, [])
        self.field_map = ensure_file_json(SETTINGS_FILE, DEFAULT_FIELD_KEYWORDS)
        self.browser_list = []

        # ---- Menu ----
        menubar = tk.Menu(self)
        m_profile = tk.Menu(menubar, tearoff=0)
        m_profile.add_command(label="Thêm hồ sơ", command=self.add_profile)
        m_profile.add_command(label="Sửa hồ sơ", command=self.edit_profile)
        m_profile.add_command(label="Xoá hồ sơ", command=self.delete_profile)
        m_profile.add_separator()
        m_profile.add_command(label="Import JSON...", command=self.import_profiles)
        m_profile.add_command(label="Export JSON...", command=self.export_profiles)
        menubar.add_cascade(label="Hồ sơ", menu=m_profile)

        m_setting = tk.Menu(menubar, tearoff=0)
        m_setting.add_command(label="Nhận dạng trường", command=self.open_field_map_editor)
        menubar.add_cascade(label="Cài đặt", menu=m_setting)
        self.config(menu=menubar)

        # ---- Layout ----
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Left: Browser list (with icons)
        frm_left = ttk.Frame(self, padding=8)
        frm_left.grid(row=0, column=0, rowspan=2, sticky="nsw")
        ttk.Label(frm_left, text="Browser đang chạy:", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.browser_tree = ttk.Treeview(frm_left, show="tree", height=12)
        self.browser_tree.pack(fill="both", expand=False, pady=(4, 6), padx=(0, 4))

        ttk.Button(frm_left, text="🔍 Quét Browser", command=self.scan_browsers).pack(fill="x", pady=(0, 6))
        ttk.Button(frm_left, text="⚡ Autofill hồ sơ đã chọn", command=self.autofill).pack(fill="x")

        # Right top: Profiles table
        frm_right_top = ttk.Frame(self, padding=(8, 8, 8, 4))
        frm_right_top.grid(row=0, column=1, sticky="nsew")
        frm_right_top.columnconfigure(0, weight=1)
        ttk.Label(frm_right_top, text="Hồ sơ", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")

        self.tbl = ttk.Treeview(frm_right_top,
                                columns=("Tên hồ sơ", "Tài khoản", "Email"),
                                show="headings", height=10)
        for c in ("Tên hồ sơ", "Tài khoản", "Email"):
            self.tbl.heading(c, text=c)
            self.tbl.column(c, width=180 if c == "Tên hồ sơ" else 160, anchor="center")
        self.tbl.grid(row=1, column=0, sticky="nsew", pady=(4, 6))
        self.tbl.bind("<<TreeviewSelect>>", lambda e: self.show_profile_detail())

        btns = ttk.Frame(frm_right_top)
        btns.grid(row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Button(btns, text="Thêm", command=self.add_profile).pack(side="left", padx=3)
        ttk.Button(btns, text="Sửa", command=self.edit_profile).pack(side="left", padx=3)
        ttk.Button(btns, text="Xoá", command=self.delete_profile).pack(side="left", padx=3)

        # Right bottom: profile detail (key/value)
        frm_right_bottom = ttk.Frame(self, padding=(8, 0, 8, 8))
        frm_right_bottom.grid(row=1, column=1, sticky="nsew")
        frm_right_bottom.columnconfigure(0, weight=1)
        ttk.Label(frm_right_bottom, text="Chi tiết hồ sơ", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")

        self.detail = ttk.Treeview(frm_right_bottom, columns=("field", "value"), show="headings", height=10)
        self.detail.heading("field", text="Trường")
        self.detail.heading("value", text="Giá trị")
        self.detail.column("field", width=200, anchor="w")
        self.detail.column("value", width=500, anchor="w")
        self.detail.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        self.refresh_profile_table()

        # Auto first scan (non-blocking)
        self.after(300, self.scan_browsers)

    # ---------- Profiles CRUD ----------
    def refresh_profile_table(self):
        self.tbl.delete(*self.tbl.get_children())
        for p in self.profiles:
            self.tbl.insert("", "end", values=(p.get("Tên hồ sơ", ""),
                                               p.get("Tài khoản", ""),
                                               p.get("Email", "")))
        self.show_profile_detail()

    def current_profile_index(self):
        sel = self.tbl.selection()
        if not sel:
            return None
        return self.tbl.index(sel[0])

    def show_profile_detail(self):
        self.detail.delete(*self.detail.get_children())
        idx = self.current_profile_index()
        if idx is None or idx >= len(self.profiles):
            return
        p = self.profiles[idx]
        for f in FIELDS:
            self.detail.insert("", "end", values=(f, p.get(f, "")))

    def add_profile(self):
        dlg = ProfileForm(self)
        self.wait_window(dlg)
        if dlg.result:
            self.profiles.append(dlg.result)
            save_json(PROFILES_FILE, self.profiles)
            self.refresh_profile_table()

    def edit_profile(self):
        idx = self.current_profile_index()
        if idx is None:
            messagebox.showinfo("Chọn hồ sơ", "Hãy chọn 1 hồ sơ để sửa.")
            return
        dlg = ProfileForm(self, initial=self.profiles[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.profiles[idx] = dlg.result
            save_json(PROFILES_FILE, self.profiles)
            self.refresh_profile_table()

    def delete_profile(self):
        idx = self.current_profile_index()
        if idx is None:
            return
        if messagebox.askyesno("Xác nhận", "Xoá hồ sơ đã chọn?"):
            del self.profiles[idx]
            save_json(PROFILES_FILE, self.profiles)
            self.refresh_profile_table()

    def import_profiles(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            data = ensure_file_json(path, [])
            if isinstance(data, list):
                self.profiles.extend(data)
                save_json(PROFILES_FILE, self.profiles)
                self.refresh_profile_table()
                messagebox.showinfo("OK", "Đã import hồ sơ.")
            else:
                messagebox.showerror("Lỗi", "File không hợp lệ (phải là mảng JSON).")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def export_profiles(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            save_json(path, self.profiles)
            messagebox.showinfo("OK", "Đã export hồ sơ.")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    # ---------- Settings editor ----------
    def open_field_map_editor(self):
        dlg = FieldMapEditor(self, self.field_map)
        self.wait_window(dlg)
        if dlg.result:
            self.field_map = dlg.result
            save_json(SETTINGS_FILE, self.field_map)
            messagebox.showinfo("Đã lưu", "Đã cập nhật cài đặt nhận dạng trường.")

    # ---------- Browsers ----------
    def scan_browsers(self):
        # clear old
        for iid in self.browser_tree.get_children():
            self.browser_tree.delete(iid)
        self.browser_list = find_running_browsers()
        if not self.browser_list:
            self.browser_tree.insert("", "end", text="(Không tìm thấy browser nào có --remote-debugging-port)")
            return
        # show with icon + title
        for i, b in enumerate(self.browser_list):
            label = f"{b['name']} | {b['title'] or '(no title)'} (port {b['port']})"
            self.browser_tree.insert("", "end", iid=str(i), text=label, image=b.get("icon"))

    def selected_browser(self):
        sel = self.browser_tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        if 0 <= idx < len(self.browser_list):
            return self.browser_list[idx]
        return None

    # ---------- Autofill ----------
    def autofill(self):
        b = self.selected_browser()
        if not b:
            messagebox.showerror("Lỗi", "Hãy chọn một browser ở khung bên trái.")
            return

        pidx = self.current_profile_index()
        if pidx is None:
            messagebox.showerror("Lỗi", "Hãy chọn một hồ sơ để autofill.")
            return
        profile = self.profiles[pidx]

        try:
            options = Options()
            options.debugger_address = f"127.0.0.1:{b['port']}"
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            messagebox.showerror("Không thể kết nối", f"Không attach được Selenium: {e}")
            return

        filled, not_found = [], []

        # Cách 1 (chính xác, nhanh): duyệt theo từng field -> tìm input theo keyword
        for field, keywords in self.field_map.items():
            val = (profile.get(field) or "").strip()
            if not val:
                continue

            success = False
            # ưu tiên một vài hint theo loại input
            xpath_base = ("//input | //textarea")
            inputs = driver.find_elements("xpath", xpath_base)
            for el in inputs:
                try:
                    attr = " ".join([
                        (el.get_attribute("name") or ""),
                        (el.get_attribute("id") or ""),
                        (el.get_attribute("placeholder") or ""),
                        (el.get_attribute("aria-label") or "")
                    ]).lower()

                    if any(k.lower() in attr for k in keywords):
                        try:
                            el.clear()
                        except Exception:
                            pass
                        el.send_keys(val)
                        filled.append(field)
                        success = True
                        break
                except Exception:
                    continue

            if not success:
                # Fallback: query theo XPATH contains cho từng keyword
                for k in keywords:
                    try:
                        el = driver.find_element(
                            "xpath",
                            f"//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{k.lower()}') "
                            f"or contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{k.lower()}') "
                            f"or contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{k.lower()}') "
                            f"or contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{k.lower()}')]"
                        )
                        try:
                            el.clear()
                        except Exception:
                            pass
                        el.send_keys(val)
                        filled.append(field)
                        success = True
                        break
                    except Exception:
                        continue

            if not success:
                not_found.append(field)

        msg = f"✅ Đã điền: {', '.join(filled) if filled else '(Không có)'}"
        if not_found:
            msg += f"\n⚠️ Không tìm thấy: {', '.join(not_found)}"
        messagebox.showinfo("Kết quả", msg)


# =============== Run ===============
if __name__ == "__main__":
    # Nếu build bằng PyInstaller, dùng --noconsole để ẩn CMD.
    # Ví dụ: pyinstaller -F -w main.py
    app = App()
    app.mainloop()
