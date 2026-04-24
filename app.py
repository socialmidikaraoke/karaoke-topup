import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from check_slip_s2g import check_slip_slip2go
import os
from datetime import datetime
import pytz
import re

# =========================================================
# 🎨 ตั้งค่าหน้าเว็บ และ CSS
# =========================================================
st.set_page_config(page_title="ระบบเติมเงิน", page_icon="🎤", layout="centered")

custom_css = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="InputInstructions"] {display: none;}
            
            .stTextInput>div>div>input {
                font-size: 20px !important; 
                font-weight: bold !important;
                padding: 15px !important;
            }
            
            .stButton>button {
                width: 100% !important; 
                height: 65px !important; 
                font-size: 22px !important; 
                font-weight: bold !important; 
                border-radius: 10px !important;
                border: 2px solid #00d26a !important;
            }
            </style>
            """
st.markdown(custom_css, unsafe_allow_html=True)
# =========================================================

# =========================================================
# 🔒 ตั้งค่าความปลอดภัย
# =========================================================
TARGET_BANK_NAME = "020300995519"
PRICE_PER_MONTH = 100
SLIP_AGE_LIMIT_DAYS = 3  
# =========================================================

def get_google_spreadsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key("1hQRW8mJVD6yMp5v2Iv1i3hCLTR3fosWyKyTk_Ibj3YQ")

def get_readable_expiry(permission_str):
    try:
        if not permission_str: return "-"
        segments = [s.strip() for s in str(permission_str).split(',') if s.strip()]
        if not segments: return "-"
        last_seg = segments[-1]
        match = re.match(r"(\d{4}):(\d+)(?:-(\d+))?:\*", last_seg)
        if match:
            year = match.group(1)
            end_month = int(match.group(3)) if match.group(3) else int(match.group(2))
            thai_months = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            return f"{thai_months[end_month]} {year}"
        return permission_str
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
                if start_m == new_end: new_seg = f"{year}:{start_m}:*"
                else: new_seg = f"{year}:{start_m}-{new_end}:*"
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
        if not slip_date_str: return False, 0
        slip_date_clean = str(slip_date_str)[:10] 
        slip_date = datetime.strptime(slip_date_clean, "%Y-%m-%d").date()
        now = datetime.now(pytz.timezone('Asia/Bangkok')).date()
        delta = now - slip_date
        if delta.days > SLIP_AGE_LIMIT_DAYS:
            return True, delta.days
        else:
            return False, delta.days
    except:
        return False, 0

def update_member_status(user_input, amount_paid, trans_ref, slip_date, sender_name):
    try:
        sh = get_google_spreadsheet()
        member_sheet = sh.get_worksheet(0) 
        try: history_sheet = sh.worksheet("History")
        except: return False, "ไม่พบหน้าชีต 'History'"

        if trans_ref:
            try:
                found = history_sheet.find(trans_ref)
                if found: return False, "⛔ สลิปนี้ถูกใช้งานไปแล้วครับ!" 
            except: pass 

        all_data = member_sheet.get_all_values()
        target_row = None
        current_permissions = ""
        user_input = str(user_input).strip()
        user_input_lower = user_input.lower() 
        
        for i, row in enumerate(all_data):
            if len(row) <= 1: continue 
            member_id = str(row[0]).strip()
            account_names = []
            if len(row) > 6:
                account_names = [str(name).strip() for name in str(row[6]).split(',')]
            
            member_id_lower = member_id.lower()
            account_names_lower = [name.lower() for name in account_names]

            if user_input_lower == member_id_lower or user_input_lower in account_names_lower:
                target_row = i + 1
                if len(row) > 4: current_permissions = row[4] 
                break
        
        if target_row:
            new_permissions = calculate_new_permission(current_permissions, amount_paid)
            if new_permissions == current_permissions: return False, "ยอดเงินไม่เพียงพอ (ขั้นต่ำ 100 บาท)"

            member_sheet.update_cell(target_row, 5, new_permissions)
            
            if trans_ref:
                if slip_date and str(slip_date).strip() != "":
                    timestamp = str(slip_date).replace('T', ' ').split('+')[0]
                else:
                    tz = pytz.timezone('Asia/Bangkok')
                    timestamp = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                
                history_sheet.append_row([timestamp, user_input, amount_paid, trans_ref, sender_name, new_permissions])

            readable_date = get_readable_expiry(new_permissions)
            return True, f"เติมเงินสำเร็จ! ใช้งานได้ถึง: {readable_date}"
        else:
            return False, f"ไม่พบรหัสสมาชิก '{user_input}' ในระบบ"
    except Exception as e:
        return False, f"System Error: {e}"

# --- UI หลัก ---

st.markdown(f"<div style='margin-top: 40px; font-size: 24px; font-weight: bold; margin-bottom: 20px;'>🏦 โอนเงินเข้า: ออมสิน {TARGET_BANK_NAME} (100บ./เดือน)</div>", unsafe_allow_html=True)

default_id = ""
try:
    if hasattr(st, "query_params"):
        if "member_id" in st.query_params: default_id = st.query_params["member_id"]
        elif "id" in st.query_params: default_id = st.query_params["id"]
        elif "user" in st.query_params: default_id = st.query_params["user"]
    else:
        params = st.experimental_get_query_params()
        if "member_id" in params: default_id = params["member_id"][0]
        elif "id" in params: default_id = params["id"][0]
        elif "user" in params: default_id = params["user"][0]
except:
    pass

with st.form("topup_form", clear_on_submit=False):
    st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 5px;'>👤 รหัสสมาชิก (Member ID)</div>", unsafe_allow_html=True)
    user_input = st.text_input("รหัสสมาชิก", value=default_id, label_visibility="collapsed")
    
    st.markdown("<div style='font-size: 18px; font-weight: bold; margin-bottom: 5px; margin-top: 15px;'>💸 อัปโหลดรูปสลิปโอนเงินตรงนี้</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("อัปโหลดสลิป", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
    
    submit_button = st.form_submit_button("✅ ตรวจสอบสลิปและเติมเงิน")

if submit_button:
    if not user_input or not uploaded_file:
        st.warning("⚠️ กรุณากรอกรหัสสมาชิกและอัปโหลดรูปสลิปก่อนครับ")
    else:
        with st.spinner("⏳ กำลังตรวจสอบข้อมูล... กรุณารอสักครู่"):
            with open("temp_slip.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            slip_result = check_slip_slip2go("temp_slip.jpg")
            if os.path.exists("temp_slip.jpg"): os.remove("temp_slip.jpg")
            
            if slip_result.get('success'):
                amount = slip_result.get('amount')
                raw = slip_result.get('raw_data', {})
                
                if amount is None or amount == "" or float(amount) == 0:
                    st.error("❌ **ระบบไม่สามารถอ่าน QR CODE จากสลิปนี้ได้**\n\nรบกวนส่งรูปสลิปให้แอดมินทางแชทเฟซบุ๊กครับ")
                    st.stop()
                
                # ระบบตรวจสอบเลขบัญชีผู้รับ
                receiver_acc = ""
                try:
                    receiver_acc = raw.get('receiver', {}).get('account', {}).get('bank', {}).get('account', '')
                    if not receiver_acc:
                        rec = slip_result.get('receiver', {})
                        if isinstance(rec, dict):
                            receiver_acc = rec.get('account', {}).get('bank', {}).get('account', '')
                            if not receiver_acc:
                                receiver_acc = rec.get('account', {}).get('account', '')
                except:
                    pass

                clean_target = re.sub(r'[^0-9]', '', TARGET_BANK_NAME)
                is_valid_account = True
                
                if not receiver_acc or str(receiver_acc).strip() == "":
                    is_valid_account = False
                else:
                    blocks = re.findall(r'\d+', str(receiver_acc))
                    if not blocks:
                        is_valid_account = False
                    else:
                        current_pos = 0
                        total_matched_digits = 0
                        
                        for block in blocks:
                            pos = clean_target.find(block, current_pos)
                            if pos == -1:
                                is_valid_account = False
                                break 
                            current_pos = pos + len(block)
                            total_matched_digits += len(block)
                            
                        if total_matched_digits < 3:
                            is_valid_account = False

                if not is_valid_account:
                    st.error(f"❌ **บัญชีผู้รับไม่ถูกต้อง!**\n\nสลิปนี้อาจโอนผิดบัญชี ({TARGET_BANK_NAME}) ครับ\nหากมั่นใจว่าโอนถูกต้อง รบกวนติดต่อแอดมินครับ")
                    st.stop()

                d = slip_result.get('transDate') or slip_result.get('date') or raw.get('dateTime') or raw.get('transDate') or raw.get('date') or raw.get('sendingBankDate')
                t = slip_result.get('transTime') or slip_result.get('time') or raw.get('transTime') or raw.get('time')

                final_slip_datetime = ""
                if d and 'T' in str(d): final_slip_datetime = str(d)
                elif d and t: final_slip_datetime = f"{d} {t}"
                elif d: final_slip_datetime = str(d)
                
                sender_name = "ไม่ระบุ"
                try:
                    sender_acc_name = raw.get('sender', {}).get('account', {}).get('name')
                    if sender_acc_name: sender_name = sender_acc_name
                    else:
                        sender_name = slip_result.get('sender', 'ไม่ระบุ')
                        if isinstance(sender_name, dict): sender_name = sender_name.get('account', {}).get('name', 'ไม่ระบุ')
                except:
                    pass

                trans_ref = slip_result.get('transRef') or raw.get('transId') or raw.get('ref1') or raw.get('id') or raw.get('bankRef') or raw.get('billerRef') or raw.get('transactionId') or ''

                if not trans_ref:
                    st.error("❌ **ระบบไม่สามารถอ่าน QR CODE จากสลิปนี้ได้**\n\nรบกวนส่งรูปสลิปให้แอดมินทางแชทเฟซบุ๊กครับ")
                else:
                    too_old, days_passed = is_slip_too_old(str(final_slip_datetime))
                    
                    if too_old:
                        st.error(f"⛔ **สลิปนี้ใช้งานไม่ได้แล้วครับ รบกวนติดต่อแอดมิน**") 
                    else:
                        success, msg = update_member_status(user_input, amount, trans_ref, final_slip_datetime, sender_name)
                        if success:
                            # แสดงผลค้างไว้ ไม่สั่งรีเฟรชแล้ว
                            st.success(f"✅ **{msg}**\n\nยอดเงินที่เติม: **{amount} บาท**")
                            st.warning("📌 **อย่าลืม! กรุณากดปุ่ม 'อัปเดตสิทธิ์' (ปุ่มสีเขียวด้านบน)** เพื่อโหลดข้อมูลสิทธิ์การใช้งานล่าสุดของคุณครับ")
                        else:
                            st.error(f"❌ **เกิดข้อผิดพลาด**\n\n{msg}")
            else:
                st.error("❌ **ระบบไม่สามารถอ่าน QR CODE จากสลิปนี้ได้**\n\nรบกวนส่งรูปสลิปให้แอดมินทางแชทเฟซบุ๊กครับ")
