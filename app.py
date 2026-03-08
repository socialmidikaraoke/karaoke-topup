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
# 🎨 ส่วนที่ซ่อน Footer, Menu, Header และ Input Instructions
# =========================================================
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* 🔥 ซ่อนคำว่า Press Enter to submit form */
            [data-testid="InputInstructions"] {
                display: none;
            }
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

# 🔥 รองรับตัวพิมพ์เล็ก/ใหญ่ (Case Insensitive)
def update_member_status(user_input, amount_paid, trans_ref, slip_date, sender_name):
    try:
        sh = get_google_spreadsheet()
        member_sheet = sh.get_worksheet(0) 
        try: history_sheet = sh.worksheet("History")
        except: return False, "ไม่พบหน้าชีต 'History'"

        if trans_ref:
            try:
                found = history_sheet.find(trans_ref)
                if found: return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ!" 
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
            return True, f"✅ อัปเดตสำเร็จ! โหลดได้ถึง: **{readable_date}**"
        else:
            return False, f"ไม่พบสมาชิก '{user_input}' ในระบบ"
    except Exception as e:
        return False, f"System Error: {e}"

# --- UI ---
st.info(f"🏦 โอนเงินเข้า: **ออมสิน {TARGET_BANK_NAME}** (100บ./เดือน)")

# แจ้งเตือนเรื่องธนาคารกรุงเทพตั้งแต่แรก
st.warning("⚠️ **หมายเหตุสำหรับ ธ.กรุงเทพ:** ระบบของธนาคารกรุงเทพจะอัปเดตข้อมูลล่าช้า หากเพิ่งโอนเสร็จ **กรุณารอประมาณ 3 นาที** แล้วค่อยอัปโหลดสลิปตรวจสอบนะครับ")

# ==========================================
# 🔥 ดึง Member ID จาก URL อัตโนมัติ (ชัวร์ 100%)
# ==========================================
default_id = ""
try:
    if hasattr(st, "query_params"):
        if "id" in st.query_params:
            default_id = st.query_params["id"]
        elif "user" in st.query_params:
            default_id = st.query_params["user"]
    else:
        params = st.experimental_get_query_params()
        if "id" in params:
            default_id = params["id"][0]
        elif "user" in params:
            default_id = params["user"][0]
except Exception as e:
    default_id = ""
# ==========================================

with st.form("topup_form"):
    user_input = st.text_input("👤 Member ID (ระบบกรอกให้อัตโนมัติ)", value=default_id)
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
                raw = slip_result.get('raw_data', {})
                
                # ดึงวันเวลา
                d = slip_result.get('transDate') or \
                    slip_result.get('date') or \
                    raw.get('dateTime') or \
                    raw.get('transDate') or \
                    raw.get('date') or \
                    raw.get('sendingBankDate')
                
                t = slip_result.get('transTime') or \
                    slip_result.get('time') or \
                    raw.get('transTime') or \
                    raw.get('time')

                final_slip_datetime = ""
                if d and 'T' in str(d):
                    final_slip_datetime = str(d)
                elif d and t:
                    final_slip_datetime = f"{d} {t}"
                elif d:
                    final_slip_datetime = str(d)
                
                # ดึงชื่อผู้โอน
                sender_name = "ไม่ระบุ"
                try:
                    sender_acc_name = raw.get('sender', {}).get('account', {}).get('name')
                    if sender_acc_name:
                        sender_name = sender_acc_name
                    else:
                        sender_name = slip_result.get('sender', 'ไม่ระบุ')
                        if isinstance(sender_name, dict):
                             sender_name = sender_name.get('account', {}).get('name', 'ไม่ระบุ')
                except:
                    pass
                
                # แสดงผลวันที่แบบไทย + พ.ศ.
                display_msg = f"วันที่: {final_slip_datetime} | ผู้โอน: {sender_name}"
                try:
                    clean_dt_str = str(final_slip_datetime).replace('Z', '+00:00')
                    if 'T' in clean_dt_str:
                         dt_obj = datetime.fromisoformat(clean_dt_str)
                    else:
                         dt_obj = datetime.strptime(clean_dt_str[:19], "%Y-%m-%d %H:%M:%S")

                    bangkok_tz = pytz.timezone('Asia/Bangkok')
                    if dt_obj.tzinfo is None:
                        dt_obj = bangkok_tz.localize(dt_obj)
                    else:
                        dt_obj = dt_obj.astimezone(bangkok_tz)

                    year_be = dt_obj.year + 543
                    day = str(dt_obj.day).zfill(2)
                    month = str(dt_obj.month).zfill(2)
                    time_str = dt_obj.strftime("%H:%M:%S")
                    
                    display_msg = f"วันที่โอน : {day}-{month}-{year_be} | เวลา {time_str} | 👤 ผู้โอน : {sender_name}"
                except Exception as e:
                    display_msg = f"วันที่โอน : {final_slip_datetime} (Raw) | 👤 ผู้โอน : {sender_name}"

                st.info(display_msg)

                # ====================================================
                # 🔥 เพิ่มคำค้นหาเผื่อธนาคารกรุงเทพใช้ชื่ออื่น (bankRef, billerRef)
                # ====================================================
                trans_ref = slip_result.get('transRef') or \
                            raw.get('transId') or \
                            raw.get('ref1') or \
                            raw.get('id') or \
                            raw.get('bankRef') or \
                            raw.get('billerRef') or \
                            raw.get('transactionId') or ''

                if not trans_ref:
                    # 🔴 ถ้ายังหาไม่เจออีก จะแสดงปุ่ม Debug ให้คุณก๊อปมาให้ผมดูครับ
                    st.error("❌ ไม่พบรหัสอ้างอิงสลิป (Transaction ID)")
                    st.info("💡 หากเป็นสลิปจาก ธ.กรุงเทพ ระบบอาจซ่อนรหัสไว้ กรุณากดปุ่มด้านล่างเพื่อดูข้อมูลดิบ แล้วส่งให้ผู้ดูแลระบบครับ")
                    
                    with st.expander("🔍 กดเพื่อดูข้อมูลดิบ (สำหรับส่งให้ทีมงานช่วยเช็ก)"):
                        st.json(slip_result)
                        
                else:
                    too_old, days_passed = is_slip_too_old(str(final_slip_datetime))
                    
                    if too_old:
                        st.error(f"⛔ สลิปนี้เก่าเกินไปครับ! ({days_passed} วัน)") 
                    else:
                        st.success(f"✅ สลิปถูกต้อง! ({amount} บาท)")
                        
                        with st.spinner("⏳ กำลังอัปเดตสิทธิ์..."):
                            success, msg = update_member_status(user_input, amount, trans_ref, final_slip_datetime, sender_name)
                            if success:
                                st.success(msg)
                                st.balloons()
                            else:
                                st.error(msg)
            else:
                st.error(f"❌ {slip_result.get('message', 'ตรวจสอบสลิปไม่ผ่าน')}")
