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

# --- ฟังก์ชันอัปเดตสมาชิก (กันสลิปซ้ำ + เช็กชื่อ) ---
def update_member_status(user_input, amount_paid, trans_ref):
    try:
        sheet = get_google_sheet()
        
        # --- 1. ระบบกันสลิปซ้ำ (Anti-Duplicate) ---
        # ค้นหารหัส TransRef ใน Sheet ทั้งหมด ถ้าเจอแสดงว่าเคยใช้แล้ว
        # (หมายเหตุ: เราจะบันทึก TransRef ไว้ที่คอลัมน์ E (5))
        try:
            # ค้นหาคำว่า trans_ref ใน sheet
            found = sheet.find(trans_ref)
            if found:
                return False, f"⛔ สลิปนี้ถูกใช้งานไปแล้วครับ! (รหัส: {trans_ref})"
        except:
            pass # ถ้าหาไม่เจอ แปลว่าสลิปใหม่ (ผ่าน)

        # --- 2. ค้นหาสมาชิก ---
        all_data = sheet.get_all_values()
        target_row = None
        user_input = user_input.strip()
        
        for i, row in enumerate(all_data):
            if len(row) <= 6: continue # ข้ามแถวที่ข้อมูลไม่ครบ
            
            # เช็ก Col A (MemberID)
            member_id = row[0].strip()
            # เช็ก Col G (ชื่อบัญชีหลายชื่อ คั่นด้วยคอมมา)
            account_names = [name.strip() for name in row[6].split(',')]
            
            if user_input == member_id or user_input in account_names:
                target_row = i + 1
                break
        
        if target_row:
            # --- เจอสมาชิกแล้ว! ---
            
            # คำนวณวัน
            days_to_add = 0
            if amount_paid >= 100: days_to_add = 30
            elif amount_paid >= 50: days_to_add = 15
            else: days_to_add = 7
            
            # อัปเดตข้อมูล
            # Col C (3) = สถานะ
            sheet.update_cell(target_row, 3, "Active") 
            # Col D (4) = รายละเอียด
            sheet.update_cell(target_row, 4, f"เติม {amount_paid}บ. (+{days_to_add}วัน) {trans_ref}")
            # Col E (5) = บันทึก TransRef (สำคัญมาก! เอาไว้เช็กซ้ำรอบหน้า)
            sheet.update_cell(target_row, 5, trans_ref)
            
            return True, f"✅ ต่ออายุเรียบร้อย! ({days_to_add} วัน) สำหรับ: {user_input}"
        else:
            return False, f"ไม่พบข้อมูลสมาชิก '{user_input}' ในระบบ"
            
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
            with open("temp_slip.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # ส่งไปเช็กกับ Slip2Go
            slip_result = check_slip_slip2go("temp_slip.jpg")
            
            if os.path.exists("temp_slip.jpg"):
                os.remove("temp_slip.jpg")
            
            if slip_result['success']:
                amount = slip_result.get('amount', 0)
                sender = slip_result.get('sender', '-')
                # ดึงรหัสธุรกรรมมาด้วย (เพื่อเอาไปเช็กซ้ำ)
                trans_ref = slip_result.get('transRef', '')
                
                if not trans_ref:
                    # กันเหนียว กรณี Slip2Go ไม่ส่ง ref กลับมา
                    st.error("❌ ไม่พบรหัสอ้างอิงสลิป (ตรวจสอบไม่ได้)")
                else:
                    st.info(f"ธนาคารตรวจสอบผ่าน: ยอด {amount} บาท (Ref: {trans_ref})")
                    
                    # วิ่งไปอัปเดต Sheet (ส่ง trans_ref ไปเช็กซ้ำด้วย)
                    with st.spinner("⏳ กำลังบันทึกและตรวจสอบสลิปซ้ำ..."):
                        success, msg = update_member_status(user_input, amount, trans_ref)
                        
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
            else:
                st.error(f"❌ สลิปใช้ไม่ได้: {slip_result['message']}")
