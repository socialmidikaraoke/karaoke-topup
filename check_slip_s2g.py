import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- 1. ใส่ Key (แก้ไข: ลบภาษาไทยออกให้หมด เหลือแค่รหัสล้วนๆ) ---
# รหัสนี้ผมเอามาจากในรูปของคุณ (b076...)
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA=" 

# --- 2. URL ใหม่ (แก้ไข: ต้องมี /api/ ซ้อน 2 ที ตามมาตรฐานใหม่) ---
# อ้างอิงจาก Error ที่ฟ้องว่าหา path ไม่เจอ และเอกสาร API Connect
SLIP2GO_URL = "https://api.slip2go.com/api/verify-slip/qr-code/info"

def check_slip_slip2go(image_path):
    print(f"🔍 กำลังตรวจสอบสลิป: {image_path}")

    # อ่าน QR Code
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "ไม่พบไฟล์รูปภาพ"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "ในรูปไม่มี QR Code"}

    qr_payload = decoded_objects[0].data.decode('utf-8')

    # --- 3. Header (แก้ไข: ต้องมีคำว่า Bearer นำหน้า ตามรูปตัวอย่าง Curl) ---
    headers = {
        'Authorization': f'Bearer {API_KEY}', 
        'Content-Type': 'application/json'
    }
    
    # --- 4. Body (แก้ไข: ต้องซ้อน payload -> qrCode ตามรูปตัวอย่าง Curl) ---
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    try:
        # ส่งข้อมูลไปตรวจสอบ
        response = requests.post(SLIP2GO_URL, headers=headers, json=body, timeout=10)
        
        # เช็กผลลัพธ์
        if response.status_code == 200:
            result = response.json()
            
            # ดึงข้อมูลจาก key 'data'
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
            # กรณี Error จาก Server (เช่น สลิปซ้ำ, ไม่พบข้อมูล)
            try:
                error_res = response.json()
                error_msg = error_res.get('message', response.text)
            except:
                error_msg = response.text
                
            return {"success": False, "message": f"สลิปไม่ผ่าน: {error_msg}"}

    except Exception as e:
        return {"success": False, "message": f"ระบบขัดข้อง: {e}"}

# --- ทดลองรัน ---
if __name__ == "__main__":
    # เปลี่ยนชื่อไฟล์รูปตรงนี้ แล้วกดรัน
    print(check_slip_slip2go("test_slip.jpg"))
