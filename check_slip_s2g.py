import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- 1. ใส่ Key ที่ถูกต้อง (ผมใส่ให้แล้วจากรูปของคุณ) ---
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA="

def check_slip_slip2go(image_path):
    print(f"🔍 เริ่มตรวจสอบรูป: {image_path}")

    # --- ส่วนอ่าน QR Code ---
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "หา QR Code ในรูปไม่เจอ"}

    qr_payload = decoded_objects[0].data.decode('utf-8')
    print(f"✅ อ่าน QR สำเร็จ (รหัสยาว {len(qr_payload)})")

    # --- 2. เตรียม Header (ต้องมี Bearer ตามรูปคู่มือ) ---
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # --- 3. เตรียม Body (ต้องซ้อน payload -> qrCode ตามรูปคู่มือ) ---
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    # --- 4. รายชื่อ URL ที่ระบบจะลองสุ่มเช็ก (เพื่อแก้ปัญหา Cannot POST) ---
    # เราจะให้มันลองยิงไปทีละอัน จนกว่าจะเจออันที่ถูก
    possible_urls = [
        "https://api.slip2go.com/verify-slip/qr-code/info",      # แบบที่ 1 (น่าจะเป็นอันนี้ที่สุด)
        "https://api.slip2go.com/api/verify-slip/qr-code/info",  # แบบที่ 2 (เผื่อมี /api ซ้ำ)
        "https://slip2go.com/api/verify-slip/qr-code/info"       # แบบที่ 3 (โดเมนหลัก)
    ]

    # เริ่มวนลูปทดสอบ URL
    for url in possible_urls:
        try:
            print(f"📡 กำลังลองเชื่อมต่อ: {url}")
            response = requests.post(url, headers=headers, json=body, timeout=10)
            
            # ถ้าไม่เจอ Error 404 (แสดงว่าเจอ Server แล้ว)
            if response.status_code != 404:
                result = response.json()
                
                # ถ้าเช็กสลิปสำเร็จ (Code 200)
                if response.status_code == 200:
                    # ดึงข้อมูลออกมา
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
                    # เจอ Server แต่สลิปผิด (เช่น สลิปปลอม/ซ้ำ/Key ผิด)
                    error_msg = result.get('message', response.text)
                    return {"success": False, "message": f"สลิปไม่ผ่าน: {error_msg}"}
            
        except Exception as e:
            # ถ้า URL นี้พัง ให้ข้ามไปลองอันถัดไปเงียบๆ
            continue

    # ถ้าลองครบทุกอันแล้วยังไม่ได้
    return {"success": False, "message": "ระบบขัดข้อง: เชื่อมต่อ Slip2Go ไม่ได้เลย (กรุณาเช็กเครดิตในเว็บ Slip2Go)"}
