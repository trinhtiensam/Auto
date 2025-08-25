import json, os, threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ------------------- File JSON -------------------
PROFILES_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"

# ------------------- Mặc định -------------------
DEFAULT_FIELDS = ["Tài khoản","Mật khẩu","Nhập lại mật khẩu","Họ tên","Số điện thoại",
                  "Email","Ngày sinh","PIN","Ngân hàng","Chi nhánh"]

DEFAULT_FIELD_MAP = {
    "username": ["username", "user", "account", "tài khoản", "login"],
    "password": ["password", "pass", "mật khẩu", "pwd"],
    "confirm_password": ["confirm_password", "confirm", "nhập lại mật khẩu", "retype"],
    "fullname": ["fullname", "full_name", "họ tên", "name"],
    "phone": ["phone", "số điện thoại", "mobile", "tel"],
    "email": ["email", "mail", "e-mail"],
    "dob": ["dob", "ngày sinh", "birthday", "date_of_birth"],
    "pin": ["pin", "mã pin", "code"],
    "bank": ["bank", "ngân hàng"],
    "branch": ["branch", "chi nhánh", "branch_name"]
}

# ------------------- Load/Save JSON -------------------
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(file,data):
    with open(file,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

# ------------------- Tự động dò Hidemium Profiles -------------------
def autodetect_hidemium_profiles(port_range=range(9222,9232)):
    profiles = []
    for port in port_range:
        try:
            url = f"http://127.0.0.1:{port}/json/version"
            resp = requests.get(url, timeout=0.3)
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("Browser","Hidemium Profile")
                profiles.append({"tên": name, "port": port})
        except:
            continue
    return profiles

# ------------------- Chuyển key code sang tên hiển thị -------------------
def field_mapping_to_human(field):
    mapping = {
        "username":"Tài khoản",
        "password":"Mật khẩu",
        "confirm_password":"Nhập lại mật khẩu",
        "fullname":"Họ tên",
        "phone":"Số điện thoại",
        "email":"Email",
        "dob":"Ngày sinh",
        "pin":"PIN",
        "bank":"Ngân hàng",
        "branch":"Chi nhánh"
    }
    return mapping.get(field,field)

# ------------------- GUI -------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Autofill Hidemium")
        self.geometry("800x500")

        # Load dữ liệu
        self.profiles = load_json(PROFILES_FILE, [])
        self.field_map = load_json(SETTINGS_FILE, DEFAULT_FIELD_MAP.copy())
        self.hidemium_profiles = []

        # GUI
        self.create_widgets()
        self.update_profile_table()

        # Tự động dò Hidemium profile
        threading.Thread(target=self.detect_profiles_thread, daemon=True).start()

    # ------------------- GUI Widgets -------------------
    def create_widgets(self):
        # Combobox chọn profile Hidemium
        frame_top = ttk.Frame(self)
        frame_top.pack(fill="x", padx=10, pady=5)
        ttk.Label(frame_top, text="Chọn profile Hidemium:").pack(side="left")
        self.hidemium_cb = ttk.Combobox(frame_top,state="readonly")
        self.hidemium_cb.pack(side="left", padx=5)

        # Combobox chọn hồ sơ
        ttk.Label(frame_top, text="Chọn hồ sơ:").pack(side="left", padx=10)
        self.profile_cb = ttk.Combobox(frame_top,state="readonly")
        self.profile_cb.pack(side="left", padx=5)
        self.profile_cb.bind("<<ComboboxSelected>>", lambda e:self.show_selected_profile())

        # Bảng hiển thị hồ sơ
        self.tree = ttk.Treeview(self, columns=("field","value"), show="headings")
        self.tree.heading("field", text="Trường")
        self.tree.heading("value", text="Giá trị")
        self.tree.column("field", width=200)
        self.tree.column("value", width=500)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # Nút Autofill
        ttk.Button(self, text="Chạy Autofill", command=self.autofill).pack(pady=5)

        # Menu
        menubar = tk.Menu(self)
        profile_menu = tk.Menu(menubar, tearoff=0)
        profile_menu.add_command(label="Thêm/Sửa/Xóa Hồ sơ", command=self.edit_profiles)
        profile_menu.add_command(label="Import Hồ sơ", command=self.import_profiles)
        profile_menu.add_command(label="Export Hồ sơ", command=self.export_profiles)
        menubar.add_cascade(label="Hồ sơ", menu=profile_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Nhận dạng trường", command=self.edit_field_map)
        menubar.add_cascade(label="Cài đặt", menu=settings_menu)
        self.config(menu=menubar)

    # ------------------- Hồ sơ -------------------
    def update_profile_table(self):
        self.tree.delete(*self.tree.get_children())
        profile_names = [p.get("Tên hồ sơ",f"Hồ sơ {i}") for i,p in enumerate(self.profiles)]
        self.profile_cb['values'] = profile_names
        if profile_names:
            self.profile_cb.current(0)
            self.show_selected_profile()

    def show_selected_profile(self):
        self.tree.delete(*self.tree.get_children())
        idx = self.profile_cb.current()
        if idx<0: return
        profile = self.profiles[idx]
        for key in DEFAULT_FIELDS:
            self.tree.insert("", "end", values=(key, profile.get(key,"")))

    def edit_profiles(self):
        ProfileEditor(self)

    def import_profiles(self):
        file = filedialog.askopenfilename(filetypes=[("JSON files","*.json")])
        if file:
            try:
                data = load_json(file,[])
                self.profiles += data
                save_json(PROFILES_FILE,self.profiles)
                self.update_profile_table()
                messagebox.showinfo("Import","Import hồ sơ thành công.")
            except Exception as e:
                messagebox.showerror("Lỗi", str(e))

    def export_profiles(self):
        file = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON files","*.json")])
        if file:
            save_json(file,self.profiles)
            messagebox.showinfo("Export","Export hồ sơ thành công.")

    # ------------------- Field Map -------------------
    def edit_field_map(self):
        FieldSettingsEditor(self)

    # ------------------- Tự động dò Hidemium -------------------
    def detect_profiles_thread(self):
        self.hidemium_profiles = autodetect_hidemium_profiles()
        names = [p['tên'] for p in self.hidemium_profiles]
        self.hidemium_cb['values'] = names
        if names: self.hidemium_cb.current(0)

    # ------------------- Autofill -------------------
    def autofill(self):
        hidemium_idx = self.hidemium_cb.current()
        profile_idx = self.profile_cb.current()
        if hidemium_idx<0 or profile_idx<0:
            messagebox.showwarning("Chọn profile","Vui lòng chọn profile Hidemium và hồ sơ.")
            return
        hidemium_profile = self.hidemium_profiles[hidemium_idx]
        profile = self.profiles[profile_idx]
        port = hidemium_profile['port']
        try:
            chrome_options = Options()
            chrome_options.debugger_address = f"127.0.0.1:{port}"
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            driver.switch_to.window(driver.current_window_handle)
            inputs = driver.find_elements("xpath","//input | //textarea")
            for inp in inputs:
                try:
                    attr_text = " ".join([
                        inp.get_attribute("name") or "",
                        inp.get_attribute("id") or "",
                        inp.get_attribute("placeholder") or "",
                        inp.get_attribute("aria-label") or ""
                    ]).lower()
                    for field, keywords in self.field_map.items():
                        if any(k.lower() in attr_text for k in keywords):
                            value = profile.get(field_mapping_to_human(field),"")
                            inp.clear()
                            inp.send_keys(value)
                            break
                except: pass
            messagebox.showinfo("Hoàn thành","Autofill xong!")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

# ------------------- Profile Editor -------------------
class ProfileEditor(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Quản lý hồ sơ")
        self.geometry("700x400")
        self.master = master

        self.fields = {}
        form_frame = ttk.Frame(self)
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for i, field in enumerate(DEFAULT_FIELDS):
            ttk.Label(form_frame, text=field).grid(row=i, column=0, sticky="w", pady=2)
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, sticky="ew", pady=2)
            self.fields[field] = entry

        # Nút thao tác
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Lưu", command=self.save_profile).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Xóa", command=self.delete_profile).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Đóng", command=self.destroy).pack(side="left", padx=5)

        idx = self.master.profile_cb.current()
        if idx >= 0:
            profile = self.master.profiles[idx]
            for k,v in profile.items():
                if k in self.fields:
                    self.fields[k].insert(0,v)

    def save_profile(self):
        profile = {field:self.fields[field].get() for field in DEFAULT_FIELDS}
        idx = self.master.profile_cb.current()
        if idx >= 0:
            self.master.profiles[idx] = profile
        else:
            self.master.profiles.append(profile)
        save_json(PROFILES_FILE, self.master.profiles)
        self.master.update_profile_table()
        messagebox.showinfo("Lưu", "Đã lưu hồ sơ.")
        self.destroy()

    def delete_profile(self):
        idx = self.master.profile_cb.current()
        if idx >= 0:
            self.master.profiles.pop(idx)
            save_json(PROFILES_FILE, self.master.profiles)
            self.master.update_profile_table()
            messagebox.showinfo("Xóa", "Đã xóa hồ sơ.")
            self.destroy()

# ------------------- Field Settings Editor -------------------
class FieldSettingsEditor(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Cấu hình Nhận dạng Trường")
        self.geometry("500x400")
        self.master = master

        self.tree = ttk.Treeview(self, columns=("keywords",), show="headings")
        self.tree.heading("keywords", text="Từ khóa")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        for field, keywords in self.master.field_map.items():
            self.tree.insert("", "end", iid=field, values=(",".join(keywords),))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Sửa", command=self.edit_keywords).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Lưu", command=self.save_settings).pack(side="left", padx=5)

    def edit_keywords(self):
        field = self.tree.focus()
        if not field: return
        old_val = ",".join(self.master.field_map.get(field,[]))
        new_val = simpledialog.askstring("Sửa từ khóa", f"Nhập từ khóa cho {field_mapping_to_human(field)}:", initialvalue=old_val)
        if new_val is not None:
            keywords = [k.strip() for k in new_val.split(",") if k.strip()]
            self.master.field_map[field] = keywords
            self.tree.item(field, values=(",".join(keywords),))

    def save_settings(self):
        save_json(SETTINGS_FILE, self.master.field_map)
        messagebox.showinfo("Lưu", "Đã lưu cấu hình.")
        self.destroy()

# ------------------- Main -------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
