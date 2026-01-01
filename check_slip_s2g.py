import cv2
from pyzbar.pyzbar import decode
import requests
import json

API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWCIZsJg0XA="

def check_slip_slip2go(image_path):
    img = cv2.imread(image_path)
    if img is None: return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}
    
    decoded_objects = decode(img)
    if not decoded_objects: return {"success": False, "message": "ไม่พบ QR Code"}
    
    qr_payload = decoded_objects[0].data.decode('utf-8')
    
    TARGET_URL = "https://connect.slip2go.com/api/verify-slip/qr-code/info"

    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }
        # เพิ่ม checkDuplicate ตามเอกสารที่คุณส่งมา
        body = {
            "payload": {
                "qrCode": qr_payload,
                "checkCondition": {
                    "checkDuplicate": True
                }
            }
        }

        response = requests.post(TARGET_URL, headers=headers, json=body, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if 'data' in result:
                d = result['data']
                return {
                    "success": True, 
                    "sender": d.get('sender', {}).get('displayName', 'ไม่ระบุ'),
                    "amount": d.get('amount', 0),
                    "transRef": d.get('transRef', ''),
                    "raw_data": d # ส่งกลับไปดูชื่อตัวแปร
                }
            else:
                return {"success": True, "data": result, "raw_data": result}
        else:
            return {"success": False, "message": f"Server Error ({response.status_code}): {response.text}"}

    except Exception as e:
        return {"success": False, "message": f"เชื่อมต่อไม่ได้: {e}"}
