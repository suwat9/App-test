import streamlit as st
import io
from PIL import Image

st.set_page_config(page_title="QR Code Generator", page_icon="🔲", layout="wide")

try:
    import pyqrcode
except ImportError:
    st.error("❌ Missing dependency. Check requirements.txt")
    st.stop()

def generate_qr_code(url, scale=10):
    """Generate QR code"""
    qr = pyqrcode.create(url)
    buffer = io.BytesIO()
    qr.png(buffer, scale=scale)
    buffer.seek(0)
    return Image.open(buffer)

def apply_colors(img, dark_color, light_color):
    """Apply custom colors"""
    img = img.convert('RGB')
    pixels = img.load()
    
    dark_rgb = tuple(int(dark_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    light_rgb = tuple(int(light_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            if pixels[x, y] == (0, 0, 0):
                pixels[x, y] = dark_rgb
            elif pixels[x, y] == (255, 255, 255):
                pixels[x, y] = light_rgb
    
    return img

def add_logo(qr_img, logo, size_percent=25):
    """Add logo to QR code"""
    qr_img = qr_img.convert('RGB')
    qr_width, qr_height = qr_img.size
    
    logo_size = int(qr_width * (size_percent / 100))
    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    bg_size = int(logo_size * 1.2)
    bg = Image.new('RGB', (bg_size, bg_size), 'white')
    
    logo_pos = ((bg_size - logo.width) // 2, (bg_size - logo.height) // 2)
    if logo.mode == 'RGBA':
        bg.paste(logo, logo_pos, logo)
    else:
        bg.paste(logo, logo_pos)
    
    qr_pos = ((qr_width - bg_size) // 2, (qr_height - bg_size) // 2)
    qr_img.paste(bg, qr_pos)
    
    return qr_img

def main():
    st.title("🔲 QR Code Generator")
    st.markdown("Generate custom QR codes with colors and logos")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        url = st.text_input("🔗 URL:", "https://streamlit.io")
        
        st.divider()
        
        use_colors = st.checkbox("Custom colors")
        if use_colors:
            dark = st.color_picker("Dark:", "#000000")
            light = st.color_picker("Light:", "#FFFFFF")
        else:
            dark, light = "#000000", "#FFFFFF"
        
        st.divider()
        
        logo_file = st.file_uploader("🖼️ Logo:", type=['png', 'jpg', 'jpeg'])
        if logo_file:
            logo_size = st.slider("Logo size %:", 15, 35, 25)
        
        st.divider()
        
        scale = st.slider("QR size:", 5, 20, 10)
    
    # Main area
    if url:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📱 Preview")
            try:
                qr_img = generate_qr_code(url, scale)
                
                if use_colors:
                    qr_img = apply_colors(qr_img, dark, light)
                
                if logo_file:
                    logo = Image.open(logo_file)
                    qr_img = add_logo(qr_img, logo, logo_size)
                
                st.image(qr_img, use_container_width=True)
                st.success("✅ Generated!")
                
            except Exception as e:
                st.error(f"Error: {e}")
        
        with col2:
            st.subheader("💾 Download")
            try:
                qr_img = generate_qr_code(url, scale)
                
                if use_colors:
                    qr_img = apply_colors(qr_img, dark, light)
                
                if logo_file:
                    logo = Image.open(logo_file)
                    qr_img = add_logo(qr_img, logo, logo_size)
                
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                
                st.download_button(
                    "📥 Download PNG",
                    data=buf.getvalue(),
                    file_name="qr_code.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                st.info(f"Size: {qr_img.size[0]}x{qr_img.size[1]}px")
                
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
