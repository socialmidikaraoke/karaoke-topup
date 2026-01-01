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
    
    # --- 2. ตั้งค่า URL ที่ถูกต้อง (แก้ไขจาก {apiUrl} เป็น slip2go.com) ---
    # เราจะลอง 2 แบบที่น่าจะเป็นไปได้ที่สุด
    possible_urls = [
        "https://slip2go.com/api/verify-slip/qr-code/info",      # แบบที่ 1: เว็บหลัก (น่าจะถูกที่สุด)
        "https://www.slip2go.com/api/verify-slip/qr-code/info",  # แบบที่ 2: มี www
        "https://api.slip2go.com/api/verify-slip/qr-code/info"   # แบบที่ 3: แบบเดิม (เผื่อไว้)
    ]

    # --- 3. ตั้งค่า Header และ Body (ตามโค้ด Curl ที่คุณส่งมา) ---
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'  # ต้องมี Bearer นำหน้า
    }
    
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    print("🚀 กำลังเชื่อมต่อ Slip2Go...")

    # วนลูปยิงจนกว่าจะเจอ
    for url in possible_urls:
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            
            # ถ้าไม่เจอ 404 (แสดงว่าเจอ Server ที่ถูกต้องแล้ว)
            if response.status_code != 404 and "Cannot POST" not in response.text:
                result = response.json()
                
                if response.status_code == 200:
                    # สำเร็จ!
                    if 'data' in result:
                        d = result['data']
                        return {
                            "success": True, 
                            "sender": d.get('sender', {}).get('displayName', 'ไม่ระบุ'),
                            "amount": d.get('amount', 0),
                            "date": d.get('transDate', '')
                        }
                    return {"success": True, "data": result}
                else:
                    # เจอ Server แล้ว แต่สลิปอาจจะผิด
                    return {"success": False, "message": f"สลิปไม่ผ่าน: {result.get('message')}"}
                    
        except Exception as e:
            continue # ลอง URL ถัดไปเงียบๆ

    return {"success": False, "message": "ยังไม่สามารถเชื่อมต่อ Server ได้ (กรุณาเช็กว่า Slip2Go ปิดปรับปรุงหรือไม่)"}
