from collections import defaultdict
import json
import scipy.sparse as sp
import numpy as np

def load_ndjson(file_path):
    """Loads and returns data from a NDJSON file as a list of objects.""" 
    result = []
    with open(file_path, 'r') as file:
        for line in file:
            result.append(json.loads(line))
    return result


def attach_authors(articles, authors, authorships):
    """Return a copy of all article objects with authors attached to a new attribute."""
    # Build mapping: doi -> list of authorship relations
    fat_articles = []

    authorships_by_doi = defaultdict(list)
    for authorship in authorships:
        doi = authorship["article_doi"]
        authorships_by_doi[doi].append(authorship)

    # Build mapping: orcid -> author
    author_by_orcid = {author["orcid"]: author for author in authors}

    # Iterate over all articles and attach authors
    for article in articles:
        fat_article = {
            "authors": [],
            **article,
        }
        for authorship in authorships_by_doi[article["doi"]]:
            author = author_by_orcid[authorship["author_orcid"]]
            fat_article["authors"].append(author)
        fat_articles.append(fat_article)

    return fat_articles


def build_coauthorship_matrix(fat_articles):
    """Return a sparse, symmetric matrix representing the coauthorship matrix.

    Each row and column represents an author, and each entry (i, j) represents the number of papers co-authored by authors i and j.
    """
    row_idx = []
    col_idx = []
    distance = []

    for article in fat_articles:

        # Iterate over all author/co-author pairs
        for author in article["authors"]:
            for coauthor in article["authors"]:
                if author["orcid"] == coauthor["orcid"]:
                    # An author is not a co-author of themselves
                    continue

                # Add entry to sparse co-authorship matrix
                row_idx.append(author["id"])
                col_idx.append(coauthor["id"])
                distance.append(1)

    coauthorship = sp.coo_matrix((distance, (row_idx, col_idx)), dtype=np.int8)

    # Convert to CSR format to allow indexing
    coauthorship = coauthorship.tocsr()
    return coauthorship

    
def erdos(coauthorship, id_a, id_b):
    """Returns the Erdos number of the path between two authors, or raises an ValueError"""
    distance = sp.csgraph.dijkstra(coauthorship, directed=True, indices=[id_a])[0][id_b]
    if np.isinf(distance):
        raise ValueError("No path between the authors exists.")
    return int(distance)

    
if __name__ == "__main__":
    # Load data
    articles = load_ndjson("esp2025_articles.ndjson")
    authors = load_ndjson("esp2025_authors.ndjson")
    authorships = load_ndjson("esp2025_authorships.ndjson")

    # Resolving many-to-many relationship
    fat_articles = attach_authors(articles, authors, authorships)

    # Build co-authorship matrix (adjacency matrix)
    coauthorship = build_coauthorship_matrix(fat_articles)

    # Compute Erdos number between two authors
    print(erdos(coauthorship, 4, 990))
