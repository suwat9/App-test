import streamlit as st
import qrcode
from PIL import Image
import io
import base64

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="QR Code Generator",
    page_icon="📱",
    layout="centered"
)

# CSS สำหรับแต่งหน้าตา
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        padding: 20px 0;
        font-size: 3em;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-size: 18px;
        padding: 15px;
        border-radius: 10px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #145a8c;
    }
    .success-box {
        padding: 20px;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 10px 0;
    }
    .info-box {
        padding: 15px;
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ฟังก์ชันสร้าง QR Code
def generate_qr_code(data, box_size=10, border=4, fill_color="black", back_color="white"):
    """สร้าง QR Code จากข้อมูล"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img

# ฟังก์ชันสร้าง QR Code พร้อมโลโก้
def generate_qr_with_logo(data, logo_path=None, box_size=10, border=4):
    """สร้าง QR Code พร้อมโลโก้ตรงกลาง"""
    # สร้าง QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # ถ้ามีโลโก้
    if logo_path:
        logo = Image.open(logo_path)
        
        # คำนวณขนาดโลโก้ (ประมาณ 1/5 ของ QR Code)
        qr_width, qr_height = img.size
        logo_size = qr_width // 5
        
        # ปรับขนาดโลโก้
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        # คำนวณตำแหน่งกึ่งกลาง
        logo_pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
        
        # วางโลโก้
        img.paste(logo, logo_pos)
    
    return img

# ฟังก์ชันแปลงรูปเป็น Base64
def get_image_download_link(img, filename, text):
    """สร้างลิงก์ดาวน์โหลดรูป"""
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:file/png;base64,{img_str}" download="{filename}">{text}</a>'
    return href

# === UI หลัก ===

st.markdown('<h1 class="main-header">📱 QR Code Generator</h1>', unsafe_allow_html=True)
st.markdown("---")

# คำอธิบาย
with st.expander("📖 วิธีใช้งาน"):
    st.markdown("""
    ### โปรแกรมนี้สามารถสร้าง QR Code ได้หลายประเภท:
    1. **ข้อความธรรมดา** - ข้อความใดๆ ที่ต้องการ
    2. **URL / เว็บไซต์** - ลิงก์เว็บไซต์
    3. **อีเมล** - สร้าง QR สำหรับส่งอีเมล
    4. **เบอร์โทรศัพท์** - สร้าง QR สำหรับโทรออก
    5. **Wi-Fi** - สร้าง QR สำหรับเชื่อมต่อ Wi-Fi
    6. **SMS** - สร้าง QR สำหรับส่ง SMS
    7. **Location** - สร้าง QR สำหรับตำแหน่งบน Google Maps
    
    ### ฟีเจอร์พิเศษ:
    - ✅ ปรับแต่งสี QR Code
    - ✅ เพิ่มโลโก้ตรงกลาง QR Code
    - ✅ ปรับขนาดและความละเอียด
    - ✅ ดาวน์โหลดเป็นไฟล์ PNG
    """)

# เลือกประเภท QR Code
st.subheader("🎯 เลือกประเภท QR Code")

qr_type = st.selectbox(
    "ประเภทข้อมูล",
    [
        "📝 ข้อความธรรมดา (Text)",
        "🌐 URL/เว็บไซต์",
        "📧 อีเมล (Email)",
        "📞 เบอร์โทรศัพท์ (Phone)",
        "📶 Wi-Fi",
        "💬 SMS",
        "📍 ตำแหน่งที่ตั้ง (Location)",
        "💳 vCard (นามบัตรดิจิทัล)"
    ]
)

st.markdown("---")

# ตัวแปรสำหรับเก็บข้อมูล QR
qr_data = ""

# === ฟอร์มตามประเภท ===

if "ข้อความธรรมดา" in qr_type:
    st.subheader("📝 ข้อความธรรมดา")
    qr_data = st.text_area(
        "กรอกข้อความที่ต้องการ",
        value="Hello, World!",
        height=100,
        help="ข้อความใดๆ ที่ต้องการเก็บใน QR Code"
    )

elif "URL" in qr_type:
    st.subheader("🌐 URL/เว็บไซต์")
    url = st.text_input(
        "URL",
        value="https://www.google.com",
        placeholder="https://example.com"
    )
    qr_data = url

elif "อีเมล" in qr_type:
    st.subheader("📧 อีเมล")
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("อีเมล", value="example@email.com")
    with col2:
        subject = st.text_input("หัวข้อ", value="")
    body = st.text_area("เนื้อหา", value="", height=100)
    
    qr_data = f"mailto:{email}?subject={subject}&body={body}"

elif "เบอร์โทรศัพท์" in qr_type:
    st.subheader("📞 เบอร์โทรศัพท์")
    phone = st.text_input(
        "เบอร์โทรศัพท์",
        value="+66812345678",
        placeholder="+66812345678"
    )
    qr_data = f"tel:{phone}"

elif "Wi-Fi" in qr_type:
    st.subheader("📶 Wi-Fi")
    col1, col2 = st.columns(2)
    with col1:
        wifi_ssid = st.text_input("ชื่อ Wi-Fi (SSID)", value="MyWiFi")
        wifi_password = st.text_input("รหัสผ่าน", value="password123", type="password")
    with col2:
        wifi_type = st.selectbox("ประเภทความปลอดภัย", ["WPA", "WEP", "nopass"])
        wifi_hidden = st.checkbox("ซ่อน SSID")
    
    hidden = "true" if wifi_hidden else "false"
    qr_data = f"WIFI:T:{wifi_type};S:{wifi_ssid};P:{wifi_password};H:{hidden};;"

elif "SMS" in qr_type:
    st.subheader("💬 SMS")
    col1, col2 = st.columns(2)
    with col1:
        sms_number = st.text_input("เบอร์โทรศัพท์", value="+66812345678")
    with col2:
        sms_message = st.text_area("ข้อความ", value="Hello!", height=100)
    
    qr_data = f"SMSTO:{sms_number}:{sms_message}"

elif "ตำแหน่งที่ตั้ง" in qr_type:
    st.subheader("📍 ตำแหน่งที่ตั้ง (Google Maps)")
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.text_input("Latitude", value="13.7563")
    with col2:
        longitude = st.text_input("Longitude", value="100.5018")
    
    qr_data = f"geo:{latitude},{longitude}"

elif "vCard" in qr_type:
    st.subheader("💳 vCard (นามบัตรดิจิทัล)")
    col1, col2 = st.columns(2)
    with col1:
        vcard_name = st.text_input("ชื่อ-นามสกุล", value="John Doe")
        vcard_tel = st.text_input("โทรศัพท์", value="+66812345678")
        vcard_email = st.text_input("อีเมล", value="john@example.com")
    with col2:
        vcard_org = st.text_input("บริษัท/องค์กร", value="My Company")
        vcard_title = st.text_input("ตำแหน่ง", value="Manager")
        vcard_url = st.text_input("เว็บไซต์", value="https://example.com")
    
    qr_data = f"""BEGIN:VCARD
VERSION:3.0
FN:{vcard_name}
ORG:{vcard_org}
TITLE:{vcard_title}
TEL:{vcard_tel}
EMAIL:{vcard_email}
URL:{vcard_url}
END:VCARD"""

# === ตั้งค่า QR Code ===

st.markdown("---")
st.subheader("🎨 ปรับแต่ง QR Code")

col1, col2, col3 = st.columns(3)

with col1:
    box_size = st.slider("ขนาด", 5, 20, 10, help="ขนาดของแต่ละกล่องใน QR Code")
    border = st.slider("ขอบ", 1, 10, 4, help="ขนาดขอบรอบ QR Code")

with col2:
    fill_color = st.color_picker("สีหลัก", "#000000")
    back_color = st.color_picker("สีพื้นหลัง", "#FFFFFF")

with col3:
    add_logo = st.checkbox("เพิ่มโลโก้", help="เพิ่มรูปภาพตรงกลาง QR Code")
    logo_file = None
    if add_logo:
        logo_file = st.file_uploader(
            "อัพโหลดโลโก้",
            type=["png", "jpg", "jpeg"],
            help="แนะนำใช้รูปสี่เหลี่ยมจัตุรัส"
        )

# === สร้าง QR Code ===

st.markdown("---")

if st.button("🎨 สร้าง QR Code", type="primary"):
    if qr_data:
        try:
            with st.spinner("กำลังสร้าง QR Code..."):
                # สร้าง QR Code
                if add_logo and logo_file:
                    qr_img = generate_qr_with_logo(qr_data, logo_file, box_size, border)
                else:
                    qr_img = generate_qr_code(qr_data, box_size, border, fill_color, back_color)
                
                # เก็บใน session state
                st.session_state['qr_image'] = qr_img
                st.session_state['qr_data'] = qr_data
                
                st.success("✅ สร้าง QR Code สำเร็จ!")
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
    else:
        st.warning("⚠️ กรุณากรอกข้อมูลก่อนสร้าง QR Code")

# === แสดงผลลัพธ์ ===

if 'qr_image' in st.session_state:
    st.markdown("---")
    st.subheader("📱 QR Code ของคุณ")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.image(st.session_state['qr_image'], use_container_width=True)
    
    # ข้อมูลที่เก็บ
    with st.expander("📄 ข้อมูลใน QR Code"):
        st.code(st.session_state['qr_data'], language="text")
    
    # ปุ่มดาวน์โหลด
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        # แปลงรูปเป็น bytes
        buf = io.BytesIO()
        st.session_state['qr_image'].save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label="⬇️ ดาวน์โหลด QR Code",
            data=byte_im,
            file_name="qrcode.png",
            mime="image/png",
            use_container_width=True
        )

# === ตัวอย่าง ===

st.markdown("---")
st.markdown("### 📝 ตัวอย่างการใช้งาน")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🌐 URL/เว็บไซต์:**")
    st.code("https://www.google.com", language="text")
    
    st.markdown("**📧 อีเมล:**")
    st.code("mailto:test@example.com", language="text")
    
    st.markdown("**📞 โทรศัพท์:**")
    st.code("tel:+66812345678", language="text")

with col2:
    st.markdown("**📶 Wi-Fi:**")
    st.code("WIFI:T:WPA;S:MyWiFi;P:password;;", language="text")
    
    st.markdown("**📍 ตำแหน่ง:**")
    st.code("geo:13.7563,100.5018", language="text")
    
    st.markdown("**💬 SMS:**")
    st.code("SMSTO:+66812345678:Hello!", language="text")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>Made with ❤️ using Streamlit | 📱 QR Code Generator</p>
    <p style='font-size: 12px;'>💡 Tips: QR Code ที่มี Error Correction สูงสามารถทำงานได้แม้เสียหายบางส่วน</p>
</div>
""", unsafe_allow_html=True)
