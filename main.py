import tkinter as tk
from tkinter import ttk, messagebox
import json, os
from selenium import webdriver
from selenium.webdriver.common.by import By

PROFILE_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"

# ---------------- JSON Utils ----------------
def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_profiles(profiles):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4, ensure_ascii=False)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # mặc định tìm theo các thuộc tính cơ bản
    return {"keywords": ["username", "email", "phone", "password"]}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

# ---------------- Selenium ----------------
def connect_hidemium():
    try:
        options = webdriver.ChromeOptions()
        options.debugger_address = "127.0.0.1:9222"
        driver = webdriver.Chrome(options=options)
        messagebox.showinfo("Thành công", f"Đã kết nối tới tab: {driver.title}")
        return driver
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không kết nối được Hidemium:\n{e}")
        return None

def autofill(driver, profile):
    if not driver: return
    settings = load_settings()
    keywords = settings.get("keywords", [])
    try:
        for key, value in profile.items():
            if not value: 
                continue
            for kw in keywords:
                try:
                    elem = driver.find_element(By.XPATH, f"//input[contains(@name,'{kw}') or contains(@id,'{kw}') or contains(@placeholder,'{kw}') or contains(@aria-label,'{kw}')]")
                    elem.clear()
                    elem.send_keys(value)
                    break
                except:
                    continue
        messagebox.showinfo("OK", "Autofill thành công!")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Autofill lỗi: {e}")

# ---------------- GUI ----------------
class ProfileApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quản lý hồ sơ & Autofill Hidemium")
        self.driver = None

        # Form nhập
        form_frame = tk.Frame(root)
        form_frame.pack(pady=5)

        tk.Label(form_frame, text="Tên hồ sơ").grid(row=0, column=0, sticky="w")
        self.entry_name = tk.Entry(form_frame)
        self.entry_name.grid(row=0, column=1)

        tk.Label(form_frame, text="Email").grid(row=1, column=0, sticky="w")
        self.entry_email = tk.Entry(form_frame)
        self.entry_email.grid(row=1, column=1)

        tk.Label(form_frame, text="Mật khẩu").grid(row=2, column=0, sticky="w")
        self.entry_password = tk.Entry(form_frame, show="*")
        self.entry_password.grid(row=2, column=1)

        tk.Button(form_frame, text="Lưu hồ sơ", command=self.add_profile).grid(row=3, column=0, columnspan=2, pady=5)

        # Bảng hồ sơ
        self.table = ttk.Treeview(root, columns=("Tên", "Email"), show="headings", height=6)
        self.table.heading("Tên", text="Tên hồ sơ")
        self.table.heading("Email", text="Email")
        self.table.bind("<Double-1>", self.load_selected_profile)
        self.table.pack(fill="x", padx=5, pady=5)

        # Nút hành động
        action_frame = tk.Frame(root)
        action_frame.pack(pady=5)

        tk.Button(action_frame, text="Kết nối Hidemium", command=self.connect_driver).grid(row=0, column=0, padx=5)
        tk.Button(action_frame, text="Autofill", command=self.run_autofill).grid(row=0, column=1, padx=5)
        tk.Button(action_frame, text="Xóa hồ sơ", command=self.delete_profile).grid(row=0, column=2, padx=5)

        self.refresh_table()

    # ---------- Profile funcs ----------
    def add_profile(self):
        name = self.entry_name.get().strip()
        email = self.entry_email.get().strip()
        password = self.entry_password.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên hồ sơ!")
            return
        profiles = load_profiles()
        # Nếu đã có tên thì update
        for p in profiles:
            if p["name"] == name:
                p.update({"email": email, "password": password})
                break
        else:
            profiles.append({"name": name, "email": email, "password": password})
        save_profiles(profiles)
        self.refresh_table()

    def refresh_table(self):
        for row in self.table.get_children():
            self.table.delete(row)
        for p in load_profiles():
            self.table.insert("", "end", values=(p["name"], p.get("email","")))

    def load_selected_profile(self, event):
        selected = self.table.focus()
        if not selected: return
        values = self.table.item(selected, "values")
        profiles = load_profiles()
        for p in profiles:
            if p["name"] == values[0]:
                self.entry_name.delete(0, tk.END)
                self.entry_name.insert(0, p["name"])
                self.entry_email.delete(0, tk.END)
                self.entry_email.insert(0, p.get("email",""))
                self.entry_password.delete(0, tk.END)
                self.entry_password.insert(0, p.get("password",""))
                break

    def delete_profile(self):
        selected = self.table.focus()
        if not selected: return
        values = self.table.item(selected, "values")
        profiles = load_profiles()
        profiles = [p for p in profiles if p["name"] != values[0]]
        save_profiles(profiles)
        self.refresh_table()

    # ---------- Selenium funcs ----------
    def connect_driver(self):
        self.driver = connect_hidemium()

    def run_autofill(self):
        if not self.driver:
            messagebox.showwarning("Chưa kết nối", "Bạn cần kết nối Hidemium trước!")
            return
        name = self.entry_name.get().strip()
        profiles = load_profiles()
        for p in profiles:
            if p["name"] == name:
                autofill(self.driver, p)
                return
        messagebox.showerror("Lỗi", "Không tìm thấy hồ sơ!")

# ---------------- Main ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ProfileApp(root)
    root.mainloop()
