import json
import time
import threading
import tkinter as tk
from tkinter import messagebox
import pyautogui

# Load profiles
with open("profiles.json", "r", encoding="utf-8") as f:
    profiles = json.load(f)

# Hàm autofill
def autofill(profile):
    messagebox.showinfo("Thông báo", "Bạn có 5 giây để chọn cửa sổ cần điền!")
    time.sleep(5)
    for key, value in profile.items():
        pyautogui.typewrite(value)
        pyautogui.press("tab")
    messagebox.showinfo("Hoàn tất", "Đã điền xong thông tin!")

# Hàm xử lý khi bấm nút
def run_autofill():
    try:
        idx = listbox.curselection()[0]
    except IndexError:
        messagebox.showerror("Lỗi", "Bạn chưa chọn profile!")
        return
    profile = profiles[idx]
    threading.Thread(target=autofill, args=(profile,), daemon=True).start()

# GUI
root = tk.Tk()
root.title("AutoFillApp (Python GUI)")
root.geometry("400x300")

label = tk.Label(root, text="Chọn profile để điền:", font=("Arial", 12))
label.pack(pady=10)

listbox = tk.Listbox(root, font=("Arial", 11), height=6)
for p in profiles:
    listbox.insert(tk.END, f"{p['Name']} - {p['Email']}")
listbox.pack(pady=10, fill=tk.BOTH, expand=True)

button = tk.Button(root, text="Điền vào ứng dụng", font=("Arial", 12), bg="#4CAF50", fg="white", command=run_autofill)
button.pack(pady=10)

root.mainloop()
