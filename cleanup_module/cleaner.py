import re
from typing import Union

from pydantic import EmailStr
from sqlalchemy import inspect, or_, text
from database import LawPersonnelAIChat, AllCases, AllClients, AllTasks, CaseDocuments, CaseRecentActions, CaseTeams, ChatMessage, ConnectionRequests, Functions, ImmigrantLawyerConnection, Invitations, LawPersonnel, LawyerRecommendations, LawyerTeams, LiveChatMessage, NotificationAlerts, SubscriptionDetails, LawPersonnelCertificates, LawPersonnelExperiences, LawPersonnelVerificationDocs, LawyerStats
from dotenv import load_dotenv
from documents_gateway import DocumentsGateway
from rag_gateway import RAGGateway

load_dotenv()

db_func = Functions()
docs = DocumentsGateway()
rag_app = RAGGateway()


class CaseDeletion:
    def delete_case(
        self, lawyer_email: EmailStr, case_id: str, disconnect: bool = False
    ) -> None:
        db_func.remove_case_notifications(lawyer_email, case_id, disconnect)
        print(f"Disconnect boolean: {disconnect}")
        if not disconnect:
            db_func.remove_case_from_lawyer_connection(
                lawyer_email=lawyer_email, case_id=case_id
            )
        db_func.remove_from_case_team(lawyer_email=lawyer_email, case_id=case_id)
        db_func.remove_case_from_all(lawyer_email=lawyer_email, case_id=case_id)
        db_func.remove_case_from_tasks(lawyer_email=lawyer_email, case_id=case_id)
        db_func.remove_case_from_invitations(case_id=case_id)
        db_func.delete_case_documents(lawyer_email=lawyer_email, case_id=case_id)
        db_func.delete_case_actions(lawyer_email=lawyer_email, case_id=case_id)
        db_func.delete_case_from_teams(lawyer_email=lawyer_email, case_id=case_id)


class DisconnectLawyer:
    delete_case = CaseDeletion()

    def disconnect_lawyer(
        self, lawyer_email: EmailStr, immigrant_email: EmailStr
    ) -> None:
        lawyer_cases = db_func.get_connected_lawyer_cases(lawyer_email, immigrant_email)
        db_func.remove_message_history(
            lawyer_email=lawyer_email, immigrant_email=immigrant_email
        )
        for case_id in lawyer_cases:
            self.delete_case.delete_case(
                lawyer_email=lawyer_email, case_id=case_id, disconnect=True
            )
        db_func.remove_immigrant_client(
            lawyer_email=lawyer_email, immigrant_email=immigrant_email
        )
        db_func.disconnect_lawyer_connection(
            lawyer_email=lawyer_email, immigrant_email=immigrant_email
        )


class DeleteImmigrant:
    disconnect = DisconnectLawyer()

    def delete_immigrant_user(self, immigrant_email: EmailStr) -> None:
        connected_lawyers = db_func.get_connected_lawyers(
            immigrant_email=immigrant_email
        )
        db_func.remove_immigrant_subscription(immigrant_email=immigrant_email)
        db_func.remove_immigrant_invitations(immigrant_email=immigrant_email)
        db_func.remove_immigrant_recommendations(immigrant_email=immigrant_email)
        immigrant = db_func.get_immigrant(immigrant_email)
        if immigrant:
            rag_app.delete_store(immigrant.username)
            docs.delete_dir(f"immigrants/{immigrant.username.lower()}/")
        for lawyer_email in connected_lawyers:
            self.disconnect.disconnect_lawyer(
                lawyer_email=lawyer_email, immigrant_email=immigrant_email
            )
        db_func.delete_immigrant_connections(immigrant_email=immigrant_email)
        db_func.delete_immigrant_files(immigrant_email=immigrant_email)
        db_func.delete_immigrant_chat(immigrant_email=immigrant_email)
        db_func.remove_from_users(immigrant_email=immigrant_email)

