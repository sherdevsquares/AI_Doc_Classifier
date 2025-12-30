import os
from dotenv import load_dotenv
import shutil
import json
import base64
import logging
import datetime
import pandas as pd
from PIL import Image
from pydantic import BaseModel, Field
from typing import Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
#from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_unstructured import UnstructuredLoader
import pytesseract
import filetype
import streamlit as st

# Explicitly setting the tesseract path for the pytesseract wrapper
# Using r'' to handle Windows backslashes correctly
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' //used for local processing


# load_dotenv() --> for local .env
# The ChatOpenAI() call will now automatically find the key via os.environ

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Setup logging
log_filename = f"log_{datetime.date.today().strftime('%Y-%m-%d')}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

##################    Pydantic category schemas #####################
class DocumentClassificationResult(BaseModel):
    category_name: str = Field(description="The suggested category name (Memberdoc, Loans, or Statements).")
    confidence_score: float = Field(description="The AI model's confidence level for the suggested category (0.0 to 1.0).")
    member_name: str = Field(description="The name of the member.")
    member_number: str = Field(description="The member's account number.")
    doc_date: Optional[str] = Field(None, description="The date of the document, statement, or loan.")
    loan_type: Optional[str] = Field(None, description="The type of loan, if applicable.")
    file_loc: Optional[str] = Field(None, description="The location where the file is stored after classification.")

##################   File Handling Functions     ##################

# def get_file_type(filepath):
#     """Determines file MIME type using python-magic."""
#     return magic.from_file(filepath, mime=True)

def get_file_type(filepath):
    """Determines file MIME type using filetype library magic numbers written in python no c libraries required."""
    try:
        kind = filetype.guess(filepath)
        return kind.mime
    except :
        return "application/octet-stream"

def extract_text_from_file(filepath):
    """Extracts text using Unstructured for multimodal functionality """
    loader = UnstructuredLoader(filepath)
    docs = loader.load()
    return " ".join([doc.page_content for doc in docs])

def encode_image_to_base64(image_path, mime_type):
    """Encodes an image to a base64 string if it's an image type."""
    if mime_type.startswith('image/'):
        with open(image_path, "rb") as image_file:
            # create a string from the bytes returned by the base64encoding
            return base64.b64encode(image_file.read()).decode('utf-8')
    return None

##################   Index File Management Functions ##################   

def get_next_index_file(category_folder, max_entries=10):
    """search available file to see which has less than 10 entries. Then use that file."""
    index_count = 0
    while True:
        index_filename = f"index_{index_count:03d}.jsonl"
        index_path = os.path.join(category_folder, index_filename)
        if not os.path.exists(index_path): return index_path
        with open(index_path, 'r') as f:
            line_count = sum(1 for line in f)
        if line_count < max_entries: return index_path
        index_count += 1

def add_entry_to_index(category_folder, data_entry, max_entries=10):
    """Writes a new dictionary entry as a JSON line to the appropriate index file."""
    index_path = get_next_index_file(category_folder, max_entries)
    with open(index_path, 'a') as f:
        f.write(json.dumps(data_entry) + '\n')
    logging.info(f"Added entry to index: {index_path}")


##################   Main Processing Logic ##################   

def process_file_with_ai(filepath, filename, exception_folder):
    """ Calls the AI for classification and manages file movement and creation """
    try:
        mime_type = get_file_type(filepath)
        document_text = extract_text_from_file(filepath)
        base64_image = encode_image_to_base64(filepath, mime_type)

        ### test results from extraction
        logging.info(f"Extracted text: {document_text[:200]}...")
        logging.info(f"Base64 image: {base64_image is not None}")

        if not document_text and not base64_image:
            # if the document is blank raise an error to be then handled by the exception block i.e. move to exception folder.
            logging.info("No extractable content found for file {filepath}.")
            raise ValueError("No extractable content found.")
       
        # Prepare multimodal input. only capture the first 2000 characters to prevent AI context window threshold
        llm_input_content = [{"type": "text", "text": f"Classify this document based on its content and extracted text: {document_text[:2000]}."}]
        if base64_image:
            llm_input_content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}})

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert document classifier. Classify the input into one of three categories: Memberdoc, Loans, or Statements. Extract structured data including a confidence score into the JSON schema."),
            HumanMessage(content=llm_input_content)
        ])

        llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o", temperature=0)
        chain = prompt_template | llm.with_structured_output(DocumentClassificationResult) 
        # output here will be in the pydantic structure defined earlier

        extracted_data = chain.invoke({}) 

        # Confidence Check (80% threshold)
        if extracted_data.confidence_score < 0.80:
            raise ValueError(f"Confidence score too low: {extracted_data.confidence_score*100}%")

        # Naming convention and moving file
        # determine if a member number is captured if not leave it empty
        member_num_prefix = f"{extracted_data.member_number}_" if extracted_data.member_number else ""
        new_filename = member_num_prefix + filename
        category_name = extracted_data.category_name 
        destination_folder = os.path.join("./classified_output", category_name)
        if not os.path.exists(destination_folder): os.makedirs(destination_folder)

        final_file_loc = os.path.join(destination_folder, new_filename)
        shutil.move(filepath, final_file_loc)

        # Update data and index
        extracted_data.file_loc = final_file_loc
        add_entry_to_index(destination_folder, extracted_data.model_dump())
        
        logging.info(f"SUCCESS: {filename} -> {category_name}. Confidence: {extracted_data.confidence_score*100}%. Data: {extracted_data.model_dump()}")
        return True, f"Classified as {category_name} ({extracted_data.confidence_score*100:.1f}%)"

    except Exception as e:
        # Move to exception folder on any failure
        logging.error(f"EXCEPTION: {filename}. Reason: {e}")
        shutil.move(filepath, os.path.join(exception_folder, filename))
        return False, f"Exception: {str(e)[:100]}..."
