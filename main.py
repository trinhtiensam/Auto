import os, json, re, psutil, requests
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.simpledialog import askstring
from PIL import Image, ImageTk
import win32gui, win32process, win32con, win32ui

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ------------------- Helpers -------------------
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_window_title_from_pid(pid):
    titles = []
    def callback(hwnd, _):
        tid, current_pid = win32process.GetWindowThreadProcessId(hwnd)
        if current_pid == pid and win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                titles.append(title)
    win32gui.EnumWindows(callback, None)
    return titles[0] if titles else ""

def get_icon_from_exe(exe_path, size=24):
    try:
        large, small = win32gui.ExtractIconEx(exe_path, 0)
        hicon = small[0] if small else large[0]
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, size, size)
        hdc = hdc.CreateCompatibleDC()
        hdc.SelectObject(hbmp)
        win32gui.DrawIconEx(hdc.GetHandleOutput(), 0, 0, hicon, size, size, 0, None, win32con.DI_NORMAL)
        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)
        from PIL import Image
        img = Image.frombuffer("RGB",(bmpinfo["bmWidth"],bmpinfo["bmHeight"]),bmpstr,"raw","BGRX",0,1)
        return ImageTk.PhotoImage(img)
    except:
        return None

def find_browser_profiles():
    profiles = []
    for p in psutil.process_iter(['pid','name','exe','cmdline']):
        try:
            name = p.info['name'].lower()
            if any(b in name for b in ["chrome","hidemium","brave","msedge"]):
                cmd = " ".join(p.info['cmdline'])
                m = re.search(r'--remote-debugging-port=(\d+)', cmd)
                if m:
                    port = m.group(1)
                    try:
                        requests.get(f"http://127.0.0.1:{port}/json/version",timeout=1)
                        title = get_window_title_from_pid(p.info['pid'])
                        icon = get_icon_from_exe(p.info['exe'])
                        profiles.append({
                            "pid": p.info['pid'],
                            "name": p.info['name'],
                            "title": title,
                            "icon": icon,
                            "port": port
                        })
                    except: pass
        except: continue
    return profiles

# ------------------- Main App -------------------
class AutoFillApp:
    def __init__(self, root):
        self.root = root
        root.title("Autofill App")
        root.geometry("900x500")

        # Load data
        self.profiles_data = load_json("profiles.json", [])
        self.settings = load_json("settings.json", {
            "Tên hồ sơ":["profile_name"],
            "Tài khoản":["username","user","login"],
            "Mật khẩu":["password","pass","pwd"],
            "Nhập lại mật khẩu":["confirm","retype"],
            "Họ tên":["fullname","name"],
            "SĐT":["phone","mobile"],
            "Email":["email","mail"],
            "Năm sinh":["dob","birth"],
            "PIN":["pin","security"],
            "Ngân hàng":["bank"],
            "Chi nhánh":["branch"]
        })

        # UI layout
        left = ttk.Frame(root); left.pack(side="left", fill="y", padx=5,pady=5)
        right = ttk.Frame(root); right.pack(side="right", expand=True, fill="both", padx=5,pady=5)

        ttk.Label(left,text="Browser đang chạy:").pack(anchor="w")
        self.browser_tree = ttk.Treeview(left, show="tree", height=8)
        self.browser_tree.pack(fill="x", pady=3)
        ttk.Button(left,text="Quét Browser",command=self.scan_browsers).pack(fill="x")

        ttk.Label(left,text="Hồ sơ:").pack(anchor="w",pady=5)
        self.tree = ttk.Treeview(left, columns=("Tên hồ sơ","Tài khoản","Email"), show="headings", height=15)
        for col in ("Tên hồ sơ","Tài khoản","Email"): self.tree.heading(col,text=col)
        self.tree.pack(fill="both", expand=True)
        self.refresh_profiles()

        btns = ttk.Frame(left); btns.pack(fill="x")
        ttk.Button(btns,text="Thêm",command=self.add_profile).pack(side="left",expand=True,fill="x")
        ttk.Button(btns,text="Xóa",command=self.del_profile).pack(side="left",expand=True,fill="x")
        ttk.Button(btns,text="Autofill",command=self.autofill).pack(side="left",expand=True,fill="x")

    # ----- Profiles -----
    def refresh_profiles(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for p in self.profiles_data:
            self.tree.insert("", "end", values=(p.get("Tên hồ sơ",""), p.get("Tài khoản",""), p.get("Email","")))

    def add_profile(self):
        profile = {}
        fields = ["Tên hồ sơ","Tài khoản","Mật khẩu","Nhập lại mật khẩu","Họ tên","SĐT","Email","Năm sinh","PIN","Ngân hàng","Chi nhánh"]
        for f in fields:
            val = askstring("Nhập", f)
            if val is None: return
            profile[f]=val
        self.profiles_data.append(profile)
        save_json("profiles.json", self.profiles_data)
        self.refresh_profiles()

    def del_profile(self):
        sel=self.tree.selection()
        if not sel: return
        idx=self.tree.index(sel[0])
        del self.profiles_data[idx]
        save_json("profiles.json", self.profiles_data)
        self.refresh_profiles()

    # ----- Browser -----
    def scan_browsers(self):
        self.browser_tree.delete(*self.browser_tree.get_children())
        self.browser_profiles=find_browser_profiles()
        for i,p in enumerate(self.browser_profiles):
            self.browser_tree.insert("", "end", iid=str(i), text=f"{p['name']} | {p['title']} (port {p['port']})", image=p["icon"])

    # ----- Autofill -----
    def autofill(self):
        if not self.browser_tree.selection():
            messagebox.showerror("Lỗi","Chưa chọn browser"); return
        if not self.tree.selection():
            messagebox.showerror("Lỗi","Chưa chọn hồ sơ"); return

        bidx=int(self.browser_tree.selection()[0])
        port=self.browser_profiles[bidx]["port"]
        pidx=self.tree.index(self.tree.selection()[0])
        profile_data=self.profiles_data[pidx]

        options=Options(); options.debugger_address=f"127.0.0.1:{port}"
        driver=webdriver.Chrome(options=options)

        filled,not_found=[],[]
        for field,keywords in self.settings.items():
            value=profile_data.get(field,"")
            if not value: continue
            success=False
            for k in keywords:
                try:
                    elem=driver.find_element("xpath",
                        f"//input[contains(@name,'{k}') or contains(@id,'{k}') or "
                        f"contains(@placeholder,'{k}') or contains(@aria-label,'{k}')]")
                    elem.clear(); elem.send_keys(value)
                    filled.append(field); success=True; break
                except: continue
            if not success: not_found.append(field)

        msg=f"✅ Đã điền: {', '.join(filled)}"
        if not_found: msg+=f"\n⚠️ Không tìm thấy: {', '.join(not_found)}"
        messagebox.showinfo("Kết quả Autofill", msg)

# ------------------- Run -------------------
if __name__=="__main__":
    root=tk.Tk()
    app=AutoFillApp(root)
    root.mainloop()
