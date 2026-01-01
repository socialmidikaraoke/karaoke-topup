import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- 1. Key ของคุณ (ถูกต้องแล้ว) ---
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA="

def check_slip_slip2go(image_path):
    print(f"🔍 เริ่มตรวจสอบรูป: {image_path}")

    # --- ส่วนอ่าน QR Code ---
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "ไม่พบ QR Code ในรูป"}

    qr_payload = decoded_objects[0].data.decode('utf-8')
    print(f"✅ อ่าน QR สำเร็จ (รหัสยาว {len(qr_payload)})")
    
    # --- 2. URL ที่ถูกต้อง (จากที่คุณส่งมาล่าสุด) ---
    # ใช้ subdomain 'connect' ตามที่คุณส่งมา
    TARGET_URL = "https://connect.slip2go.com/api/verify-slip/qr-code/info"

    # --- 3. Header และ Body (ตามมาตรฐาน Slip2Go) ---
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'  # ต้องมี Bearer
    }
    
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    print(f"🚀 กำลังเชื่อมต่อ: {TARGET_URL}")

    try:
        response = requests.post(TARGET_URL, headers=headers, json=body, timeout=10)
        
        # ถ้าเชื่อมต่อสำเร็จ (ไม่ขึ้น 404 หรือ Error แปลกๆ)
        if response.status_code == 200:
            result = response.json()
            
            # เช็กข้อมูลที่ได้กลับมา
            if 'data' in result:
                d = result['data']
                return {
                    "success": True, 
                    "sender": d.get('sender', {}).get('displayName', 'ไม่ระบุ'),
                    "receiver": d.get('receiver', {}).get('displayName', 'ไม่ระบุ'),
                    "amount": d.get('amount', 0),
                    "date": d.get('transDate', ''),
                    "transRef": d.get('transRef', '')
                }
            else:
                # เชื่อมต่อได้ แต่สลิปอาจจะมีปัญหา หรือรูปแบบข้อมูลต่างออกไป
                return {"success": True, "data": result}
        
        else:
            # กรณี Error จาก Server (เช่น 400, 401, 404, 500)
            try:
                error_res = response.json()
                error_msg = error_res.get('message', response.text)
            except:
                error_msg = response.text
                
            return {"success": False, "message": f"Server Error ({response.status_code}): {error_msg}"}

    except Exception as e:
        return {"success": False, "message": f"เชื่อมต่อไม่ได้เลย: {e}"}
