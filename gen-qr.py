import streamlit as st
import segno
from PIL import Image
import io

st.set_page_config(page_title="QR Code Generator", page_icon="🔲", layout="wide")

def generate_qr_code(url, dark_color, light_color, logo=None, scale=10):
    """Generate QR code with custom colors and optional logo"""
    
    # Convert hex colors to RGB tuples
    dark_rgb = tuple(int(dark_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    light_rgb = tuple(int(light_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    # Create QR code
    qr = segno.make(url, error='h', boost_error=False)
    
    # Save to buffer
    buff = io.BytesIO()
    qr.save(buff, kind='png', scale=scale, dark=dark_rgb, light=light_rgb)
    buff.seek(0)
    
    # Load as PIL Image
    img = Image.open(buff)
    
    # Add logo if provided
    if logo is not None:
        # Get QR code dimensions
        qr_width, qr_height = img.size
        
        # Calculate logo size (20-30% of QR code)
        logo_size = int(qr_width * 0.25)
        
        # Resize logo maintaining aspect ratio
        logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        # Create white background slightly larger than logo
        bg_size = int(logo_size * 1.15)
        logo_bg = Image.new('RGB', (bg_size, bg_size), 'white')
        
        # Center logo on white background
        logo_pos = ((bg_size - logo.width) // 2, (bg_size - logo.height) // 2)
        
        # Handle transparency
        if logo.mode == 'RGBA':
            logo_bg.paste(logo, logo_pos, logo)
        else:
            logo_bg.paste(logo, logo_pos)
        
        # Center position for logo on QR code
        qr_logo_pos = ((qr_width - bg_size) // 2, (qr_height - bg_size) // 2)
        
        # Paste logo onto QR code
        img.paste(logo_bg, qr_logo_pos)
    
    return img

def main():
    st.title("🔲 QR Code Generator")
    st.markdown("Generate custom QR codes with colors and logos")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        url = st.text_input(
            "🔗 Enter URL:",
            value="https://www.example.com",
            help="The URL to encode in the QR code"
        )
        
        st.divider()
        
        st.subheader("🎨 Colors")
        dark_color = st.color_picker("QR Code Color (Dark):", "#000000")
        light_color = st.color_picker("Background Color (Light):", "#FFFFFF")
        
        st.divider()
        
        st.subheader("🖼️ Logo")
        logo_file = st.file_uploader(
            "Upload Logo (Optional):",
            type=['png', 'jpg', 'jpeg', 'gif'],
            help="Add a logo to the center of your QR code"
        )
        
        st.divider()
        
        scale = st.slider(
            "QR Code Size:",
            min_value=5,
            max_value=20,
            value=10,
            help="Adjust the size of the generated QR code"
        )
    
    # Main area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📱 Preview")
        
        if url:
            try:
                # Load logo if uploaded
                logo = None
                if logo_file is not None:
                    logo = Image.open(logo_file)
                
                # Generate QR code
                with st.spinner("Generating QR code..."):
                    qr_img = generate_qr_code(url, dark_color, light_color, logo, scale)
                
                # Display
                st.image(qr_img, use_container_width=True)
                
                st.success("✅ QR code generated successfully!")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Please check your URL and try again.")
        else:
            st.info("👈 Enter a URL in the sidebar to generate a QR code")
    
    with col2:
        st.header("💾 Download")
        
        if url:
            try:
                logo = None
                if logo_file is not None:
                    logo = Image.open(logo_file)
                
                qr_img = generate_qr_code(url, dark_color, light_color, logo, scale)
                
                # Convert to bytes
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                # Download button
                st.download_button(
                    label="📥 Download QR Code",
                    data=byte_im,
                    file_name="qr_code.png",
                    mime="image/png",
                    use_container_width=True
                )
                
                # Show info
                st.info(f"""
                **QR Code Info:**
                - Size: {qr_img.width} x {qr_img.height} pixels
                - URL: {url}
                - Has Logo: {'Yes' if logo_file else 'No'}
                """)
                
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Footer
    st.divider()
    
    with st.expander("📖 How to Use"):
        st.markdown("""
        ### Steps:
        1. **Enter URL** - Input the website address in the sidebar
        2. **Customize Colors** - Choose your brand colors
        3. **Add Logo** (Optional) - Upload an image file
        4. **Adjust Size** - Use the slider to change QR code dimensions
        5. **Download** - Click the download button to save
        
        ### Best Practices:
        - ✅ Use **high contrast** colors (e.g., black on white)
        - ✅ Test your QR code with multiple scanners
        - ✅ Keep URLs short for simpler QR codes
        - ✅ Logo should be **20-30%** of QR code size
        - ✅ Use PNG format for best quality
        
        ### Tips:
        - Logos work best with high error correction
        - Always test before printing in bulk
        - QR codes work best at 2cm x 2cm minimum size
        """)

if __name__ == "__main__":
    main()
