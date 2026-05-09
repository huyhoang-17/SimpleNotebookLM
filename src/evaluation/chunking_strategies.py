from dataclasses import dataclass
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ==========================================
# Cấu hình Recursive Chunking (Trang 30 - 31)
# ==========================================

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

_RECURSIVE_CONFIGS = [
    ("rc_500_50", 500, 50),
    ("rc_800_100", 800, 100),
    ("rc_1000_150", 1000, 150),
    ("rc_1500_200", 1500, 200),
]


@dataclass
class ChunkingStrategy:
    strategy_id: str
    chunker: object
    params: dict


@dataclass
class RecursiveChunker:
    chunk_size: int = 500
    chunk_overlap: int = 50
    separators: list[str] | None = None

    def _splitter(self) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators or DEFAULT_SEPARATORS,
            is_separator_regex=False,
        )

    def split_documents(self, documents: list[Document]) -> list[Document]:
        if not documents:
            return []
        return self._splitter().split_documents(documents)


# ==========================================
# Cấu hình Semantic Chunking (Trang 31 - 32)
# ==========================================

_SEMANTIC_CONFIGS = [
    ("semantic_percentile", "percentile"),
    ("semantic_std_dev", "standard_deviation"),
    ("semantic_interquartile", "interquartile"),
]


@dataclass
class SemanticChunkerWrapper:
    embeddings: Embeddings
    breakpoint_type: str = "percentile"

    def _splitter(self) -> SemanticChunker:
        return SemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type=self.breakpoint_type,
        )

    def split_documents(self, documents: list[Document]) -> list[Document]:
        if not documents:
            return []
        return self._splitter().split_documents(documents)

    def split_text(self, text: str) -> list[str]:
        return self._splitter().split_text(text)


def build_all_strategies(embeddings: Embeddings | None = None) -> list[ChunkingStrategy]:
    strategies = []

    for sid, size, overlap in _RECURSIVE_CONFIGS:
        strategies.append(ChunkingStrategy(
            strategy_id=sid,
            chunker=RecursiveChunker(chunk_size=size, chunk_overlap=overlap),
            params={"chunk_size": size, "chunk_overlap": overlap},
        ))

    if embeddings is not None:
        for sid, btype in _SEMANTIC_CONFIGS:
            strategies.append(ChunkingStrategy(
                strategy_id=sid,
                chunker=SemanticChunkerWrapper(embeddings=embeddings, breakpoint_type=btype),
                params={"breakpoint_type": btype},
            ))

    return strategies
