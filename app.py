import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os
from datetime import datetime
import pytz
import re

st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

# =========================================================
# 🔒 ตั้งค่าความปลอดภัย
# =========================================================
TARGET_BANK_NAME = "020300995519" # เลขบัญชีออมสิน
PRICE_PER_MONTH = 100             # 100 บาท = 1 เดือน
# =========================================================

def get_google_spreadsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key("1hQRW8mJVD6yMp5v2Iv1i3hCLTR3fosWyKyTk_Ibj3YQ")

def calculate_new_permission(current_perm_str, amount_paid):
    """
    ฟังก์ชันคำนวณสิทธิ์แบบรายเดือน (2568:1-12:*)
    - 100 บาท = 1 เดือน
    - เติมข้ามปี ปัดขึ้นปีใหม่ให้เอง
    """
    # 1. คำนวณจำนวนเดือนที่ได้ (หาร 100)
    months_to_add = int(amount_paid // PRICE_PER_MONTH)
    if months_to_add <= 0:
        return current_perm_str # ยอดเงินไม่ถึง 1 เดือน ไม่เปลี่ยนแปลง

    # 2. เตรียมข้อมูลปีปัจจุบัน (เผื่อไม่มีข้อมูลเดิม)
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz)
    current_thai_year = now.year + 543
    current_month = now.month

    # 3. แยกข้อมูลเดิม (Split Comma)
    if not current_perm_str or str(current_perm_str).strip() == "":
        segments = []
    else:
        segments = [s.strip() for s in str(current_perm_str).split(',') if s.strip()]

    # ถ้าไม่มีข้อมูลเดิมเลย ให้เริ่มสร้างจากปัจจุบัน
    # แต่ต้องถอยหลัง 1 เดือนเพื่อให้ logic การ "เติมเพิ่ม" ทำงานต่อได้ง่าย
    # (เสมือนว่าเพิ่งหมดเดือนที่แล้วไป)
    if not segments:
        # สร้าง Dummy segment เพื่อให้ไปบวกต่อ
        # เช่น ถ้าปัจจุบันเดือน 1 ให้เริ่มจากปีที่แล้วเดือน 12
        start_year = current_thai_year
        start_month = current_month - 1
        if start_month == 0:
            start_month = 12
            start_year -= 1
        segments.append(f"{start_year}:{start_month}:*")

    # 4. ลูปเพื่อเติมเดือนเข้าไปจนกว่า months_to_add จะหมด
    while months_to_add > 0:
        last_seg = segments[-1]
        
        # Parse: "2568:1-12:*" หรือ "2569:1:*"
        # Pattern: Year : Start(-End)? : *
        match = re.match(r"(\d{4}):(\d+)(?:-(\d+))?:\*", last_seg)
        
        if match:
            year = int(match.group(1))
            start_m = int(match.group(2))
            end_m = int(match.group(3)) if match.group(3) else start_m
            
            # เช็กว่าปีนี้เต็ม 12 เดือนหรือยัง?
            if end_m < 12:
                # ยังไม่เต็มปี -> เติมต่อในปีนี้
                space_left = 12 - end_m
                take = min(months_to_add, space_left)
                
                new_end = end_m + take
                months_to_add -= take
                
                # อัปเดต Segment เดิม
                if start_m == new_end:
                    new_seg = f"{year}:{start_m}:*" # เดือนเดียว
                else:
                    new_seg = f"{year}:{start_m}-{new_end}:*" # ช่วงเดือน
                
                segments[-1] = new_seg
                
            else:
                # ปีนี้เต็ม 12 แล้ว -> ขึ้นปีใหม่
                new_year = year + 1
                
                # ตัดเดือนที่จะเติมในปีใหม่
                # (Logic: ขึ้น Segment ใหม่ เริ่มที่เดือน 1)
                take = 1 # เริ่มทีละ 1 เดือนในลูปรอบหน้า
                months_to_add -= 1
                
                # เพิ่ม Segment ปีใหม่ (เดือน 1)
                segments.append(f"{new_year}:1:*")
                
        else:
            # กรณีข้อมูลเดิม Format ผิด -> สร้างใหม่จากปัจจุบัน
            segments.append(f"{current_thai_year}:{current_month}:*")
            # (ไม่ลด months_to_add ให้วนลูปใหม่มาเติมใส่ตัวนี้)

    # 5. รวมกลับเป็น String
    return " , ".join(segments)

def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sh = get_google_spreadsheet()
        member_sheet = sh.get_worksheet(0) 
        try:
            history_sheet = sh.worksheet("History")
        except:
            return False, "ไม่พบหน้าชีต 'History'"

        if trans_ref:
            try:
                found = history_sheet.find(trans_ref)
                if found:
                    return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ! (Ref: {trans_ref})"
            except:
                pass 

        all_data = member_sheet.get_all_values()
        target_row = None
        current_permissions = ""
        user_input = str(user_input).strip()
        
        for i, row in enumerate(all_data):
            if len(row) <= 1: continue 
            member_id = str(row[0]).strip()
            
            account_names = []
            if len(row) > 6:
                account_names = [str(name).strip() for name in str(row[6]).split(',')]
            
            if user_input == member_id or user_input in account_names:
                target_row = i + 1
                # ดึงข้อมูลเดิมจาก Col E (SpecificPermissions)
                if len(row) > 4:
                    current_permissions = row[4] 
                break
        
        if target_row:
            # คำนวณสิทธิ์ใหม่ (Logic รายเดือน)
            new_permissions = calculate_new_permission(current_permissions, amount_paid)
            
            # ถ้าไม่มีการเปลี่ยนแปลง (เช่น เติมไม่ถึง 100)
            if new_permissions == current_permissions:
                 return False, "ยอดเงินไม่เพียงพอสำหรับการต่ออายุรายเดือน (ขั้นต่ำ 100 บาท)"

            # อัปเดต Col E (SpecificPermissions)
            member_sheet.update_cell(target_row, 5, new_permissions)
            
            # บันทึกประวัติ
            if trans_ref:
                tz = pytz.timezone('Asia/Bangkok')
                timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                # [เวลา, ใครเติม, ยอดเงิน, รหัสสลิป, สิทธิ์ใหม่]
                history_sheet.append_row([timestamp, user_input, amount_paid, trans_ref, new_permissions])

            return True, f"✅ อัปเดตสิทธิ์สำเร็จ! (ข้อมูลใหม่: {new_permissions})"
        else:
            return False, f"ไม่พบสมาชิก '{user_input}' ในระบบ"
            
    except Exception as e:
        return False, f"System Error: {e}"

# --- UI ---
st.title("🎤 ระบบเติมเงินสมาชิกคาราโอเกะ")
st.info(f"🏦 โอนเงินเข้าบัญชี: **ธนาคารออมสิน {TARGET_BANK_NAME}** (100 บาท/เดือน)")

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
                else:
                    st.success(f"✅ สลิปถูกต้อง! ยอด {amount} บาท")
                    with st.spinner("⏳ กำลังคำนวณสิทธิ์และบันทึก..."):
                        success, msg = update_member_status(user_input, amount, trans_ref)
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
            else:
                st.error(f"❌ {slip_result['message']}")
