"""python -m sinta_ls {scrape <SET> | analyze <SET> | stats}"""
import argparse
import json

from . import ANALYSIS_SETS, FIGURES, PROCESSED, SCRAPE_SETS


def analyze(dataset):
    from . import analysis as a

    data = a.load(dataset)
    figs = FIGURES / dataset
    figs.mkdir(parents=True, exist_ok=True)
    graphs = PROCESSED / dataset
    graphs.mkdir(parents=True, exist_ok=True)

    profiles, reduced, _ = a.author_pca(data)
    a.cluster_metrics_chart(a.cluster_metrics(reduced)).save(figs / "01_clusterplot_publication_titles.html")
    profiles, explained, sil = a.title_clusters(data, ANALYSIS_SETS[dataset]["k"])
    a.pca_chart(profiles, explained, sil).save(figs / "01_PCA_publication_titles.html")

    G = a.coauthor_graph(data)
    H = a.connecting_subgraph(G)
    a.draw(G, figs / "02.0_co-author_graph.png")
    a.draw(H, figs / "02.2_connecting_co-author_graph.png")
    a.nx.write_graphml(G, graphs / "co-author_network.graphml")
    a.nx.write_graphml(H, graphs / "co-author_subgraph_network.graphml")
    print(f"{dataset}: {len(data)} authors, silhouette {sil:.2f}, "
          f"graph {G.number_of_nodes()} nodes / {G.number_of_edges()} edges, subgraph {H.number_of_nodes()} nodes")


def stats():
    print("| set | lecturers | with Google Scholar | publications | co-authors listed |")
    print("|---|---:|---:|---:|---:|")
    for name, cfg in SCRAPE_SETS.items():
        d = json.loads((PROCESSED / cfg["out"]).read_text())
        scholar = sum(1 for v in d.values() if v.get("scholar_id"))
        pubs = sum(len(v.get("publications") or []) for v in d.values())
        coauth = sum(len(v.get("coauthors") or []) for v in d.values())
        print(f"| {name} | {len(d)} | {scholar} | {pubs:,} | {coauth:,} |")


def main():
    p = argparse.ArgumentParser(prog="sinta_ls")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scrape", help="roster -> SINTA -> Google Scholar (network)").add_argument("set", choices=SCRAPE_SETS)
    sub.add_parser("analyze", help="clustering + co-author network (offline)").add_argument("set", choices=ANALYSIS_SETS)
    sub.add_parser("stats", help="markdown summary of the scraped data")
    args = p.parse_args()
    if args.cmd == "scrape":
        from .scrape import scrape
        scrape(args.set)
    elif args.cmd == "analyze":
        analyze(args.set)
    else:
        stats()


if __name__ == "__main__":
    main()
