import streamlit as st
import ipaddress

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="IP Validator",
    page_icon="🔍",
    layout="centered"
)

# หัวข้อ
st.title("🔍 IP Address Validator")
st.markdown("---")

# คำอธิบาย
st.markdown("""
### วิธีใช้งาน
1. กรอก IP Address ในช่องด้านล่าง
2. กดปุ่ม **ตรวจสอบ**
3. ดูผลลัพธ์
""")

# Input
col1, col2 = st.columns([3, 1])

with col1:
    ip_input = st.text_input(
        "IP Address",
        value="192.168.1.1",
        placeholder="เช่น 192.168.1.1"
    )

with col2:
    st.write("")  # spacing
    st.write("")  # spacing
    check_button = st.button("🔍 ตรวจสอบ", use_container_width=True)

# ตรวจสอบเมื่อกดปุ่ม
if check_button and ip_input:
    try:
        ip_obj = ipaddress.ip_address(ip_input)
        
        # แสดงผลสำเร็จ
        st.success(f"✅ IP Address ถูกต้อง!")
        
        # แสดงรายละเอียด
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("IP Address", str(ip_obj))
            st.metric("Version", f"IPv{ip_obj.version}")
            
        with col2:
            st.metric(
                "ประเภท", 
                "Private" if ip_obj.is_private else "Public"
            )
            st.metric(
                "Loopback",
                "Yes" if ip_obj.is_loopback else "No"
            )
        
        # แสดงข้อมูลเพิ่มเติม
        st.markdown("---")
        st.subheader("📊 รายละเอียดเพิ่มเติม")
        
        info_data = {
            "Private IP": "✅" if ip_obj.is_private else "❌",
            "Loopback": "✅" if ip_obj.is_loopback else "❌",
            "Multicast": "✅" if ip_obj.is_multicast else "❌",
            "Link-local": "✅" if ip_obj.is_link_local else "❌",
        }
        
        for key, value in info_data.items():
            st.text(f"{key}: {value}")
            
    except ValueError as e:
        st.error(f"❌ IP Address ไม่ถูกต้อง!")
        st.code(str(e))

# ตัวอย่าง
st.markdown("---")
st.subheader("📝 ตัวอย่าง IP Address")

examples = {
    "Private IP": "192.168.1.1",
    "Public IP": "8.8.8.8",
    "Loopback": "127.0.0.1",
    "IPv6": "2001:db8::1"
}

for name, ip in examples.items():
    if st.button(f"{name}: {ip}"):
        st.rerun()
