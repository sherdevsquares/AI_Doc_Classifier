import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import os
import shutil
import time
import pandas as pd
import glob
import json
import mammoth # for word doc to html conversion
import io
import matplotlib.pyplot as plt
from main import process_file_with_ai, add_entry_to_index, get_file_type, DocumentClassificationResult # Import backend functions
from PIL import Image
import numpy as np

# --- Configuration ---
INPUT_FOLDER = "./temp_dir"
EXCEPTION_FOLDER = "./exceptions"
OUTPUT_DIR = "./classified_output"

# Ensure directories exist if not make them
for folder in [INPUT_FOLDER, EXCEPTION_FOLDER, OUTPUT_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

st.set_page_config(page_title="AI Document Classifier Dashboard", layout="wide")
st.title("Document Classification System")

# --- Function to get file list ---
def get_files_to_process(folder):
    # check the returned list of items from listdir to ensure they are files and not directories.
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    #### Alternate method ######
    # for f in os.listdir(folder):
    # full_path = os.path.join(folder, f)
    # if os.path.isfile(full_path):
    #     files.append(f)
    return files

# --- Tab Navigation ---
tab1, tab2, tab3 = st.tabs(["Process Documents", "Review Exceptions", "Analytics Dashboard"])


############ Tab 1: Process Documents   ############

with tab1:
    st.header("Automatic Processing")

    # 8a. Allow user to select folder (simulate with input field)
    st.subheader("Configuration")

            # 1. Create a multiple file uploader
    uploaded_files = st.file_uploader(
        "Choose documents to classify", 
        accept_multiple_files=True,
        type=['png', 'jpg', 'jpeg', 'pdf', 'docx', 'tif', 'tiff']
        )

        # 2. Process the files
    if uploaded_files:
        st.info(f"Loaded {len(uploaded_files)} files for processing.")
        
        for uploaded_file in uploaded_files:
            # Streamlit provides the file name and content (bytes)
            filename = uploaded_file.name
            
            # Save a temporary copy because UnstructuredLoader/Pillow often need a path
            temp_path = os.path.join("temp_dir", filename)
            if not os.path.exists("temp_dir"):
                os.makedirs("temp_dir")
                
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

    selected_folder = "temp_dir"

    files_list = get_files_to_process(selected_folder)
    initial_file_count = len(files_list)

    if st.button("Start Processing"):
        if not files_list:
            st.warning("No files found in the input folder.")
        else:
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, filename in enumerate(files_list): # Enumerate captures index to use for progress tracking
                filepath = os.path.join(selected_folder, filename)
                
                # Call main functions to process file
                success, message = process_file_with_ai(filepath, filename, EXCEPTION_FOLDER)
                
                # Show status and count remaining
                status_text.text(f"Processing file {i+1}/{initial_file_count}: {filename} - Status: {message}")
                
                # Update progress bar
                progress = (i + 1) / initial_file_count
                progress_bar.progress(progress)
            
            end_time = time.time()
            duration = end_time - start_time
            # 8d. Estimate time (simple average)
            st.success(f"Processing complete! Total time: {duration:.2f}s. Average time per file: {duration/initial_file_count:.2f}s.")
            status_text.text("Idle.")



############# Tab 2: Review Exceptions ############

with tab2:
    st.header("Manual Exception Review")

    exception_files = get_files_to_process(EXCEPTION_FOLDER)
    if not exception_files:
        st.info("No files currently in the exception folder.")
        # Reset index if folder is empty
        st.session_state.exception_index = 0
    else:
        st.write(f"Found {len(exception_files)} files requiring manual review.")
        
        # Initialize the index in session state if it doesn't exist
        if 'exception_index' not in st.session_state:
            st.session_state.exception_index = 0

        # Safety check: ensure index doesn't exceed list length
        if st.session_state.exception_index >= len(exception_files):
            st.session_state.exception_index = 0

        # Define the 'move to next' callback function
        def next_exception():
            st.session_state.exception_index = (st.session_state.exception_index + 1) % len(exception_files)

        current_file = exception_files[st.session_state.exception_index]
        file_path = os.path.join(EXCEPTION_FOLDER, current_file)

        col1, col2 = st.columns([1, 1])
        
        # Display the image to the user
        with col1:
            st.subheader(f"Reviewing {st.session_state.exception_index + 1} of {len(exception_files)}")
            try:
                
                #add logic here to determine how to handle file based on type
                # first determine mime type again
                mime_type = get_file_type(file_path)

                # compare mimetype then execute the appropriate display flow
                if mime_type == "image/png" :
                    with st.container (height=600):
                        file_image =Image.open(file_path)
                        try:
                            st.image(file_image, caption="PNG Image", width='stretch')
                        except Exception:
                            st.warning("Cannot display this file  PNG type.")
                elif mime_type == "application/pdf":
                    try:
                        with st.container(height=600):
                            pdf_viewer(file_path, zoom_level=1.2)
                    except Exception:
                            st.warning("Cannot display this file PDF type.")
                elif mime_type =="application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    with st.container (height=600):
                        try:
                            # Use mammoth to convert the docx to html
                            with open(file_path,"rb") as docx_file:
                                result = mammoth.convert_to_html(docx_file)
                                
                                #display the markdown content.
                                st.markdown(result.value, unsafe_allow_html=True)
                        except Exception:
                            st.warning("Cannot display this file Word Docx.")
                elif mime_type == "image/jpeg":
                    with st.container (height=600):
                        file_image =Image.open(file_path)
                        try:
                            st.image(file_image, caption="JPEG Image", width='stretch')
                        except Exception:
                            st.warning(f"Cannot display this file JPEG/TIFF type. --> {file_path}.")
                elif mime_type == "image/tiff":
                        with st.container (height=600):
                            try:
                                # 1. Open with Pillow
                                img = Image.open(file_path)
                                
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
                                    
                                st.image(img, width='stretch')
                                    
                            except Exception as e:
                                st.error(f"Failed to process TIFF: {e}")
                                st.warning(f"Cannot display this file type. review the file manually at this path --> {file_path} .")
            except:
               st.error(f"Cannot display image located at {file_path}") 
       
        # The skip button
        st.button("Skip to Next Document ⏭️", on_click=next_exception)

   
        # manually update the exception item
        with col2:
            st.subheader("Manual Categorization")
            
            with st.form("manual_review_form", clear_on_submit=True):
                manual_category = st.selectbox("Select Category", ["Memberdoc", "Loans", "Statements"])
                manual_member_name = st.text_input("Member Name", "")
                manual_member_number = st.text_input("Member Number", "")
                manual_date = st.text_input("Date (YYYY-MM-DD)", "")
                manual_loan_type = st.text_input("Loan Type (if applicable)", "")
                
                submitted = st.form_submit_button("Approve and Index Manually")

                if submitted:
                    # Manually create a data object for indexing (using 100% confidence for manual approval)
                    manual_data = DocumentClassificationResult(
                        category_name=manual_category,
                        confidence_score=1.0,
                        member_name=manual_member_name,
                        member_number=manual_member_number,
                        doc_date=manual_date if manual_date else None,
                        loan_type=manual_loan_type if manual_loan_type else None,
                        file_loc=None # Will be updated after move
                    )

                    # Move file logic (same as core processor)
                    member_num_prefix = f"{manual_data.member_number}_" if manual_data.member_number else ""
                    new_filename = member_num_prefix + current_file
                    destination_folder = os.path.join(OUTPUT_DIR, manual_category)
                    if not os.path.exists(destination_folder): os.makedirs(destination_folder)

                    final_file_loc = os.path.join(destination_folder, new_filename)
                    shutil.move(file_path, final_file_loc) # Remove item from exceptions folder

                    manual_data.file_loc = final_file_loc
                    add_entry_to_index(destination_folder, manual_data.model_dump()) # Add to index file

                    st.success(f"Manually indexed and moved {file_path} to {manual_category}.")
                    st.rerun() # Refresh the page to show the next exception file



############ Tab 3: Analytics Dashboard  ############

with tab3:
    st.header("Processing Statistics")
    
    # Using pandas to iterate through index and exception files
    # Load all index files from all categories
    all_records = []
    for category in ["Memberdoc", "Loans", "Statements"]:
        category_path = os.path.join(OUTPUT_DIR, category)
        if os.path.exists(category_path):
            for file in glob.glob(os.path.join(category_path, "*.jsonl")):
                with open(file, 'r') as f:
                    for line in f:
                        all_records.append(json.loads(line))
    
    df_completed = pd.DataFrame(all_records)
    
    # Count exceptions
    exception_count = len(get_files_to_process(EXCEPTION_FOLDER))

    st.subheader("Completion Status")
    
    if not df_completed.empty:
        total_processed = len(df_completed)
        st.write(f"Total documents automatically processed: **{total_processed}**")
        st.write(f"Documents currently in exception folder: **{exception_count}**")

        # 10. Create a graph of the amount of documents completed per category
        st.subheader("Documents Processed Per Category (Automatic)")
        category_counts = df_completed['category_name'].value_counts()
        
        fig, ax = plt.subplots()
        category_counts.plot(kind='bar', ax=ax)
        ax.set_ylabel('Count')
        ax.set_title('Document Count by Category')
        st.pyplot(fig)
        
    else:
        st.info("No documents processed yet for analytics.")
