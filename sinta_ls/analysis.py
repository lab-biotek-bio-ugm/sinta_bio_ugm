"""Offline analysis of scraped data: title clustering and co-author network."""
import json

import altair as alt
import networkx as nx
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import davies_bouldin_score, silhouette_score

from . import ANALYSIS_SETS, PROCESSED, SCRAPE_SETS

SEED = 42
INDONESIAN_STOP_WORDS = [
    'dan', 'yang', 'untuk', 'dari', 'dengan', 'pada', 'adalah', 'ke', 'di', 'sebagai', 'ini',
    'itu', 'oleh', 'dalam', 'atau', 'juga', 'tersebut', 'sangat', 'agar', 'bisa', 'karena', 'terhadap',
    'pengaruh', 'berdasarkan', 'indonesia', 'isolated', 'based', 'daerah', 'indonesian', 'yogyakarta',
    'java', 'analysis', 'effect', 'using', "sp"
]
STOP_WORDS = list(set(TfidfVectorizer(stop_words='english').get_stop_words()).union(INDONESIAN_STOP_WORDS))


def load(dataset):
    """Merged {sinta_id: author record} for an analysis set (or a single scrape set)."""
    members = ANALYSIS_SETS[dataset]["members"] if dataset in ANALYSIS_SETS else [dataset]
    data = {}
    for m in members:
        data.update(json.loads((PROCESSED / SCRAPE_SETS[m]["out"]).read_text()))
    return data


def titles(data):
    """One row per publication: author (sinta_id), title. Authors without publications are skipped."""
    rows = [{"author": sid, "title": p["bib"]["title"]}
            for sid, v in data.items() for p in (v["publications"] or [])]
    return pd.DataFrame(rows)


def top_words(texts, top_n=5):
    vectorizer = TfidfVectorizer(stop_words=STOP_WORDS)
    tfidf = vectorizer.fit_transform(texts)
    order = tfidf.toarray().sum(axis=0).argsort()[::-1]
    return ', '.join(vectorizer.get_feature_names_out()[order[:top_n]])


def author_pca(data):
    """TF-IDF of each author's concatenated titles reduced to 3 PCA components."""
    df = titles(data)
    vectorizer = TfidfVectorizer(stop_words=STOP_WORDS).fit(df['title'])
    profiles = df.groupby('author')['title'].apply(' '.join).reset_index()
    pca = PCA(n_components=3)
    reduced = pca.fit_transform(vectorizer.transform(profiles['title']).toarray())
    return profiles, reduced, pca.explained_variance_ratio_


def cluster_metrics(reduced, ks=range(2, 21)):
    rows = []
    for k in ks:
        km = KMeans(n_clusters=k, random_state=SEED)
        labels = km.fit_predict(reduced)
        rows.append({'k': k, 'WCSS': km.inertia_,
                     'Silhouette Score': silhouette_score(reduced, labels),
                     'Davies-Bouldin Index': davies_bouldin_score(reduced, labels)})
    return pd.DataFrame(rows)


def cluster_metrics_chart(metrics, box_size=150, font_size=10):
    """Elbow / silhouette / Davies-Bouldin side by side."""
    axis = alt.Axis(labelFontSize=font_size, titleFontSize=font_size)

    def panel(col, title):
        return alt.Chart(metrics).mark_line(point=True).encode(
            x=alt.X('k', title='Number of Clusters (k)', axis=axis),
            y=alt.Y(col, title=col, axis=axis),
            tooltip=['k', col],
        ).properties(title=alt.TitleParams(title, fontSize=font_size + 2), height=box_size, width=box_size)

    return (panel('WCSS', 'Elbow Method for Optimal k')
            | panel('Silhouette Score', 'Silhouette Score for Optimal k')
            | panel('Davies-Bouldin Index', 'Davies-Bouldin Index for Optimal k'))


