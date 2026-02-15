import streamlit as st
import io
from PIL import Image

st.set_page_config(page_title="QR Code Generator", page_icon="🔲", layout="wide")

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

if not QR_AVAILABLE:
    st.error("❌ QR Code library not installed!")
    st.info("""
    **To fix this:**
    
    1. Make sure `requirements.txt` exists in your GitHub repository root
    2. It should contain:
       ```
       qrcode
       pillow
       ```
    3. Reboot your app on Streamlit Cloud
    """)
    st.stop()

def remove_white_background(image, threshold=240):
    """
    ตัดพื้นหลังสีขาวออกและทำให้โปร่งใส
    
    Args:
        image: PIL Image object
        threshold: ค่าความสว่างของสีขาว (0-255)
    
    Returns:
        PIL Image with transparent background
    """
    # แปลงเป็น RGBA (รองรับความโปร่งใส)
    image = image.convert("RGBA")
    
    # ดึงข้อมูล pixel
    datas = image.getdata()
    
    newData = []
    for item in datas:
        # ตรวจสอบว่าเป็นสีขาวหรือใกล้เคียง
        # ถ้า R, G, B มีค่ามากกว่า threshold = สีขาว
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            # แปลงเป็น transparent (alpha = 0)
            newData.append((255, 255, 255, 0))
        else:
            # เก็บสีเดิม
            newData.append(item)
    
    # อัพเดทข้อมูล pixel
    image.putdata(newData)
    
    # ตัดส่วนที่โปร่งใสออก (crop to content)
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    
    return image

