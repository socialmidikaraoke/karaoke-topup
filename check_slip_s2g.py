import cv2
from pyzbar.pyzbar import decode
import requests
import json

# 1. เอา Secret Key จากรูปมาใส่ตรงนี้
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA=" 

# URL ของ Slip2Go (เช็กสลิป)
SLIP2GO_URL = "https://api.slip2go.com/v1/verify"

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

    # --- ส่วนตั้งค่า Header (แก้ตามรูปที่คุณส่งมา) ---
    headers = {
        'Authorization': API_KEY,  # ใส่ Key ตรงๆ เลยตามคำแนะนำในรูป
        'Content-Type': 'application/json'
    }
    
    # Slip2Go ส่งข้อมูลด้วย key ชื่อ 'data'
    body = {
        "data": qr_payload
    }

    try:
        response = requests.post(SLIP2GO_URL, headers=headers, json=body, timeout=10)
        result = response.json()

        # --- เช็กผลลัพธ์ ---
        if response.status_code == 200 and result.get('status') == 200:
            data = result['data']
            return {
                "success": True,
                "sender": data['sender']['displayName'],
                "receiver": data['receiver']['displayName'],
                "amount": data['amount'],
                "date": data['transDate']
            }
        else:
            # กรณี Error
            return {"success": False, "message": f"สลิปไม่ผ่าน: {result.get('message')}"}

    except Exception as e:
        return {"success": False, "message": f"เชื่อมต่อไม่ได้: {e}"}

# --- ทดสอบ ---
if __name__ == "__main__":
    # อย่าลืมเปลี่ยนชื่อไฟล์รูปตรงนี้ เป็นรูปสลิปที่คุณมีในเครื่อง
    print(check_slip_slip2go("test_slip.jpg"))