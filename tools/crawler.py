"""
Crawler: アダプターを使って判例を取得し、DBに格納する。
管轄間は並列、管轄内は直列（rate limiting遵守）。
"""
import sys
import os
import time
import importlib
import glob
import concurrent.futures
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.storage import init_db, store_case, get_stats


def get_adapter(adapter_file: str):
    """アダプターファイルからAdapterクラスをロードする"""
    modname = adapter_file.replace("/", ".").replace(".py", "")
    mod = importlib.import_module(modname)
    for name in dir(mod):
        if name.endswith("Adapter") and name != "BaseAdapter":
            return getattr(mod, name)()
    return None


def crawl_jurisdiction(adapter_file: str, queries: list, max_per_query: int = 50,
                       rate_limit: float = 1.0) -> dict:
    """1管轄をクロールする"""
    adapter = get_adapter(adapter_file)
    if not adapter:
        return {"adapter": adapter_file, "status": "error", "reason": "no adapter class found"}

    modname = adapter_file.split("/")[-1].replace(".py", "")

    # jurisdictionの推定（アダプター名から）
    jur_map = {
        "courtlistener": "US", "hudoc": "EU", "jpcourts": "JP",
        "eurlex": "EU", "indiankanoon": "IN", "delaw": "DE",
        "africanlii": "AF", "paclii": "PC", "icj": "ICJ",
        "enforcement": "EU", "gipc_index": "US", "court_stats": "JP",
        "egov": "JP", "destatis": "DE", "epo_stats": "EU",
        "canlii": "CA", "legifrance": "FR", "ukleg": "GB",
        "nlleg": "NL", "ptleg": "PT", "ptlaw": "PT", "etlaw": "ET",
    }
    jur = jur_map.get(modname, modname.replace("leg", "").replace("law", "").upper()[:2])

    total = 0
    errors = 0

    for query in queries:
        try:
            results = adapter.search_with_text(query, max_results=max_per_query)
            for case in results:
                try:
                    store_case(case, jurisdiction=jur, adapter_name=modname)
                    total += 1
                except Exception as e:
                    errors += 1
            time.sleep(rate_limit)
        except Exception as e:
            errors += 1
            print(f"  {modname} query='{query}': {str(e)[:80]}")

    return {"adapter": modname, "jurisdiction": jur, "stored": total, "errors": errors}


# デフォルトクエリ（法分野横断）
DEFAULT_QUERIES = [
    "fraud", "contract", "negligence", "employment", "property",
    "criminal", "tax", "family", "intellectual property", "bankruptcy",
    "human rights", "environmental", "competition", "data protection",
    "arbitration", "insurance", "tort", "constitutional",
    "administrative", "immigration",
]


def main():
    parser = argparse.ArgumentParser(description="Crawl case law from all adapters")
    parser.add_argument("--adapters", nargs="*", help="Specific adapter files to crawl")
    parser.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES, help="Search queries")
    parser.add_argument("--max-per-query", type=int, default=50, help="Max results per query")
    parser.add_argument("--rate-limit", type=float, default=1.5, help="Seconds between requests")
    parser.add_argument("--parallel", type=int, default=5, help="Max parallel jurisdictions")
    args = parser.parse_args()

    init_db()

    # アダプターファイルの一覧
    if args.adapters:
        adapter_files = args.adapters
    else:
        adapter_files = sorted(glob.glob("tools/adapters/*.py"))
        adapter_files = [f for f in adapter_files if "__" not in f and "base" not in f]

    print(f"=== Crawl Start ===")
    print(f"Adapters: {len(adapter_files)}")
    print(f"Queries: {len(args.queries)}")
    print(f"Max per query: {args.max_per_query}")
    print(f"Rate limit: {args.rate_limit}s")
    print(f"Parallel: {args.parallel}")
    print()

    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(
                crawl_jurisdiction, f, args.queries, args.max_per_query, args.rate_limit
            ): f for f in adapter_files
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            status = "OK" if result.get("stored", 0) > 0 else "NG"
            print(f"{status} {result['adapter']:25s} {result.get('jurisdiction','??'):5s} "
                  f"stored={result.get('stored',0):5d} errors={result.get('errors',0)}")

    elapsed = time.time() - start
    stats = get_stats()

    print()
    print(f"=== Crawl Complete ({elapsed:.0f}s) ===")
    print(f"Total cases in DB: {stats['total_cases']}")
    print(f"By jurisdiction:")
    for jur, cnt in stats["by_jurisdiction"].items():
        print(f"  {jur}: {cnt}")


if __name__ == "__main__":
    main()