def generate_qr(url, color="#000000", bg_color="#FFFFFF"):
    """Generate QR code with qrcode library"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=color, back_color=bg_color)
    return img.convert('RGB')

def add_logo(qr_img, logo, size_percent=25, remove_bg=True, threshold=240):
    """
    เพิ่มโลโก้ตรงกลาง QR Code
    
    Args:
        qr_img: QR Code image
        logo: Logo image
        size_percent: ขนาดโลโก้เป็น % ของ QR Code
        remove_bg: เปิด/ปิดการตัดพื้นหลังสีขาว
        threshold: ค่าความไวในการตัดพื้นหลัง
    """
    qr_img = qr_img.convert('RGB')
    
    # ตัดพื้นหลังสีขาวออก (ถ้าเปิดใช้งาน)
    if remove_bg:
        logo = remove_white_background(logo, threshold)
    
    qr_width, qr_height = qr_img.size
    logo_size = int(qr_width * (size_percent / 100))
    
    # ปรับขนาดโลโก้ (รักษาอัตราส่วน)
    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # สร้างพื้นหลังสีขาวรอบโลโก้ (padding เล็กน้อย)
    padding = 10
    bg_size = logo.width + padding * 2
    bg = Image.new('RGB', (bg_size, bg_size), 'white')
    
    # วางโลโก้กึ่งกลางบนพื้นหลังสีขาว
    logo_x = (bg_size - logo.width) // 2
    logo_y = (bg_size - logo.height) // 2
    
    if logo.mode == 'RGBA':
        # ใช้ alpha channel สำหรับความโปร่งใส
        bg.paste(logo, (logo_x, logo_y), logo)
    else:
        bg.paste(logo, (logo_x, logo_y))
    
    # วางลงบน QR Code กึ่งกลาง
    qr_x = (qr_width - bg_size) // 2
    qr_y = (qr_height - bg_size) // 2
    qr_img.paste(bg, (qr_x, qr_y))
    
    return qr_img

def main():
    st.title("🔲 QR Code Generator")
    st.markdown("สร้าง QR Code พร้อมโลโก้ | รองรับการตัดพื้นหลังสีขาวอัตโนมัติ")
    st.success("✅ All dependencies loaded!")
    
    # Sidebar
    st.sidebar.header("⚙️ ตั้งค่า")
    url = st.sidebar.text_input(
        "🔗 ใส่ URL:", 
        "https://streamlit.io",
        placeholder="https://example.com"
    )
    
    st.sidebar.divider()
    
    st.sidebar.subheader("🎨 ปรับแต่งสี")
    qr_color = st.sidebar.color_picker("สี QR Code:", "#000000")
    bg_color = st.sidebar.color_picker("สีพื้นหลัง:", "#FFFFFF")
    
    st.sidebar.divider()
    
    st.sidebar.subheader("🖼️ โลโก้")
    logo_file = st.sidebar.file_uploader(
        "อัพโหลดโลโก้:",
        type=['png', 'jpg', 'jpeg'],
        help="รองรับ PNG, JPG, JPEG"
    )
    
    if logo_file:
        logo_size = st.sidebar.slider("ขนาดโลโก้ (%):", 15, 40, 25, 1)
        
        st.sidebar.divider()
        st.sidebar.subheader("✂️ ตัดพื้นหลัง")
        
        remove_bg = st.sidebar.checkbox(
            "ตัดพื้นหลังสีขาวออก",
            value=True,
            help="ลบพื้นหลังสีขาวให้เป็นแบบโปร่งใส"
        )
        
        if remove_bg:
            threshold = st.sidebar.slider(
                "ความไวในการตัดพื้นหลัง:",
                200, 255, 240, 5,
                help="ค่าสูง = ตัดเฉพาะสีขาวจัด, ค่าต่ำ = ตัดสีอ่อนด้วย"
            )
        else:
            threshold = 240
    else:
        logo_size = 25
        remove_bg = True
        threshold = 240
    
    # พื้นที่หลัก
    if url:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📱 ตัวอย่าง QR Code")
            try:
                qr_img = generate_qr(url, qr_color, bg_color)
                
                if logo_file:
                    logo = Image.open(logo_file)
                    qr_img = add_logo(qr_img, logo, logo_size, remove_bg, threshold)
                
                st.image(qr_img, use_container_width=True)
                st.success("✅ สร้าง QR Code สำเร็จ!")
                
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        
        with col2:
            st.subheader("💾 ดาวน์โหลด")
            
            # แสดงตัวอย่างโลโก้ก่อน-หลังตัดพื้นหลัง
            if logo_file:
                st.write("**ตัวอย่างโลโก้:**")
                
                try:
                    original_logo = Image.open(logo_file)
                    
                    if remove_bg:
                        processed_logo = remove_white_background(original_logo.copy(), threshold)
                        
                        preview_col1, preview_col2 = st.columns(2)
                        with preview_col1:
                            st.image(original_logo, caption="ต้นฉบับ", width=120)
                        with preview_col2:
                            st.image(processed_logo, caption="ตัดพื้นหลังแล้ว", width=120)
                    else:
                        st.image(original_logo, caption="ต้นฉบับ", width=150)
                    
                    st.divider()
                except Exception as e:
                    st.warning(f"⚠️ ไม่สามารถแสดงตัวอย่างโลโก้: {e}")
            
            # ปุ่มดาวน์โหลด
            try:
                qr_img = generate_qr(url, qr_color, bg_color)
                
                if logo_file:
                    logo = Image.open(logo_file)
                    qr_img = add_logo(qr_img, logo, logo_size, remove_bg, threshold)
                
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG", optimize=True)
                
                st.download_button(
                    "📥 ดาวน์โหลด QR Code",
                    data=buf.getvalue(),
                    file_name="qr_code.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # ข้อมูล QR Code
                st.info(f"""
                **ข้อมูล QR Code:**
                - ขนาด: {qr_img.size[0]} x {qr_img.size[1]} px
                - URL: `{url[:40]}...` {'(ย่อ)' if len(url) > 40 else ''}
                - มีโลโก้: {'✅ ใช่' if logo_file else '❌ ไม่มี'}
                - ตัดพื้นหลัง: {'✅ เปิด' if remove_bg and logo_file else '❌ ปิด'}
                """)
                
            except Exception as e:
                st.error(f"❌ ไม่สามารถสร้างไฟล์ดาวน์โหลด: {e}")
    
    else:
        st.info("👈 กรุณาใส่ URL ในแถบด้านซ้ายเพื่อสร้าง QR Code")
    
    # คำแนะนำ
    with st.expander("📖 วิธีใช้งาน"):
        st.markdown("""
        ### ขั้นตอนการใช้งาน:
        
        1. **ใส่ URL** - พิมพ์ลิงก์เว็บไซต์ที่ต้องการ
        2. **ปรับสี** - เลือกสีที่เหมาะกับแบรนด์ของคุณ
        3. **อัพโหลดโลโก้** - เพิ่มโลโก้ตรงกลาง QR Code
        4. **ตัดพื้นหลัง** - เปิดใช้งานเพื่อลบพื้นสีขาว
        5. **ปรับความไว** - ตั้งค่าความไวในการตัดพื้นหลัง
        6. **ดาวน์โหลด** - บันทึก QR Code
        
        ### เคล็ดลับ:
        
        ✅ **สี:** ใช้สีตัดกัน (เช่น ดำ-ขาว) เพื่อให้สแกนง่าย
        
        ✅ **โลโก้:** ขนาดที่แนะนำคือ 20-30% ของ QR Code
        
        ✅ **การตัดพื้นหลัง:**
        - ค่าความไว 240-255 = ตัดเฉพาะสีขาวจัด
        - ค่าความไว 200-230 = ตัดสีอ่อนๆ ด้วย
        
        ✅ **การทดสอบ:** ทดสอบสแกนก่อนใช้งานจริงเสมอ
        
        ✅ **ขนาดพิมพ์:** ขนาดขั้นต่ำในการพิมพ์คือ 2x2 ซม.
        
        ### ตัวอย่างการใช้งาน:
        
        - นามบัตร
        - โปสเตอร์
        - เมนูร้านอาหาร
        - ป้ายประชาสัมพันธ์
        - บรรจุภัณฑ์สินค้า
        """)
    
    # Footer
    st.divider()
    st.caption("💡 เคล็ดลับ: ทดสอบ QR Code ด้วยมือถือหลายเครื่องก่อนพิมพ์")

if __name__ == "__main__":
    main()
