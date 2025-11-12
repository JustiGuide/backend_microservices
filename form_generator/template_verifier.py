import json
import fitz
import os


class FormListSorter:
    @staticmethod
    def sort_forms(sort_by_pages: bool = True) -> list[str]:
        item_idx = 1
        if not sort_by_pages:
            return sorted(os.listdir("./gen_forms/"))
        sort_forms = {}
        all_forms = [
            f"./gen_forms/{form}/{form}_template.pdf"
            for form in os.listdir("./gen_forms/")
        ]
        for form in all_forms:
            doc = fitz.open(form)
            page_count = len(doc)
            sort_forms[form] = page_count
            doc.close()
        sorted_forms = dict(
            sorted(sort_forms.items(), key=lambda item: item[1], reverse=True)
        )
        return [key.split("/")[-2] for key in sorted_forms.keys()]


class FormChecker:
    def __init__(self, formname: str):
        self.formname = formname
        self.context_path = f"./gen_forms/{formname}/{formname}_context.json"
        self.template_path = f"./gen_forms/{formname}/{formname}_template.pdf"
        self.fieldmap_path = f"./gen_forms/{formname}/{formname}_fieldmap.json"

    def load_context(self) -> dict[str, str]:
        with open(self.context_path, "r", encoding="utf-8") as f:
            return {field["field_name"]: "" for field in json.load(f)["items"]}

    def load_fieldmap(self) -> dict[str, str]:
        with open(self.fieldmap_path, "r", encoding="utf-8") as f:
            return {
                field["proposed_canonical_name"]: "" for field in json.load(f)["items"]
            }

    def load_pdfdets(self) -> dict[str, str]:
        doc = fitz.open(self.template_path)
        out = {}
        for pno in range(len(doc)):
            page = doc[pno]
            widgets = [w for w in page.widgets()] or []
            for w in widgets:
                out[w.field_name] = ""
        doc.close()
        return out

    def compare_fields(self):
        context_fields = set(self.load_context().keys())
        fieldmap_fields = set(self.load_fieldmap().keys())
        pdf_fields = set(self.load_pdfdets().keys())

        missing_in_pdf = context_fields - pdf_fields
        extra_in_pdf = pdf_fields - context_fields
        missing_in_fieldmap = context_fields - fieldmap_fields
        extra_in_fieldmap = fieldmap_fields - context_fields

        print(
            f"Fields in context but missing in {self.formname} PDF: {missing_in_pdf if missing_in_pdf else 'None'}"
        )
        print(
            f"Fields in {self.formname} PDF but not in context: {extra_in_pdf if extra_in_pdf else 'None'}"
        )
        print(
            f"Fields in context but missing in {self.formname} field map: {missing_in_fieldmap if missing_in_fieldmap else 'None'}"
        )
        print(
            f"Fields in {self.formname} field map but not in context: {extra_in_fieldmap if extra_in_fieldmap else 'None'}"
        )
        print(
            f"Fields in field map but not in {self.formname} PDF: {fieldmap_fields - pdf_fields if fieldmap_fields - pdf_fields else 'None'}"
        )
        print(
            f"Fields in {self.formname} PDF but not in field map: {pdf_fields - fieldmap_fields if pdf_fields - fieldmap_fields else 'None'}"
        )


if __name__ == "__main__":
    sorter = FormListSorter.sort_forms()
    for formname in sorter:
        checker = FormChecker(formname)
        checker.compare_fields()
        print("=" * 100)
