from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class RAGConfig:
    # Core settings
    enable_cross_encoder: bool = True
    batch_size: int = 7500

    # Retrieval settings
    initial_candidate_multiplier: int = (
        4  # How many candidates to get before re-ranking
    )
    max_initial_candidates: int = 20
    default_top_k: int = 5

    # Processing settings
    chunk_size: int = 1000
    chunk_overlap: int = 150
    max_file_size_mb: int = 100
    max_workers: int = 4

    # Vision model settings
    vision_model: str = "gpt-5"
    vision_detail: str = "high"
    vision_max_tokens: int = 1024
    vision_temperature: float = 0.2

    # HyDE settings
    hyde_model: str = "gpt-4o"
    hyde_max_tokens: int = 100
    hyde_temperature: float = 0.0

    # Cache settings
    enable_caching: bool = True
    cache_max_size: int = 128

    # Logging settings
    log_level: str = "INFO"
    log_file: str = "optimized_rag.log"

    # Performance monitoring
    enable_performance_tracking: bool = True
    performance_log_file: str = "rag_performance.log"

SPEED_OPTIMIZED_CONFIG = RAGConfig(
    enable_cross_encoder=False,
    batch_size=10000,
    initial_candidate_multiplier=2,
    max_initial_candidates=10,
    default_top_k=3,
    vision_detail="low",
    vision_max_tokens=512,
    hyde_model="gpt-3.5",
    enable_performance_tracking=False,
    max_workers=8,
)

ACCURACY_OPTIMIZED_CONFIG = RAGConfig(
    enable_cross_encoder=True,
    batch_size=5000,
    initial_candidate_multiplier=6,
    max_initial_candidates=30,
    default_top_k=8,
    chunk_overlap=200,
    vision_detail="high",
    vision_max_tokens=1500,
    hyde_model="gpt-4",
    hyde_max_tokens=150,
    max_workers=4,
)

BALANCED_CONFIG = RAGConfig(
    enable_cross_encoder=True,
    batch_size=7500,
    initial_candidate_multiplier=4,
    max_initial_candidates=20,
    default_top_k=5,
    vision_detail="high",
    vision_max_tokens=1024,
)

LARGE_SCALE_CONFIG = RAGConfig(
    enable_cross_encoder=False,
    batch_size=15000,
    initial_candidate_multiplier=2,
    max_initial_candidates=8,
    default_top_k=3,
    vision_detail="low",
    vision_max_tokens=256,
    enable_performance_tracking=True,
    max_workers=16,
)

DEVELOPMENT_CONFIG = RAGConfig(
    enable_cross_encoder=True,
    batch_size=1000,
    initial_candidate_multiplier=3,
    max_initial_candidates=15,
    default_top_k=5,
    log_level="DEBUG",
    enable_performance_tracking=True,
)


class ConfigManager:
    CONFIGS = {
        "speed": SPEED_OPTIMIZED_CONFIG,
        "accuracy": ACCURACY_OPTIMIZED_CONFIG,
        "balanced": BALANCED_CONFIG,
        "large_scale": LARGE_SCALE_CONFIG,
        "development": DEVELOPMENT_CONFIG,
    }

    @classmethod
    def get_config(cls, config_name: str) -> RAGConfig:
        if config_name not in cls.CONFIGS:
            raise ValueError(
                f"Unknown config: {config_name}. Available: {list(cls.CONFIGS.keys())}"
            )
        return cls.CONFIGS[config_name]

    @classmethod
    def create_custom_config(
        cls, base_config: str = "balanced", **overrides
    ) -> RAGConfig:
        base = cls.get_config(base_config)
        
        config_dict = base.__dict__.copy()
        config_dict.update(overrides)

        return RAGConfig(**config_dict)

    @classmethod
    def get_config_for_user_count(cls, user_count: int) -> RAGConfig:
        if user_count < 100:
            return cls.get_config("balanced")
        elif user_count < 1000:
            return cls.get_config("speed")
        else:
            return cls.get_config("large_scale")

    @classmethod
    def get_config_for_data_size(cls, total_documents: int) -> RAGConfig:
        if total_documents < 10000:
            return cls.get_config("accuracy")
        elif total_documents < 100000:
            return cls.get_config("balanced")
        else:
            return cls.get_config("speed")


def get_performance_recommendations(
    current_performance: Dict[str, float],
) -> Dict[str, Any]:
    recommendations = {"config_changes": {}, "suggestions": [], "priority": "medium"}

    avg_time = current_performance.get("avg_retrieval_time", 0)
    accuracy = current_performance.get("accuracy_score", 0)
    user_count = current_performance.get("active_users", 0)

    if avg_time > 3.0:  # Slow retrieval
        recommendations["config_changes"]["enable_cross_encoder"] = False
        recommendations["config_changes"]["default_top_k"] = 3
        recommendations["suggestions"].append(
            "Consider disabling cross-encoder for faster retrieval"
        )
        recommendations["priority"] = "high"

    if avg_time > 1.5 and accuracy > 0.8:  # Decent accuracy, but slow
        recommendations["config_changes"]["initial_candidate_multiplier"] = 2
        recommendations["suggestions"].append(
            "Reduce candidate pool size for faster processing"
        )

    if accuracy < 0.6:  # Poor accuracy
        recommendations["config_changes"]["enable_cross_encoder"] = True
        recommendations["config_changes"]["initial_candidate_multiplier"] = 6
        recommendations["config_changes"]["hyde_model"] = "gpt-4-0125-preview"
        recommendations["suggestions"].append(
            "Enable advanced retrieval features for better accuracy"
        )
        recommendations["priority"] = "high"

    if user_count > 1000:  # High load
        recommendations["config_changes"]["batch_size"] = 15000
        recommendations["config_changes"]["enable_cross_encoder"] = False
        recommendations["suggestions"].append("Optimize for high-scale operations")

    return recommendations