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
    """ตัดพื้นหลังสีขาวออกและทำให้โปร่งใส"""
    image = image.convert("RGBA")
    datas = image.getdata()
    
    newData = []
    for item in datas:
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    
    image.putdata(newData)
    
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    
    return image

def generate_qr(url, color="#000000", bg_color="#FFFFFF", box_size=10, border=4):
    """
    สร้าง QR Code
    
    Args:
        url: ลิงก์ที่จะเข้ารหัส
        color: สี QR Code
        bg_color: สีพื้นหลัง
        box_size: ขนาดของแต่ละช่อง (ยิ่งมากยิ่งใหญ่)
        border: ขนาดขอบ (จำนวนช่อง)
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=color, back_color=bg_color)
    return img.convert('RGB')

def add_logo_no_bg(qr_img, logo, size_percent=25, remove_bg=True, threshold=240):
    """
    เพิ่มโลโก้ตรงกลาง QR Code โดยไม่มีกรอบสีขาว
    วางโลโก้โดยตรงบน QR Code
    """
    qr_img = qr_img.convert('RGBA')
    
    # ตัดพื้นหลังสีขาวออก (ถ้าเปิดใช้งาน)
    if remove_bg:
        logo = remove_white_background(logo, threshold)
    else:
        logo = logo.convert('RGBA')
    
    qr_width, qr_height = qr_img.size
    logo_size = int(qr_width * (size_percent / 100))
    
    # ปรับขนาดโลโก้ (รักษาอัตราส่วน)
    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # คำนวณตำแหน่งกึ่งกลาง
    logo_x = (qr_width - logo.width) // 2
    logo_y = (qr_height - logo.height) // 2
    
    # วางโลโก้โดยตรงบน QR Code (ใช้ alpha channel)
    qr_img.paste(logo, (logo_x, logo_y), logo)
    
    return qr_img.convert('RGB')

def add_logo_with_bg(qr_img, logo, size_percent=25, remove_bg=True, threshold=240, padding=10):
    """
    เพิ่มโลโก้ตรงกลาง QR Code พร้อมกรอบสีขาว
    """
    qr_img = qr_img.convert('RGB')
    
    # ตัดพื้นหลังสีขาวออก
    if remove_bg:
        logo = remove_white_background(logo, threshold)
    
    qr_width, qr_height = qr_img.size
    logo_size = int(qr_width * (size_percent / 100))
    
    # ปรับขนาดโลโก้
    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    # สร้างพื้นหลังสีขาวรอบโลโก้
    bg_size = logo.width + padding * 2
    bg = Image.new('RGB', (bg_size, bg_size), 'white')
    
    # วางโลโก้กึ่งกลางบนพื้นหลัง
    logo_x = (bg_size - logo.width) // 2
    logo_y = (bg_size - logo.height) // 2
    
    if logo.mode == 'RGBA':
        bg.paste(logo, (logo_x, logo_y), logo)
    else:
        bg.paste(logo, (logo_x, logo_y))
    
    # วางลงบน QR Code
    qr_x = (qr_width - bg_size) // 2
    qr_y = (qr_height - bg_size) // 2
    qr_img.paste(bg, (qr_x, qr_y))
    
    return qr_img

def main():
    st.title("🔲 QR Code Generator")
    st.markdown("สร้าง QR Code พร้อมโลโก้ | ปรับแต่งได้ทุกอย่าง")
    st.success("✅ All dependencies loaded!")
    
    # Sidebar
    st.sidebar.header("⚙️ ตั้งค่า")
    
    # URL Input
    url = st.sidebar.text_input(
        "🔗 ใส่ URL:", 
        "https://streamlit.io",
        placeholder="https://example.com"
    )
    
    st.sidebar.divider()
    
    # ขนาด QR Code
    st.sidebar.subheader("📏 ขนาด QR Code")
    
    box_size = st.sidebar.slider(
        "ขนาดพิกเซลของแต่ละช่อง:",
        min_value=5,
        max_value=30,
        value=10,
        step=1,
        help="ค่าสูง = QR Code ใหญ่ขึ้น"
    )
    
    border = st.sidebar.slider(
        "ขนาดขอบ (จำนวนช่อง):",
        min_value=1,
        max_value=10,
        value=4,
        step=1,
        help="ระยะห่างระหว่าง QR Code กับขอบ"
    )
    
    st.sidebar.divider()
    
    # สี
    st.sidebar.subheader("🎨 ปรับแต่งสี")
    qr_color = st.sidebar.color_picker("สี QR Code:", "#000000")
    bg_color = st.sidebar.color_picker("สีพื้นหลัง:", "#FFFFFF")
    
    st.sidebar.divider()
    
    # โลโก้
    st.sidebar.subheader("🖼️ โลโก้")
    logo_file = st.sidebar.file_uploader(
        "อัพโหลดโลโก้:",
        type=['png', 'jpg', 'jpeg'],
        help="รองรับ PNG, JPG, JPEG"
    )
    
    if logo_file:
        logo_size = st.sidebar.slider(
            "ขนาดโลโก้ (%):", 
            15, 40, 25, 1,
            help="เปอร์เซ็นต์ของขนาด QR Code"
        )
        
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
                help="ค่าสูง = ตัดเฉพาะสีขาวจัด"
            )
        else:
            threshold = 240
        
        st.sidebar.divider()
        st.sidebar.subheader("🎯 รูปแบบโลโก้")
        
        logo_style = st.sidebar.radio(
            "เลือกรูปแบบ:",
            ["ไม่มีกรอบสีขาว (วางตรงบน QR)", "มีกรอบสีขาว"],
            index=0,
            help="แนะนำ: ใช้แบบไม่มีกรอบสำหรับโลโก้ที่ตัดพื้นหลังแล้ว"
        )
        
        if logo_style == "มีกรอบสีขาว":
            padding = st.sidebar.slider(
                "ขนาดกรอบสีขาว (px):",
                5, 30, 10, 1
            )
        else:
            padding = 0
            
    else:
        logo_size = 25
        remove_bg = True
        threshold = 240
        logo_style = "ไม่มีกรอบสีขาว (วางตรงบน QR)"
        padding = 10
    
    # พื้นที่หลัก
    if url:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📱 ตัวอย่าง QR Code")
            try:
                # สร้าง QR Code
                qr_img = generate_qr(url, qr_color, bg_color, box_size, border)
                
                # เพิ่มโลโก้
                if logo_file:
                    logo = Image.open(logo_file)
                    
                    if logo_style == "ไม่มีกรอบสีขาว (วางตรงบน QR)":
                        qr_img = add_logo_no_bg(qr_img, logo, logo_size, remove_bg, threshold)
                    else:
                        qr_img = add_logo_with_bg(qr_img, logo, logo_size, remove_bg, threshold, padding)
                
                st.image(qr_img, use_container_width=True)
                st.success("✅ สร้าง QR Code สำเร็จ!")
                
                # แสดงขนาดจริง
                actual_size = qr_img.size
                st.caption(f"ขนาดจริง: {actual_size[0]} x {actual_size[1]} พิกเซล")
                
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {e}")
                st.exception(e)
        
        with col2:
            st.subheader("💾 ดาวน์โหลด")
            
            # แสดงตัวอย่างโลโก้
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
                # สร้าง QR Code สำหรับดาวน์โหลด
                qr_img = generate_qr(url, qr_color, bg_color, box_size, border)
                
                if logo_file:
                    logo = Image.open(logo_file)
                    
                    if logo_style == "ไม่มีกรอบสีขาว (วางตรงบน QR)":
                        qr_img = add_logo_no_bg(qr_img, logo, logo_size, remove_bg, threshold)
                    else:
                        qr_img = add_logo_with_bg(qr_img, logo, logo_size, remove_bg, threshold, padding)
                
                # บันทึกเป็น PNG
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG", optimize=True, quality=95)
                
                st.download_button(
                    "📥 ดาวน์โหลด QR Code (PNG)",
                    data=buf.getvalue(),
                    file_name=f"qr_code_{box_size}x{box_size}.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # ข้อมูล QR Code
                st.info(f"""
                **ข้อมูล QR Code:**
                - ขนาดไฟล์: {qr_img.size[0]} x {qr_img.size[1]} px
                - ขนาดช่อง: {box_size} px
                - ขนาดขอบ: {border} ช่อง
                - URL: `{url[:35]}...` {'(ย่อ)' if len(url) > 35 else ''}
                - มีโลโก้: {'✅ ใช่' if logo_file else '❌ ไม่มี'}
                - รูปแบบโลโก้: {logo_style}
                - ตัดพื้นหลัง: {'✅ เปิด' if remove_bg and logo_file else '❌ ปิด'}
                """)
                
                # คำแนะนำขนาดพิมพ์
                st.success(f"""
                **แนะนำสำหรับการพิมพ์:**
                - ขนาดขั้นต่ำ: 2 x 2 ซม. (300 DPI)
                - ขนาดที่แนะนำ: 3 x 3 ซม. ขึ้นไป
                - ทดสอบสแกนก่อนพิมพ์จำนวนมาก
                """)
                
            except Exception as e:
                st.error(f"❌ ไม่สามารถสร้างไฟล์ดาวน์โหลด: {e}")
    
    else:
        st.info("👈 กรุณาใส่ URL ในแถบด้านซ้ายเพื่อสร้าง QR Code")
    
    # คำแนะนำ
    with st.expander("📖 คู่มือการใช้งาน"):
        st.markdown("""
        ### 🚀 ขั้นตอนการใช้งาน:
        
        #### 1️⃣ **ตั้งค่าพื้นฐาน**
        - ใส่ URL ที่ต้องการเข้ารหัส
        - ปรับขนาด QR Code ตามความต้องการ
        - เลือกสีที่เหมาะสม
        
        #### 2️⃣ **เพิ่มโลโก้ (ถ้าต้องการ)**
        - อัพโหลดไฟล์รูปภาพ
        - เปิดการตัดพื้นหลังสีขาว
        - ปรับขนาดโลโก้ให้เหมาะสม (20-30%)
        
        #### 3️⃣ **เลือกรูปแบบโลโก้**
        - **ไม่มีกรอบสีขาว**: โลโก้วางตรงบน QR Code (แนะนำ!)
        - **มีกรอบสีขาว**: โลโก้มีพื้นหลังสีขาวรอบๆ
        
        #### 4️⃣ **ดาวน์โหลดและใช้งาน**
        - ดาวน์โหลด QR Code
        - ทดสอบสแกนก่อนใช้งาน
        
        ---
        
        ### 💡 เคล็ดลับ:
        
        #### 📏 **ขนาด QR Code:**
        - **5-10**: เหมาะสำหรับเว็บไซต์ (ขนาดเล็ก)
        - **10-15**: ⭐ แนะนำสำหรับงานพิมพ์ทั่วไป
        - **15-20**: สำหรับป้ายขนาดใหญ่
        - **20-30**: สำหรับโปสเตอร์หรือบิลบอร์ด
        
        #### 🎨 **การเลือกสี:**
        - ใช้สีตัดกันชัดเจน (เช่น ดำ-ขาว)
        - หลีกเลี่ยงสีอ่อนเกินไป
        - ทดสอบสีก่อนพิมพ์จำนวนมาก
        
        #### 🖼️ **โลโก้:**
        - ขนาดที่แนะนำ: 20-30% ของ QR Code
        - ใช้ไฟล์ PNG พื้นหลังโปร่งใสจะดีที่สุด
        - เลือก "ไม่มีกรอบสีขาว" สำหรับผลลัพธ์สวยงาม
        - ตัดพื้นหลังสีขาวออกก่อนอัปโหลด
        
        #### ✂️ **การตัดพื้นหลัง:**
        - **ค่าความไว 240-255**: ตัดเฉพาะสีขาวจัด ⭐ แนะนำ
        - **ค่าความไว 220-240**: ตัดสีอ่อน, ครีม
        - **ค่าความไว 200-220**: ตัดสีอ่อนมาก (ระวังตัดโลโก้ไปด้วย)
        
        ---
        
        ### ⚠️ ข้อควรระวัง:
        
        ❗ **ทดสอบการสแกน QR Code เสมอก่อนใช้งานจริง**
        
        ❗ **ขนาดพิมพ์ขั้นต่ำ 2x2 ซม.** เพื่อให้สแกนได้ชัดเจน
        
        ❗ **โลโก้ใหญ่เกินไป** อาจทำให้สแกนไม่ได้
        
        ❗ **ตรวจสอบ URL** ให้ถูกต้องก่อนนำไปใช้
        
        ---
        
        ### 🎯 ตัวอย่างการใช้งาน:
        
        ✅ นามบัตร (QR Code ขนาด 2-3 ซม.)
        
        ✅ โปสเตอร์ (QR Code ขนาด 5-8 ซม.)
        
        ✅ เมนูร้านอาหาร (QR Code ขนาด 3-4 ซม.)
        
        ✅ ป้ายประชาสัมพันธ์ (QR Code ขนาด 8-15 ซม.)
        
        ✅ บรรจุภัณฑ์สินค้า (QR Code ขนาด 2-4 ซม.)
        
        ✅ สติกเกอร์ (QR Code ขนาด 3-5 ซม.)
        """)
    
    # Footer
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("💡 ทดสอบ QR Code ด้วยมือถือหลายเครื่อง")
    with col2:
        st.caption("🎨 ใช้สีตัดกันเพื่อการสแกนที่ดี")
    with col3:
        st.caption("📏 ขนาดพิมพ์ขั้นต่ำ 2x2 ซม.")

if __name__ == "__main__":
    main()
