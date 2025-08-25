import json
import time
import pyautogui

# Load profiles
with open("profiles.json", "r", encoding="utf-8") as f:
    profiles = json.load(f)

print("=== AutoFillApp Python Demo ===")
for i, profile in enumerate(profiles, 1):
    print(f"{i}. {profile['Name']} ({profile['Email']})")

choice = int(input("Chọn số profile: ")) - 1
data = profiles[choice]

print("Bạn có 5 giây để chọn cửa sổ cần điền...")
time.sleep(5)

for key, value in data.items():
    print(f"Typing {key}...")
    pyautogui.typewrite(value)
    pyautogui.press("tab")

print("Hoàn tất!")
