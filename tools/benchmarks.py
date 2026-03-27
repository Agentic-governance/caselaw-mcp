# tools/benchmarks.py
"""Sector benchmark database for litigation analytics."""

SECTOR_BENCHMARKS = {
    'cdn_provider': {
        'win_rate_defendant': 0.55,
        'win_rate_plaintiff': 0.48,
        'settlement_rate': 0.18,
        'injunction_rate': 0.12,
        'median_duration_days': 450
    },
    'streaming_platform': {
        'win_rate_defendant': 0.48,
        'win_rate_plaintiff': 0.62,
        'settlement_rate': 0.25,
        'injunction_rate': 0.35,
        'median_duration_days': 540
    },
    'ecommerce_marketplace': {
        'win_rate_defendant': 0.52,
        'win_rate_plaintiff': 0.58,
        'settlement_rate': 0.30,
        'injunction_rate': 0.22,
        'median_duration_days': 480
    }
}


def get_benchmark(sector: str, metric: str) -> float:
    """
    Get benchmark value for a sector and metric.

    Args:
        sector: Sector name (e.g., 'cdn_provider')
        metric: Metric name (e.g., 'win_rate_defendant')

    Returns:
        Benchmark value

    Raises:
        ValueError: If sector or metric not found

    Example:
        >>> get_benchmark('cdn_provider', 'win_rate_defendant')
        0.55
    """
    if sector not in SECTOR_BENCHMARKS:
        raise ValueError(
            f"Unknown sector: {sector}. "
            f"Available: {list(SECTOR_BENCHMARKS.keys())}"
        )

    if metric not in SECTOR_BENCHMARKS[sector]:
        raise ValueError(
            f"Unknown metric: {metric}. "
            f"Available for {sector}: {list(SECTOR_BENCHMARKS[sector].keys())}"
        )

    return SECTOR_BENCHMARKS[sector][metric]
