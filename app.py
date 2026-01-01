import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

# --- ฟังก์ชันเชื่อมต่อ Google Sheet ---
def get_google_sheet():
    # กำหนดสิทธิ์ให้ครบ (Sheet + Drive) แก้ Error 403
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # ดึง Key จาก Secrets
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=scopes
    )
    client = gspread.authorize(creds)
    
    # เปิดไฟล์ Google Sheet (ชื่อไฟล์ต้องตรงกับใน Google Drive เป๊ะๆ)
    sheet = client.open("Midi Slip System Data").sheet1 
    return sheet

# --- ฟังก์ชันอัปเดตสมาชิก ---
def update_member_status(username, amount_paid):
    try:
        sheet = get_google_sheet()
        
        # ค้นหาชื่อสมาชิกในคอลัมน์ A (col 1)
        try:
            cell = sheet.find(username)
        except gspread.exceptions.CellNotFound:
            return False, "ไม่พบชื่อสมาชิกนี้ในระบบ"
        
        if cell:
            # คำนวณวันใช้งาน
            days_to_add = 0
            if amount_paid >= 100:
                days_to_add = 30
            elif amount_paid >= 50:
                days_to_add = 15
            else:
                days_to_add = 7
            
            # อัปเดตข้อมูล (แก้คอลัมน์ 3 และ 4)
            sheet.update_cell(cell.row, 3, "Active") 
            sheet.update_cell(cell.row, 4, f"เติมเงิน {amount_paid} บาท (+{days_to_add} วัน)")
            
            return True, f"เติมเงินเรียบร้อย! (ต่ออายุ {days_to_add} วัน)"
        else:
            return False, "ไม่พบชื่อสมาชิก"
            
    except Exception as e:
        return False, f"Google Sheet Error: {e}"

# --- ส่วนหน้าจอ (UI) ---
st.title("🎤 ระบบเติมเงินสมาชิกคาราโอเกะ")

with st.form("topup_form"):
    user_input = st.text_input("👤 ชื่อสมาชิก (Username)")
    uploaded_file = st.file_uploader("💸 อัปโหลดสลิปโอนเงิน", type=['jpg', 'png'])
    submit_button = st.form_submit_button("ตรวจสอบและเติมเงิน")

if submit_button:
    if not user_input or not uploaded_file:
        st.warning("⚠️ กรุณากรอกข้อมูลให้ครบ")
    else:
        with st.spinner("⏳ กำลังตรวจสอบ..."):
            # บันทึกไฟล์รูปชั่วคราว
            with open("temp_slip.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # เช็กสลิป
            slip_result = check_slip_slip2go("temp_slip.jpg")
            
            # ลบไฟล์ทิ้ง
            if os.path.exists("temp_slip.jpg"):
                os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                sender = slip_result.get('sender', 'ไม่ระบุ')
                
                st.info(f"✅ สลิปถูกต้อง! ยอดเงิน {amount} บาท (จาก: {sender})")
                
                # บันทึกลง Sheet
                success, msg = update_member_status(user_input, amount)
                
                if success:
                    st.success(f"🎉 {msg}")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.error(f"❌ {slip_result['message']}")
