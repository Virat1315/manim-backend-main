import fitz  # PyMuPDF
from google import genai
from dotenv import load_dotenv
import os
import json  
import time
from PyPDF2 import PdfReader, PdfWriter
import re
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI"))



def trim_pdf(pdf_path, start_page, end_page, output_path=None):
    """
    Trims a PDF from start_page to end_page (inclusive) and saves it as a new file.

    Args:
        pdf_path (str): Path to the original PDF.
        start_page (int): Starting page index (0-based).
        end_page (int): Ending page index (0-based).
        output_path (str, optional): Path to save the trimmed PDF. 
                                     If None, saves as 'trimmed_<originalname>.pdf' in same directory.

    Returns:
        str: Path to the trimmed PDF file.
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    total_pages = len(reader.pages)
    if start_page < 0 or end_page >= total_pages or start_page > end_page:
        raise ValueError("Invalid page range.")

    for i in range(start_page-1, end_page ):
        writer.add_page(reader.pages[i])

    if not output_path:
        base_name = os.path.basename(pdf_path)
        dir_name = os.path.dirname(pdf_path)
        trimmed_name = f"trimmed_{base_name}"
        output_path = os.path.join(dir_name, trimmed_name)

    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    return output_path



# make function to get topics and it's content from simple pdf/ slides, etc...
def extract_others_and_parse(pdf_path):
    # Implement PDF extraction logic here
    pass


def markdown_to_plain_text(markdown_text):
    """
    Converts markdown text to plain text suitable for voice conversion.
    
    Args:
        markdown_text (str): The input markdown text.
        
    Returns:
        str: Plain text with markdown formatting removed.
    """
    # Remove bold/italic formatting
    plain_text = markdown_text.replace("**", "").replace("*", "")
    
    # Remove heading markers
    for i in range(6, 0, -1):
        heading_marker = '#' * i + ' '
        plain_text = plain_text.replace(heading_marker, "")
    
    # Replace links [text](url) with just the text
    plain_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', plain_text)
    
    # Replace code blocks
    plain_text = re.sub(r'```[^\n]*\n(.*?)\n```', r'\1', plain_text, flags=re.DOTALL)
    plain_text = plain_text.replace('`', '')
    
    # Replace bullet points
    plain_text = re.sub(r'^[\*\-\+]\s+', '', plain_text, flags=re.MULTILINE)
    
    return plain_text.strip()




# Function to extract Table of Contents and parse it using Gemini
def extract_toc_and_parse(pdf_path, toc_start_pdf_pg, toc_end_pdf_pg):

    final_result = []
    last_chapter = None

    for page_num in range(toc_start_pdf_pg, toc_end_pdf_pg + 1):
        # Extract single page as a PDF
        single_page_pdf_path = trim_pdf(pdf_path, start_page=page_num, end_page=page_num)
        with open(single_page_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # Build the prompt with context from the last chapter
        prompt = f"""Please extract the Table of Contents from the BOOK PDF file provided. there can be many pages for table of contents, and current pdf might be one of them. 

If this taable of contents page starts with subtopics, i.e. the chapter name (main topic) is missing, it means the main topic name was present in previous page . In this case, please use the below chapter name (main topic):
Chapter name: {last_chapter if last_chapter else "None"} , and add the subtopics to it.

Please extract the content into this format. please do not change the format . the format contains a list of lists. each list contains a chapter name and a dictionary of topics with their page numbers. :
[
  ["Chapter X: Chapter Title", {{
      "Topic x : Topic Title" : "Page Number",
      "Topic y : Topic Title" : "Page Number",
      ...
      "Topic z : Topic Title" : "Page Number"
  }}],
  ...
]

"""
        try:

            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    {
                        "mime_type": "application/pdf",
                        "data": pdf_bytes
                    },
                    prompt
                ],
            ).text
        except:
            time.sleep(5)
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    {
                        "mime_type": "application/pdf",
                        "data": pdf_bytes
                    },
                    prompt
                ],
            ).text
            

        print(f"Gemini response for page {page_num}:", response)
        if response[0] == "`":
            response = response.replace("```json", "").replace("```", "")
        print(f"Gemini response after trimming for page {page_num}:", response)

        try:
            parsed_json = eval(response)  # Changed from eval to json.loads for safety
            if parsed_json:
                # Extract the last chapter for context in the next iteration
                last_chapter = parsed_json[-1][0] if parsed_json else last_chapter
                final_result.extend(parsed_json)
        except Exception as e:
            print(f"JSON decoding error for page {page_num}:", e)
            return None
    with open("save.json", "w") as outfile:
        json.dump(final_result, outfile, indent=4)
    return final_result




def search_svg():
    pass




if __name__ == "__main__":


    parsed_toc = extract_toc_and_parse("/home/aryan/deep-spark-mentor-ai/backend/Concepts_of_Physics_Vol_2_2023_Edition.pdf", toc_start_pdf_pg=12, toc_end_pdf_pg=16)
    
    if parsed_toc:
        print("Parsed Table of Contents:", parsed_toc)
    else:
        print("Failed to parse Table of Contents.")
