import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- ตั้งค่า Slip2Go (อัปเดตใหม่) ---
# ใส่ Key ที่คุณได้จากเว็บ (ตัวยาวๆ สีเขียว)
API_KEY = "ใส่_Secret_Key_ของคุณตรงนี้" 

# URL ใหม่ของ Slip2Go (ตามเอกสารล่าสุด)
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

    # 2. ตั้งค่า Header (ตามรูปที่คุณส่งมา ไม่ต้องมี Bearer)
    headers = {
        'Authorization': API_KEY, 
        'Content-Type': 'application/json'
    }
    
    # 3. สร้าง Body ข้อมูล (ตามรูปแบบใหม่ของ Slip2Go)
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    try:
        # ยิง API ไปที่ Slip2Go
        response = requests.post(SLIP2GO_URL, headers=headers, json=body, timeout=10)
        result = response.json()

        # 4. เช็กผลลัพธ์
        # ถ้าสำเร็จ ปกติจะส่ง status 200 หรือ data กลับมา
        if response.status_code == 200:
            # บางที data อาจจะซ้อนอยู่ใน key 'data' อีกที ต้องดูผลลัพธ์จริง
            # แต่โครงสร้างทั่วไปน่าจะประมาณนี้
            if 'data' in result:
                data = result['data']
                return {
                    "success": True,
                    "sender": data.get('sender', {}).get('displayName', 'ไม่ระบุ'),
                    "amount": data.get('amount', 0),
                    "date": data.get('transDate', ''),
                    "transRef": data.get('transRef', '')
                }
            else:
                 return {"success": True, "data": result} # กรณีโครงสร้างต่างจากที่คาด
        else:
            # กรณี Error
            error_msg = result.get('message', 'ตรวจสอบไม่ได้')
            return {"success": False, "message": f"สลิปไม่ผ่าน: {error_msg}"}

    except Exception as e:
        return {"success": False, "message": f"ระบบขัดข้อง: {e}"}
