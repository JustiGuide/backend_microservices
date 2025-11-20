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

    def delete_store(self, username: str) -> bool:
        # """Delete entire vector store for user."""
        # try:
        #     vector_store = self.get_vector_store(username)
        #     if vector_store:
        #         vector_store.delete_collection()
        #         # Clear cache
        #         if self.rag_config.enable_caching:
        #             if (
        #                 self._vector_store_cache
        #                 and username in self._vector_store_cache
        #             ):
        #                 del self._vector_store_cache[username]
        #             if (
        #                 self._collection_name_cache
        #                 and username in self._collection_name_cache
        #             ):
        #                 del self._collection_name_cache[username]
        #         print(f"RAG: Successfully deleted store for {username}")
        #         return True
        # except Exception as e:
        #     raise ProcessError(desc=f"RAG: Failed to delete store for {username}: {e}")
        # return False
        # TODO: Connect to RAG Gateway
        pass
