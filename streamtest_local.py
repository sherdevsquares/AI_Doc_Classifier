# file used to test startegy to find mime type and display the various types.

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from main import  get_file_type
from PIL import Image
import mammoth
import numpy as np
import io

st.header("Try to show various files appearing in the exceptions folder")

st.subheader("PNG File Example")
mime_type = get_file_type(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Account_Closing_2.png")
print(mime_type)
if mime_type == "image/png" :
    with st.container (height=600):
        file_image =Image.open(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Account_Closing_2.png")
        try:
            st.image(file_image, caption="PNG Image", use_container_width=True)
        except Exception:
            st.warning("Cannot display this file  PNG type. Please use fillable fields only.")

st.subheader("PDF File Example")
mime_type = get_file_type(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Customer_Statement_Alt_2.pdf")
print(mime_type)
if mime_type == "application/pdf":
    try:
        with st.container(height=300):
            pdf_viewer(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Customer_Statement_Alt_2.pdf", zoom_level=1.2)
    except Exception:
            st.warning("Cannot display this file PDF type. Please use fillable fields only.")

st.subheader("MS WordFile Example")
mime_type = get_file_type(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Signature_Card_Filled_3.docx")
print(mime_type)
if mime_type =="application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    with st.container (height=600):
        try:
            # Use mammoth t conert the docx to html
            with open(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Signature_Card_Filled_3.docx","rb") as docx_file:
                result = mammoth.convert_to_html(docx_file)
                
                #display the markdown content.
                st.markdown(result.value, unsafe_allow_html=True)
            
  
        except Exception:
            st.warning("Cannot display this file  Wordtype. Please use fillable fields only.")

st.subheader("JPEG Example")
mime_type = get_file_type(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Wire_Authorization_2.jpeg")
print(mime_type)
if mime_type == "image/jpeg":
    with st.container (height=600):
        file_image =Image.open(r"C:\Users\smj39\Documents\python class\Personal projects\Doc Classifier fictious samples\samplesvariety chosen\Wire_Authorization_2.jpeg")
        try:
            st.image(file_image, caption="JPEG Image", use_container_width=True)
        except Exception:
            st.warning("Cannot display this file  JPEG type. Please use fillable fields only.")

st.subheader("TIFF Example")
mime_type = get_file_type(r"C:\Users\smj39\Documents\python class\Personal projects\Classificationv2\exceptions\sig_tiff.tiff")
print(mime_type)
if mime_type == "image/tiff":
    with st.container (height=600):
        # file_image =Image.open(r"C:\Users\smj39\Documents\python class\Personal projects\Classificationv2\exceptions\sig_tiff.tiff")
        try:
            # 1. Open with Pillow
            img = Image.open(r"C:\Users\smj39\Documents\python class\Personal projects\Classificationv2\exceptions\sig_tiff.tiff")
            
            # 2. Check if it's 16-bit (mode 'I;16')
            if img.mode == 'I;16':
                # Convert to numpy to normalize the data
                img_array = np.array(img)
                
                # Normalize 16-bit (0-65535) to 8-bit (0-255)
                # This prevents the image from appearing completely black or white
                img_8bit = (img_array / 256).astype('uint8')
                
                # Convert back to a Pillow image in 'L' (Grayscale) or 'RGB' mode
                img = Image.fromarray(img_8bit).convert("RGB")
            else:
                # For other non-standard modes, a direct conversion often works
                img = img.convert("RGB")
                
            st.image(img, use_container_width=True)
                
        except Exception as e:
            st.error(f"Failed to process TIFF: {e}")