def title_clusters(data, k):
    """Author profiles with KMeans cluster, PCA coords and top words. Returns (profiles, explained_variance, silhouette)."""
    profiles, reduced, explained = author_pca(data)
    clusters = KMeans(n_clusters=k, random_state=SEED).fit_predict(reduced)
    profiles['cluster'] = clusters
    profiles['PCA1'] = reduced[:, 0]
    profiles['PCA2'] = reduced[:, 1]
    profiles['sinta_id'] = profiles['author']
    profiles['author_name'] = profiles['author'].map(lambda x: data[x]['name_inputted'])
    profiles['subjects'] = profiles['author'].map(lambda x: ", ".join(data[x]['subjects']))
    profiles['affiliation_sinta'] = profiles['author'].map(lambda x: data[x]['affiliation_sinta']['name'])
    cluster_words = {c: top_words(g['title']) for c, g in profiles.groupby('cluster')}
    profiles['top_words_cluster'] = profiles['cluster'].map(cluster_words)
    profiles['top_words_author'] = profiles['title'].map(lambda t: top_words([t]))
    return profiles, explained, silhouette_score(reduced, clusters)


def pca_chart(profiles, explained, silhouette, width=400, height=400, field='cluster', label='Cluster'):
    """Interactive PCA scatter with marginal histograms and a cluster dropdown."""
    options = list(profiles[field].unique())
    resize = alt.selection_interval(bind='scales')
    base = alt.Chart(profiles)
    dropdown = alt.binding_select(options=options + [None],
                                  labels=[f'{o} ' for o in options] + ['All '], name=f'{label} ')
    selection = alt.selection_point(fields=[field], bind=dropdown)
    color = alt.condition(selection, alt.Color(f'{field}:N').legend(None), alt.value('lightgray'))

    scatter = base.mark_circle(size=75).encode(
        x=alt.X('PCA1', title=None),
        y=alt.Y('PCA2', title=f'PCA2 ({explained[1]*100:.2f}% variance)'),
        color=color,
        tooltip=['author_name', 'affiliation_sinta', 'cluster', 'top_words_cluster',
                 'top_words_author', 'subjects', 'sinta_id'],
    ).add_params(selection, resize).properties(height=height, width=width)
    legend = base.mark_circle(size=75).encode(alt.Y(f'{field}:N', title=label).axis(orient='right'), color=color)
    right_hist = base.mark_bar().encode(
        x=alt.X('count()', title='Author Count'),
        y=alt.Y('PCA2:Q', title="").bin(maxbins=18),
        color=color,
    ).add_params(selection, resize).properties(height=height, width=50)
    bottom_hist = base.mark_bar().encode(
        x=alt.X('PCA1:Q', bin=alt.Bin(maxbins=18), title=f'PCA1 ({explained[0]*100:.2f}% variance)'),
        y=alt.Y('count()', title='Author Count', scale=alt.Scale(reverse=True)),
        color=color,
    ).add_params(selection, resize).properties(height=50, width=width)
    vline = base.mark_rule(color='gray').encode(x=alt.datum(0))
    hline = base.mark_rule(color='gray').encode(y=alt.datum(0))

    combined = alt.vconcat(scatter + vline + hline, bottom_hist + vline).resolve_scale(color='independent') \
        | right_hist + hline | legend
    return combined.properties(title=alt.TitleParams(f'Silhouette Score: {silhouette:.2f}', anchor='middle'))


def coauthor_graph(data):
    """Directed graph main author -> Google Scholar co-authors, keyed by scholar_id."""
    G = nx.DiGraph()
    for v in data.values():
        main = v.get("scholar_id")
        if main is None:
            continue
        G.add_node(main)
        for c in v.get("coauthors") or []:
            G.add_node(c["scholar_id"], role='coauthor', name=c["name"], affiliation=c["affiliation"])
            G.add_edge(main, c["scholar_id"])
    # set main-author attributes last so a main author listed as someone's co-author stays 'main'
    for v in data.values():
        if v.get("scholar_id") is not None:
            G.nodes[v["scholar_id"]].update(role='main', name=v['name_inputted'],
                                            affiliation=v['affiliation_sinta']['name'])
    return G


def connecting_subgraph(G):
    """Main authors plus co-authors linked to more than one main author."""
    keep = [n for n in G if G.nodes[n]["role"] == "main" or len(list(nx.all_neighbors(G, n))) > 1]
    return G.subgraph(keep)


def draw(G, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    main = {n: d["name"] for n, d in G.nodes(data=True) if d["role"] == "main"}
    pos = nx.kamada_kawai_layout(G)
    plt.figure()
    nx.draw(G, pos, node_color=['red' if n in main else 'gray' for n in G],
            node_size=[100 if n in main else 25 for n in G], alpha=0.5, with_labels=False)
    nx.draw_networkx_labels(G, pos, main, font_size=5)
    plt.savefig(path)
    plt.close()
