import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- Key ของคุณ (ใช้ตัวเดิมที่ถูกต้อง) ---
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA="

def check_slip_slip2go(image_path):
    # อ่าน QR Code
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "หา QR Code ไม่เจอ"}

    qr_payload = decoded_objects[0].data.decode('utf-8')
    
    # --- รายชื่อ URL ที่จะสุ่มทดสอบ (เพิ่มความครอบคลุม) ---
    possible_urls = [
        "https://api.slip2go.com/verify-slip/qr-code/info",      # 1. มาตรฐาน (ไม่มี /api ซ้ำ)
        "https://api.slip2go.com/api/verify-slip/qr-code/info",  # 2. แบบซ้อน /api (ตาม Error ก่อนหน้า)
        "https://slip2go.com/api/verify-slip/qr-code/info",      # 3. โดเมนหลัก
        "http://api.slip2go.com/verify-slip/qr-code/info",       # 4. แบบ http ธรรมดา
    ]
    
    # เก็บ Error ไว้รายงานผล (ถ้าหาไม่เจอเลย)
    error_logs = []

    # เริ่มไล่เช็กทีละ URL
    for url in possible_urls:
        # ลอง Header 2 แบบ (กันเหนียว)
        # แบบ A: มี Bearer (ตามรูป Curl)
        # แบบ B: ไม่มี Bearer (ตามรูปหน้าเว็บ)
        auth_formats = [f'Bearer {API_KEY}', API_KEY]

        for auth in auth_formats:
            try:
                headers = {'Authorization': auth, 'Content-Type': 'application/json'}
                body = {"payload": {"qrCode": qr_payload}}
                
                # ยิงไปที่ Server
                response = requests.post(url, headers=headers, json=body, timeout=5)
                
                # ถ้าเจอช่องทางที่ถูกต้อง (ไม่ตอบ 404 หรือ Cannot POST)
                if response.status_code != 404 and "Cannot POST" not in response.text:
                    result = response.json()
                    
                    if response.status_code == 200:
                        # --- สำเร็จ! เจอทางเข้าแล้ว ---
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
                        # เจอ Server แต่ Key ผิด หรือ สลิปผิด
                        error_msg = result.get('message', response.text)
                        error_logs.append(f"URL: {url} -> Error: {error_msg}")
                        break # ข้ามไปลอง URL ถัดไป

                else:
                    # ทางตัน (404)
                    error_logs.append(f"URL: {url} -> ไม่พบหน้านี้ (404)")

            except Exception as e:
                error_logs.append(f"URL: {url} -> เชื่อมต่อไม่ได้ ({e})")
                continue

    # ถ้าลองทุกทางแล้วยังไม่ได้ ให้คืนค่า Error ทั้งหมดออกมาดู
    all_errors = "\n".join(error_logs[:3]) # ตัดมาโชว์แค่ 3 อันแรกกันรก
    return {"success": False, "message": f"หา Server ไม่เจอเลยครับ:\n{all_errors}"}
