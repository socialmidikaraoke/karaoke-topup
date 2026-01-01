import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os
from datetime import datetime
import pytz

st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

# --- ฟังก์ชันเชื่อมต่อ Google Sheet (เข้าถึงทั้งไฟล์) ---
def get_google_spreadsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    
    # ID ไฟล์เดิมของคุณ
    SPREADSHEET_ID = "1hQRW8mJVD6yMp5v2Iv1i3hCLTR3fosWyKyTk_Ibj3YQ" 
    
    # ส่งกลับไปทั้งก้อน (เพื่อให้เลือกหน้าชีตย่อยได้)
    return client.open_by_key(SPREADSHEET_ID)

def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sh = get_google_spreadsheet()
        
        # 1. เชื่อมต่อชีต "สมาชิก" (แผ่นแรก)
        member_sheet = sh.get_worksheet(0) 
        
        # 2. เชื่อมต่อชีต "History" (ต้องสร้างชื่อนี้ไว้ตามข้อ 1)
        try:
            history_sheet = sh.worksheet("History")
        except:
            return False, "ไม่พบหน้าชีตชื่อ 'History' ใน Google Sheet กรุณาสร้างก่อนครับ"

        # =========================================================
        # 🛡️ เช็กสลิปซ้ำ (Global Check)
        # =========================================================
        if trans_ref:
            try:
                # ค้นหาในหน้า History ทั้งหมด ว่ารหัสนี้เคยมีใครใช้หรือยัง
                found = history_sheet.find(trans_ref)
                if found:
                    return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ! (Ref: {trans_ref})"
            except:
                pass # ไม่เจอ = สลิปใหม่ (ผ่าน)

        # =========================================================
        # 👤 ค้นหาและอัปเดตสมาชิก (ในหน้าแรก)
        # =========================================================
        all_data = member_sheet.get_all_values()
        target_row = None
        user_input = str(user_input).strip()
        
        for i, row in enumerate(all_data):
            if len(row) <= 1: continue 
            
            member_id = str(row[0]).strip()
            
            # เช็กชื่อใน Col G (ถ้ามี)
            account_names = []
            if len(row) > 6:
                account_names = [str(name).strip() for name in str(row[6]).split(',')]
            
            if user_input == member_id or user_input in account_names:
                target_row = i + 1
                break
        
        if target_row:
            days = 30 if amount_paid >= 100 else (15 if amount_paid >= 50 else 7)
            
            # --- อัปเดตสถานะที่หน้าสมาชิก ---
            # แก้ Col C (3) เป็น Active
            member_sheet.update_cell(target_row, 3, "Active")
            
            # (ทางเลือก) แก้ Note ใน Col D (4) 
            # member_sheet.update_cell(target_row, 4, f"เติม {amount_paid} เมื่อ {datetime.now().strftime('%d/%m')}")

            # =========================================================
            # 📝 บันทึกประวัติลงหน้า History (ต่อท้ายแถวล่างสุด)
            # =========================================================
            if trans_ref:
                tz = pytz.timezone('Asia/Bangkok')
                timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                
                # เพิ่มแถวใหม่: [เวลา, ใครเติม, ยอดเงิน, รหัสสลิป]
                history_sheet.append_row([timestamp, user_input, amount_paid, trans_ref])

            return True, f"✅ เติมเงินสำเร็จ! ({days} วัน) บันทึกประวัติเรียบร้อย"
        else:
            return False, f"ไม่พบสมาชิก '{user_input}' ในระบบ"
            
    except Exception as e:
        return False, f"System Error: {e}"

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
