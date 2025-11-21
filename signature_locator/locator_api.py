from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from pydantic import BaseModel
from .locator_agent import SignaturePositionLocatorApplication
from documents_gateway import DocumentsGateway

app = APIRouter()
locator = SignaturePositionLocatorApplication()
docs = DocumentsGateway()


class FileURLRequest(BaseModel):
    url: str = Form()


@app.post("/sign-locator/file/locate")
async def locate_signature_positions(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail="Only PDF files are supported"
            )

        pdf_bytes = await file.read()

        signature_positions = await locator._analyze_pdf_for_signatures(pdf_bytes)

        return {
            "filename": file.filename,
            "signature_positions": signature_positions,
            "total_positions": len(signature_positions),
            "status": "success",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Analysis failed: {str(e)}"
        )


@app.post("/sign-locator/url/locate")
async def locate_positions_from_path(payload: FileURLRequest):
    try:
        if not payload.url.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail="Only PDF files are supported"
            )

        pdf_bytes = docs.download_file(payload.url)
        output_filename = "./tmp/temp.pdf"
        with open(output_filename, "wb") as f:
            f.write(pdf_bytes)

        signature_positions = await locator._analyze_pdf_file_for_signatures(
            output_filename
        )

        return {
            "url": payload.url,
            "signature_positions": signature_positions,
            "total_positions": len(signature_positions),
            "status": "success",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Analysis failed: {str(e)}"
        )
