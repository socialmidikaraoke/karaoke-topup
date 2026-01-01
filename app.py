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

    # ---------------------------------------------------------
    # ✅ ระบุ ID ของไฟล์คุณโดยเฉพาะ (แม่นยำ 100%)
    # ---------------------------------------------------------
    SPREADSHEET_ID = "1hQRW8mJVD6yMp5v2Iv1i3hCLTR3fosWyKyTk_Ibj3YQ"
    
    # ใช้คำสั่ง open_by_key เพื่อเจาะจงไฟล์นี้เท่านั้น
    return client.open_by_key(SPREADSHEET_ID).sheet1

# --- ฟังก์ชันอัปเดตสมาชิก ---
def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sheet = get_google_sheet()
        
        # 1. เช็กสลิปซ้ำ (Anti-Duplicate)
        if trans_ref:
            try:
                # ค้นหาทั้ง Sheet ว่าเคยมีรหัสนี้ไหม
                found = sheet.find(trans_ref)
                if found:
                    return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ! (Ref: {trans_ref})"
            except:
                pass # ถ้าหาไม่เจอ แปลว่าสลิปใหม่ (ผ่าน)

        # 2. ค้นหาสมาชิก
        all_data = sheet.get_all_values()
        target_row = None
        user_input = user_input.strip()
        
        for i, row in enumerate(all_data):
            if len(row) <= 6: continue # ข้ามแถวที่ข้อมูลไม่ครบ
            
            # แปลงเป็นข้อความเพื่อความชัวร์
            member_id = str(row[0]).strip() # Col A
            # Col G แยกด้วยลูกน้ำ
            account_names = [str(name).strip() for name in str(row[6]).split(',')]
            
            if user_input == member_id or user_input in account_names:
                target_row = i + 1
                break
        
        if target_row:
            # คำนวณวัน
            days = 30 if amount_paid >= 100 else (15 if amount_paid >= 50 else 7)
            
            # อัปเดตข้อมูลลง Sheet
            # Col C (3) = สถานะ
            sheet.update_cell(target_row, 3, "Active")
            # Col D (4) = รายละเอียด
            sheet.update_cell(target_row, 4, f"เติม {amount_paid}บ. (+{days}วัน) {trans_ref}")
            # Col E (5) = บันทึกรหัสสลิป (กันซ้ำ)
            if trans_ref:
                sheet.update_cell(target_row, 5, trans_ref)
            
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
            
            # ส่งไปตรวจที่ Slip2Go
            slip_result = check_slip_slip2go("temp_slip.jpg")
            
            if os.path.exists("temp_slip.jpg"):
                os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                trans_ref = slip_result.get('transRef', '')

                # กรณีฉุกเฉิน: ถ้ายังหา Ref ไม่เจอ ให้ลองกวาดหาจากตัวแปรอื่นใน raw_data
                if not trans_ref and 'raw_data' in slip_result:
                     raw = slip_result['raw_data']
                     # ลองเดาชื่อตัวแปรยอดฮิต
                     trans_ref = raw.get('transId') or raw.get('ref1') or raw.get('id') or ''

                if not trans_ref:
                    st.error("❌ ไม่พบรหัสอ้างอิงสลิป (แต่ยอดเงินเข้าแล้ว)")
                    if 'raw_data' in slip_result:
                        st.warning("👇 ข้อมูลดิบ (แคปส่งให้ผู้พัฒนาดูเพื่อแก้ชื่อตัวแปร):")
                        st.json(slip_result['raw_data'])
                else:
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
