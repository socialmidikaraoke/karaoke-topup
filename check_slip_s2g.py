import cv2
from pyzbar.pyzbar import decode
import requests
import json

# --- KEY ของคุณ (ตรวจสอบแล้วถูกต้อง ไม่มีภาษาไทย) ---
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA="

def check_slip_slip2go(image_path):
    # 1. อ่าน QR Code
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}

    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "หา QR Code ในรูปไม่เจอ (รูปอาจไม่ชัด)"}

    qr_payload = decoded_objects[0].data.decode('utf-8')
    
    # 2. ตั้งค่า Header (ต้องมี Bearer ตามคู่มือ)
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Body ต้องซ้อน payload -> qrCode
    body = {
        "payload": {
            "qrCode": qr_payload
        }
    }

    # 3. รายชื่อ URL ที่เป็นไปได้ทั้งหมด (เพิ่ม www และ http เพื่อความชัวร์)
    possible_urls = [
        "https://api.slip2go.com/api/verify-slip/qr-code/info",  # แบบมาตรฐาน 1
        "https://slip2go.com/api/verify-slip/qr-code/info",      # แบบมาตรฐาน 2 (Root domain)
        "https://www.slip2go.com/api/verify-slip/qr-code/info",  # แบบมี www
        "http://api.slip2go.com/api/verify-slip/qr-code/info",   # แบบ http (เผื่อ https มีปัญหา)
    ]

    error_logs = [] # เก็บประวัติความผิดพลาดไว้บอกผู้ใช้

    # ลูปทดสอบทีละ URL
    for url in possible_urls:
        try:
            # print(f"กำลังทดสอบ: {url}") # (ดูใน Log หลังบ้าน)
            response = requests.post(url, headers=headers, json=body, timeout=15)
            
            # ถ้าเชื่อมต่อ Server ติด (ไม่ว่าจะผ่านหรือไม่)
            if response.status_code != 404: 
                # 404 = Cannot POST (ผิดที่อยู่) -> ให้ข้ามไปลองอันอื่น
                # ถ้าไม่ใช่ 404 แสดงว่าเจอ Server ถูกตัวแล้ว!
                
                if response.status_code == 200:
                    result = response.json()
                    # สำเร็จ!
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
                    # เจอ Server แต่สลิปมีปัญหา (เช่น Key ผิด, สลิปซ้ำ, เครดิตหมด)
                    try:
                        res_json = response.json()
                        err_msg = res_json.get('message', str(res_json))
                    except:
                        err_msg = response.text
                    return {"success": False, "message": f"Server ตอบกลับ ({response.status_code}): {err_msg}"}
            
            else:
                error_logs.append(f"{url} -> 404 Not Found")

        except Exception as e:
            error_logs.append(f"{url} -> Error: {str(e)}")
            continue

    # ถ้าลองครบทุกอันแล้วยังไม่ได้
    return {
        "success": False, 
        "message": f"ไม่พบ Server ที่ถูกต้อง (ตรวจสอบแล้ว {len(possible_urls)} ช่องทาง) Log: {'; '.join(error_logs)}"
    }
