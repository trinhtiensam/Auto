import json, os, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import psutil, re

# ------------------- File JSON -------------------
PROFILES_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"

# ------------------- Mặc định -------------------
DEFAULT_FIELDS = [
    "Tên hồ sơ","Tài khoản","Mật khẩu","Nhập lại mật khẩu","Họ tên","Số điện thoại",
    "Email","Năm sinh","PIN","Ngân hàng","Chi nhánh"
]

DEFAULT_FIELD_MAP = {
    "username": ["username", "user", "account", "tài khoản", "login"],
    "password": ["password", "pass", "mật khẩu", "pwd"],
    "confirm_password": ["confirm_password", "confirm", "nhập lại mật khẩu", "retype"],
    "fullname": ["fullname", "full_name", "họ tên", "name"],
    "phone": ["phone", "số điện thoại", "mobile", "tel"],
    "email": ["email", "mail", "e-mail"],
    "dob": ["dob", "năm sinh", "birthday", "date_of_birth"],
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

# ------------------- Quét process Hidemium -------------------
def detect_hidemium_profiles():
    profiles = []
    for proc in psutil.process_iter(['pid','name','cmdline']):
        try:
            name = proc.info['name'] or ''
            if 'hidemium' in name.lower():
                cmdline = " ".join(proc.info['cmdline'])
                match = re.search(r'--remote-debugging-port=(\d+)', cmdline)
                if match:
                    port = int(match.group(1))
                    profiles.append({"tên": f"Hidemium PID {proc.info['pid']}", "port": port})
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return profiles

# ------------------- Chuyển field code sang tên hiển thị -------------------
def field_mapping_to_human(field):
    mapping = {
        "username":"Tài khoản",
        "password":"Mật khẩu",
        "confirm_password":"Nhập lại mật khẩu",
        "fullname":"Họ tên",
        "phone":"Số điện thoại",
        "email":"Email",
        "dob":"Năm sinh",
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
        self.geometry("850x500")
        
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
        self.config(menu=menubar)
        menubar.add_cascade(label="Cài đặt", menu=settings_menu)
    
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
        self.hidemium_profiles = detect_hidemium_profiles()
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
            driver = webdriver.Chrome(options=chrome_options)
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
                            if value:
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
        self.geometry("500x500")
        self.master = master

        self.vars = {f: tk.StringVar() for f in DEFAULT_FIELDS}
        form = ttk.Frame(self)
        form.pack(fill="both", expand=True, padx=10, pady=10)

        for i, field in enumerate(DEFAULT_FIELDS):
            ttk.Label(form, text=field+":").grid(row=i, column=0, sticky="w", pady=2)
            ttk.Entry(form, textvariable=self.vars[field]).grid(row=i, column=1, sticky="ew", pady=2)
        form.columnconfigure(1, weight=1)

        ttk.Button(self, text="Lưu hồ sơ", command=self.save_profile).pack(pady=5)

    def save_profile(self):
        profile = {f:self.vars[f].get() for f in DEFAULT_FIELDS}
        if not profile["Tên hồ sơ"]:
            messagebox.showwarning("Thiếu thông tin","Vui lòng nhập Tên hồ sơ.")
            return
        self.master.profiles.append(profile)
        save_json(PROFILES_FILE, self.master.profiles)
        self.master.update_profile_table()
        self.destroy()

# ------------------- Field Settings Editor -------------------
class FieldSettingsEditor(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Nhận dạng trường")
        self.geometry("500x400")
        self.master = master

        self.entries = {}
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        for i, (field, keywords) in enumerate(self.master.field_map.items()):
            ttk.Label(frame, text=field_mapping_to_human(field)).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=", ".join(keywords))
            ent = ttk.Entry(frame, textvariable=var)
            ent.grid(row=i, column=1, sticky="ew", pady=2)
            self.entries[field] = var
        frame.columnconfigure(1, weight=1)

        ttk.Button(self, text="Lưu", command=self.save).pack(pady=5)

    def save(self):
        new_map = {}
        for field, var in self.entries.items():
            kws = [x.strip() for x in var.get().split(",") if x.strip()]
            new_map[field] = kws
        self.master.field_map = new_map
        save_json(SETTINGS_FILE, new_map)
        self.destroy()

# ------------------- Main -------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
