import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

import db
import extractor_tika as tika
import extractor_docling as docling

DATA_DIR = Path(os.getenv("DATA_DIR", "datas"))

EXTRACTORS = {
    "tika": tika.extract,
    "docling": docling.extract,
}


def process_pdf(pdf_path: Path):
    for name, extract_fn in EXTRACTORS.items():
        print(f"  [{name}] extraindo {pdf_path.name}...")
        try:
            content = extract_fn(str(pdf_path))
            db.insert_extraction(pdf_path.name, name, content)
            print(f"  [{name}] gravado — {len(content)} caracteres")
        except Exception as exc:
            print(f"  [{name}] ERRO: {exc}")


def main():
    db.setup_table()

    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF encontrado em '{DATA_DIR}'")
        return

    print(f"Encontrados {len(pdfs)} PDF(s) em '{DATA_DIR}'\n")
    for pdf in pdfs:
        print(f"Processando: {pdf.name}")
        process_pdf(pdf)
        print()

    print("Concluído.")


if __name__ == "__main__":
    main()
