# autofill_app.py
# Ứng dụng Autofill + Trình quản lý hồ sơ (1 file)
# - Tất cả giao diện tiếng Việt
# - 10 trường: Tài khoản, Mật khẩu, Nhập lại mật khẩu, Họ tên, Số điện thoại, Email, Ngày sinh, PIN, Bank, Chi nhánh
# - Menu Hồ sơ: Chỉnh sửa, Xuất, Nhập (nhập = gộp thêm, tránh trùng tên)
# - Hiển thị bảng 2 cột (Tên trường - Giá trị) readonly
# - Nút Chạy Autofill

import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui

try:
    import pygetwindow as gw
    HAVE_PYGETWINDOW = True
except Exception:
    HAVE_PYGETWINDOW = False

APP_TITLE = 'Autofill - Ứng dụng tự động điền'

FIELDS = [
    "Tài khoản",
    "Mật khẩu",
    "Nhập lại mật khẩu",
    "Họ tên",
    "Số điện thoại",
    "Email",
    "Ngày sinh",
    "PIN",
    "Bank",
    "Chi nhánh"
]

DEFAULT_PROFILES_PATH = 'profiles.json'

# -------------------------
# I/O
# -------------------------

def load_profiles(path=DEFAULT_PROFILES_PATH):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError('File JSON phải chứa một danh sách các hồ sơ')
        return data
    except FileNotFoundError:
        return []

def save_profiles(profiles, path=DEFAULT_PROFILES_PATH):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

# -------------------------
# Autofill logic
# -------------------------

def autofill_profile(profile, press_tab=True, interval=0.02):
    for i, field in enumerate(FIELDS):
        val = profile.get(field, "")
        # Ensure string
        pyautogui.write(str(val), interval=interval)
        if press_tab and i < len(FIELDS) - 1:
            pyautogui.press('tab')
            time.sleep(0.05)

def run_autofill(profiles, mode, countdown, activate_title, interval, press_tab=True):
    # mode: 'countdown' or 'title'
    if mode == 'title' and HAVE_PYGETWINDOW:
        try:
            wins = gw.getWindowsWithTitle(activate_title)
            if not wins:
                raise Exception('Không tìm thấy cửa sổ có tiêu đề phù hợp')
            wins[0].activate()
            time.sleep(0.3)
        except Exception as e:
            print('Không thể kích hoạt cửa sổ theo tiêu đề:', e)
            mode = 'countdown'

    if mode == 'countdown':
        for i in range(countdown, 0, -1):
            print(f'Bắt đầu trong {i} giây...')
            time.sleep(1)

    for p in profiles:
        print('Đang điền hồ sơ:', p.get('name', '(không tên)'))
        autofill_profile(p, press_tab=press_tab, interval=interval)
        time.sleep(0.3)

# -------------------------
# Helpers: merge import
# -------------------------

def unique_name(existing_names, name):
    if name not in existing_names:
        return name
    # add suffix (2), (3), ...
    i = 2
    while True:
        cand = f"{name} ({i})"
        if cand not in existing_names:
            return cand
        i += 1

def merge_profiles(existing, new_list):
    # existing, new_list are lists of profile dicts
    existing_names = {p.get('name','') for p in existing}
    added = 0
    for p in new_list:
        name = p.get('name','')
        if not name:
            # generate a fallback name
            name = 'Hồ sơ'
        if name in existing_names:
            new_name = unique_name(existing_names, name)
            p['name'] = new_name
        existing.append(p)
        existing_names.add(p['name'])
        added += 1
    return added

# -------------------------
# GUI: Profile Editor (Tiếng Việt)
# -------------------------

