# tools/analytics.py
"""Analytics framework with quality guardrails for litigation data."""

from dataclasses import dataclass, asdict
from typing import Optional, Literal, Any
import statistics
from scipy import stats


@dataclass
class AnalyticsOutput:
    """Standardized output for all analytics functions."""

    metric_value: float
    metric_name: str
    n_cases: int
    confidence_interval: tuple[float, float]
    sample_quality: Literal["reliable", "limited", "unreliable"]
    sector_benchmark: float
    benchmark_delta: float
    timeline: list[tuple[int, float]]
    trend: Literal["improving", "declining", "stable"]
    trend_rate: Optional[float]
    segments: dict[str, float]
    weakest_segment: Optional[tuple[str, float]]
    outliers: list[str]
    red_flags: list[str]
    supporting_cases: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class Recommendation:
    """Structured recommendation with priority and rationale."""

    priority: Literal["URGENT", "SHORT_TERM", "MID_TERM", "LONG_TERM"]
    icon: str
    action: str
    rationale: str


def compute_confidence_interval(
    wins: int,
    total: int,
    confidence: float = 0.95
) -> tuple[float, float]:
    """
    Compute Bayesian confidence interval using Beta distribution.

    Args:
        wins: Number of successful outcomes
        total: Total number of cases
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        (lower_bound, upper_bound) tuple

    Example:
        >>> compute_confidence_interval(5, 10)
        (0.191, 0.809)
    """
    if total == 0:
        return (0.0, 0.0)

    # Beta(1,1) prior (uninformative)
    alpha = wins + 1
    beta = total - wins + 1

    lower, upper = stats.beta.interval(confidence, alpha, beta)
    return (round(lower, 3), round(upper, 3))


def assess_sample_quality(n: int) -> tuple[str, str]:
    """
    Assess sample size quality with warnings.

    Args:
        n: Sample size

    Returns:
        (quality_label, warning_message) tuple

    Example:
        >>> assess_sample_quality(5)
        ('unreliable', '⚠️ WARNING: Sample size (N=5) is too small...')
    """
    if n >= 30:
        return ("reliable", "")
    elif n >= 10:
        return (
            "limited",
            f"⚠️ Sample size (N={n}) provides limited statistical power. "
            f"Confidence intervals are wider. Use with caution."
        )
    else:
        return (
            "unreliable",
            f"⚠️ WARNING: Sample size (N={n}) is too small for reliable inference. "
            f"This analysis is illustrative only. Expand to N≥10 before strategic decisions."
        )


