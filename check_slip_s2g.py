import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- 1. Key ของคุณ (ใช้ตัวที่ถูกต้อง) ---
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA="

def check_slip_slip2go(image_path):
    # อ่าน QR Code
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "ไม่พบ QR Code ในรูป"}

    qr_payload = decoded_objects[0].data.decode('utf-8')
    
    # --- 2. ตั้งค่า URL ที่ถูกต้อง (ใช้เว็บหลัก ตัด api. ออก) ---
    # จากข้อมูลล่าสุด นี่คือ URL ที่ถูกต้องที่สุดครับ
    TARGET_URL = "https://slip2go.com/api/verify-slip/qr-code/info"

    # --- 3. ตั้งค่า Header และ Body (ตามโค้ด Curl เป๊ะๆ) ---
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'  # ต้องมี Bearer นำหน้า
    }
    
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    print(f"🚀 กำลังเชื่อมต่อ: {TARGET_URL}")

    try:
        response = requests.post(TARGET_URL, headers=headers, json=body, timeout=10)
        
        # กรณีเชื่อมต่อสำเร็จ (ไม่ขึ้น 404)
        if response.status_code == 200:
            result = response.json()
            
            # เช็กว่ามีข้อมูล data ส่งกลับมาไหม
            if 'data' in result:
                d = result['data']
                return {
                    "success": True, 
                    "sender": d.get('sender', {}).get('displayName', 'ไม่ระบุ'),
                    "amount": d.get('amount', 0),
                    "date": d.get('transDate', '')
                }
            else:
                # เชื่อมต่อได้ แต่สลิปมีปัญหา (เช่น สลิปปลอม/ซ้ำ)
                return {"success": False, "message": f"ตรวจสอบแล้ว: {result.get('message', 'ไม่ผ่านเงื่อนไข')}"}
        
        elif response.status_code == 404:
             return {"success": False, "message": "ผิดพลาด: หา Server ไม่เจอ (404) - รบกวนแจ้ง Support Slip2Go"}
        elif response.status_code == 401:
             return {"success": False, "message": "ผิดพลาด: Key ไม่ถูกต้อง (401)"}
        else:
             return {"success": False, "message": f"Server Error ({response.status_code}): {response.text}"}

    except Exception as e:
        return {"success": False, "message": f"เชื่อมต่อไม่ได้เลย: {e}"}
