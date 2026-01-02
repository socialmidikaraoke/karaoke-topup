import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os
from datetime import datetime
import pytz
import re

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบเติมเงินสมาชิก", page_icon="🎤")

# =========================================================
# 🎨 ส่วนที่เพิ่ม: ซ่อน Footer, Menu และ Header (ตามที่ขอ)
# =========================================================
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# =========================================================

# =========================================================
# 🔒 ตั้งค่าความปลอดภัย
# =========================================================
TARGET_BANK_NAME = "020300995519"
PRICE_PER_MONTH = 100
SLIP_AGE_LIMIT_DAYS = 30  
# =========================================================

def get_google_spreadsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key("1hQRW8mJVD6yMp5v2Iv1i3hCLTR3fosWyKyTk_Ibj3YQ")

def get_readable_expiry(permission_str):
    """แปลงรหัส 2569:1-2:* เป็นข้อความ 'กุมภาพันธ์ 2569'"""
    try:
        if not permission_str: return "-"
        
        # เอาตัวสุดท้ายมา (เพราะคือเดือนล่าสุดที่โหลดได้)
        segments = [s.strip() for s in str(permission_str).split(',') if s.strip()]
        if not segments: return "-"
        
        last_seg = segments[-1]
        
        # แกะปีและเดือนสิ้นสุด
        match = re.match(r"(\d{4}):(\d+)(?:-(\d+))?:\*", last_seg)
        if match:
            year = match.group(1)
            # ถ้ามีขีด (1-12) เอาตัวหลัง, ถ้าไม่มี (1) เอาตัวหน้า
            end_month = int(match.group(3)) if match.group(3) else int(match.group(2))
            
            thai_months = [
                "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
            ]
            
            month_name = thai_months[end_month]
            return f"{month_name} {year}"
            
        return permission_str # ถ้าแกะไม่ออก โชว์ตัวเดิม
    except:
        return permission_str

def calculate_new_permission(current_perm_str, amount_paid):
    months_to_add = int(amount_paid // PRICE_PER_MONTH)
    if months_to_add <= 0: return current_perm_str

    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz)
    current_thai_year = now.year + 543
    current_month = now.month

    if not current_perm_str or str(current_perm_str).strip() == "":
        segments = []
    else:
        segments = [s.strip() for s in str(current_perm_str).split(',') if s.strip()]

    if not segments:
        start_year = current_thai_year
        start_month = current_month - 1
        if start_month == 0:
            start_month = 12
            start_year -= 1
        segments.append(f"{start_year}:{start_month}:*")

    while months_to_add > 0:
        last_seg = segments[-1]
        match = re.match(r"(\d{4}):(\d+)(?:-(\d+))?:\*", last_seg)
        
        if match:
            year = int(match.group(1))
            start_m = int(match.group(2))
            end_m = int(match.group(3)) if match.group(3) else start_m
            
            if end_m < 12:
                space_left = 12 - end_m
                take = min(months_to_add, space_left)
                new_end = end_m + take
                months_to_add -= take
                
                if start_m == new_end:
                    new_seg = f"{year}:{start_m}:*"
                else:
                    new_seg = f"{year}:{start_m}-{new_end}:*"
                segments[-1] = new_seg
            else:
                new_year = year + 1
                take = 1
                months_to_add -= 1
                segments.append(f"{new_year}:1:*")
        else:
            segments.append(f"{current_thai_year}:{current_month}:*")

    return " , ".join(segments)

def is_slip_too_old(slip_date_str):
    try:
        slip_date_clean = slip_date_str[:10]
        slip_date = datetime.strptime(slip_date_clean, "%Y-%m-%d").date()
        now = datetime.now(pytz.timezone('Asia/Bangkok')).date()
        delta = now - slip_date
        if delta.days > SLIP_AGE_LIMIT_DAYS:
            return True, delta.days
        else:
            return False, delta.days
    except:
        return False, 0

def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sh = get_google_spreadsheet()
        member_sheet = sh.get_worksheet(0) 
        try: history_sheet = sh.worksheet("History")
        except: return False, "ไม่พบหน้าชีต 'History'"

        if trans_ref:
            try:
                found = history_sheet.find(trans_ref)
                if found: 
                    return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ!" 
            except: pass 

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
                if len(row) > 4: current_permissions = row[4] 
                break
        
        if target_row:
            new_permissions = calculate_new_permission(current_permissions, amount_paid)
            if new_permissions == current_permissions:
                 return False, "ยอดเงินไม่เพียงพอ (ขั้นต่ำ 100 บาท)"

            member_sheet.update_cell(target_row, 5, new_permissions)
            
            if trans_ref:
                tz = pytz.timezone('Asia/Bangkok')
                timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                history_sheet.append_row([timestamp, user_input, amount_paid, trans_ref, new_permissions])

            # --- แปลงรหัสเป็นภาษาคนตรงนี้ ---
            readable_date = get_readable_expiry(new_permissions)
            return True, f"✅ อัปเดตสำเร็จ! โหลดได้ถึง: **{readable_date}**"
        else:
            return False, f"ไม่พบสมาชิก '{user_input}' ในระบบ"
            
    except Exception as e:
        return False, f"System Error: {e}"

# --- UI ---
# st.title("🎤 ระบบเติมเงินสมาชิกคาราโอเกะ") # Comment ออกตามที่ขอ
st.info(f"🏦 โอนเงินเข้า: **ออมสิน {TARGET_BANK_NAME}** (100บ./เดือน)")

with st.form("topup_form"):
    user_input = st.text_input("👤 Member ID (กรอกให้ถูกต้อง เช่น MIDI-Test1)")
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
            
            if os.path.exists("temp_slip.jpg"): os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                trans_ref = slip_result.get('transRef', '')
                trans_date = slip_result.get('transDate', '') 
                
                if not trans_ref and 'raw_data' in slip_result:
                      raw = slip_result['raw_data']
                      trans_ref = raw.get('transId') or raw.get('ref1') or raw.get('id') or ''

                if not trans_ref:
                    st.error("❌ ไม่พบรหัสอ้างอิงสลิป")
                else:
                    too_old, days_passed = is_slip_too_old(trans_date)
                    
                    if too_old:
                        st.error(f"⛔ สลิปนี้เก่าเกินไปครับ!") 
                    else:
                        st.success(f"✅ สลิปถูกต้อง! ({amount} บาท)")
                        
                        with st.spinner("⏳ กำลังอัปเดตสิทธิ์..."):
                            success, msg = update_member_status(user_input, amount, trans_ref)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
            else:
                st.error(f"❌ {slip_result['message']}")
