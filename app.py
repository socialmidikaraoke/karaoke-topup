import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import requests

# ตั้งค่า API Key (ในขั้นตอนจริง เราจะไปซ่อนไว้ใน Secret ของเว็บ)
API_URL = "https://developer.easyslip.com/api/v1/verify"
API_KEY = st.secrets["API_KEY"] # ดึงคีย์จากระบบความปลอดภัย

def check_slip(image_bytes):
    # แปลงไฟล์ภาพที่อัปโหลดให้เป็น format ที่ OpenCV อ่านได้
    file_bytes = np.asarray(bytearray(image_bytes.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    decoded_objects = decode(img)
    if not decoded_objects:
        return {"success": False, "message": "ไม่พบ QR Code"}
        
    qr_payload = decoded_objects[0].data.decode('utf-8')
    
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    response = requests.post(API_URL, headers=headers, json={"payload": qr_payload})
    
    if response.status_code == 200 and response.json()['status'] == 200:
        return {"success": True, "data": response.json()['data']}
    else:
        return {"success": False, "message": "สลิปไม่ถูกต้อง หรือเช็กไม่ได้"}

# --- ส่วนหน้าตาเว็บ ---
st.title("ระบบเติมเงินสมาชิกคาราโอเกะ")

# 1. ให้สมาชิกกรอกชื่อ (เพื่อไปเช็กใน Google Sheet)
username = st.text_input("กรุณากรอกชื่อสมาชิก (Username)")

# 2. อัปโหลดสลิป
uploaded_file = st.file_uploader("อัปโหลดสลิปโอนเงิน", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None and username:
    if st.button("ตรวจสอบสลิป"):
        with st.spinner('กำลังตรวจสอบกับธนาคาร...'):
            result = check_slip(uploaded_file)
            
        if result['success']:
            amount = result['data']['amount']['amount']
            sender = result['data']['sender']['account']['name']['th']
            
            st.success(f"✅ ได้รับยอดเงิน {amount} บาท จากคุณ {sender}")
            
            # --- ตรงนี้ใส่โค้ดอัปเดต Google Sheet ---
            # update_google_sheet(username, amount)
            
            st.balloons() # เอฟเฟกต์ลูกโป่งฉลอง
            st.info("ระบบได้ต่ออายุสมาชิกให้คุณแล้ว ขอบคุณครับ!")
        else:
            st.error(f"❌ เกิดข้อผิดพลาด: {result['message']}")