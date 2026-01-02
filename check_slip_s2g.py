import cv2
from pyzbar.pyzbar import decode
import requests
import json

# Key ของคุณ
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWCIZsJg0XA="
MY_ACCOUNT_NO = "020300995519" 

def check_slip_slip2go(image_path):
    img = cv2.imread(image_path)
    if img is None: return {"success": False, "message": "เปิดไฟล์รูปไม่ได้"}
    
    decoded_objects = decode(img)
    if not decoded_objects: return {"success": False, "message": "ไม่พบ QR Code ในรูป"}
    
    qr_payload = decoded_objects[0].data.decode('utf-8')
    
    TARGET_URL = "https://connect.slip2go.com/api/verify-slip/qr-code/info"

    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }
        
        body = {
            "payload": {
                "qrCode": qr_payload,
                "checkCondition": {
                    "checkDuplicate": True,
                    "checkReceiver": [{"accountNumber": MY_ACCOUNT_NO}]
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
                    "receiver": d.get('receiver', {}).get('displayName', 'ไม่ระบุ'),
                    "amount": d.get('amount', 0),
                    "transRef": d.get('transRef', ''),
                    # ดึงวันที่โอนมาด้วย (สำคัญมาก!)
                    "transDate": d.get('transDate') or d.get('transTime') or "", 
                    "raw_data": d
                }
            else:
                error_msg = result.get('message', 'สลิปไม่ถูกต้องตามเงื่อนไข')
                return {"success": False, "message": f"ตรวจสอบไม่ผ่าน: {error_msg}"}
        
        else:
            return {"success": False, "message": f"Server Error: {response.text}"}

    except Exception as e:
        return {"success": False, "message": f"เชื่อมต่อไม่ได้: {e}"}
