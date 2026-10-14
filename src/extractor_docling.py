from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.datamodel.base_models import InputFormat

_pipeline_options = PdfPipelineOptions(do_ocr=True, ocr_options=EasyOcrOptions(lang=["pt"]))

_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=_pipeline_options)
    }
)


def extract(pdf_path: str) -> str:
    result = _converter.convert(pdf_path)
    return result.document.export_to_markdown().strip()
