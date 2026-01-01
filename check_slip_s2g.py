import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- 1. ใส่ Key (ผมลบภาษาไทยออกให้แล้ว ใช้ Key จากรูปของคุณ) ---
# ต้องเป็นตัวเลขและภาษาอังกฤษล้วนๆ ห้ามมีเว้นวรรค
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA=" 

def check_slip_slip2go(image_path):
    print(f"🔍 กำลังตรวจสอบสลิป: {image_path}")

    # --- ส่วนอ่าน QR Code ---
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "ไม่พบไฟล์รูปภาพ"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "ในรูปไม่มี QR Code"}

    qr_payload = decoded_objects[0].data.decode('utf-8')

    # --- ส่วนตั้งค่า Request (ตามรูปตัวอย่าง Curl) ---
    headers = {
        'Authorization': f'Bearer {API_KEY}', 
        'Content-Type': 'application/json'
    }
    
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    # --- 2. ระบบลอง URL ให้อัตโนมัติ (แก้ปัญหา Cannot POST) ---
    # เราจะลอง 2 URL ที่เป็นไปได้มากที่สุด
    possible_urls = [
        "https://api.slip2go.com/verify-slip/qr-code/info",      # แบบที่ 1 (ไม่มี /api ซ้ำ)
        "https://api.slip2go.com/api/verify-slip/qr-code/info",  # แบบที่ 2 (ตามเอกสารบางจุด)
        "https://slip2go.com/api/verify-slip/qr-code/info"       # แบบที่ 3 (โดเมนหลัก)
    ]

    for url in possible_urls:
        try:
            print(f"📡 กำลังลองเชื่อมต่อ: {url} ...")
            response = requests.post(url, headers=headers, json=body, timeout=10)
            
            # ถ้าเจอ URL ที่ถูกต้อง (ไม่ขึ้น 404 Cannot POST)
            if response.status_code != 404:
                result = response.json()
                
                if response.status_code == 200:
                    # สำเร็จ! ดึงข้อมูลออกมา
                    if 'data' in result:
                        data = result['data']
                        return {
                            "success": True,
                            "sender": data.get('sender', {}).get('displayName', 'ไม่ระบุ'),
                            "receiver": data.get('receiver', {}).get('displayName', 'ไม่ระบุ'),
                            "amount": data.get('amount', 0),
                            "date": data.get('transDate', ''),
                            "transRef": data.get('transRef', '')
                        }
                    else:
                        return {"success": True, "data": result}
                else:
                    # เจอ URL ถูก แต่สลิปอาจจะผิด (เช่น สลิปปลอม)
                    error_msg = result.get('message', response.text)
                    return {"success": False, "message": f"สลิปไม่ผ่าน: {error_msg}"}
        
        except Exception as e:
            print(f"⚠️ URL นี้ใช้ไม่ได้: {e}")
            continue # ลอง URL ถัดไป

    return {"success": False, "message": "เชื่อมต่อ Server ไม่ได้เลย (กรุณาเช็กเน็ต หรือระบบ Slip2Go ล่ม)"}

# --- ทดลองรัน ---
if __name__ == "__main__":
    # เปลี่ยนชื่อไฟล์รูปตรงนี้ แล้วกดรัน
    print(check_slip_slip2go("test_slip.jpg"))
