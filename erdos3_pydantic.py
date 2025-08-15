from collections import defaultdict
import json
from pydantic import BaseModel
import scipy.sparse as sp
import numpy as np


class Article(BaseModel):
    doi: str
    title: str
    publication_date: int

class Author(BaseModel):
    id: int
    orcid: str
    last_name: str
    given_names: str

class Authorship(BaseModel):
    author_orcid: str
    article_doi: str


class FatArticle(BaseModel):
    doi: str
    title: str
    publication_date: int
    authors: list[Author]


def _load_ndjson(file_path: str) -> list[dict]:
    """Loads and returns data from a NDJSON file as a list of dictionaries."""
    result = []
    with open(file_path, 'r') as file:
        for line in file:
            result.append(json.loads(line))
    return result

def load_authors(file_path: str) -> list[Author]:
    """Loads and returns authors from a NDJSON file as a list of objects.""" 
    data = _load_ndjson(file_path)
    return [Author(**item) for item in data]

def load_articles(file_path: str) -> list[Article]:
    """Loads and returns articles from a NDJSON file as a list of objects.""" 
    data = _load_ndjson(file_path)
    return [Article(**item) for item in data]

def load_authorship(file_path: str) -> list[Authorship]:
    """Loads and returns authorship relations from a NDJSON file as a list of objects."""
    data = _load_ndjson(file_path)
    return [Authorship(**item) for item in data]


def attach_authors(articles: list[Article], authors: list[Author], authorships: list[Authorship]) -> list[FatArticle]:
    """Return a copy of all article objects with authors attached to a new attribute."""
    # Build mapping: doi -> list of authorship relations
    fat_articles: list[FatArticle] = []

    authorships_by_doi: defaultdict[str, list[Authorship]] = defaultdict(list)
    for authorship in authorships:
        doi = authorship.article_doi
        authorships_by_doi[doi].append(authorship)

    # Build mapping: orcid -> author
    author_by_orcid = {author.orcid: author for author in authors}

    # Iterate over all articles and attach authors
    for article in articles:
        fat_article = FatArticle(
            authors=[],
            title=article.title,
            publication_date=article.publication_date,
            doi=article.doi,
        )
        for authorship in authorships_by_doi[article.doi]:
            author = author_by_orcid[authorship.author_orcid]
            fat_article.authors.append(author)
        fat_articles.append(fat_article)

    return fat_articles


def build_coauthorship_matrix(fat_articles: list[FatArticle]) -> sp.csr_matrix:
    """Return a sparse, symmetric matrix representing the coauthorship matrix.

    Each row and column represents an author, and each entry (i, j) represents the number of papers co-authored by authors i and j.
    """
    row_idx: list[int] = []
    col_idx: list[int]= []
    distance: list[int]= []

    for article in fat_articles:

        # Iterate over all author/co-author pairs
        for author in article.authors:
            for coauthor in article.authors:
                if author.orcid == coauthor.orcid:
                    # An author is not a co-author of themselves
                    continue

                # Add entry to sparse co-authorship matrix
                row_idx.append(author.id)
                col_idx.append(coauthor.id)
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
    authorships = load_authorship("esp2025_authorships.ndjson")

    # Resolving many-to-many relationship
    fat_articles = attach_authors(articles, authors, authorships)

    # Build co-authorship matrix (adjacency matrix)
    coauthorship = build_coauthorship_matrix(fat_articles)

    # Compute Erdos number between two authors
    print(erdos(coauthorship, 4, 990))
