import requests
import json
import cv2
from pyzbar.pyzbar import decode

# --- ใส่ Key ของคุณ (ผมใส่ให้แล้ว) ---
API_KEY = "b076J7gGoJj8j+hDzwwV8B29Q86sGDXjOWClZsJg0XA="

def test_connection():
    # 1. จำลองข้อมูล QR Code (ใช้ของจริงจากการอ่านภาพ)
    # เพื่อความชัวร์ ให้เอารูปสลิปวางคู่กับไฟล์นี้ แล้วเปลี่ยนชื่อไฟล์ตรงนี้
    image_path = "test_slip.jpg" 
    
    img = cv2.imread(image_path)
    if img is None:
        print("❌ ไม่พบไฟล์รูปภาพ 'test_slip.jpg' (กรุณาเอารูปสลิปมาวางก่อน)")
        return

    decoded = decode(img)
    if not decoded:
        print("❌ อ่าน QR ไม่เจอในรูป")
        return
        
    qr_payload = decoded[0].data.decode('utf-8')
    print(f"✅ อ่าน QR ได้แล้ว (ยาว {len(qr_payload)} ตัวอักษร)")

    # 2. รายชื่อ URL ที่น่าจะเป็นไปได้ทั้งหมด
    possible_urls = [
        "https://api.slip2go.com/api/verify-slip/qr-code/info",     # แบบมาตรฐาน
        "https://slip2go.com/api/verify-slip/qr-code/info",         # แบบไม่มี api.
        "https://www.slip2go.com/api/verify-slip/qr-code/info",     # แบบมี www
        "http://api.slip2go.com/api/verify-slip/qr-code/info",      # แบบ http (ตามคู่มือบางจุด)
    ]

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    body = {"payload": {"qrCode": qr_payload}}

    print("\n🚀 เริ่มต้นค้นหา URL ที่ถูกต้อง...\n")

    for url in possible_urls:
        print(f"📡 กำลังทดสอบ: {url}")
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            
            print(f"   👉 ผลลัพธ์: Status Code {response.status_code}")
            
            # ถ้าเจอ 200 แสดงว่าเจอทางเข้าที่ถูกต้องแล้ว!
            if response.status_code == 200:
                print("\n🎉🎉 เจอแล้ว! URL ที่ถูกต้องคือ:")
                print(f"--> {url}")
                print("\nข้อมูลที่ได้กลับมา:")
                print(response.json())
                return # จบการทำงานทันที
            elif response.status_code == 404:
                print("   ❌ ไม่ผ่าน (หาไม่เจอ / Cannot POST)")
            else:
                print(f"   ⚠️ เจอ Server แต่ติด error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ เชื่อมต่อไม่ได้เลย ({e})")
        print("-" * 30)

if __name__ == "__main__":
    test_connection()
