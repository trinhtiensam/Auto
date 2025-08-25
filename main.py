import tkinter as tk
from tkinter import ttk, messagebox
import json, os, psutil, re, requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ================== JSON Helper ==================
PROFILE_FILE = "profiles.json"
SETTINGS_FILE = "settings.json"

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ================== Browser Scan ==================
def find_browser_profiles():
    profiles = []
    for p in psutil.process_iter(['pid','name','cmdline']):
        try:
            name = p.info['name'].lower()
            if any(browser in name for browser in ["chrome", "hidemium", "brave", "msedge"]):
                cmd = " ".join(p.info['cmdline'])
                match = re.search(r'--remote-debugging-port=(\d+)', cmd)
                if match:
                    port = match.group(1)
                    try:
                        info = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=1).json()
                        profiles.append({
                            "pid": p.info['pid'],
                            "name": p.info['name'],
                            "port": port,
                            "desc": f"{p.info['name']} (PID {p.info['pid']} | Port {port})"
                        })
                    except Exception:
                        pass
        except (psutil.AccessDenied, psutil.ZombieProcess, psutil.NoSuchProcess):
            continue
    return profiles

# ================== Main App ==================
class AutofillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Autofill Manager")
        self.root.geometry("900x600")

        # Load data
        self.profiles_data = load_json(PROFILE_FILE, [])
        self.settings = load_json(SETTINGS_FILE, {
            "account":["username","user","login"],
            "password":["password","pass","pwd"]
        })
        self.browser_profiles = []

        # ---------- Frames ----------
        self.left_frame = tk.Frame(root, padx=10, pady=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.right_frame = tk.Frame(root, padx=10, pady=10)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ---------- Left: Profile Form ----------
        tk.Label(self.left_frame, text="Thông tin hồ sơ", font=("Arial", 12, "bold")).pack(pady=5)

        self.fields = ["Tên hồ sơ","Tài khoản","Mật khẩu","Nhập lại mật khẩu","Họ tên",
                       "SĐT","Email","Năm sinh","PIN","Ngân hàng","Chi nhánh"]
        self.entries = {}
        for f in self.fields:
            tk.Label(self.left_frame, text=f).pack(anchor="w")
            e = tk.Entry(self.left_frame, width=30)
            e.pack(pady=2)
            self.entries[f] = e

        tk.Button(self.left_frame, text="Lưu hồ sơ", command=self.save_profile).pack(pady=5)

        # ---------- Right: Profile List + Browser ----------
        tk.Label(self.right_frame, text="Danh sách hồ sơ", font=("Arial", 12, "bold")).pack(pady=5)

        self.tree = ttk.Treeview(self.right_frame, columns=self.fields, show="headings", height=8)
        for f in self.fields:
            self.tree.heading(f, text=f)
            self.tree.column(f, width=100, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)

        btn_frame = tk.Frame(self.right_frame)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Xoá hồ sơ", command=self.delete_profile).grid(row=0, column=0, padx=5)

        # ---------- Browser Selection ----------
        tk.Label(self.right_frame, text="Chọn Browser Profile", font=("Arial", 12, "bold")).pack(pady=10)

        self.combo = ttk.Combobox(self.right_frame, width=80, state="readonly")
        self.combo.pack(pady=5)

        tk.Button(self.right_frame, text="🔍 Quét Browser", command=self.scan_browsers).pack(pady=5)
        tk.Button(self.right_frame, text="⚡ Autofill", command=self.autofill).pack(pady=10)

        # Load profiles list
        self.refresh_tree()

    # ---------- Profile Management ----------
    def save_profile(self):
        profile = {f: self.entries[f].get() for f in self.fields}
        if not profile["Tên hồ sơ"]:
            messagebox.showerror("Lỗi", "Tên hồ sơ không được để trống.")
            return
        self.profiles_data.append(profile)
        save_json(PROFILE_FILE, self.profiles_data)
        self.refresh_tree()
        messagebox.showinfo("OK", "Đã lưu hồ sơ.")

    def refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.profiles_data:
            self.tree.insert("", "end", values=[p.get(f,"") for f in self.fields])

    def delete_profile(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        del self.profiles_data[idx]
        save_json(PROFILE_FILE, self.profiles_data)
        self.refresh_tree()

    # ---------- Browser ----------
    def scan_browsers(self):
        self.browser_profiles = find_browser_profiles()
        if not self.browser_profiles:
            messagebox.showwarning("Không tìm thấy", "Không có browser nào đang chạy với remote-debugging-port.")
            return
        self.combo["values"] = [p["desc"] for p in self.browser_profiles]
        self.combo.current(0)

    def autofill(self):
        if not self.browser_profiles:
            messagebox.showerror("Lỗi", "Chưa chọn browser.")
            return
        if not self.profiles_data:
            messagebox.showerror("Lỗi", "Chưa có hồ sơ để điền.")
            return

        idx_browser = self.combo.current()
        port = self.browser_profiles[idx_browser]["port"]

        idx_profile = self.tree.selection()
        if not idx_profile:
            messagebox.showerror("Lỗi", "Hãy chọn một hồ sơ trong danh sách.")
            return
        profile_data = self.profiles_data[self.tree.index(idx_profile[0])]

        # Selenium attach
        options = Options()
        options.debugger_address = f"127.0.0.1:{port}"
        driver = webdriver.Chrome(options=options)

        # Điền thử username/password (mẫu)
        try:
            for keyword in self.settings.get("account", []):
                try:
                    elem = driver.find_element("xpath", f"//input[contains(@name,'{keyword}') or contains(@id,'{keyword}') or contains(@placeholder,'{keyword}')]")
                    elem.clear()
                    elem.send_keys(profile_data["Tài khoản"])
                    break
                except: pass
            for keyword in self.settings.get("password", []):
                try:
                    elem = driver.find_element("xpath", f"//input[contains(@name,'{keyword}') or contains(@id,'{keyword}') or contains(@placeholder,'{keyword}')]")
                    elem.clear()
                    elem.send_keys(profile_data["Mật khẩu"])
                    break
                except: pass
            messagebox.showinfo("OK", "Đã autofill thành công (username + password).")
        except Exception as e:
            messagebox.showerror("Lỗi Autofill", str(e))

# ================== Run ==================
if __name__ == "__main__":
    root = tk.Tk()
    app = AutofillApp(root)
    root.mainloop()
