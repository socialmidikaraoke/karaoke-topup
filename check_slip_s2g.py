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
    if img is None: return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}
    
    decoded_objects = decode(img)
    if not decoded_objects: return {"success": False, "message": "ไม่พบ QR Code ในรูป"}
    
    qr_payload = decoded_objects[0].data.decode('utf-8')
    print(f"✅ อ่าน QR สำเร็จ")
    
    # --- 2. URL ที่ถูกต้อง (Confirmed!) ---
    TARGET_URL = "https://connect.slip2go.com/api/verify-slip/qr-code/info"

    # --- 3. ลองกุญแจ 2 รูปแบบ (เพื่อแก้ Token Mismatch) ---
    auth_options = [
        # แบบที่ 1: ใส่แค่ Key เพียวๆ (ตามคำแนะนำภาษาไทยในเว็บ)
        API_KEY,
        # แบบที่ 2: มี Bearer นำหน้า (ตามตัวอย่าง Curl)
        f'Bearer {API_KEY}'
    ]

    print(f"🚀 กำลังเชื่อมต่อ: {TARGET_URL}")

    for auth_value in auth_options:
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': auth_value
            }
            body = {"payload": {"qrCode": qr_payload}}

            response = requests.post(TARGET_URL, headers=headers, json=body, timeout=10)
            
            # ถ้าผ่าน (200) หรือได้ข้อมูลกลับมา
            if response.status_code == 200:
                result = response.json()
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
                    return {"success": True, "data": result}
            
            elif response.status_code == 401:
                print(f"⚠️ แบบ '{auth_value[:10]}...' ใช้ไม่ได้ (Token Mismatch) -> กำลังลองอีกแบบ...")
                continue # ลองแบบถัดไป

        except Exception as e:
            print(f"Error: {e}")
            continue

    # ถ้าลองครบแล้วยังไม่ได้
    return {"success": False, "message": "เชื่อมต่อได้แต่รหัส Key ไม่ถูกต้อง (Token Mismatch) - ลองกดปุ่ม 'เปลี่ยน' Key ในเว็บ Slip2Go ดูไหมครับ?"}
