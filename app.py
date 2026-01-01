import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os
from datetime import datetime
import pytz

st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

def get_google_spreadsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    # Spreadsheet ID ของคุณ (ตรวจสอบให้ถูกต้อง)
    return client.open_by_key("1hQRW8mJVD6yMp5v2Iv1i3hCLTR3fosWyKyTk_Ibj3YQ")

def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sh = get_google_spreadsheet()
        member_sheet = sh.get_worksheet(0) 
        
        try:
            history_sheet = sh.worksheet("History")
        except:
            return False, "ไม่พบหน้าชีต 'History'"

        # 1. เช็กสลิปซ้ำใน History (Double Check)
        if trans_ref:
            try:
                found = history_sheet.find(trans_ref)
                if found:
                    return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ! (Ref: {trans_ref})"
            except:
                pass 

        # 2. ค้นหาสมาชิก
        all_data = member_sheet.get_all_values()
        target_row = None
        user_input = str(user_input).strip()
        
        for i, row in enumerate(all_data):
            if len(row) <= 1: continue 
            
            member_id = str(row[0]).strip()
            account_names = []
            if len(row) > 6:
                account_names = [str(name).strip() for name in str(row[6]).split(',')]
            
            if user_input == member_id or user_input in account_names:
                target_row = i + 1
                break
        
        if target_row:
            days = 30 if amount_paid >= 100 else (15 if amount_paid >= 50 else 7)
            
            # อัปเดตสถานะ (Col C)
            member_sheet.update_cell(target_row, 3, "Active")
            
            # บันทึกประวัติ
            if trans_ref:
                tz = pytz.timezone('Asia/Bangkok')
                timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                history_sheet.append_row([timestamp, user_input, amount_paid, trans_ref])

            return True, f"✅ เติมเงินสำเร็จ! ({days} วัน)"
        else:
            return False, f"ไม่พบสมาชิก '{user_input}' ในระบบ"
            
    except Exception as e:
        return False, f"System Error: {e}"

# --- UI ---
st.title("🎤 ระบบเติมเงินสมาชิกคาราโอเกะ")
st.info("🏦 โอนเงินเข้าบัญชี: **ธนาคารออมสิน 020300995519** เท่านั้น")

with st.form("topup_form"):
    user_input = st.text_input("👤 Member ID หรือ ชื่อบัญชี")
    uploaded_file = st.file_uploader("💸 อัปโหลดสลิปโอนเงิน", type=['jpg', 'png', 'jpeg'])
    submit_button = st.form_submit_button("ตรวจสอบและเติมเงิน")

if submit_button:
    if not user_input or not uploaded_file:
        st.warning("⚠️ กรุณากรอกข้อมูลให้ครบ")
    else:
        with st.spinner("⏳ กำลังตรวจสอบกับธนาคาร..."):
            with open("temp_slip.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # ระบบจะเช็กเลขบัญชี 020300995519 ให้อัตโนมัติในนี้
            slip_result = check_slip_slip2go("temp_slip.jpg")
            
            if os.path.exists("temp_slip.jpg"):
                os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                trans_ref = slip_result.get('transRef', '')
                
                # ถ้ายังหา Ref ไม่เจอ (เผื่อไว้)
                if not trans_ref and 'raw_data' in slip_result:
                     raw = slip_result['raw_data']
                     trans_ref = raw.get('transId') or raw.get('ref1') or raw.get('id') or ''

                if not trans_ref:
                    st.error("❌ ไม่พบรหัสอ้างอิงสลิป")
                else:
                    st.success(f"✅ สลิปถูกต้อง! (เข้าบัญชีออมสินเรียบร้อย)")
                    with st.spinner("⏳ กำลังบันทึกข้อมูล..."):
                        success, msg = update_member_status(user_input, amount, trans_ref)
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
            else:
                st.error(f"❌ {slip_result['message']}")
