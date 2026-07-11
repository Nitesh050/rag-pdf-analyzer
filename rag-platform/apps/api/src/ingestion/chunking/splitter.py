from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentSplitter:
    """
    Responsible for splitting documents into semantically
    meaningful chunks using recursive splitting.
    """

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
    ):

        self.splitter = RecursiveCharacterTextSplitter(

            chunk_size=chunk_size,

            chunk_overlap=chunk_overlap,

            separators=[
                "\n# ",      # Markdown Heading
                "\n## ",
                "\n### ",
                "\n\n",      # Paragraph
                "\n",        # Line
                ". ",        # Sentence
                "? ",
                "! ",
                "; ",
                ", ",
                " ",         # Word
                "",          # Character
            ],

            keep_separator=True,

            add_start_index=True,
        )

    def split(
        self,
        documents: list[Document],
    ) -> list[Document]:

        return self.splitter.split_documents(documents)