import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- ตั้งค่า Slip2Go (ผมใส่ Key จากรูปภาพให้แล้ว) ---
# สังเกต: ตรงนี้ต้องไม่มีภาษาไทยเลย
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA=" 

# URL ที่ถูกต้องจากภาพตัวอย่าง Curl
SLIP2GO_URL = "https://api.slip2go.com/api/verify-slip/qr-code/info"

def check_slip_slip2go(image_path):
    print(f"🔍 กำลังตรวจสอบสลิป: {image_path}")

    # 1. อ่าน QR Code
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "ไม่พบไฟล์รูปภาพ"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "ในรูปไม่มี QR Code"}

    qr_payload = decoded_objects[0].data.decode('utf-8')

    # 2. ตั้งค่า Header (ต้องมี Bearer ตามตัวอย่างในภาพ)
    headers = {
        'Authorization': f'Bearer {API_KEY}', 
        'Content-Type': 'application/json'
    }
    
    # 3. สร้าง Body (ซ้อน payload -> qrCode ตามภาพตัวอย่าง)
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    try:
        # ยิง API
        response = requests.post(SLIP2GO_URL, headers=headers, json=body, timeout=10)
        
        # 4. เช็กผลลัพธ์
        if response.status_code == 200:
            result = response.json()
            
            # Slip2Go มักจะส่งข้อมูลกลับมาใน key ชื่อ 'data'
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
                 # เผื่อกรณีโครงสร้างไม่เหมือนเดิม ให้ส่งข้อมูลดิบกลับไปดู
                 return {"success": True, "data": result} 
        else:
            # กรณี Error จากฝั่ง Server
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
    # เปลี่ยนชื่อไฟล์รูปสลิปตรงนี้ แล้วกดรันได้เลย
    res = check_slip_slip2go("test_slip.jpg")
    print(res)
