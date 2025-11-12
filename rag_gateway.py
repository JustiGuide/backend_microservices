from typing import Optional


class RAGGateway:
    def __init__(self, config_name="balanced"):
        self.config_name = config_name

    def retrieve_hybrid_context(
        self,
        username: str,
        query: str,
        file_urls: Optional[list[str]] = None,
        top_k_files: int = 5,
        top_k_general: int = 3,
    ) -> str:
        # TODO: Connect to RAG Gateway
        pass

    def delete_data_by_source(self, username: str, sources: list[str]) -> bool:
        # TODO: Connect to RAG Gateway
        pass

    def load_kyc_map(self):
        # TODO: Connect to RAG Gateway
        pass