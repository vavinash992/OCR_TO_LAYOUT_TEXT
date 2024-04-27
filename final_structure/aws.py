from loguru import logger
import boto3
import numpy as np
import cv2
from trp import Document


import numpy as np
import cv2
import fitz  # PyMuPDF



def make_request(image) -> dict:
    try:
        # logger.info(f"Making request to AWS Textract version {self._version}.")
        client = boto3.client("textract")
        response = client.analyze_document(
            Document={"Bytes": image}, FeatureTypes=["TABLES"]
        )
    except Exception as e:
        message = f"[Error] while making request to AWS Textract client. Exception: {str(e)}"
        logger.error(message)
        response = {}
    return response


def get_table_markdown(image,width,height,number):
    doc = make_request(image)
    doc = Document(doc)
    dict = {}
    dimesion_dict = {}
    for page_number, page in enumerate(doc.pages):
        for table_number, table in enumerate(page.tables):
            table_str = ""
            # Create a row for column numbers
        
            column_numbers = ["Row\\Col"] + [f"Col {c+1}" for c, _ in enumerate(table.rows[0].cells)]
            column_number_row = "| " + " | ".join(column_numbers) + " |"
            table_str += column_number_row + "\n"
            # Create the separator for column numbers
            column_number_separator = "| " + " | ".join(["---"] * len(column_numbers)) + " |"
            table_str += column_number_separator + "\n"
            # Assuming the first column is the header, we process it separately
            headers = [" "] + [cell.text.strip() for cell in table.rows[0].cells]
            # Create the header row
            header_row = "| " + " | ".join(headers) + " |"
            table_str += header_row + "\n"

            # Print each row of the table, starting from the second row since the first row is used as the header
            for r, row in enumerate(table.rows[1:], start=1):  # Start counting from 1 for data rows
                row_data = "| " + f"Row {r} " + "| " + " | ".join([cell.text.strip() for cell in row.cells]) + " |"
                table_str += row_data + "\n"
                
            dict[f"Table_{table_number}_of_page{number}"]= table_str  # Add a newline for better separation between tables1
            top = table.geometry.boundingBox.top
            left = table.geometry.boundingBox.left
            height_table = table.geometry.boundingBox.height
            width_table = table.geometry.boundingBox.width
            x1 = int(left * width)
            y1 = int(top * height)
            x2 = int((left + width_table) * width)
            y2 = int((top + height_table) * height)
            dimesion_dict[f"{table_number}"] = (x1,y1,x2,y2)
    return (dict,dimesion_dict)