def detect_trend(
    timeline: list[tuple[int, float]]
) -> tuple[Literal["improving", "declining", "stable"], float]:
    """
    Detect trend via linear regression.

    Args:
        timeline: List of (year, metric_value) tuples

    Returns:
        (trend_label, slope) tuple
        - "improving" if slope > +0.01/year
        - "declining" if slope < -0.01/year
        - "stable" otherwise

    Example:
        >>> detect_trend([(2020, 0.6), (2021, 0.65), (2022, 0.7)])
        ('improving', 0.05)
    """
    if len(timeline) < 3:
        return ("stable", 0.0)

    years = [t[0] for t in timeline]
    values = [t[1] for t in timeline]

    # Simple linear regression
    n = len(years)
    x_mean = statistics.mean(years)
    y_mean = statistics.mean(values)

    numerator = sum((years[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((years[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return ("stable", 0.0)

    slope = numerator / denominator

    if slope > 0.01:
        return ("improving", slope)
    elif slope < -0.01:
        return ("declining", slope)
    else:
        return ("stable", slope)


def detect_outliers(
    segments: dict[str, float],
    overall_mean: float
) -> list[str]:
    """
    Detect segments that are 3σ away from overall mean.

    Args:
        segments: Dict of segment -> metric_value
        overall_mean: Overall metric value

    Returns:
        List of outlier descriptions

    Example:
        >>> detect_outliers({'US': 0.71, 'France': 0.25}, 0.68)
        ['France: 3.2σ below mean']
    """
    if len(segments) < 3:
        return []

    values = list(segments.values())

    try:
        stdev = statistics.stdev(values)
    except statistics.StatisticsError:
        return []

    if stdev == 0:
        return []

    outliers = []
    for segment, value in segments.items():
        z_score = (value - overall_mean) / stdev
        if abs(z_score) >= 3:
            direction = "below" if z_score < 0 else "above"
            outliers.append(f"{segment}: {abs(z_score):.1f}σ {direction} mean")

    return outliers


class PartyAnalyzer:
    """Analyze litigation party performance with quality guardrails."""

    def __init__(self, cases: list[dict], sector_benchmarks: dict):
        """
        Initialize analyzer.

        Args:
            cases: List of case metadata dicts
            sector_benchmarks: Sector benchmark dict
        """
        self.cases = cases
        self.benchmarks = sector_benchmarks

    def analyze_defendant_performance(
        self,
        entity: str,
        sector: str = "cdn_provider"
    ) -> AnalyticsOutput:
        """
        Analyze defendant win rate with ALL guardrails.

        Args:
            entity: Entity name
            sector: Sector for benchmarking

        Returns:
            Complete AnalyticsOutput with all fields populated
        """
        # Filter cases
        entity_cases = [c for c in self.cases if entity in c.get('parties', [])]
        as_defendant = [c for c in entity_cases if self._is_defendant(c, entity)]

        n_cases = len(as_defendant)

        if n_cases == 0:
            raise ValueError(f"No cases found for {entity} as defendant")

        # Core metric
        wins = [c for c in as_defendant if c['result'] in ['defendant_win', 'dismissed']]
        metric_value = len(wins) / n_cases

        # GUARDRAIL 1: Sample quality
        sample_quality, warning = assess_sample_quality(n_cases)

        # GUARDRAIL 2: Confidence interval
        ci_lower, ci_upper = compute_confidence_interval(len(wins), n_cases)

        # GUARDRAIL 3: Benchmark comparison
        from tools.benchmarks import get_benchmark
        benchmark = get_benchmark(sector, 'win_rate_defendant')
        benchmark_delta = metric_value - benchmark

        # GUARDRAIL 4: Timeline analysis
        timeline = self._compute_timeline(as_defendant)
        trend, trend_rate = detect_trend(timeline)

        # GUARDRAIL 5: Segmentation
        segments = self._compute_segments(as_defendant, 'jurisdiction')
        weakest_segment = self._identify_weakest_segment(segments)

        # GUARDRAIL 6: Outlier detection
        outliers = detect_outliers(segments, metric_value)

        # GUARDRAIL 7: Red flags
        red_flags = []
        if warning:
            red_flags.append(warning)
        if trend == "declining" and abs(trend_rate or 0) > 0.01:
            red_flags.append(
                f"Declining win rate: -{abs(trend_rate)*100:.1f}% per year"
            )
        if weakest_segment and weakest_segment[1] < metric_value * 0.5:
            red_flags.append(
                f"Critical weakness in {weakest_segment[0]}: "
                f"{weakest_segment[1]:.1%} vs overall {metric_value:.1%}"
            )
        if ci_upper - ci_lower > 0.3:
            red_flags.append(
                f"Wide confidence interval ({ci_upper - ci_lower:.1%}) indicates high uncertainty"
            )

        return AnalyticsOutput(
            metric_value=metric_value,
            metric_name="defendant_win_rate",
            n_cases=n_cases,
            confidence_interval=(ci_lower, ci_upper),
            sample_quality=sample_quality,
            sector_benchmark=benchmark,
            benchmark_delta=benchmark_delta,
            timeline=timeline,
            trend=trend,
            trend_rate=trend_rate,
            segments=segments,
            weakest_segment=weakest_segment,
            outliers=outliers,
            red_flags=red_flags,
            supporting_cases=[c.get('case_id', '') for c in as_defendant]
        )

    def _is_defendant(self, case: dict, entity: str) -> bool:
        """Check if entity is defendant in case."""
        case_name = case.get('case_name', '')
        return ' v. ' + entity in case_name or ' v ' + entity in case_name or entity in case.get('defendants', [])

    def _compute_timeline(self, cases: list[dict]) -> list[tuple[int, float]]:
        """Compute year-by-year win rate."""
        from collections import defaultdict

        year_wins = defaultdict(int)
        year_total = defaultdict(int)

        for case in cases:
            year = case.get('year')
            if year:
                year_total[year] += 1
                if case['result'] in ['defendant_win', 'dismissed']:
                    year_wins[year] += 1

        timeline = []
        for year in sorted(year_total.keys()):
            rate = year_wins[year] / year_total[year] if year_total[year] > 0 else 0.0
            timeline.append((year, rate))

        return timeline

    def _compute_segments(self, cases: list[dict], segment_key: str) -> dict[str, float]:
        """Compute win rate by segment."""
        from collections import defaultdict

        segment_wins = defaultdict(int)
        segment_total = defaultdict(int)

        for case in cases:
            segment = case.get(segment_key)
            if segment:
                segment_total[segment] += 1
                if case['result'] in ['defendant_win', 'dismissed']:
                    segment_wins[segment] += 1

        segments = {}
        for segment in segment_total:
            rate = segment_wins[segment] / segment_total[segment] if segment_total[segment] > 0 else 0.0
            segments[segment] = rate

        return segments

    def _identify_weakest_segment(self, segments: dict[str, float]) -> Optional[tuple[str, float]]:
        """Identify segment with lowest value."""
        if not segments:
            return None

        min_segment = min(segments.items(), key=lambda x: x[1])
        return min_segment


def generate_recommendations(analytics: AnalyticsOutput) -> list[Recommendation]:
    """
    Generate priority-ranked recommendations via decision tree.

    Args:
        analytics: AnalyticsOutput instance

    Returns:
        List of Recommendation objects sorted by priority
    """
    recs = []

    # URGENT: Unreliable sample
    if analytics.sample_quality == "unreliable":
        recs.append(Recommendation(
            priority="URGENT",
            icon="🔴",
            action=f"Expand dataset to N≥10 before strategic decisions",
            rationale=(
                f"Current sample size (N={analytics.n_cases}) is too small for reliable inference. "
                f"Confidence interval spans {analytics.confidence_interval[0]:.1%} to "
                f"{analytics.confidence_interval[1]:.1%}, making conclusions unreliable."
            )
        ))

    # URGENT: Critical geographic weakness
    if analytics.weakest_segment and analytics.weakest_segment[1] < analytics.metric_value * 0.5:
        jurisdiction, rate = analytics.weakest_segment
        recs.append(Recommendation(
            priority="URGENT",
            icon="🔴",
            action=f"Challenge jurisdiction or settle in {jurisdiction} cases",
            rationale=(
                f"Critical weakness in {jurisdiction} ({rate:.1%} vs overall {analytics.metric_value:.1%}). "
                f"Expected value of litigation is likely negative. Jurisdictional challenges to move to "
                f"favorable forum, or early settlement at 30-40% of claim value recommended."
            )
        ))

    # SHORT-TERM: Declining trend
    if analytics.trend == "declining" and abs(analytics.trend_rate or 0) > 0.01:
        recs.append(Recommendation(
            priority="SHORT_TERM",
            icon="🟡",
            action=f"Investigate root cause of {abs(analytics.trend_rate or 0)*100:.1f}% annual decline",
            rationale=(
                f"Win rate has declined {abs(analytics.trend_rate or 0)*100:.1f}% per year "
                f"since {analytics.timeline[0][0] if analytics.timeline else 'baseline'}. "
                f"If trend continues, competitive advantage will erode. "
                f"Root cause analysis and corrective action needed."
            )
        ))

    # MID-TERM: Below benchmark
    if analytics.benchmark_delta < -0.05:
        recs.append(Recommendation(
            priority="MID_TERM",
            icon="🟢",
            action=f"Enhance defensive strategy to close {abs(analytics.benchmark_delta)*100:.1f}pt gap vs industry",
            rationale=(
                f"Performance ({analytics.metric_value:.1%}) trails sector average "
                f"({analytics.sector_benchmark:.1%}). Review defensive playbook, safe harbor compliance, "
                f"and counsel selection to improve outcomes."
            )
        ))

    # LONG-TERM: Monitor developments
    if any("CJEU" in flag or "pending" in flag.lower() for flag in analytics.red_flags):
        recs.append(Recommendation(
            priority="LONG_TERM",
            icon="🔵",
            action="Monitor pending legal developments",
            rationale=(
                "Upcoming legal developments may materially impact safe harbor defenses. "
                "Track case law evolution and adjust strategy proactively."
            )
        ))

    # Sort by priority
    priority_order = {"URGENT": 0, "SHORT_TERM": 1, "MID_TERM": 2, "LONG_TERM": 3}
    return sorted(recs, key=lambda r: priority_order[r.priority])
