import cv2
from pyzbar.pyzbar import decode
import requests
import json

# Key ที่ถูกต้อง
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWCIZsJg0XA="

def check_slip_slip2go(image_path):
    img = cv2.imread(image_path)
    if img is None: return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}
    
    decoded_objects = decode(img)
    if not decoded_objects: return {"success": False, "message": "ไม่พบ QR Code"}
    
    qr_payload = decoded_objects[0].data.decode('utf-8')
    
    # URL ที่ถูกต้อง (สำหรับการสแกน QR)
    TARGET_URL = "https://connect.slip2go.com/api/verify-slip/qr-code/info"

    try:
        # ใช้ Key แบบ Bearer
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }
        body = {"payload": {"qrCode": qr_payload}}

        response = requests.post(TARGET_URL, headers=headers, json=body, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            # --- จุดสำคัญ: ส่งข้อมูลดิบกลับไปดูเลย ---
            return {
                "success": True,
                "raw_data": result # ส่งกลับไปทั้งก้อน เดี๋ยวไปแกะที่หน้าเว็บ
            }
        else:
            return {"success": False, "message": f"Error {response.status_code}: {response.text}"}

    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}