class DeleteLawpersonnel:
    session = db_func.Session()
    # inspector = inspect(db_func.engine)
    inspector = None
    # TODO: uncomment after AWS is live
    def __init__(self, personnel_username: str) -> None:
        self.username = personnel_username
        self.personnel = self.get_personnel()
        self.personnel_info = (
            self.personnel.get("personnel", None) if self.personnel else None
        )
        self.personnel_table = (
            self.personnel.get("table", None) if self.personnel else None
        )
        self.personnel_case_ids = []

    def get_personnel(self) -> dict[str, Union[LawPersonnel, str]]:
        law_personnel = db_func.get_lawpersonnel(self.username)

        if not law_personnel:
            return {"error": "404 - Personnel Not Found."}

        personnel_info = (
            {"personnel": law_personnel, "table": "law_personnel"}
            if law_personnel
            else None
        )
        return personnel_info

    def outer_cleanup(self) -> str:
        if self.personnel_info.personnel_type == "lawyer":
            try:
                personnel_associated_tables = [
                    f"{self.username}",
                    f"{self.username}_cases",
                    f"{self.username}_clients",
                    f"{self.username}_feedback",
                    f"{self.username}_stats",
                    f"{self.username}_tasks",
                    f"{self.username}_team",
                ]

                personnel_cases_by_ids = self.session.execute(
                    text(f"SELECT id FROM lawyer_{self.username}_cases")
                ).fetchall()
                self.personnel_case_ids = personnel_case_ids = [
                    case_id[0] for case_id in personnel_cases_by_ids
                ]
                personnel_case_tables = [
                    f"{self.username}_case_{case_id}" for case_id in personnel_case_ids
                ]
                personnel_case_team_tables = [
                    f"{self.username}_{case_id}_team" for case_id in personnel_case_ids
                ]
                personnel_document_tables = [
                    f"{self.username}_{case_id}_documents"
                    for case_id in personnel_case_ids
                ]
                personnel_tables = (
                    personnel_associated_tables
                    + personnel_case_tables
                    + personnel_case_team_tables
                    + personnel_document_tables
                )
                case_del = CaseDeletion()
                for case in personnel_case_ids:
                    try:
                        print("Cleaning Case: ", f"{self.username}_case_{case}")
                        lawyer = db_func.get_lawpersonnel(self.username)
                        case_del.delete_case(lawyer.email, case)
                    except Exception as e:
                        print(
                            f"Error Deleting {self.username.capitalize()}'s Case {case}: {e}"
                        )

                for table in personnel_tables:
                    print(f"Running Command: DROP TABLE IF EXISTS {table}")
                    self.session.execute(text(f"DROP TABLE IF EXISTS {table}"))

                self.session.commit()
            except Exception as e:
                print("Law Personnel Not Deleted.")
                self.session.rollback()
                return f"Error Deleting Law Personnel Account: {e}"
            finally:
                self.session.close()

        if self.personnel_info.personnel_type == "nonlawyer":
            query = text(f"SELECT to_regclass('public.lawyer_{self.username}_cases');")
            is_consultant = self.session.execute(query).scalar()
            if is_consultant:
                print(f"{self.username.capitalize()} Is A Consultant.")
                return self.clean_consultants()
            else:
                print(f"{self.username.capitalize()} Is Not A Consultant.")
                return self.clean_other_personnel()

        return "Outer Cleanup Complete."

    def inner_cleanup(self) -> str:
        if not self.personnel:
            return {"error": "404 - Personnel Not Found."}

        table_map = {
            "all_cases": AllCases,
            "case_documents": CaseDocuments,
            "all_tasks": AllTasks,
            "lawyer_teams": LawyerTeams,
            "case_teams": CaseTeams,
            "lawyer_stats": LawyerStats,
            "case_actions": CaseRecentActions,
            "all_clients": AllClients,
            "lawyer_ai_chat": LawPersonnelAIChat,
            "immigrant_lawyer_connection": ImmigrantLawyerConnection,
            "lawpersonnel_certificates": LawPersonnelCertificates,
            "lawpersonnel_experiences": LawPersonnelExperiences,
            "lawpersonnel_verification_docs": LawPersonnelVerificationDocs,
            "sent_messages": ConnectionRequests,
            "chat_messages": ChatMessage,
            "live_chat_messages": LiveChatMessage,
            "subscription_details": SubscriptionDetails,
            "invitations": Invitations,
            "notification_alerts": NotificationAlerts,
            "lawyer_recommendations": LawyerRecommendations,
        }

        personnel_email = self.personnel_info.email if self.personnel_info else None
        personnel_username = (
            self.personnel_info.username if self.personnel_info else None
        )

        if not personnel_email or not personnel_username:
            return {"error": "404 - Personnel Not Found."}

        tables_list = [
            (
                "lawyer_email",
                [
                    "all_cases",
                    "case_documents",
                    "all_tasks",
                    "lawyer_teams",
                    "case_teams",
                    "lawyer_stats",
                    "case_actions",
                    "all_clients",
                    "lawyer_ai_chat",
                    "immigrant_lawyer_connection",
                ],
            ),
            (
                "lawpersonnel_email",
                [
                    "lawpersonnel_certificates",
                    "lawpersonnel_experiences",
                    "lawpersonnel_verification_docs",
                ],
            ),
            (
                "sender_email",
                ["sent_messages", "chat_messages", "live_chat_messages"],
            ),
            ("user_email", ["subscription_details"]),
            (
                "invitee_email",
                ["invitations"],
            ),
            (
                "sender",
                ["notification_alerts"],
            ),
            ("recommendation", ["lawyer_recommendations"]),
        ]

        for target, tables in tables_list:
            try:
                for table in tables:
                    table = table_map.get(table, None)
                    if target == "sender_email":
                        deletion_selection = (
                            self.session.query(table)
                            .filter(
                                or_(
                                    getattr(table, target) == personnel_email,
                                    getattr(table, "recipient_email")
                                    == personnel_email,
                                )
                            )
                            .delete()
                        )
                        print(
                            f"Deleted {deletion_selection} rows from {table} where {target} = {personnel_email}"
                        )
                    elif target == "sender":
                        deletion_selection = (
                            self.session.query(table)
                            .filter(
                                or_(
                                    getattr(table, target) == personnel_email,
                                    getattr(table, "receiver") == personnel_email,
                                )
                            )
                            .delete()
                        )
                        print(
                            f"Deleted {deletion_selection} rows from {table} where {target} = {personnel_email}"
                        )
                    elif target == "invitee_email":
                        deletion_selection = (
                            self.session.query(table)
                            .filter(
                                or_(
                                    getattr(table, target) == personnel_email,
                                    getattr(table, "invited_email") == personnel_email,
                                )
                            )
                            .delete()
                        )
                        print(
                            f"Deleted {deletion_selection} rows from {table} where {target} = {personnel_email}"
                        )
                    elif target == "recommendation":
                        all_recs = self.session.query(LawyerRecommendations).all()
                        for rec in all_recs:
                            rec.registered_lawyers = [
                                lawyer
                                for lawyer in rec.registered_lawyers
                                if lawyer != personnel_email
                            ]
                            rec.unregistered_lawyers = [
                                lawyer
                                for lawyer in rec.unregistered_lawyers
                                if lawyer != personnel_email
                            ]
                            self.session.add(rec)
                        print(
                            f"Deleted Recommendations from {table} where {target} = {personnel_email}"
                        )
                    else:
                        deletion_selection = (
                            self.session.query(table)
                            .filter(getattr(table, target) == personnel_email)
                            .delete()
                        )
                        print(
                            f"Deleted {deletion_selection} rows from {table} where {target} = {personnel_email}"
                        )

                self.session.commit()

            except Exception as e:
                self.session.rollback()

                print(f"Error Deleting Data from {table}: {e}")
                return f"Error Deleting Data from {table}: {e}"
            finally:
                self.session.close()

        print("Deletion Successful")
        return "Inner Cleanup Complete."

    def clean_consultants(self) -> str:
        try:
            personnel_associated_tables = [
                f"{self.username}",
                f"{self.username}_cases",
                f"{self.username}_clients",
                f"{self.username}_feedback",
                f"{self.username}_stats",
                f"nonlawyer_{self.username}_certificates",
                f"nonlawyer_{self.username}_experiences",
            ]

            personnel_cases_by_ids = self.session.execute(
                text(f"SELECT id FROM lawyer_{self.username}_cases")
            ).fetchall()
            personnel_case_ids = [case_id[0] for case_id in personnel_cases_by_ids]
            personnel_case_tables = [
                f"{self.username}_case_{case_id}" for case_id in personnel_case_ids
            ]
            personnel_case_team_tables = [
                f"{self.username}_{case_id}_team" for case_id in personnel_case_ids
            ]
            personnel_document_tables = [
                f"{self.username}_{case_id}_documents" for case_id in personnel_case_ids
            ]
            personnel_tables = (
                personnel_associated_tables
                + personnel_case_tables
                + personnel_case_team_tables
                + personnel_document_tables
            )

            case_del = CaseDeletion()
            for case in personnel_case_ids:
                try:
                    print("Cleaning Case: ", f"{self.username}_case_{case}")
                    lawyer = db_func.get_lawpersonnel(self.username)
                    case_del.delete_case(lawyer.email, case)
                except Exception as e:
                    print(
                        f"Error Deleting {self.username.capitalize()}'s Case {case}: {e}"
                    )

            for table in personnel_tables:
                print(f"Running Command: DROP TABLE IF EXISTS {table}")
                self.session.execute(text(f"DROP TABLE IF EXISTS {table}"))

            self.session.commit()
        except Exception as e:
            print("Law Personnel Not Deleted.")
            self.session.rollback()
            return f"Error Deleting Law Personnel Account: {e}"
        finally:
            self.session.close()

        return "Outer Cleanup Complete."

    def clean_other_personnel(self) -> str:
        try:
            personnel_tables = {
                "lawstudents": [
                    f"lawstdn_{self.username}_certificates",
                    f"lawstdn_{self.username}_experiences",
                ],
                "paralegals": [
                    f"paralegal_{self.username}_certificates",
                    f"paralegal_{self.username}_experiences",
                ],
                "nonlawyers": [
                    f"nonlawyer_{self.username}_certificates",
                    f"nonlawyer_{self.username}_experiences",
                ],
            }
            personnel_tables = personnel_tables.get(self.personnel_table, [])

            for table in personnel_tables:
                print(f"Running Command: DROP TABLE IF EXISTS {table}")
                self.session.execute(text(f"DROP TABLE IF EXISTS {table}"))

            self.session.commit()
        except Exception as e:
            print("Law Personnel Not Deleted.")
            self.session.rollback()
            return f"Error Deleting Law Personnel Account: {e}"
        finally:
            self.session.close()

        return "Outer Cleanup Complete."

    def delete_personnel(self) -> str:
        try:
            self.session.delete(self.personnel_info)
            print(
                f"Running Command: DELETE FROM {self.personnel_table} WHERE username = {self.username}"
            )

            self.session.commit()
        except Exception as e:
            print("Law Personnel Not Deleted.")

            self.session.rollback()
            return f"Error Deleting Law Personnel Account: {e}"
        finally:
            self.session.close()

    def complete_clean(self) -> str:
        try:
            db_tables = self.inspector.get_table_names()
            search_pattern = re.compile(
                rf"{self.username}.*(chat|clients|cases|feedback|stats|tasks|team|documents)"
            )

            personnel_associated_tables = [
                table for table in db_tables if search_pattern.search(table)
            ]
            for table in personnel_associated_tables:
                self.session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"Running Command: DROP TABLE IF EXISTS {table}")

            self.delete_personnel()

            self.session.commit()
        except Exception as e:
            print("Law Personnel Not Deleted.")
            self.session.rollback()
            return f"Error Deleting Law Personnel Account: {e}"
        finally:
            self.session.close()

        return "Complete Cleanup Done."

    def run_cleanup(self) -> str:
        outer_cleanup = self.outer_cleanup()
        inner_cleanup = self.inner_cleanup()

        if (
            outer_cleanup == "Outer Cleanup Complete."
            and inner_cleanup == "Inner Cleanup Complete."
        ):
            self.delete_personnel()
            return "Personnel Cleanup Complete."
        else:
            return "Personnel Cleanup Failed - Check Personnel Username."

    def run_keep_cleanup(self) -> str:
        try:
            personnel_s3_directory = f"https://doloreschatbucket.s3.us-east-2.amazonaws.com/lawyers/{self.username}"
            exists = docs.is_exists(personnel_s3_directory)
            if exists:
                for case_id in self.personnel_case_ids:
                    case_s3_directory = f"{personnel_s3_directory}/{case_id}/"
                    print(f"Cleaning S3 Directory: {case_s3_directory}")
                    docs.delete_dir(case_s3_directory)
                    print(
                        f"Deleted {self.username.capitalize()}'s S3 Case Directory With ID: {case_id}"
                    )
            else:
                print(f"No S3 Case Directory Found For {self.username.capitalize()}.")
                return "No S3 Directory Found."
        except Exception as e:
            print(f"Error Cleaning S3 Files: {e}")
            return "Error Cleaning S3 Files."

        print(f"All {self.username.capitalize()}'s Case Directories Cleaned.")
        outer_cleanup = self.outer_cleanup()
        inner_cleanup = self.inner_cleanup()

        if (
            outer_cleanup == "Outer Cleanup Complete."
            and inner_cleanup == "Inner Cleanup Complete."
        ):
            return "Personnel Keep Cleanup Complete."
        else:
            return "Personnel Keep Cleanup Failed - Check Personnel Username."
