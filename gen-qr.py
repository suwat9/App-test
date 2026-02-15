import streamlit as st
try:
    import qrcode
    from PIL import Image, ImageDraw
except ImportError as e:
    st.error(f"Missing required package: {e}")
    st.info("Please ensure requirements.txt contains: streamlit, qrcode, pillow")
    st.stop()

import io

st.set_page_config(page_title="QR Code Generator", page_icon="🔲", layout="wide")

def generate_qr_code(url, fill_color, back_color, logo=None, logo_size=0.3):
    """Generate QR code with custom colors and optional logo"""
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    # Add data
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create QR code image with custom colors
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    img = img.convert('RGB')
    
    # Add logo if provided
    if logo is not None:
        qr_width, qr_height = img.size
        logo_max_size = int(qr_width * logo_size)
        
        # Resize logo
        logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
        
        # Create white background for logo
        logo_bg_size = int(logo_max_size * 1.1)
        logo_bg = Image.new('RGB', (logo_bg_size, logo_bg_size), 'white')
        
        # Paste logo on white background
        logo_pos = ((logo_bg_size - logo.width) // 2, (logo_bg_size - logo.height) // 2)
        logo_bg.paste(logo, logo_pos, logo if logo.mode == 'RGBA' else None)
        
        # Position logo in center
        logo_pos = ((qr_width - logo_bg_size) // 2, (qr_height - logo_bg_size) // 2)
        img.paste(logo_bg, logo_pos)
    
    return img

def main():
    st.title("🔲 QR Code Generator")
    st.markdown("Generate customized QR codes with colors and logos")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("⚙️ Settings")
        
        url = st.text_input("🔗 Enter URL:", value="https://www.example.com", 
                           help="Enter the URL you want to encode")
        
        st.subheader("🎨 Colors")
        fill_color = st.color_picker("QR Code Color:", "#000000")
        back_color = st.color_picker("Background Color:", "#FFFFFF")
        
        st.subheader("🖼️ Logo (Optional)")
        logo_file = st.file_uploader("Upload logo:", 
                                     type=['png', 'jpg', 'jpeg'])
        
        if logo_file:
            logo_size = st.slider("Logo Size:", 0.1, 0.5, 0.3, 0.05)
        else:
            logo_size = 0.3
        
        generate_btn = st.button("✨ Generate QR Code", type="primary", use_container_width=True)
    
    with col2:
        st.header("📱 Preview")
        
        if generate_btn or url:
            try:
                logo = None
                if logo_file is not None:
                    logo = Image.open(logo_file)
                
                with st.spinner("Generating QR code..."):
                    qr_img = generate_qr_code(url, fill_color, back_color, logo, logo_size)
                
                st.image(qr_img, caption="Your QR Code", use_container_width=True)
                
                # Download
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="📥 Download QR Code (PNG)",
                    data=byte_im,
                    file_name="qr_code.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                st.success("✅ QR code generated successfully!")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Please check your inputs and try again.")
    
    st.markdown("---")
    with st.expander("📖 Instructions"):
        st.markdown("""
        ### How to use:
        1. **Enter URL** - Type the web address you want to encode
        2. **Choose Colors** - Customize foreground and background colors
        3. **Add Logo** (Optional) - Upload your brand logo
        4. **Generate** - Click the button to create your QR code
        5. **Download** - Save the QR code as PNG
        
        ### Tips:
        - ✅ Use high contrast colors (dark on light or vice versa)
        - ✅ Keep logo size between 20-30% for best results
        - ✅ Always test the QR code before printing
        - ✅ Higher error correction allows logos without affecting scanning
        """)

if __name__ == "__main__":
    main()
