import json, os, time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ------------------- File JSON -------------------
PROFILES_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"
HIDEMIUM_FILE = "hidemium_profiles.json"

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

# ------------------- GUI -------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Autofill Hidemium")
        self.geometry("800x500")
        
        # Load dữ liệu
        self.profiles = load_json(PROFILES_FILE, [])
        self.field_map = load_json(SETTINGS_FILE, DEFAULT_FIELD_MAP.copy())
        self.hidemium_profiles = load_json(HIDEMIUM_FILE, [])
        
        # GUI
        self.create_widgets()
        self.update_profile_table()
        self.update_hidemium_combo()

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
        # Hồ sơ
        profile_menu = tk.Menu(menubar, tearoff=0)
        profile_menu.add_command(label="Thêm/Sửa/Xóa Hồ sơ", command=self.edit_profiles)
        profile_menu.add_command(label="Import Hồ sơ", command=self.import_profiles)
        profile_menu.add_command(label="Export Hồ sơ", command=self.export_profiles)
        menubar.add_cascade(label="Hồ sơ", menu=profile_menu)
        # Cài đặt
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
    
    # ------------------- Hidemium -------------------
    def update_hidemium_combo(self):
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
            # Tab hiện tại
            driver.switch_to.window(driver.current_window_handle)
            # Dò input
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

# Chuyển key code sang tên hiển thị
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

# ------------------- Profile Editor -------------------
class ProfileEditor(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Quản lý hồ sơ")
        self.geometry("700x400")
        self.master = master
        self.create_widgets()
        self.update_table()
    
    def create_widgets(self):
        self.tree = ttk.Treeview(self, columns=("Tên hồ sơ",*DEFAULT_FIELDS), show="headings")
        for col in ["Tên hồ sơ"]+DEFAULT_FIELDS:
            self.tree.heading(col,text=col)
            self.tree.column(col,width=100)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Thêm", command=self.add_profile).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Sửa", command=self.edit_profile).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Xóa", command=self.delete_profile).pack(side="left", padx=5)
    
    def update_table(self):
        self.tree.delete(*self.tree.get_children())
        for p in self.master.profiles:
            vals = [p.get("Tên hồ sơ", "")]+[p.get(f,"") for f in DEFAULT_FIELDS]
            self.tree.insert("", "end", values=vals)
    
    def add_profile(self):
        ProfileForm(self, None)
    
    def edit_profile(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        ProfileForm(self, idx)
    
    def delete_profile(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        self.master.profiles.pop(idx)
        save_json(PROFILES_FILE, self.master.profiles)
        self.update_table()
        self.master.update_profile_table()

# ------------------- Profile Form -------------------
class ProfileForm(tk.Toplevel):
    def __init__(self, master, idx):
        super().__init__(master)
        self.title("Thêm/Sửa hồ sơ")
        self.geometry("500x500")
        self.master = master
        self.idx = idx
        self.entries = {}
        self.create_widgets()
        if idx is not None:
            self.load_profile()
    
    def create_widgets(self):
        frm = ttk.Frame(self)
        frm.pack(padx=10, pady=10, fill="both", expand=True)
        ttk.Label(frm,text="Tên hồ sơ:").grid(row=0,column=0,sticky="e")
        self.name_var = tk.StringVar()
        ttk.Entry(frm,textvariable=self.name_var).grid(row=0,column=1,sticky="w")
        for i, field in enumerate(DEFAULT_FIELDS):
            ttk.Label(frm,text=field+":").grid(row=i+1,column=0,sticky="e")
            var = tk.StringVar()
            ttk.Entry(frm,textvariable=var).grid(row=i+1,column=1,sticky="w")
            self.entries[field] = var
        ttk.Button(frm,text="Lưu", command=self.save).grid(row=len(DEFAULT_FIELDS)+1,column=0,columnspan=2,pady=10)
    
    def load_profile(self):
        profile = self.master.master.profiles[self.idx]
        self.name_var.set(profile.get("Tên hồ sơ",""))
        for field in DEFAULT_FIELDS:
            self.entries[field].set(profile.get(field,""))
    
    def save(self):
        data = {"Tên hồ sơ": self.name_var.get()}
        for field in DEFAULT_FIELDS:
            data[field] = self.entries[field].get()
        if self.idx is None:
            self.master.master.profiles.append(data)
        else:
            self.master.master.profiles[self.idx] = data
        save_json(PROFILES_FILE, self.master.master.profiles)
        self.master.update_table()
        self.master.master.update_profile_table()
        self.destroy()

# ------------------- Field Settings Editor -------------------
class FieldSettingsEditor(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Cài đặt nhận dạng trường")
        self.geometry("600x400")
        self.master = master
        self.field_map = load_json(SETTINGS_FILE, DEFAULT_FIELD_MAP.copy())
        self.create_widgets()
    
    def create_widgets(self):
        self.tree = ttk.Treeview(self, columns=("field","keywords"), show="headings")
        self.tree.heading("field", text="Trường")
        self.tree.heading("keywords", text="Từ khóa (phân tách bằng ,)")
        self.tree.column("field", width=150)
        self.tree.column("keywords", width=400)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        for field, keywords in self.field_map.items():
            self.tree.insert("", "end", values=(field,", ".join(keywords)))
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Lưu thay đổi", command=self.save_changes).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Khôi phục mặc định", command=self.reset_default).pack(side="left", padx=5)
    
    def save_changes(self):
        for item in self.tree.get_children():
            field, keywords = self.tree.item(item,"values")
            self.field_map[field] = [k.strip() for k in keywords.split(",") if k.strip()]
        save_json(SETTINGS_FILE, self.field_map)
        self.master.field_map = self.field_map
        messagebox.showinfo("Lưu","Đã lưu các từ khóa nhận dạng mới.")
    
    def reset_default(self):
        self.field_map = DEFAULT_FIELD_MAP.copy()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for field, keywords in self.field_map.items():
            self.tree.insert("", "end", values=(field,", ".join(keywords)))
        save_json(SETTINGS_FILE, self.field_map)
        self.master.field_map = self.field_map
        messagebox.showinfo("Khôi phục","Đã khôi phục các từ khóa mặc định.")

# ------------------- Chạy ứng dụng -------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
