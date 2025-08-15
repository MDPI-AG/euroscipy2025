import pandas as pd
import scipy.sparse as sp
import numpy as np
import pandera.pandas as pa
from pandera.typing.pandas import Series, DataFrame


class ArticleSchema(pa.DataFrameModel):
    doi: Series[str]
    title: Series[str]
    publication_date: Series[int]


class AuthorSchema(pa.DataFrameModel):
    id: Series[int]
    orcid: Series[str]
    last_name: Series[str]
    given_names: Series[str]


class AuthorshipSchema(pa.DataFrameModel):
    author_orcid: Series[str]
    article_doi: Series[str]


def _load_ndjson(file_path: str) -> pd.DataFrame:
    """Loads and returns data from a NDJSON file as a list of objects.""" 
    return pd.read_json(file_path, lines=True)


def load_articles(file_path: str) -> DataFrame[ArticleSchema]:
    """Loads and returns articles from a NDJSON file as a list of objects.""" 
    df = _load_ndjson(file_path)
    return ArticleSchema.validate(df)


def load_authors(file_path: str) -> DataFrame[AuthorSchema]:
    """Loads and returns authors from a NDJSON file as a list of objects.""" 
    df = _load_ndjson(file_path)
    return AuthorSchema.validate(df)


def load_authorships(file_path: str) -> DataFrame[AuthorshipSchema]:
    """Loads and returns authorships from a NDJSON file as a list of objects.""" 
    df = _load_ndjson(file_path)
    return AuthorshipSchema.validate(df)


def build_coauthorship_matrix(authors: DataFrame[AuthorSchema], authorships: DataFrame[AuthorshipSchema]) -> sp.csr_matrix:
    """Return a sparse, symmetric matrix representing the coauthorship matrix.

    Each row and column represents an author, and each entry (i, j) represents the number of papers co-authored by authors i and j.
    """
    article_groups = authorships.merge(authors, left_on="author_orcid", right_on="orcid").groupby("article_doi")

    row_idx: list[int] = []
    col_idx: list[int] = []
    distance: list[int] = []

    for _, article in article_groups:
        # Iterate over all author/co-author pairs
        for _, author in article.iterrows():
            for _, coauthor in article.iterrows():
                if author["orcid"] == coauthor["orcid"]:
                    # An author is not a co-author of themselves
                    continue

                # Add entry to sparse co-authorship matrix
                row_idx.append(author["id"])
                col_idx.append(coauthor["id"])
                distance.append(1)

    coauthorship = sp.coo_matrix((distance, (row_idx, col_idx)), dtype=np.int8)  # type: ignore

    # Convert to CSR format to allow indexing
    return coauthorship.tocsr()

    
def erdos(coauthorship: sp.csr_matrix, id_a: int, id_b: int) -> int:
    """Returns the Erdos number of the path between two authors, or raises an ValueError"""
    distance = sp.csgraph.dijkstra(coauthorship, directed=True, indices=[id_a])[0][id_b]
    if np.isinf(distance):
        raise ValueError("No path between the authors exists.")
    return int(distance)


if __name__ == "__main__":
    # Load data
    articles = load_articles("esp2025_articles.ndjson")
    authors = load_authors("esp2025_authors.ndjson")
    authorships = load_authorships("esp2025_authorships.ndjson")

    # Build co-authorship matrix (adjacency matrix)
    coauthorship = build_coauthorship_matrix(authors, authorships)

    # Compute Erdos number between two authors
    print(erdos(coauthorship, 4, 990))
