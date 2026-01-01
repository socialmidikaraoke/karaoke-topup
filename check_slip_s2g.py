import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- 1. Key ที่ถูกต้อง (แก้ไขตัวอักษรผิดจาก l เป็น I แล้ว) ---
# สังเกตตรง ...OWCIZsJ... ครับ
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWCIZsJg0XA="

def check_slip_slip2go(image_path):
    print(f"🔍 เริ่มตรวจสอบรูป: {image_path}")

    # --- ส่วนอ่าน QR Code ---
    img = cv2.imread(image_path)
    if img is None: return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}
    
    decoded_objects = decode(img)
    if not decoded_objects: return {"success": False, "message": "ไม่พบ QR Code ในรูป"}
    
    qr_payload = decoded_objects[0].data.decode('utf-8')
    print(f"✅ อ่าน QR สำเร็จ")
    
    # --- 2. URL ที่ถูกต้อง (connect.slip2go.com) ---
    TARGET_URL = "https://connect.slip2go.com/api/verify-slip/qr-code/info"

    # --- 3. ลองส่ง Key ทั้ง 2 แบบ (กันพลาด) ---
    auth_options = [
        # แบบที่ 1: มี Bearer (ตามคู่มือ Curl) - น่าจะใช่อันนี้
        f'Bearer {API_KEY}',
        # แบบที่ 2: ใส่ Key เพียวๆ
        API_KEY
    ]

    print(f"🚀 กำลังเชื่อมต่อ: {TARGET_URL}")

    for auth_value in auth_options:
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': auth_value
            }
            body = {"payload": {"qrCode": qr_payload}}

            response = requests.post(TARGET_URL, headers=headers, json=body, timeout=10)
            
            # ถ้าผ่าน (200)
            if response.status_code == 200:
                result = response.json()
                if 'data' in result:
                    d = result['data']
                    return {
                        "success": True, 
                        "sender": d.get('sender', {}).get('displayName', 'ไม่ระบุ'),
                        "amount": d.get('amount', 0),
                        "date": d.get('transDate', '')
                    }
                else:
                    return {"success": True, "data": result}
            
            elif response.status_code == 401:
                # ถ้าแบบนี้ไม่ผ่าน ให้วนลูปไปลองแบบถัดไปเงียบๆ
                continue

        except Exception as e:
            continue

    # ถ้าลองหมดแล้วยัง 401
    return {"success": False, "message": "เชื่อมต่อได้แต่ Key ผิด (ตรวจสอบ IP Whitelist ในเว็บ หรือกดสร้าง Key ใหม่)"}
