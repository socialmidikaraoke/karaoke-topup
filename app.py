import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os

# --- ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

# --- ฟังก์ชันเชื่อมต่อ Google Sheet ---
def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=scopes
    )
    client = gspread.authorize(creds)
    # ชื่อไฟล์ต้องตรงเป๊ะๆ
    sheet = client.open("Midi Slip System Data").sheet1 
    return sheet

# --- ฟังก์ชันอัปเดตสมาชิก (กันสลิปซ้ำ) ---
def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sheet = get_google_sheet()
        
        # 1. เช็กสลิปซ้ำ (Anti-Duplicate)
        try:
            # ค้นหา trans_ref ใน Sheet (ถ้าเจอแปลว่าซ้ำ)
            if trans_ref:
                found = sheet.find(trans_ref)
                if found:
                    return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ! (Ref: {trans_ref})"
        except:
            pass # หาไม่เจอ = สลิปใหม่ (ผ่าน)

        # 2. ค้นหาสมาชิก
        all_data = sheet.get_all_values()
        target_row = None
        user_input = user_input.strip()
        
        for i, row in enumerate(all_data):
            if len(row) <= 6: continue
            
            member_id = row[0].strip()
            account_names = [name.strip() for name in row[6].split(',')]
            
            if user_input == member_id or user_input in account_names:
                target_row = i + 1
                break
        
        if target_row:
            # คำนวณวัน
            days = 30 if amount_paid >= 100 else (15 if amount_paid >= 50 else 7)
            
            # อัปเดตข้อมูล
            sheet.update_cell(target_row, 3, "Active") 
            sheet.update_cell(target_row, 4, f"เติม {amount_paid}บ. (+{days}วัน) {trans_ref}")
            if trans_ref:
                sheet.update_cell(target_row, 5, trans_ref) # บันทึก Ref กันซ้ำ
            
            return True, f"✅ ต่ออายุเรียบร้อย! ({days} วัน) ให้คุณ {user_input}"
        else:
            return False, f"ไม่พบสมาชิก '{user_input}' ในระบบ"
            
    except Exception as e:
        return False, f"Google Sheet Error: {e}"

# --- ส่วนหน้าจอ (UI) ---
st.title("🎤 ระบบเติมเงินสมาชิกคาราโอเกะ")

with st.form("topup_form"):
    user_input = st.text_input("👤 Member ID หรือ ชื่อบัญชี")
    uploaded_file = st.file_uploader("💸 อัปโหลดสลิปโอนเงิน", type=['jpg', 'png', 'jpeg'])
    submit_button = st.form_submit_button("ตรวจสอบและเติมเงิน")

if submit_button:
    if not user_input or not uploaded_file:
        st.warning("⚠️ กรุณากรอกข้อมูลให้ครบ")
    else:
        with st.spinner("⏳ กำลังตรวจสอบสลิป..."):
            with open("temp_slip.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # เรียกใช้ฟังก์ชันเช็กสลิป
            slip_result = check_slip_slip2go("temp_slip.jpg")
            
            if os.path.exists("temp_slip.jpg"):
                os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                sender = slip_result.get('sender', '-')
                trans_ref = slip_result.get('transRef', '')
                
                # --- ส่วน Debug: ถ้ารหัสอ้างอิงหาย ให้โชว์ข้อมูลดิบ ---
                if not trans_ref:
                    st.error("❌ ไม่พบรหัสอ้างอิงสลิป (ตรวจสอบไม่ได้)")
                    st.warning("👇 กรุณาแคปภาพข้อมูลด้านล่างนี้ ส่งมาให้ผู้พัฒนาแก้ไขครับ:")
                    
                    # โชว์ข้อมูลดิบออกมาเลย
                    st.json(slip_result.get('raw_data', 'ไม่พบข้อมูลดิบ'))
                else:
                    # ถ้าทุกอย่างปกติ ทำงานต่อ
                    st.info(f"✅ ยอดเงิน {amount} บาท (Ref: {trans_ref})")
                    
                    with st.spinner("⏳ กำลังบันทึกข้อมูล..."):
                        success, msg = update_member_status(user_input, amount, trans_ref)
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
            else:
                st.error(f"❌ {slip_result['message']}")
