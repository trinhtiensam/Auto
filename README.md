# Autofill App

Ứng dụng Python (Tkinter + PyAutoGUI) dùng để **tự động điền dữ liệu vào ứng dụng khác** (form web, Notepad...).  
Có thể chọn nhiều profile từ file `profiles.json`.

---

## 🚀 Cách chạy trực tiếp (Windows EXE)
1. Vào tab [Releases](../../releases) của repo này.
2. Tải file `autofill_app.exe` trong phần **Assets**.
3. Đặt `profiles.json` cùng thư mục với `autofill_app.exe`.
4. Double-click file `.exe` để chạy.

---

## 🛠 Cách build từ source
### 1. Chuẩn bị
Cài Python 3.8+ và pip. Sau đó:
```bash
git clone https://github.com/<your-username>/autofill-app.git
cd autofill-app
pip install -r requirements.txt
