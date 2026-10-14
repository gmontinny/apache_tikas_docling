import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

TIKA_URL = os.getenv("TIKA_SERVER_URL", "http://localhost:9998")


def _clean(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)       # remove linhas em branco excessivas
    text = re.sub(r"[ \t]{2,}", " ", text)        # colapsa espaços múltiplos
    text = re.sub(r" \n", "\n", text)             # remove espaço antes de quebra de linha
    return text.strip()


def extract(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        response = requests.put(
            f"{TIKA_URL}/tika",
            data=f,
            headers={
                "Accept": "text/plain",
                "Content-Type": "application/pdf",
                "Accept-Language": "pt-BR",
                "X-Tika-PDFextractInlineImages": "true",
                "X-Tika-PDFSortByPosition": "true",
                "X-Tika-PDFextractAnnotationText": "true",
            },
            timeout=60,
        )
    response.raise_for_status()
    return _clean(response.text)
