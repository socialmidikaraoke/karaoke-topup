# --- แก้ไขส่วนนี้ในไฟล์ app.py ---

def get_google_sheet():
    # เพิ่ม Scope "drive" เข้าไปในรายการ (บรรทัดที่ 2)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    
    # ใส่ชื่อไฟล์ Google Sheet ของคุณให้ถูกต้องตรงนี้
    # (ต้องชื่อตรงเป๊ะๆ กับที่ตั้งใน Google Drive)
    sheet = client.open("Midi Slip System Data").sheet1 
    # ^^^ ถ้าชื่อไฟล์คุณไม่ใช่ "Midi Slip System Data" ให้แก้ตรงนี้ด้วยนะครับ
    
    return sheet
