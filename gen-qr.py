import streamlit as st
import qrcode
from PIL import Image, ImageDraw
import io

st.set_page_config(page_title="QR Code Generator", page_icon="🔲", layout="wide")

def generate_qr_code(url, fill_color, back_color, logo=None, logo_size=0.3):
    """Generate QR code with custom colors and optional logo"""
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction for logo
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
        # Calculate logo size
        qr_width, qr_height = img.size
        logo_max_size = int(qr_width * logo_size)
        
        # Resize logo
        logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
        
        # Create a white background for logo
        logo_bg_size = int(logo_max_size * 1.1)
        logo_bg = Image.new('RGB', (logo_bg_size, logo_bg_size), 'white')
        
        # Paste logo on white background
        logo_pos = ((logo_bg_size - logo.width) // 2, (logo_bg_size - logo.height) // 2)
        logo_bg.paste(logo, logo_pos, logo if logo.mode == 'RGBA' else None)
        
        # Calculate position to paste logo (center)
        logo_pos = ((qr_width - logo_bg_size) // 2, (qr_height - logo_bg_size) // 2)
        
        # Paste logo on QR code
        img.paste(logo_bg, logo_pos)
    
    return img

def main():
    st.title("🔲 QR Code Generator")
    st.markdown("Generate customized QR codes with colors and logos")
    
    # Create two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Settings")
        
        # URL input
        url = st.text_input("Enter URL:", value="https://www.example.com", 
                           help="Enter the URL you want to encode in the QR code")
        
        # Color pickers
        st.subheader("Colors")
        fill_color = st.color_picker("QR Code Color (foreground):", "#000000")
        back_color = st.color_picker("Background Color:", "#FFFFFF")
        
        # Logo upload
        st.subheader("Logo (Optional)")
        logo_file = st.file_uploader("Upload logo image:", 
                                     type=['png', 'jpg', 'jpeg'],
                                     help="Upload a logo to place in the center of QR code")
        
        logo_size = st.slider("Logo Size:", 0.1, 0.5, 0.3, 0.05,
                             help="Adjust the size of the logo relative to QR code")
        
        # Generate button
        generate_btn = st.button("Generate QR Code", type="primary")
    
    with col2:
        st.header("Preview")
        
        if generate_btn or url:
            try:
                # Process logo if uploaded
                logo = None
                if logo_file is not None:
                    logo = Image.open(logo_file)
                
                # Generate QR code
                qr_img = generate_qr_code(url, fill_color, back_color, logo, logo_size)
                
                # Display QR code
                st.image(qr_img, caption="Generated QR Code", use_container_width=True)
                
                # Download button
                buf = io.BytesIO()
                qr_img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="📥 Download QR Code",
                    data=byte_im,
                    file_name="qr_code.png",
                    mime="image/png"
                )
                
            except Exception as e:
                st.error(f"Error generating QR code: {str(e)}")
    
    # Footer with instructions
    st.markdown("---")
    st.markdown("""
    ### How to use:
    1. Enter the URL you want to encode
    2. Customize the colors using the color pickers
    3. (Optional) Upload a logo image to add to the center
    4. Click "Generate QR Code"
    5. Download your customized QR code!
    
    **Tips:**
    - Use high contrast colors for better scanning
    - Keep the logo size reasonable (20-30% recommended)
    - Test your QR code with a scanner before using it
    """)

if __name__ == "__main__":
    main()
