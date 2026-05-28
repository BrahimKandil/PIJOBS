import os
from PyPDF2 import PdfReader
from docx import Document


def extract_text_from_pdf(path):

    text = ""

    reader = PdfReader(path)

    for page in reader.pages:

        extracted = page.extract_text()

        if extracted:
            text += extracted + "\n"

    return text


def extract_text_from_docx(path):

    doc = Document(path)

    return "\n".join(
        [p.text for p in doc.paragraphs]
    )


def extract_cv_text(path):

    extension = os.path.splitext(path)[1].lower()

    if extension == ".pdf":
        return extract_text_from_pdf(path)

    elif extension == ".docx":
        return extract_text_from_docx(path)

    return ""