class ProfileEditor(tk.Toplevel):
    def __init__(self, master, profiles, on_save_callback):
        super().__init__(master)
        self.title('Chỉnh sửa hồ sơ')
        self.geometry('700x520')
        self.profiles = profiles
        self.on_save_callback = on_save_callback
        self.selected_index = None
        self.create_widgets()

    def create_widgets(self):
        self.columnconfigure(1, weight=1)

        left = ttk.Frame(self, padding=8)
        left.pack(side='left', fill='y')
        right = ttk.Frame(self, padding=8)
        right.pack(side='right', fill='both', expand=True)

        ttk.Label(left, text='Danh sách hồ sơ').pack(anchor='w')
        self.listbox = tk.Listbox(left, width=30)
        self.listbox.pack(fill='y', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text='Thêm', command=self.add_profile).pack(fill='x', pady=2)
        ttk.Button(btn_frame, text='Xóa', command=self.delete_profile).pack(fill='x', pady=2)

        # Right: form fields
        self.fields_vars = {}
        row = 0
        ttk.Label(right, text='Tên hồ sơ').grid(row=row, column=0, sticky='e', padx=4, pady=4)
        self.fields_vars['name'] = tk.StringVar()
        ttk.Entry(right, textvariable=self.fields_vars['name'], width=40).grid(row=row, column=1, sticky='w')
        row += 1

        for f in FIELDS:
            ttk.Label(right, text=f).grid(row=row, column=0, sticky='e', padx=4, pady=4)
            var = tk.StringVar()
            ttk.Entry(right, textvariable=var, width=40).grid(row=row, column=1, sticky='w')
            self.fields_vars[f] = var
            row += 1

        action_frame = ttk.Frame(right)
        action_frame.grid(row=row, column=0, columnspan=2, pady=8)
        ttk.Button(action_frame, text='Lưu thay đổi', command=self.save_changes).pack(side='left', padx=4)
        ttk.Button(action_frame, text='Lưu ra file...', command=self.export_profiles).pack(side='left', padx=4)
        ttk.Button(action_frame, text='Nhập từ file...', command=self.import_profiles).pack(side='left', padx=4)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, 'end')
        for p in self.profiles:
            self.listbox.insert('end', p.get('name','(không tên)'))

    def on_select(self, event):
        try:
            idx = self.listbox.curselection()[0]
            self.selected_index = idx
            p = self.profiles[idx]
            self.fields_vars['name'].set(p.get('name',''))
            for f in FIELDS:
                self.fields_vars[f].set(p.get(f,''))
        except Exception:
            pass

    def add_profile(self):
        new = { 'name': 'Hồ sơ mới' }
        for f in FIELDS:
            new[f] = ''
        self.profiles.append(new)
        self.refresh_listbox()
        self.listbox.select_set(len(self.profiles)-1)
        self.on_select(None)

    def delete_profile(self):
        if self.selected_index is None:
            messagebox.showinfo('Chú ý', 'Vui lòng chọn hồ sơ để xóa.')
            return
        confirm = messagebox.askyesno('Xóa hồ sơ', 'Bạn có muốn xóa hồ sơ đã chọn?')
        if confirm:
            del self.profiles[self.selected_index]
            self.selected_index = None
            save_profiles(self.profiles)
            self.refresh_listbox()
            self.on_save_callback(self.profiles)

    def save_changes(self):
        if self.selected_index is None:
            messagebox.showinfo('Chú ý', 'Vui lòng chọn hồ sơ để lưu.')
            return
        p = self.profiles[self.selected_index]
        p['name'] = self.fields_vars['name'].get()
        for f in FIELDS:
            p[f] = self.fields_vars[f].get()
        save_profiles(self.profiles)
        self.refresh_listbox()
        self.on_save_callback(self.profiles)
        messagebox.showinfo('Lưu', 'Đã lưu thay đổi vào profiles.json')

    def export_profiles(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')], title='Lưu hồ sơ ra file')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
            messagebox.showinfo('Xuất', f'Đã lưu {len(self.profiles)} hồ sơ ra {path}')
        except Exception as e:
            messagebox.showerror('Lỗi', f'Không thể lưu file: {e}')

    def import_profiles(self):
        path = filedialog.askopenfilename(filetypes=[('JSON','*.json')], title='Chọn file hồ sơ để nhập')
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                new_list = json.load(f)
            if not isinstance(new_list, list):
                raise ValueError('File không hợp lệ: phải là danh sách hồ sơ')
            added = merge_profiles(self.profiles, new_list)
            save_profiles(self.profiles)
            self.refresh_listbox()
            self.on_save_callback(self.profiles)
            messagebox.showinfo('Nhập', f'✅ Đã nhập thêm {added} hồ sơ từ file thành công.')
        except Exception as e:
            messagebox.showerror('Lỗi', f'Không thể nhập file: {e}')

# -------------------------
# GUI: Main App (Tiếng Việt)
# -------------------------

class AutofillApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('760x520')
        self.profiles = load_profiles()
        self.create_menu()
        self.create_widgets()

    def create_menu(self):
        menubar = tk.Menu(self)
        hs_menu = tk.Menu(menubar, tearoff=0)
        hs_menu.add_command(label='Chỉnh sửa hồ sơ', command=self.open_editor)
        hs_menu.add_command(label='Xuất hồ sơ', command=self.export_profiles)
        hs_menu.add_command(label='Nhập hồ sơ (gộp thêm)', command=self.import_profiles)
        menubar.add_cascade(label='Hồ sơ', menu=hs_menu)
        self.config(menu=menubar)

    def create_widgets(self):
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill='x')

        ttk.Label(top_frame, text='Chọn hồ sơ:').pack(side='left')
        self.selected_profile = tk.StringVar()
        self.profile_combo = ttk.Combobox(top_frame, textvariable=self.selected_profile, state='readonly', width=50)
        self.profile_combo.pack(side='left', padx=8)
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_selected)

        ttk.Button(top_frame, text='Chạy Autofill', command=self.start_autofill, width=20).pack(side='right')

        # Options row
        opt_frame = ttk.Frame(self, padding=8)
        opt_frame.pack(fill='x')
        self.start_mode = tk.StringVar(value='countdown')
        ttk.Radiobutton(opt_frame, text='Đếm ngược (tự click vào cửa sổ đích)', variable=self.start_mode, value='countdown').grid(row=0, column=0, sticky='w')
        ttk.Radiobutton(opt_frame, text='Kích hoạt cửa sổ theo tiêu đề (yêu cầu pygetwindow)', variable=self.start_mode, value='title').grid(row=0, column=1, sticky='w')

        ttk.Label(opt_frame, text='Đếm ngược (s):').grid(row=1, column=0, sticky='e')
        self.countdown_var = tk.IntVar(value=5)
        ttk.Entry(opt_frame, textvariable=self.countdown_var, width=6).grid(row=1, column=1, sticky='w')

        ttk.Label(opt_frame, text='Tiêu đề cửa sổ:').grid(row=2, column=0, sticky='e')
        self.title_var = tk.StringVar()
        ttk.Entry(opt_frame, textvariable=self.title_var, width=40).grid(row=2, column=1, sticky='w')

        ttk.Label(opt_frame, text='Khoảng cách gõ (s/ký tự):').grid(row=3, column=0, sticky='e')
        self.interval_var = tk.DoubleVar(value=0.02)
        ttk.Entry(opt_frame, textvariable=self.interval_var, width=6).grid(row=3, column=1, sticky='w')

        self.press_tab_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text='Nhấn TAB sau mỗi trường', variable=self.press_tab_var).grid(row=4, column=0, sticky='w')

        # Grid display of fields (2 columns)
        grid_frame = ttk.Frame(self, padding=10)
        grid_frame.pack(fill='both', expand=True)

        self.field_vars = {}
        for i, f in enumerate(FIELDS):
            ttk.Label(grid_frame, text=f+':', width=20, anchor='e').grid(row=i, column=0, padx=6, pady=4)
            var = tk.StringVar()
            ent = ttk.Entry(grid_frame, textvariable=var, width=60, state='readonly')
            ent.grid(row=i, column=1, padx=6, pady=4, sticky='w')
            self.field_vars[f] = var

        # Status bar
        self.status_var = tk.StringVar(value='Sẵn sàng')
        ttk.Label(self, textvariable=self.status_var).pack(fill='x', padx=8, pady=6)

        self.refresh_profile_list()

    def refresh_profile_list(self):
        names = [p.get('name','(không tên)') for p in self.profiles]
        self.profile_combo['values'] = names
        if names:
            self.profile_combo.current(0)
            self.load_profile_to_grid(0)

    def on_profile_selected(self, event):
        idx = self.profile_combo.current()
        if idx >= 0:
            self.load_profile_to_grid(idx)

    def load_profile_to_grid(self, idx):
        p = self.profiles[idx]
        for f in FIELDS:
            self.field_vars[f].set(p.get(f,''))
        self.status_var.set(f'Đang hiển thị: {p.get("name","(không tên)")}")')

    def open_editor(self):
        editor = ProfileEditor(self, self.profiles, self.on_profiles_saved)
        editor.grab_set()

    def on_profiles_saved(self, profiles):
        self.profiles = profiles
        save_profiles(self.profiles)
        self.refresh_profile_list()

    def export_profiles(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')], title='Xuất hồ sơ ra file')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
            messagebox.showinfo('Xuất hồ sơ', f'Đã xuất {len(self.profiles)} hồ sơ ra {path}')
        except Exception as e:
            messagebox.showerror('Lỗi', f'Không thể lưu file: {e}')

    def import_profiles(self):
        path = filedialog.askopenfilename(filetypes=[('JSON','*.json')], title='Chọn file hồ sơ để nhập (gộp thêm)')
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                new_list = json.load(f)
            if not isinstance(new_list, list):
                raise ValueError('File không hợp lệ: phải là danh sách hồ sơ')
            added = merge_profiles(self.profiles, new_list)
            save_profiles(self.profiles)
            self.refresh_profile_list()
            messagebox.showinfo('Nhập hồ sơ', f'✅ Đã nhập thêm {added} hồ sơ từ file thành công.')
        except Exception as e:
            messagebox.showerror('Lỗi', f'Không thể nhập file: {e}')

    def start_autofill(self):
        idx = self.profile_combo.current()
        if idx < 0:
            messagebox.showinfo('Chú ý', 'Vui lòng chọn ít nhất một hồ sơ để chạy.')
            return
        # allow selecting multiple? For simplicity, run single selected profile
        profiles_to_fill = [self.profiles[idx]]
        mode = self.start_mode.get()
        countdown = int(self.countdown_var.get())
        title = self.title_var.get()
        interval = float(self.interval_var.get())
        press_tab = self.press_tab_var.get()

        self.status_var.set('Đang bắt đầu autofill...')
        worker = threading.Thread(target=self._worker_thread, args=(profiles_to_fill, mode, countdown, title, interval, press_tab), daemon=True)
        worker.start()

    def _worker_thread(self, profiles_to_fill, mode, countdown, title, interval, press_tab):
        try:
            run_autofill(profiles_to_fill, mode, countdown, title, interval, press_tab)
            self.status_var.set('Hoàn tất autofill')
        except Exception as e:
            self.status_var.set(f'Lỗi: {e}')

# -------------------------
# Main
# -------------------------

if __name__ == '__main__':
    app = AutofillApp()
    app.mainloop()

# ---------
# GHI CHÚ
# ---------
# - Đảm bảo file profiles.json nằm cùng thư mục (app sẽ tự tạo nếu không có). 
# - Để dừng khẩn cấp khi pyautogui đang gõ: di chuyển chuột lên góc trên-trái màn hình để kích hoạt PyAutoGUI fail-safe.
# - Nếu muốn autofill nhiều hồ sơ liên tục, có thể mở rộng giao diện để chọn nhiều. Hiện tại nút Chạy chỉ chạy hồ sơ đang chọn trong combobox.
# - File JSON mẫu nên có cấu trúc: danh sách các object với key 'name' và các key trùng với FIELDS.

# Ví dụ profiles.json:
# [
#   {
#     "name": "User1",
#     "Tài khoản": "username1",
#     "Mật khẩu": "password123",
#     "Nhập lại mật khẩu": "password123",
#     "Họ tên": "Nguyen Van A",
#     "Số điện thoại": "0123456789",
#     "Email": "a@example.com",
#     "Ngày sinh": "01/01/2000",
#     "PIN": "1234",
#     "Bank": "VCB",
#     "Chi nhánh": "Hanoi"
#   }
# ]
