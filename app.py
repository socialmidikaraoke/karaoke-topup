import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

# --- ฟังก์ชันเชื่อมต่อ Google Sheet ---
def get_google_sheet():
    # กำหนดสิทธิ์ให้ครบ (Sheet + Drive)
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
    
    # เปิดไฟล์ Google Sheet (ต้องชื่อตรงกับใน Drive เป๊ะๆ)
    sheet = client.open("Midi Slip System Data").sheet1 
    return sheet

# --- ฟังก์ชันอัปเดตสมาชิก (แก้ไขใหม่: เช็ก Col A และ Col G แบบมีลูกน้ำ) ---
def update_member_status(user_input, amount_paid):
    try:
        sheet = get_google_sheet()
        
        # ดึงข้อมูลทั้งหมดมาเช็กในโปรแกรม (เพื่อรองรับการแยกเครื่องหมายคอมมา)
        all_data = sheet.get_all_values()
        
        target_row = None
        user_input = user_input.strip() # ตัดช่องว่างหน้าหลังออกกันพลาด
        
        # วนลูปเช็กทีละแถว (เริ่ม i=0 คือแถวที่ 1 ใน Sheet)
        for i, row in enumerate(all_data):
            # ป้องกันกรณีแถวว่าง หรือข้อมูลไม่ครบคอลัมน์
            # เราต้องการเช็กถึง Col G (Index 6) ดังนั้นแถวต้องยาวพอ
            if len(row) <= 6: 
                continue
            
            # 1. เช็ก Col A (MemberID) -> Index 0
            member_id = row[0].strip()
            
            # 2. เช็ก Col G (Account Name) -> Index 6
            # แยกชื่อด้วยเครื่องหมายคอมมา (,) แล้วลบช่องว่างออก
            account_names_str = row[6]
            account_names = [name.strip() for name in account_names_str.split(',')]
            
            # ตรวจสอบว่า User Input ตรงกับ MemberID หรือ อยู่ในรายชื่อ Col G หรือไม่
            if user_input == member_id or user_input in account_names:
                target_row = i + 1 # เก็บเลขแถวที่เจอ (Google Sheet เริ่มนับที่ 1)
                break
        
        if target_row:
            # --- เจอสมาชิกแล้ว! ทำการคำนวณวันและอัปเดตสิทธิ์ ---
            
            # คำนวณวันใช้งาน
            days_to_add = 0
            if amount_paid >= 100:
                days_to_add = 30
            elif amount_paid >= 50:
                days_to_add = 15
            else:
                days_to_add = 7
            
            # อัปเดตข้อมูลลง Sheet
            # Col C (3) = สถานะ
            # Col D (4) = รายละเอียดการเติมเงิน
            sheet.update_cell(target_row, 3, "Active") 
            sheet.update_cell(target_row, 4, f"เติมเงิน {amount_paid} บาท (+{days_to_add} วัน)")
            
            return True, f"ต่ออายุเรียบร้อย! ({days_to_add} วัน) สำหรับสมาชิก: {user_input}"
        else:
            return False, f"ไม่พบข้อมูลสมาชิก '{user_input}' ในระบบ (เช็ก Col A หรือ G แล้วไม่เจอ)"
            
    except Exception as e:
        return False, f"Google Sheet Error: {e}"

# --- ส่วนหน้าจอ (UI) ---
st.title("🎤 ระบบเติมเงินสมาชิกคาราโอเกะ")

with st.form("topup_form"):
    user_input = st.text_input("👤 กรอก Member ID หรือ ชื่อบัญชี (ที่มีใน Col G)")
    uploaded_file = st.file_uploader("💸 อัปโหลดสลิปโอนเงิน", type=['jpg', 'png', 'jpeg'])
    submit_button = st.form_submit_button("ตรวจสอบและเติมเงิน")

if submit_button:
    if not user_input or not uploaded_file:
        st.warning("⚠️ กรุณากรอกข้อมูลให้ครบ")
    else:
        with st.spinner("⏳ กำลังตรวจสอบสลิป..."):
            # บันทึกไฟล์รูปชั่วคราว
            with open("temp_slip.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # เช็กสลิปกับ Slip2Go
            slip_result = check_slip_slip2go("temp_slip.jpg")
            
            # ลบไฟล์ทิ้ง
            if os.path.exists("temp_slip.jpg"):
                os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                sender = slip_result.get('sender', 'ไม่ระบุ')
                
                st.info(f"✅ สลิปถูกต้อง! ยอดเงิน {amount} บาท (จาก: {sender})")
                
                # วิ่งไปอัปเดต Google Sheet ตามเงื่อนไขใหม่
                with st.spinner("⏳ กำลังค้นหาและอัปเดตสิทธิ์..."):
                    success, msg = update_member_status(user_input, amount)
                    
                    if success:
                        st.success(f"🎉 {msg}")
                        st.balloons()
                    else:
                        st.error(f"❌ {msg}")
            else:
                st.error(f"❌ {slip_result['message']}")
