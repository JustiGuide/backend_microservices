from fastapi import APIRouter
from pydantic import BaseModel
from authorization import FormNameValidator
from documents_gateway import DocumentsGateway
from dotenv import load_dotenv
from .form_generator import UnifiedTemplateGenerator

load_dotenv()

docs = DocumentsGateway()

app = APIRouter()

class FormTemplateInput(BaseModel):
    form_name: FormNameValidator

@app.post("/form-generator/immigrant/generate-form")
async def generate_immigrant_form_template(payload: FormTemplateInput):
    form_url = f"s3://<bucket>/pregen_forms/{payload.form_name}"
    form_data = docs.download_file(form_url)
    generator = UnifiedTemplateGenerator(payload.form_name)
    results = generator.generate_template()
    docs.upload_file(f"./tmp/{payload.form_name}_template.pdf")
    # TODO: Complete implementation