import streamlit as st
import ipaddress
import socket
import re

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="IP Validator & DNS Lookup",
    page_icon="🔍",
    layout="centered"
)

# CSS สำหรับแต่งหน้าตา
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        padding: 20px 0;
    }
    .success-box {
        padding: 20px;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-box {
        padding: 20px;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
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

# ฟังก์ชันตรวจสอบว่าเป็น Domain หรือ IP
def is_valid_domain(domain):
    """ตรวจสอบว่าเป็น domain name ที่ถูกต้องหรือไม่"""
    domain_pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    )
    return bool(domain_pattern.match(domain))

# ฟังก์ชันแปลง Domain เป็น IP
def resolve_domain(domain):
    """แปลง domain name เป็น IP address"""
    try:
        # ลบ protocol (http://, https://) ถ้ามี
        domain = re.sub(r'^https?://', '', domain)
        # ลบ path ถ้ามี
        domain = domain.split('/')[0]
        
        # แปลงเป็น IP
        ip_address = socket.gethostbyname(domain)
        
        # หา IP ทั้งหมด
        all_ips = socket.gethostbyname_ex(domain)[2]
        
        return {
            'success': True,
            'primary_ip': ip_address,
            'all_ips': all_ips,
            'domain': domain
        }
    except socket.gaierror as e:
        return {
            'success': False,
            'error': f"ไม่สามารถแปลง domain '{domain}' เป็น IP ได้",
            'details': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'error': "เกิดข้อผิดพลาด",
            'details': str(e)
        }

# ฟังก์ชัน Reverse DNS Lookup
def reverse_dns(ip):
    """หาชื่อ domain จาก IP"""
    try:
        hostname = socket.gethostbyaddr(ip)
        return {
            'success': True,
            'hostname': hostname[0],
            'aliases': hostname[1]
        }
    except:
        return {
            'success': False,
            'hostname': None
        }

# ฟังก์ชันตรวจสอบ IP
def validate_ip_address(ip):
    """ตรวจสอบ IP Address และแสดงรายละเอียด"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        # Reverse DNS Lookup
        reverse_info = reverse_dns(ip)
        
        return {
            'valid': True,
            'ip': str(ip_obj),
            'version': ip_obj.version,
            'is_private': ip_obj.is_private,
            'is_loopback': ip_obj.is_loopback,
            'is_multicast': ip_obj.is_multicast,
            'is_global': ip_obj.is_global,
            'is_link_local': ip_obj.is_link_local,
            'hostname': reverse_info.get('hostname'),
            'aliases': reverse_info.get('aliases', [])
        }
    except ValueError as e:
        return {
            'valid': False,
            'error': str(e)
        }

# === UI หลัก ===

st.markdown('<h1 class="main-header">🔍 IP Validator & DNS Lookup</h1>', unsafe_allow_html=True)
st.markdown("---")

# คำอธิบาย
with st.expander("📖 วิธีใช้งาน"):
    st.markdown("""
    ### โปรแกรมนี้สามารถ:
    1. **ตรวจสอบ IP Address** - ตรวจสอบความถูกต้องและรายละเอียดของ IP
    2. **แปลง Domain เป็น IP** - กรอกชื่อเว็บไซต์แล้วแปลงเป็น IP Address
    3. **Reverse DNS Lookup** - หาชื่อ domain จาก IP Address
    
    ### ตัวอย่างการใช้งาน:
    - **IP Address:** `8.8.8.8`, `192.168.1.1`, `2001:4860:4860::8888`
    - **Domain Name:** `google.com`, `facebook.com`, `github.com`
    - **URL:** `https://www.google.com` (จะแปลงเป็น domain อัตโนมัติ)
    """)

# เลือกโหมด
st.subheader("🎯 เลือกโหมดการใช้งาน")
mode = st.radio(
    "เลือกสิ่งที่ต้องการตรวจสอบ:",
    ["🌐 กรอก Domain Name (เช่น google.com)", "📍 กรอก IP Address โดยตรง"],
    horizontal=True
)

st.markdown("---")

# โหมด Domain Name
if "Domain" in mode:
    st.subheader("🌐 DNS Lookup: แปลง Domain เป็น IP")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        domain_input = st.text_input(
            "Domain Name หรือ URL",
            value="google.com",
            placeholder="เช่น google.com หรือ https://www.google.com",
            help="กรอกชื่อเว็บไซต์ที่ต้องการตรวจสอบ"
        )
    
    with col2:
        st.write("")
        st.write("")
        lookup_button = st.button("🔍 ค้นหา IP", use_container_width=True, type="primary")
    
    if lookup_button and domain_input:
        with st.spinner('กำลังค้นหา IP Address...'):
            # แปลง Domain เป็น IP
            dns_result = resolve_domain(domain_input)
            
            if dns_result['success']:
                st.success(f"✅ พบ IP Address สำหรับ '{dns_result['domain']}'")
                
                # แสดง IP หลัก
                st.markdown("### 🎯 IP Address หลัก")
                st.code(dns_result['primary_ip'], language="text")
                
                # แสดง IP ทั้งหมด (ถ้ามีหลาย IP)
                if len(dns_result['all_ips']) > 1:
                    st.markdown("### 📋 IP Address ทั้งหมด")
                    for idx, ip in enumerate(dns_result['all_ips'], 1):
                        st.text(f"{idx}. {ip}")
                
                # ตรวจสอบ IP แต่ละตัว
                st.markdown("---")
                st.markdown("### 🔬 รายละเอียด IP Address")
                
                for ip in dns_result['all_ips']:
                    with st.expander(f"📊 วิเคราะห์ {ip}"):
                        ip_info = validate_ip_address(ip)
                        
                        if ip_info['valid']:
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Version", f"IPv{ip_info['version']}")
                                st.metric("Private", "✅" if ip_info['is_private'] else "❌")
                            
                            with col2:
                                st.metric("Loopback", "✅" if ip_info['is_loopback'] else "❌")
                                st.metric("Multicast", "✅" if ip_info['is_multicast'] else "❌")
                            
                            with col3:
                                st.metric("Global", "✅" if ip_info['is_global'] else "❌")
                                st.metric("Link-Local", "✅" if ip_info['is_link_local'] else "❌")
                            
                            # แสดง Hostname ถ้ามี
                            if ip_info['hostname']:
                                st.info(f"🏷️ **Hostname:** {ip_info['hostname']}")
                
            else:
                st.error(f"❌ {dns_result['error']}")
                if 'details' in dns_result:
                    st.code(dns_result['details'])

# โหมด IP Address
else:
    st.subheader("📍 ตรวจสอบ IP Address")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ip_input = st.text_input(
            "IP Address",
            value="8.8.8.8",
            placeholder="เช่น 192.168.1.1 หรือ 2001:4860:4860::8888",
            help="กรอก IPv4 หรือ IPv6 ที่ต้องการตรวจสอบ"
        )
    
    with col2:
        st.write("")
        st.write("")
        check_button = st.button("🔍 ตรวจสอบ", use_container_width=True, type="primary")
    
    if check_button and ip_input:
        ip_info = validate_ip_address(ip_input)
        
        if ip_info['valid']:
            st.success(f"✅ IP Address ถูกต้อง!")
            
            # แสดงข้อมูลหลัก
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("IP Address", ip_info['ip'])
                st.metric("Version", f"IPv{ip_info['version']}")
            
            with col2:
                ip_type = "🔒 Private" if ip_info['is_private'] else "🌍 Public"
                if ip_info['is_loopback']:
                    ip_type = "🔁 Loopback"
                st.metric("ประเภท", ip_type)
                st.metric("Global", "✅" if ip_info['is_global'] else "❌")
            
            with col3:
                st.metric("Multicast", "✅" if ip_info['is_multicast'] else "❌")
                st.metric("Link-Local", "✅" if ip_info['is_link_local'] else "❌")
            
            # Reverse DNS
            st.markdown("---")
            st.markdown("### 🔄 Reverse DNS Lookup")
            if ip_info['hostname']:
                st.success(f"🏷️ **Hostname:** {ip_info['hostname']}")
                if ip_info['aliases']:
                    st.info(f"📝 **Aliases:** {', '.join(ip_info['aliases'])}")
            else:
                st.warning("⚠️ ไม่พบชื่อ hostname สำหรับ IP นี้")
            
            # รายละเอียดเพิ่มเติม
            st.markdown("---")
            st.markdown("### 📊 รายละเอียดทั้งหมด")
            
            details = {
                "IP Address": ip_info['ip'],
                "Version": f"IPv{ip_info['version']}",
                "Private IP": "✅ ใช่" if ip_info['is_private'] else "❌ ไม่ใช่",
                "Public IP": "✅ ใช่" if ip_info['is_global'] else "❌ ไม่ใช่",
                "Loopback": "✅ ใช่" if ip_info['is_loopback'] else "❌ ไม่ใช่",
                "Multicast": "✅ ใช่" if ip_info['is_multicast'] else "❌ ไม่ใช่",
                "Link-Local": "✅ ใช่" if ip_info['is_link_local'] else "❌ ไม่ใช่",
            }
            
            for key, value in details.items():
                st.text(f"{key:.<30} {value}")
                
        else:
            st.error(f"❌ IP Address ไม่ถูกต้อง!")
            st.code(ip_info['error'])

# ส่วนตัวอย่าง
st.markdown("---")
st.markdown("### 📝 ตัวอย่างที่น่าสนใจ")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🌐 Domain Names:**")
    domains = [
        "google.com",
        "facebook.com", 
        "github.com",
        "cloudflare.com",
        "netflix.com"
    ]
    for domain in domains:
        st.text(f"• {domain}")

with col2:
    st.markdown("**📍 IP Addresses:**")
    ips = [
        "8.8.8.8 (Google DNS)",
        "1.1.1.1 (Cloudflare DNS)",
        "192.168.1.1 (Private)",
        "127.0.0.1 (Loopback)",
        "2001:4860:4860::8888 (IPv6)"
    ]
    for ip in ips:
        st.text(f"• {ip}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>Made with ❤️ using Streamlit | 🔍 IP Validator & DNS Lookup Tool</p>
</div>
""", unsafe_allow_html=True)
