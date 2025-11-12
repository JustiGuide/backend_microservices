from datetime import datetime, timezone
from typing import Union

from authorization import FormNameValidator
from database import Functions, Immigrants
from documents_gateway import DocumentsGateway
from compiler import Compiler
from autofill import AutofillGenerator
from helpers import Helpers
from email_gateway import Email
from recommendation import Recommender

docs = DocumentsGateway()
compiler = Compiler()
db_func = Functions()
autofill = AutofillGenerator()
recommender = Recommender()

class BackgroundUtilities:
    @staticmethod
    def start_compiler(immigrant_username: str, lawyer_map: dict[str, Union[str, list[str]]], case_type: str, form_name: FormNameValidator, to_create_checklist: bool, lawyer_username: str = None) -> None:
        immigrant = db_func.get_immigrant(immigrant_username)
        form_details_url = f"https://doloreschatbucket.s3.us-east-2.amazonaws.com/immigrants/{str(immigrant.username).lower()}/{form_name}_formdetails.json"
        if to_create_checklist:
            client_form = docs.get_formdetails_json(form_details_url)
            required_documents = compiler.get_document_checklist_with_ai(form_name=form_name, form_values=client_form)
            db_func.add_application_checklist(immigrant_email=immigrant.email, form_name=form_name, checklist_items=required_documents)
        else:
            db_func.get_application_checklist(immigrant_email=immigrant.email, form_name=form_name)

        all_user_documets = docs.get_all_compiler_documents(immigrant_username=immigrant.username, lawyer_map=lawyer_map)
        analysis_report = compiler.analyze_and_validate_documents(
            document_checklist=required_documents,
            file_details_list=all_user_documets
        )

        db_func.verify_checked_checklist(immigrant_email=immigrant.email, form_name=form_name)
        new_analysis_report = []

        for file_analysis in analysis_report:
            if file_analysis["file_url"]:
                dummy_file = Helpers.create_dummy_upload(file_analysis["file_url"])
                file_analysis["file_size"] = Helpers.get_file_size(dummy_file.size)
            else:
                file_analysis["file_size"] = "N/A"
            if file_analysis not in new_analysis_report:
                new_analysis_report.append(file_analysis)

        case_ids = []
        for lawyer in lawyer_map:
            lawyer_obj = db_func.get_lawpersonnel(lawyer)
            for case in lawyer_map[lawyer]:
                if (
                    db_func.retrieve_case_type(
                        lawyer_email=lawyer_obj.email, case_id=case
                    )
                    == case_type
                ):
                    case_ids.append(case)

        if len(case_ids) == 0:
            case_ids = [None]

        for case_id in case_ids:
            db_func.update_compiler_status(
                email=immigrant.email,
                case_type=case_type,
                analysis_report=new_analysis_report,
                case_id=case_id,
            )

        sender = immigrant
        if lawyer_username:
            sender = db_func.get_lawpersonnel(lawyer_username)

        Helpers.add_notification(
            receiver=sender.email,
            sender=sender.email,
            type="forms",
            content=f"Your {form_name} Application checklist has been generated. Documents uploaded by you have been analyzed and validated against the checklist.",
            target_id={"form_name": form_name},
            one_time=True,
        )

    @staticmethod
    def start_autofill(immigrant_username: str, form_name: str, case_type: str = None):
        previous_autofill_data = db_func.retrieve_autofill_data(immigrant_username=immigrant_username, form_name=form_name)
        immigrant_context_override = None
        immigrant_rag_override = None
        if previous_autofill_data and (previous_autofill_data.created_at - datetime.now(timezone.utc)).days() <= 1:
            immigrant_context_override = previous_autofill_data.immigrant_context
            immigrant_rag_override = previous_autofill_data.immigrant_rag_context
            
        new_autofill_data = autofill.generate(immigrant_username=immigrant_username, form_name=form_name, case_type=case_type, context_override=immigrant_context_override, rag_context_override=immigrant_rag_override)
        if new_autofill_data.success:
            previous_autofill_data.form_data.update(new_autofill_data.autofill_data)
            db_func.update_autofill_data(immigrant_username=immigrant_username, form_name=new_autofill_data.form_name, autofill_data=previous_autofill_data.form_data)

        Email.send_autofill_email(immigrant_username)
        
    @staticmethod
    def start_recommender(immigrant: Immigrants, force: bool = False):
        recommender.generate(immigrant.email, force=force)
        Email.send_recommendation_email(immigrant.username)