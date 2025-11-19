from pydantic import EmailStr


class DisconnectLawyer:

    def disconnect_lawyer(
        self, lawyer_email: EmailStr, immigrant_email: EmailStr
    ) -> None:
        # db = self.Session()
        # lawyer_cases = self.get_connected_lawyer_cases(lawyer_email, immigrant_email)
        # self.remove_message_history(
        #     lawyer_email=lawyer_email, immigrant_email=immigrant_email
        # )
        # for case_id in lawyer_cases:
        #     self.delete_case.delete_case(
        #         lawyer_email=lawyer_email, case_id=case_id, disconnect=True
        #     )
        # self.remove_immigrant_client(
        #     lawyer_email=lawyer_email, immigrant_email=immigrant_email
        # )
        # self.disconnect_lawyer_connection(
        #     lawyer_email=lawyer_email, immigrant_email=immigrant_email
        # )
        # db.close()
        # TODO: Connect with utilities service
        pass