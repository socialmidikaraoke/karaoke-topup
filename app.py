import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os

st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    
    # ใส่ Spreadsheet ID ของคุณ (ตัวเดิมที่ถูกต้อง)
    SPREADSHEET_ID = "1hQRW8mJVD6yMp5v2Iv1i3hCLTR3fosWyKyTk_Ibj3YQ" 
    return client.open_by_key(SPREADSHEET_ID).sheet1

def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sheet = get_google_sheet()

        # =========================================================
        # ⚙️ ตั้งค่าคอลัมน์ที่จะแก้ไข (นับ A=1, B=2, C=3, ...)
        # =========================================================
        
        # 1. ช่องที่จะแก้สถานะเป็น Active (เช่น Col C หรือ F)
        TARGET_COL_STATUS = 3   # <--- แก้เลขนี้ให้ตรงกับช่อง "สถานะ" ของคุณ
        
        # 2. ช่องที่จะบันทึกรหัสสลิป (เพื่อกันสลิปซ้ำ) *แนะนำให้สร้างคอลัมน์ใหม่ว่างๆ*
        TARGET_COL_TRANS_REF = 6  # <--- (คอลัมน์ F) จะได้ไม่ไปทับ SpecificPermissions (Col E)
        
        # 3. ช่องที่จะบันทึกรายละเอียด (ถ้าไม่ต้องการให้ใส่ 0)
        TARGET_COL_NOTE = 0       # <--- ใส่ 0 เพื่อปิดการเขียนช่อง Access ที่คุณไม่ต้องการให้ยุ่ง
        
        # =========================================================

        # 1. ระบบเช็กสลิปซ้ำ (หาทั่วทั้งแผ่น)
        if trans_ref:
            try:
                found = sheet.find(trans_ref)
                if found:
                    return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ! (Ref: {trans_ref})"
            except:
                pass 

        # 2. ค้นหาสมาชิก
        all_data = sheet.get_all_values()
        target_row = None
        user_input = str(user_input).strip()
        
        for i, row in enumerate(all_data):
            if len(row) <= 1: continue 
            
            # เช็ก MemberID (Col A -> Index 0)
            member_id = str(row[0]).strip()
            
            # เช็กชื่อบัญชีใน Col G (Index 6) *ถ้ามีข้อมูล*
            account_names = []
            if len(row) > 6:
                account_names = [str(name).strip() for name in str(row[6]).split(',')]
            
            if user_input == member_id or user_input in account_names:
                target_row = i + 1
                break
        
        if target_row:
            days = 30 if amount_paid >= 100 else (15 if amount_paid >= 50 else 7)
            
            # --- เริ่มบันทึกข้อมูลลงช่องที่กำหนด ---
            
            # 1. อัปเดตสถานะ (Col 3 หรือตามที่ตั้งไว้)
            sheet.update_cell(target_row, TARGET_COL_STATUS, "Active")
            
            # 2. บันทึกรหัสสลิป (Col 6 หรือตามที่ตั้งไว้) - ย้ายมานี่ ไม่ทับ Permissions
            if trans_ref:
                sheet.update_cell(target_row, TARGET_COL_TRANS_REF, trans_ref)
            
            # 3. บันทึก Note (ถ้าเปิดใช้งาน)
            if TARGET_COL_NOTE > 0:
                sheet.update_cell(target_row, TARGET_COL_NOTE, f"เติม {amount_paid} (+{days}วัน)")

            return True, f"✅ ต่ออายุเรียบร้อย! ({days} วัน) ให้คุณ {user_input}"
        else:
            return False, f"ไม่พบสมาชิก '{user_input}' ในระบบ"
            
    except Exception as e:
        return False, f"Google Sheet Error: {e}"

# --- ส่วน UI ---
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
            
            slip_result = check_slip_slip2go("temp_slip.jpg")
            
            if os.path.exists("temp_slip.jpg"):
                os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                trans_ref = slip_result.get('transRef', '')

                if not trans_ref and 'raw_data' in slip_result:
                     raw = slip_result['raw_data']
                     trans_ref = raw.get('transId') or raw.get('ref1') or raw.get('id') or ''

                if not trans_ref:
                    st.error("❌ ไม่พบรหัสอ้างอิงสลิป")
                    if 'raw_data' in slip_result:
                        st.json(slip_result['raw_data'])
                else:
                    st.info(f"✅ ยอดเงิน {amount} บาท")
                    with st.spinner("⏳ กำลังบันทึกข้อมูล..."):
                        success, msg = update_member_status(user_input, amount, trans_ref)
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
            else:
                st.error(f"❌ {slip_result['message']}")
