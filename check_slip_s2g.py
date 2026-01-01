import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- KEY ของคุณ (ใส่ให้แล้ว) ---
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA="

def check_slip_slip2go(image_path):
    print(f"🔍 เริ่มตรวจสอบรูป: {image_path}")

    # 1. อ่าน QR Code
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "หา QR Code ในรูปไม่เจอ"}

    qr_payload = decoded_objects[0].data.decode('utf-8')
    print(f"✅ อ่าน QR สำเร็จ (รหัสยาว {len(qr_payload)})")

    # 2. เตรียม Header (ต้องมี Bearer)
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # เตรียม Body (ต้องซ้อน payload -> qrCode)
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    # 3. รายชื่อ URL ที่จะให้ระบบลองสุ่มเช็ก (อันไหนผ่านเอาอันนั้น)
    possible_urls = [
        "https://api.slip2go.com/api/verify-slip/qr-code/info",     # แบบที่ 1 (มาตรฐาน)
        "https://slip2go.com/api/verify-slip/qr-code/info",         # แบบที่ 2 (ไม่มี api.)
        "https://api.slip2go.com/verify-slip/qr-code/info",         # แบบที่ 3 (ไม่มี /api ซ้ำ)
    ]

    # ลูปเพื่อลองยิงทีละ URL
    for url in possible_urls:
        try:
            print(f"📡 กำลังลองเชื่อมต่อ: {url}")
            response = requests.post(url, headers=headers, json=body, timeout=10)
            
            # ถ้าเชื่อมต่อติด (ไม่ว่าจะผ่านหรือไม่ผ่าน)
            if response.status_code != 404: # 404 คือหา Server ไม่เจอ (Cannot POST)
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
                    # เจอ Server แต่สลิปผิด (เช่น สลิปปลอม/ซ้ำ)
                    error_msg = result.get('message', response.text)
                    return {"success": False, "message": f"สลิปไม่ผ่าน: {error_msg}"}
            
        except Exception as e:
            print(f"⚠️ URL นี้ใช้ไม่ได้ ({e}) ข้ามไปอันถัดไป...")
            continue

    # ถ้าลองครบทุกอันแล้วยังไม่ได้
    return {"success": False, "message": "ระบบขัดข้อง: เชื่อมต่อ Slip2Go ไม่ได้เลยทุกช่องทาง"}
