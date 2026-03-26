from __future__ import annotations

from collections import defaultdict
from typing import Any

from core.enums import KnowledgeStatus, KnowledgeTier
from domain.schemas import (
    KnowledgeAggregatedNode,
    KnowledgeAnalyticsWindow,
    KnowledgeCoverageAggregateOut,
    KnowledgeCoverageOut,
    KnowledgeCoverageReportOut,
    KnowledgeCoverageSummaryOut,
    KnowledgeLifecycleAggregateSummary,
    KnowledgeLifecycleReportOut,
    KnowledgeLifecycleSummary,
    KnowledgePruningCandidateOut,
    KnowledgePruningExplanation,
    KnowledgePruningReportOut,
    KnowledgePruningSignal,
    KnowledgeTrendPoint,
    KnowledgeTrendReportOut,
    KnowledgeTrendSeries,
    KnowledgeTrendSummary,
    KnowledgeTimelineEvent,
    KnowledgeTimelineOut,
    KnowledgeTimelineSummary,
)
from domain.taxonomy import match_structured_tags, normalize_tags
from memory.models import KnowledgePruningThresholds


class KnowledgeAnalyticsService:
    TREND_REVIEW_WINDOWS = (5, 10, 20)

    def __init__(self, analytics_repository, knowledge_repository=None, thresholds: KnowledgePruningThresholds | None = None):
        self.analytics_repository = analytics_repository
        self.knowledge_repository = knowledge_repository
        self.thresholds = thresholds or KnowledgePruningThresholds()

    def build_coverage_report(
        self,
        *,
        window_type: str = 'all_time',
        window_value: int | None = None,
        view_mode: str = 'active',
        limit: int = 500,
    ) -> KnowledgeCoverageReportOut:
        window = self._resolve_window(window_type=window_type, window_value=window_value, view_mode=view_mode)
        inventory = self._build_inventory(limit=limit)
        lineage_items = self._build_lineage_items(
            inventory=inventory,
            window=window,
        )
        items = self._apply_view_mode(lineage_items, view_mode=window.view_mode)
        pruning = self._build_pruning_candidates(items)
        summary = KnowledgeCoverageSummaryOut(
            total_knowledge_count=len(items),
            lineage_node_count=len(lineage_items),
            active_knowledge_count=sum(1 for item in items if item.status != KnowledgeStatus.ARCHIVED),
            active_hot_knowledge_count=sum(
                1 for item in items if item.tier == KnowledgeTier.HOT and item.status == KnowledgeStatus.ACTIVE
            ),
            active_cold_knowledge_count=sum(
                1 for item in items if item.tier == KnowledgeTier.COLD and item.status == KnowledgeStatus.ACTIVE
            ),
            pruning_candidate_count=len(pruning),
            top_conflict_knowledge=[
                {
                    'knowledge_id': item.knowledge_id,
                    'lineage_id': item.lineage_id,
                    'category': item.category,
                    'conflict_count': item.conflict_count,
                    'match_count': item.match_count,
                }
                for item in sorted(items, key=lambda row: (-row.conflict_count, -row.match_count, row.knowledge_id))[:5]
                if item.conflict_count > 0
            ],
            top_low_coverage_knowledge=[
                {
                    'knowledge_id': item.knowledge_id,
                    'lineage_id': item.lineage_id,
                    'category': item.category,
                    'coverage_count': item.coverage_count,
                    'status': item.status.value if hasattr(item.status, 'value') else str(item.status),
                }
                for item in sorted(items, key=lambda row: (row.coverage_count, -row.fail_rate, row.knowledge_id))[:5]
            ],
        )
        return KnowledgeCoverageReportOut(
            window=window,
            summary=summary,
            items=items,
            by_category=self._aggregate(items, 'category'),
            by_applicable_event_tag=self._aggregate(items, 'applicable_event_tags'),
            by_applicable_technical_tag=self._aggregate(items, 'applicable_technical_tags'),
            by_applicable_market_regime=self._aggregate(items, 'applicable_market_regimes'),
        )

    def get_knowledge_coverage(
        self,
        knowledge_id: str,
        *,
        window_type: str = 'all_time',
        window_value: int | None = None,
        view_mode: str = 'active',
        limit: int = 500,
    ) -> KnowledgeCoverageOut | None:
        report = self.build_coverage_report(
            window_type=window_type,
            window_value=window_value,
            view_mode=view_mode,
            limit=limit,
        )
        for item in report.items:
            if knowledge_id in {item.knowledge_id, item.lineage_id}:
                return item
            if any(node.knowledge_id == knowledge_id for node in item.aggregated_from_nodes):
                return item
        return None

    def list_pruning_candidates(
        self,
        *,
        window_type: str = 'all_time',
        window_value: int | None = None,
        view_mode: str = 'active',
        limit: int = 500,
    ) -> KnowledgePruningReportOut:
        items = self.build_coverage_report(
            window_type=window_type,
            window_value=window_value,
            view_mode=view_mode,
            limit=limit,
        )
        trend_report = self.build_coverage_trends(
            view_mode=view_mode,
            limit=limit,
        )
        trend_signal_map = {item.lineage_id if view_mode == 'active' else item.knowledge_id: item.trend_signal for item in trend_report.items}
        candidates = self._build_pruning_candidates(items.items, trend_signal_map=trend_signal_map, view_mode=view_mode)
        return KnowledgePruningReportOut(
            window=self._resolve_window(window_type=window_type, window_value=window_value, view_mode=view_mode),
            total_candidates=len(candidates),
            items=candidates,
        )

    def build_coverage_trends(
        self,
        *,
        knowledge_id: str | None = None,
        lineage_id: str | None = None,
        view_mode: str = 'active',
        limit: int = 500,
    ) -> KnowledgeTrendReportOut:
        trend_reports = self._build_review_window_reports(view_mode=view_mode, limit=limit)
        series = self._build_trend_series(
            trend_reports=trend_reports,
            knowledge_id=knowledge_id,
            lineage_id=lineage_id,
            view_mode=view_mode,
            candidates_only=False,
        )
        summary = self._build_trend_summary(
            trend_reports=trend_reports,
            knowledge_id=knowledge_id,
            lineage_id=lineage_id,
            view_mode=view_mode,
            candidates_only=False,
        )
        return KnowledgeTrendReportOut(
            view_mode=view_mode,
            summary=summary,
            items=series,
        )

    def build_pruning_trends(
        self,
        *,
        knowledge_id: str | None = None,
        lineage_id: str | None = None,
        view_mode: str = 'active',
        limit: int = 500,
    ) -> KnowledgeTrendReportOut:
        trend_reports = self._build_review_window_reports(view_mode=view_mode, limit=limit)
        series = self._build_trend_series(
            trend_reports=trend_reports,
            knowledge_id=knowledge_id,
            lineage_id=lineage_id,
            view_mode=view_mode,
            candidates_only=True,
        )
        summary = self._build_trend_summary(
            trend_reports=trend_reports,
            knowledge_id=knowledge_id,
            lineage_id=lineage_id,
            view_mode=view_mode,
            candidates_only=True,
        )
        return KnowledgeTrendReportOut(
            view_mode=view_mode,
            summary=summary,
            items=series,
        )

    def get_knowledge_trends(
        self,
        *,
        knowledge_id: str,
        view_mode: str = 'active',
        limit: int = 500,
    ) -> KnowledgeTrendSeries | None:
        trend_report = self.build_coverage_trends(
            knowledge_id=knowledge_id,
            view_mode=view_mode,
            limit=limit,
        )
        return trend_report.items[0] if trend_report.items else None

    def get_lineage_timeline(
        self,
        *,
        lineage_id: str,
        descending: bool = False,
        limit: int = 500,
    ) -> KnowledgeTimelineOut | None:
        if self.knowledge_repository is None:
            raise ValueError('knowledge_repository is required for lineage timeline queries')

        lineage_nodes = self.knowledge_repository.list_lineage_nodes(lineage_id)
        nodes = lineage_nodes['all']
        if not nodes:
            return None

        node_map = {row.knowledge_id: row for row in nodes}
        knowledge_ids = set(node_map)
        raw_events = self.knowledge_repository.list_lineage_events(
            lineage_id=lineage_id,
            descending=False,
            limit=limit,
        )
        timeline_events = self._build_raw_timeline_events(
            raw_events=raw_events,
            lineage_id=lineage_id,
            node_map=node_map,
        )
        derived_events = self._build_derived_timeline_events(
            lineage_id=lineage_id,
            knowledge_ids=knowledge_ids,
        )
        events = sorted(timeline_events + derived_events, key=self._timeline_event_sort_key)
        total_events = len(events)
        promoted_count = sum(1 for event in events if event.event_type == 'promoted')
        demoted_count = sum(1 for event in events if event.event_type == 'demoted')
        archived_count = sum(1 for event in events if event.event_type == 'archived')
        if descending:
            events = list(reversed(events))
        if limit > 0:
            events = events[:limit]

        current_node = self._resolve_timeline_current_node(nodes)
        summary = KnowledgeTimelineSummary(
            total_nodes=len(nodes),
            total_events=total_events,
            promoted_count=promoted_count,
            demoted_count=demoted_count,
            archived_count=archived_count,
            current_status=current_node.status if current_node is not None else None,
        )
        return KnowledgeTimelineOut(
            lineage_id=lineage_id,
            current_active_node=current_node,
            lineage_summary=summary,
            events=events,
        )

    def get_knowledge_timeline(
        self,
        *,
        knowledge_id: str,
        descending: bool = False,
        limit: int = 500,
    ) -> KnowledgeTimelineOut | None:
        if self.knowledge_repository is None:
            raise ValueError('knowledge_repository is required for lineage timeline queries')

        lineage_id = self.knowledge_repository.resolve_lineage_id(knowledge_id)
        if lineage_id is None:
            return None
        return self.get_lineage_timeline(lineage_id=lineage_id, descending=descending, limit=limit)

    def build_lifecycle_report(
        self,
        *,
        category: str | None = None,
        regime: str | None = None,
        limit: int = 500,
    ) -> KnowledgeLifecycleReportOut:
        items = self._list_lifecycle_summaries(category=category, regime=regime, limit=limit)
        return KnowledgeLifecycleReportOut(
            total_lineages=len(items),
            items=items,
            by_category=self._aggregate_lifecycle(items, 'category'),
            by_applicable_market_regime=self._aggregate_lifecycle(items, 'applicable_market_regimes'),
            by_knowledge_type=self._aggregate_lifecycle(items, 'knowledge_type'),
        )

    def get_lineage_lifecycle_summary(
        self,
        *,
        lineage_id: str,
        limit: int = 500,
    ) -> KnowledgeLifecycleSummary | None:
        if self.knowledge_repository is None:
            raise ValueError('knowledge_repository is required for lifecycle summary queries')

        timeline = self.get_lineage_timeline(lineage_id=lineage_id, descending=False, limit=limit)
        if timeline is None:
            return None

        lineage_nodes = self.knowledge_repository.list_lineage_nodes(lineage_id)
        nodes = list(lineage_nodes['all'])
        current_active_node = timeline.current_active_node
        category = self._resolve_lineage_category(nodes=nodes, current_active_node=current_active_node)
        applicable_market_regimes = self._resolve_lineage_market_regimes(nodes)
        knowledge_type = current_active_node.knowledge_type if current_active_node is not None else self._resolve_lineage_type(nodes)
        first_created_at = self._find_first_timestamp(timeline.events, 'created')
        first_promoted_at = self._find_first_timestamp(timeline.events, 'promoted')
        first_demoted_at = self._find_first_timestamp(timeline.events, 'demoted')
        last_archived_at = self._find_last_timestamp(timeline.events, 'archived')
        lifecycle_end_at = last_archived_at or self._latest_event_timestamp(timeline.events) or (
            current_active_node.updated_at if current_active_node is not None else None
        )
        status_flip_count = self._count_status_flips(timeline.events)
        promotion_count = self._count_timeline_events(timeline.events, 'promoted')
        demotion_count = self._count_timeline_events(timeline.events, 'demoted')
        degrade_count = self._count_timeline_events(timeline.events, 'degraded')
        restore_count = self._count_timeline_events(timeline.events, 'restored')
        archive_count = self._count_timeline_events(timeline.events, 'archived')
        lifecycle_days = self._diff_days(first_created_at, lifecycle_end_at)
        promotion_to_demotion_days = self._diff_days(first_promoted_at, first_demoted_at)
        restore_to_next_degrade_days = self._restore_to_next_degrade_days(timeline.events)
        current_status = timeline.lineage_summary.current_status or (current_active_node.status if current_active_node else None)

        summary = KnowledgeLifecycleSummary(
            lineage_id=lineage_id,
            category=category,
            applicable_market_regimes=applicable_market_regimes,
            knowledge_type=knowledge_type,
            current_status=current_status,
            current_active_node=current_active_node,
            first_created_at=first_created_at,
            first_promoted_at=first_promoted_at,
            first_demoted_at=first_demoted_at,
            last_archived_at=last_archived_at,
            lifecycle_days=lifecycle_days,
            promotion_to_demotion_days=promotion_to_demotion_days,
            restore_to_next_degrade_days=restore_to_next_degrade_days,
            promotion_count=promotion_count,
            demotion_count=demotion_count,
            degrade_count=degrade_count,
            restore_count=restore_count,
            archive_count=archive_count,
            status_flip_count=status_flip_count,
            lifecycle_state='young',
            total_nodes=timeline.lineage_summary.total_nodes,
            total_events=timeline.lineage_summary.total_events,
        )
        summary.lifecycle_state = self._resolve_lifecycle_state(summary)
        return summary

    def _list_lifecycle_summaries(
        self,
        *,
        category: str | None,
        regime: str | None,
        limit: int,
    ) -> list[KnowledgeLifecycleSummary]:
        inventory = self._build_inventory(limit=limit)
        lineage_ids = sorted({node['lineage_id'] for node in inventory if node.get('lineage_id')})
        normalized_regime = normalize_tags([regime])[0] if regime and normalize_tags([regime]) else None
        items: list[KnowledgeLifecycleSummary] = []
        for lineage_id in lineage_ids:
            summary = self.get_lineage_lifecycle_summary(lineage_id=lineage_id, limit=limit)
            if summary is None:
                continue
            if category and summary.category != category:
                continue
            if normalized_regime and normalized_regime not in summary.applicable_market_regimes:
                continue
            items.append(summary)
        return sorted(items, key=lambda row: (row.category, row.lineage_id))

    def _aggregate_lifecycle(
        self,
        items: list[KnowledgeLifecycleSummary],
        field_name: str,
    ) -> list[KnowledgeLifecycleAggregateSummary]:
        buckets: dict[str, list[KnowledgeLifecycleSummary]] = defaultdict(list)
        for item in items:
            raw_values = getattr(item, field_name)
            values = raw_values if isinstance(raw_values, list) else [raw_values]
            for value in values:
                if value in (None, ''):
                    continue
                key = value.value if hasattr(value, 'value') else str(value)
                buckets[key].append(item)

        aggregates: list[KnowledgeLifecycleAggregateSummary] = []
        for key, group in buckets.items():
            lifecycle_days = [item.lifecycle_days for item in group if item.lifecycle_days is not None]
            promotion_to_demotion_days = [
                item.promotion_to_demotion_days for item in group if item.promotion_to_demotion_days is not None
            ]
            aggregates.append(
                KnowledgeLifecycleAggregateSummary(
                    dimension=field_name,
                    key=key,
                    lineage_count=len(group),
                    avg_lifecycle_days=round(sum(lifecycle_days) / len(lifecycle_days), 4) if lifecycle_days else 0.0,
                    avg_promotion_to_demotion_days=round(
                        sum(promotion_to_demotion_days) / len(promotion_to_demotion_days),
                        4,
                    )
                    if promotion_to_demotion_days
                    else 0.0,
                    avg_status_flip_count=round(sum(item.status_flip_count for item in group) / len(group), 4) if group else 0.0,
                    archive_rate=round(
                        sum(1 for item in group if item.current_status == KnowledgeStatus.ARCHIVED) / len(group),
                        4,
                    )
                    if group
                    else 0.0,
                    oscillating_rate=round(
                        sum(1 for item in group if item.lifecycle_state == 'oscillating') / len(group),
                        4,
                    )
                    if group
                    else 0.0,
                )
            )
        return sorted(aggregates, key=lambda row: (-row.lineage_count, row.key))

    @staticmethod
    def _resolve_lineage_category(*, nodes: list[Any], current_active_node: KnowledgeAggregatedNode | None) -> str:
        if current_active_node is not None:
            for node in nodes:
                if node.knowledge_id == current_active_node.knowledge_id:
                    return getattr(node, 'category', '')
        return getattr(nodes[0], 'category', '') if nodes else ''

    @staticmethod
    def _resolve_lineage_market_regimes(nodes: list[Any]) -> list[str]:
        regimes: list[str] = []
        for node in nodes:
            regimes = KnowledgeAnalyticsService._merge_unique(regimes, list(getattr(node, 'applicable_market_regimes', []) or []))
        return regimes

    @staticmethod
    def _resolve_lineage_type(nodes: list[Any]) -> KnowledgeTier | None:
        if not nodes:
            return None
        candidate = sorted(nodes, key=KnowledgeAnalyticsService._timeline_node_sort_key)[0]
        return KnowledgeTier.COLD if hasattr(candidate, 'source_hot_knowledge_id') else KnowledgeTier.HOT

    @staticmethod
    def _find_first_timestamp(events: list[KnowledgeTimelineEvent], event_type: str):
        for event in events:
            if event.event_type == event_type and event.timestamp is not None:
                return event.timestamp
        return None

    @staticmethod
    def _find_last_timestamp(events: list[KnowledgeTimelineEvent], event_type: str):
        timestamps = [event.timestamp for event in events if event.event_type == event_type and event.timestamp is not None]
        return timestamps[-1] if timestamps else None

    @staticmethod
    def _latest_event_timestamp(events: list[KnowledgeTimelineEvent]):
        timestamps = [event.timestamp for event in events if event.timestamp is not None]
        return timestamps[-1] if timestamps else None

    @staticmethod
    def _diff_days(start_at, end_at) -> float | None:
        if start_at is None or end_at is None or end_at < start_at:
            return None
        return round((end_at - start_at).total_seconds() / 86400, 4)

    @staticmethod
    def _restore_to_next_degrade_days(events: list[KnowledgeTimelineEvent]) -> float | None:
        for index, event in enumerate(events):
            if event.event_type != 'restored' or event.timestamp is None:
                continue
            for next_event in events[index + 1 :]:
                if next_event.event_type == 'degraded' and next_event.timestamp is not None:
                    return KnowledgeAnalyticsService._diff_days(event.timestamp, next_event.timestamp)
        return None

    @staticmethod
    def _count_timeline_events(events: list[KnowledgeTimelineEvent], event_type: str) -> int:
        return sum(1 for event in events if event.event_type == event_type)

    @staticmethod
    def _count_status_flips(events: list[KnowledgeTimelineEvent]) -> int:
        flip_event_ids: set[str] = set()
        for event in events:
            if event.before_status is None or event.after_status is None or event.before_status == event.after_status:
                continue
            flip_event_ids.add(event.event_id.split(':', 1)[0])
        return len(flip_event_ids)

    def _resolve_lifecycle_state(self, summary: KnowledgeLifecycleSummary) -> str:
        if summary.current_status == KnowledgeStatus.ARCHIVED or summary.archive_count > 0 and summary.current_active_node is None:
            return 'retired'
        if summary.status_flip_count >= 4 or (summary.restore_count > 0 and summary.degrade_count >= 2):
            return 'oscillating'
        if summary.promotion_count == 0 and summary.demotion_count == 0 and summary.degrade_count == 0 and summary.archive_count == 0:
            return 'young'
        if summary.demotion_count > 0 or summary.degrade_count > 0 or (
            summary.promotion_to_demotion_days is not None and summary.promotion_to_demotion_days <= 14
        ):
            return 'fragile'
        return 'stable'

    def _build_raw_timeline_events(
        self,
        *,
        raw_events: list[Any],
        lineage_id: str,
        node_map: dict[str, Any],
    ) -> list[KnowledgeTimelineEvent]:
        timeline_events: list[KnowledgeTimelineEvent] = []
        for event in raw_events:
            node = node_map.get(event.knowledge_id)
            knowledge_type = self._coerce_knowledge_tier(
                getattr(event, 'knowledge_type', None) or ('cold' if node and hasattr(node, 'source_hot_knowledge_id') else 'hot')
            )
            details_json = dict(getattr(event, 'details_json', {}) or {})
            metrics_snapshot = dict(details_json.get('metrics_snapshot', {}) or {})
            before_status = self._coerce_optional_status(details_json.get('before_status'))
            after_status = self._coerce_optional_status(details_json.get('after_status'))
            for index, normalized_event_type in enumerate(
                self._normalize_raw_timeline_event_types(
                    raw_event_type=event.event_type,
                    before_status=before_status,
                    after_status=after_status,
                )
            ):
                timeline_events.append(
                    KnowledgeTimelineEvent(
                        event_id=event.event_id if index == 0 else f'{event.event_id}:{normalized_event_type}',
                        event_type=normalized_event_type,
                        knowledge_id=event.knowledge_id,
                        knowledge_type=knowledge_type,
                        lineage_id=lineage_id,
                        source_run_id=getattr(event, 'source_run_id', None),
                        source_review_report_id=getattr(event, 'source_review_report_id', None),
                        timestamp=getattr(event, 'created_at', None),
                        details_json=self._timeline_details_payload(
                            details_json=details_json,
                            raw_event_type=event.event_type,
                        ),
                        before_status=before_status,
                        after_status=after_status,
                        metrics_snapshot=metrics_snapshot,
                    )
                )
        return timeline_events

    def _build_derived_timeline_events(
        self,
        *,
        lineage_id: str,
        knowledge_ids: set[str],
    ) -> list[KnowledgeTimelineEvent]:
        events: list[KnowledgeTimelineEvent] = []
        recommendations = self.analytics_repository.list_recommendations(limit=5000)
        for row in recommendations:
            evidence_json = dict(getattr(row, 'evidence_json', {}) or {})
            matched_ids = sorted(knowledge_ids & self._extract_knowledge_ids(evidence_json))
            for knowledge_id in matched_ids:
                events.append(
                    KnowledgeTimelineEvent(
                        event_id=f'{row.recommendation_id}:matched:{knowledge_id}',
                        event_type='matched',
                        knowledge_id=knowledge_id,
                        knowledge_type=self._infer_knowledge_type_from_ref(
                            knowledge_id=knowledge_id,
                            evidence_json=evidence_json,
                        ),
                        lineage_id=lineage_id,
                        source_run_id=getattr(row, 'run_id', None),
                        source_review_report_id=None,
                        timestamp=getattr(row, 'created_at', None),
                        details_json={
                            'symbol': getattr(row, 'symbol', ''),
                            'action': getattr(getattr(row, 'action', None), 'value', getattr(row, 'action', None)),
                            'reason': getattr(row, 'reason', ''),
                            'raw_event_type': 'recommendation_match',
                            'matched_knowledge_ids': matched_ids,
                            'knowledge_conflict_flag': bool(evidence_json.get('knowledge_conflict_flag')),
                        },
                        metrics_snapshot={
                            'final_score': getattr(row, 'final_score', 0.0),
                            'knowledge_match_score': float(evidence_json.get('knowledge_match_score', 0.0)),
                            'knowledge_risk_penalty': float(evidence_json.get('knowledge_risk_penalty', 0.0)),
                        },
                    )
                )

        reports = self.analytics_repository.list_review_reports(limit=5000)
        for report in reports:
            for verdict in (getattr(report, 'verdicts_json', {}) or {}).get('items', []):
                evidence_json = dict(verdict.get('evidence_json', {}) or {})
                matched_ids = sorted(knowledge_ids & self._extract_knowledge_ids(evidence_json))
                for knowledge_id in matched_ids:
                    events.append(
                        KnowledgeTimelineEvent(
                            event_id=(
                                f"{getattr(report, 'review_report_id', '')}:reviewed:"
                                f"{knowledge_id}:{verdict.get('recommendation_id', '')}"
                            ),
                            event_type='reviewed',
                            knowledge_id=knowledge_id,
                            knowledge_type=self._infer_knowledge_type_from_ref(
                                knowledge_id=knowledge_id,
                                evidence_json=evidence_json,
                            ),
                            lineage_id=lineage_id,
                            source_run_id=getattr(report, 'run_id', None),
                            source_review_report_id=getattr(report, 'review_report_id', None),
                            timestamp=getattr(report, 'created_at', None),
                            details_json={
                                'symbol': verdict.get('symbol', ''),
                                'recommendation_id': verdict.get('recommendation_id', ''),
                                'verdict': verdict.get('verdict', 'insufficient_data'),
                                'horizon': getattr(report, 'horizon', 5),
                                'target_run_id': getattr(report, 'target_run_id', None),
                                'raw_event_type': 'review_verdict',
                            },
                            metrics_snapshot={
                                key: verdict.get(key)
                                for key in (
                                    'actual_return_1d',
                                    'actual_return_3d',
                                    'actual_return_5d',
                                    'benchmark_return',
                                    'max_drawdown',
                                )
                                if key in verdict
                            },
                        )
                    )
        return events

    def _resolve_timeline_current_node(self, nodes: list[Any]) -> KnowledgeAggregatedNode | None:
        if not nodes:
            return None
        candidate = sorted(nodes, key=self._timeline_node_sort_key)[0]
        knowledge_type = KnowledgeTier.COLD if hasattr(candidate, 'source_hot_knowledge_id') else KnowledgeTier.HOT
        return KnowledgeAggregatedNode(
            knowledge_id=candidate.knowledge_id,
            knowledge_type=knowledge_type,
            status=candidate.status,
            created_at=getattr(candidate, 'created_at', None),
            updated_at=getattr(candidate, 'updated_at', None),
        )

    @staticmethod
    def _normalize_raw_timeline_event_types(
        *,
        raw_event_type: str,
        before_status: KnowledgeStatus | None,
        after_status: KnowledgeStatus | None,
    ) -> list[str]:
        mapping = {
            'hot_created': ['created'],
            'hot_updated': ['reviewed'],
            'validated_pass': ['reviewed'],
            'validated_fail': ['reviewed'],
            'promoted_to_cold': ['promoted'],
            'promoted_from_hot': ['promoted'],
            'demoted_to_hot': ['demoted'],
            'restored_from_cold': ['restored'],
            'archived_from_cold': ['archived'],
            'archived_after_cold_failure': ['archived'],
            'archived_hot': ['archived'],
        }
        normalized = list(mapping.get(raw_event_type, ['reviewed']))
        if after_status == KnowledgeStatus.DEGRADED and 'degraded' not in normalized:
            normalized.append('degraded')
        return normalized

    @staticmethod
    def _timeline_details_payload(*, details_json: dict[str, Any], raw_event_type: str) -> dict[str, Any]:
        payload = dict(details_json)
        payload['raw_event_type'] = raw_event_type
        return payload

    @staticmethod
    def _coerce_optional_status(value: Any) -> KnowledgeStatus | None:
        if value in (None, ''):
            return None
        if isinstance(value, KnowledgeStatus):
            return value
        return KnowledgeStatus(str(value))

    @staticmethod
    def _coerce_knowledge_tier(value: Any) -> KnowledgeTier:
        if isinstance(value, KnowledgeTier):
            return value
        return KnowledgeTier(str(value))

    @staticmethod
    def _infer_knowledge_type_from_ref(*, knowledge_id: str, evidence_json: dict[str, Any]) -> KnowledgeTier:
        for item in evidence_json.get('knowledge_refs', []) or []:
            if not isinstance(item, dict):
                continue
            ref_id = item.get('ref_id') or item.get('knowledge_id')
            if str(ref_id) != knowledge_id:
                continue
            ref_type = str(item.get('ref_type') or item.get('knowledge_type') or '')
            if 'cold' in ref_type:
                return KnowledgeTier.COLD
            if 'hot' in ref_type:
                return KnowledgeTier.HOT
        if str(knowledge_id).startswith('cold_'):
            return KnowledgeTier.COLD
        return KnowledgeTier.HOT

    @staticmethod
    def _timeline_node_sort_key(node: Any) -> tuple[int, int, int]:
        status_priority = {KnowledgeStatus.ACTIVE: 0, KnowledgeStatus.DEGRADED: 1, KnowledgeStatus.ARCHIVED: 2}
        tier_priority = {True: 0, False: 1}
        updated_at = getattr(node, 'updated_at', None)
        timestamp = int(updated_at.timestamp()) if updated_at else 0
        return (
            status_priority.get(getattr(node, 'status', None), 99),
            tier_priority.get(hasattr(node, 'source_hot_knowledge_id'), 99),
            -timestamp,
        )

    @staticmethod
    def _timeline_event_sort_key(event: KnowledgeTimelineEvent) -> tuple[float, str]:
        timestamp = event.timestamp.timestamp() if event.timestamp else 0.0
        return (timestamp, event.event_id)

    def _build_review_window_reports(self, *, view_mode: str, limit: int) -> dict[int, KnowledgeCoverageReportOut]:
        available_windows = self.analytics_repository.get_review_trend_windows(list(self.TREND_REVIEW_WINDOWS))
        reports: dict[int, KnowledgeCoverageReportOut] = {}
        for window_size in self.TREND_REVIEW_WINDOWS:
            reports[window_size] = self.build_coverage_report(
                window_type='reviews',
                window_value=window_size if window_size in available_windows else window_size,
                view_mode=view_mode,
                limit=limit,
            )
        return reports

    def _build_trend_series(
        self,
        *,
        trend_reports: dict[int, KnowledgeCoverageReportOut],
        knowledge_id: str | None,
        lineage_id: str | None,
        view_mode: str,
        candidates_only: bool,
    ) -> list[KnowledgeTrendSeries]:
        filtered_items_by_window = {
            window_size: self._filter_items(
                report.items,
                knowledge_id=knowledge_id,
                lineage_id=lineage_id,
            )
            for window_size, report in trend_reports.items()
        }
        item_map: dict[str, dict[int, KnowledgeCoverageOut]] = defaultdict(dict)
        fallback_items: dict[str, KnowledgeCoverageOut] = {}
        for window_size, items in filtered_items_by_window.items():
            for item in items:
                series_key = self._series_key(item, view_mode=view_mode)
                item_map[series_key][window_size] = item
                fallback_items.setdefault(series_key, item)

        series_list: list[KnowledgeTrendSeries] = []
        for series_key, by_window in item_map.items():
            reference_item = fallback_items[series_key]
            points = [
                self._trend_point_from_item(
                    by_window.get(window_size),
                    window_size=window_size,
                )
                for window_size in self.TREND_REVIEW_WINDOWS
            ]
            if candidates_only and all(point.pruning_reason_snapshot == 'stable_recent_window' for point in points):
                continue
            series_list.append(
                KnowledgeTrendSeries(
                    knowledge_id=reference_item.knowledge_id,
                    lineage_id=reference_item.lineage_id,
                    tier=reference_item.tier,
                    status=reference_item.status,
                    category=reference_item.category,
                    view_mode=view_mode,
                    trend_windows=[point.window_label for point in points],
                    trend_signal=self._resolve_trend_signal(points),
                    is_current_active=reference_item.is_current_active,
                    aggregated_from_nodes=reference_item.aggregated_from_nodes,
                    points=points,
                )
            )

        return sorted(series_list, key=lambda row: (row.lineage_id, row.knowledge_id))

    def _build_trend_summary(
        self,
        *,
        trend_reports: dict[int, KnowledgeCoverageReportOut],
        knowledge_id: str | None,
        lineage_id: str | None,
        view_mode: str,
        candidates_only: bool,
    ) -> KnowledgeTrendSummary:
        active_knowledge_count_trend: list[dict[str, Any]] = []
        pruning_candidate_count_trend: list[dict[str, Any]] = []
        avg_hit_rate_trend: list[dict[str, Any]] = []
        avg_conflict_rate_trend: list[dict[str, Any]] = []

        for window_size in self.TREND_REVIEW_WINDOWS:
            report = trend_reports[window_size]
            filtered_items = self._filter_items(report.items, knowledge_id=knowledge_id, lineage_id=lineage_id)
            if candidates_only:
                filtered_items = [item for item in filtered_items if item.pruning_recommendation != 'keep']
            evaluated_total = sum(item.evaluated_match_count for item in filtered_items)
            hit_total = sum(item.hit_count for item in filtered_items)
            match_total = sum(item.match_count for item in filtered_items)
            conflict_total = sum(item.conflict_count for item in filtered_items)
            active_total = sum(1 for item in filtered_items if item.status != KnowledgeStatus.ARCHIVED)
            pruning_total = sum(1 for item in filtered_items if item.pruning_recommendation != 'keep')
            window_label = self._window_label(window_size)

            active_knowledge_count_trend.append({'window_label': window_label, 'value': active_total})
            pruning_candidate_count_trend.append({'window_label': window_label, 'value': pruning_total})
            avg_hit_rate_trend.append(
                {
                    'window_label': window_label,
                    'value': round(hit_total / evaluated_total, 4) if evaluated_total else 0.0,
                }
            )
            avg_conflict_rate_trend.append(
                {
                    'window_label': window_label,
                    'value': round(conflict_total / match_total, 4) if match_total else 0.0,
                }
            )

        return KnowledgeTrendSummary(
            view_mode=view_mode,
            trend_windows=[self._window_label(size) for size in self.TREND_REVIEW_WINDOWS],
            active_knowledge_count_trend=active_knowledge_count_trend,
            pruning_candidate_count_trend=pruning_candidate_count_trend,
            avg_hit_rate_trend=avg_hit_rate_trend,
            avg_conflict_rate_trend=avg_conflict_rate_trend,
        )

    def _filter_items(
        self,
        items: list[KnowledgeCoverageOut],
        *,
        knowledge_id: str | None,
        lineage_id: str | None,
    ) -> list[KnowledgeCoverageOut]:
        if knowledge_id is None and lineage_id is None:
            return list(items)

        filtered: list[KnowledgeCoverageOut] = []
        for item in items:
            matches_lineage = lineage_id is None or item.lineage_id == lineage_id
            matches_knowledge = knowledge_id is None or (
                knowledge_id in {item.knowledge_id, item.lineage_id}
                or any(node.knowledge_id == knowledge_id for node in item.aggregated_from_nodes)
            )
            if matches_lineage and matches_knowledge:
                filtered.append(item)
        return filtered

    def _trend_point_from_item(
        self,
        item: KnowledgeCoverageOut | None,
        *,
        window_size: int,
    ) -> KnowledgeTrendPoint:
        if item is None:
            return KnowledgeTrendPoint(window_label=self._window_label(window_size), pruning_reason_snapshot='no_data')
        return KnowledgeTrendPoint(
            window_label=self._window_label(window_size),
            coverage_count=item.coverage_count,
            match_count=item.match_count,
            hit_rate=item.hit_rate,
            fail_rate=item.fail_rate,
            avg_return_after_match=item.avg_return_after_match,
            avg_max_drawdown=item.avg_max_drawdown,
            conflict_count=item.conflict_count,
            pruning_reason_snapshot=item.pruning_reason,
        )

    @staticmethod
    def _window_label(window_size: int) -> str:
        return f'last_{window_size}_reviews'

    @staticmethod
    def _series_key(item: KnowledgeCoverageOut, *, view_mode: str) -> str:
        return item.lineage_id if view_mode == 'active' else item.knowledge_id

    def _resolve_trend_signal(self, points: list[KnowledgeTrendPoint]) -> str:
        meaningful_points = [point for point in points if point.coverage_count or point.match_count]
        if len(meaningful_points) < 2:
            return 'stable'

        recent = meaningful_points[0]
        baseline = meaningful_points[-1]
        improvements = 0
        deteriorations = 0

        if recent.hit_rate >= baseline.hit_rate + 0.1:
            improvements += 1
        elif recent.hit_rate + 0.1 <= baseline.hit_rate:
            deteriorations += 1

        if recent.fail_rate + 0.1 <= baseline.fail_rate:
            improvements += 1
        elif recent.fail_rate >= baseline.fail_rate + 0.1:
            deteriorations += 1

        if recent.avg_return_after_match >= baseline.avg_return_after_match + 0.02:
            improvements += 1
        elif recent.avg_return_after_match + 0.02 <= baseline.avg_return_after_match:
            deteriorations += 1

        recent_conflict_rate = round(recent.conflict_count / recent.match_count, 4) if recent.match_count else 0.0
        baseline_conflict_rate = round(baseline.conflict_count / baseline.match_count, 4) if baseline.match_count else 0.0
        if recent_conflict_rate + 0.1 <= baseline_conflict_rate:
            improvements += 1
        elif recent_conflict_rate >= baseline_conflict_rate + 0.1:
            deteriorations += 1

        if improvements >= 2 and improvements > deteriorations:
            return 'improving'
        if deteriorations >= 2 and deteriorations > improvements:
            return 'deteriorating'
        return 'stable'

    def _build_inventory(self, limit: int) -> list[dict[str, Any]]:
        hot_rows = self.analytics_repository.list_hot_knowledge(include_archived=True, limit=limit)
        cold_rows = self.analytics_repository.list_cold_knowledge(include_archived=True, include_degraded=True, limit=limit)
        nodes: list[dict[str, Any]] = []
        for row in hot_rows:
            nodes.append(self._knowledge_node_from_row(row, tier=KnowledgeTier.HOT, lineage_id=getattr(row, 'lineage_id', None) or row.knowledge_id))
        for row in cold_rows:
            nodes.append(self._knowledge_node_from_row(row, tier=KnowledgeTier.COLD, lineage_id=getattr(row, 'lineage_id', None) or row.source_hot_knowledge_id))
        return nodes

    def _build_lineage_items(
        self,
        *,
        inventory: list[dict[str, Any]],
        window: KnowledgeAnalyticsWindow,
    ) -> list[KnowledgeCoverageOut]:
        window_ctx = self._resolve_window_context(window=window)
        event_metrics = self._build_event_metrics(window_ctx['knowledge_events'])
        representatives = self._resolve_representatives(inventory)
        items: list[KnowledgeCoverageOut] = []

        for node in inventory:
            coverage_ids: set[str] = set()
            match_ids: set[str] = set()
            conflict_ids: set[str] = set()
            observed_market_regimes: list[str] = []

            for recommendation in window_ctx['recommendations']:
                tag_match = match_structured_tags(
                    candidate_event_tags=recommendation['event_tags'],
                    candidate_technical_tags=recommendation['technical_pattern_tags'],
                    candidate_market_regime_tags=recommendation['market_regime_tags'],
                    candidate_risk_tags=recommendation['risk_pattern_tags'],
                    applicable_event_tags=node['applicable_event_tags'],
                    applicable_technical_tags=node['applicable_technical_tags'],
                    applicable_market_regimes=node['applicable_market_regimes'],
                    negative_match_tags=node['negative_match_tags'],
                )
                if tag_match.match_score > 0 or tag_match.matched_tags or tag_match.conflicting_tags:
                    coverage_ids.add(recommendation['recommendation_id'])
                    observed_market_regimes = self._merge_unique(observed_market_regimes, recommendation['market_regime_tags'])
                if node['knowledge_id'] in recommendation['knowledge_ids']:
                    match_ids.add(recommendation['recommendation_id'])
                    if recommendation['knowledge_conflict_flag'] or recommendation['conflicts_by_knowledge'].get(node['knowledge_id']):
                        conflict_ids.add(recommendation['recommendation_id'])

            evaluation_entries = [entry for entry in window_ctx['review_entries'] if node['knowledge_id'] in entry['knowledge_ids']]
            for entry in evaluation_entries:
                observed_market_regimes = self._merge_unique(observed_market_regimes, entry['market_regime_tags'])

            representative = representatives.get(node['lineage_id'])
            is_current_active = bool(
                representative
                and representative['knowledge_id'] == node['knowledge_id']
                and representative['status'] == KnowledgeStatus.ACTIVE
            )
            items.append(
                self._build_coverage_item(
                    base_node=node,
                    coverage_ids=coverage_ids,
                    match_ids=match_ids,
                    conflict_ids=conflict_ids,
                    evaluation_entries=evaluation_entries,
                    observed_market_regimes=observed_market_regimes,
                    promoted_ids=event_metrics[node['knowledge_id']]['promoted_ids'],
                    demoted_ids=event_metrics[node['knowledge_id']]['demoted_ids'],
                    aggregated_from_nodes=[self._aggregated_node(node)],
                    is_current_active=is_current_active,
                    window=window,
                )
            )
        return sorted(items, key=lambda row: (row.lineage_id, row.tier.value, row.knowledge_id))

    def _apply_view_mode(self, lineage_items: list[KnowledgeCoverageOut], *, view_mode: str) -> list[KnowledgeCoverageOut]:
        if view_mode == 'lineage':
            return lineage_items

        grouped: dict[str, list[KnowledgeCoverageOut]] = defaultdict(list)
        for item in lineage_items:
            grouped[item.lineage_id].append(item)

        active_items: list[KnowledgeCoverageOut] = []
        for lineage_id, nodes in grouped.items():
            representative = self._select_representative_item(nodes)
            if representative is None:
                continue
            active_items.append(
                self._build_coverage_item(
                    base_node={
                        'knowledge_id': representative.knowledge_id,
                        'lineage_id': lineage_id,
                        'tier': representative.tier,
                        'status': representative.status,
                        'text': representative.text,
                        'category': representative.category,
                        'applicable_event_tags': representative.applicable_event_tags,
                        'applicable_technical_tags': representative.applicable_technical_tags,
                        'applicable_market_regimes': representative.applicable_market_regimes,
                        'negative_match_tags': representative.negative_match_tags,
                    },
                    coverage_ids=self._union_from_items(nodes, 'coverage_ids'),
                    match_ids=self._union_from_items(nodes, 'match_ids'),
                    conflict_ids=self._union_from_items(nodes, 'conflict_ids'),
                    evaluation_entries=self._merge_evaluation_entries(nodes),
                    observed_market_regimes=self._merge_observed_market_regimes(nodes),
                    promoted_ids=self._union_from_items(nodes, 'promoted_ids'),
                    demoted_ids=self._union_from_items(nodes, 'demoted_ids'),
                    aggregated_from_nodes=sorted(
                        [self._aggregated_node_from_item(node) for node in nodes],
                        key=lambda ref: (ref.knowledge_id, ref.knowledge_type.value),
                    ),
                    is_current_active=representative.status == KnowledgeStatus.ACTIVE,
                    window=self._resolve_window(
                        window_type=self._item_meta(representative).get('window_type', 'all_time'),
                        window_value=self._item_meta(representative).get('window_value'),
                        view_mode='active',
                    ),
                )
            )
        return sorted(active_items, key=lambda row: (row.tier.value, row.category, row.knowledge_id))

    def _build_coverage_item(
        self,
        *,
        base_node: dict[str, Any],
        coverage_ids: set[str],
        match_ids: set[str],
        conflict_ids: set[str],
        evaluation_entries: list[dict[str, Any]],
        observed_market_regimes: list[str],
        promoted_ids: set[str],
        demoted_ids: set[str],
        aggregated_from_nodes: list[KnowledgeAggregatedNode],
        is_current_active: bool,
        window: KnowledgeAnalyticsWindow,
    ) -> KnowledgeCoverageOut:
        evaluation_map = {entry['recommendation_id']: entry for entry in evaluation_entries if entry['recommendation_id']}
        unique_evaluations = list(evaluation_map.values())
        hit_count = sum(1 for entry in unique_evaluations if entry['verdict'] == 'outperform')
        fail_count = sum(1 for entry in unique_evaluations if entry['verdict'] in {'underperform', 'insufficient_data'})
        selected_returns = [entry['selected_return'] for entry in unique_evaluations if entry['selected_return'] is not None]
        drawdowns = [entry['max_drawdown'] for entry in unique_evaluations if entry['max_drawdown'] is not None]
        evaluated_match_count = len(unique_evaluations)
        item = KnowledgeCoverageOut(
            knowledge_id=base_node['knowledge_id'],
            lineage_id=base_node['lineage_id'],
            tier=base_node['tier'],
            status=base_node['status'],
            text=base_node['text'],
            category=base_node['category'],
            applicable_event_tags=base_node['applicable_event_tags'],
            applicable_technical_tags=base_node['applicable_technical_tags'],
            applicable_market_regimes=base_node['applicable_market_regimes'],
            negative_match_tags=base_node['negative_match_tags'],
            coverage_count=len(coverage_ids),
            match_count=len(match_ids),
            evaluated_match_count=evaluated_match_count,
            hit_count=hit_count,
            fail_count=fail_count,
            hit_rate=round(hit_count / evaluated_match_count, 4) if evaluated_match_count else 0.0,
            fail_rate=round(fail_count / evaluated_match_count, 4) if evaluated_match_count else 0.0,
            avg_return_after_match=round(sum(selected_returns) / len(selected_returns), 4) if selected_returns else 0.0,
            avg_max_drawdown=round(sum(drawdowns) / len(drawdowns), 4) if drawdowns else 0.0,
            conflict_count=len(conflict_ids),
            promoted_count=len(promoted_ids),
            demoted_count=len(demoted_ids),
            regime_drift_flag=self._detect_regime_drift(
                applicable_market_regimes=base_node['applicable_market_regimes'],
                observed_market_regimes=observed_market_regimes,
            ),
            observed_market_regimes=sorted(normalize_tags(observed_market_regimes)),
            is_current_active=is_current_active,
            aggregated_from_nodes=aggregated_from_nodes,
            pruning_recommendation='keep',
            pruning_explanation=KnowledgePruningExplanation(),
        )
        recommendation, reason, reasons, explanation = self._evaluate_pruning(item, window=window)
        item.pruning_recommendation = recommendation
        item.pruning_reason = reason
        item.pruning_explanation = explanation
        item.__dict__['_analytics_meta'] = {
            'coverage_ids': set(coverage_ids),
            'match_ids': set(match_ids),
            'conflict_ids': set(conflict_ids),
            'evaluation_entries': unique_evaluations,
            'promoted_ids': set(promoted_ids),
            'demoted_ids': set(demoted_ids),
            'pruning_reasons': reasons,
            'window_type': window.window_type,
            'window_value': window.window_value,
            'created_at': base_node.get('created_at'),
            'updated_at': base_node.get('updated_at'),
        }
        return item

    def _resolve_window(self, *, window_type: str, window_value: int | None, view_mode: str) -> KnowledgeAnalyticsWindow:
        return KnowledgeAnalyticsWindow(
            window_type=window_type,
            window_value=window_value,
            view_mode=view_mode,
        )

    def _resolve_window_context(self, *, window: KnowledgeAnalyticsWindow) -> dict[str, Any]:
        reports = self.analytics_repository.list_review_reports(
            window_type=window.window_type,
            window_value=window.window_value,
            limit=5000,
        )
        target_run_ids = [row.target_run_id for row in reports]
        report_run_ids = [row.run_id for row in reports]
        report_ids = [row.review_report_id for row in reports]
        recommendations = [
            self._build_recommendation_context(row)
            for row in self.analytics_repository.list_recommendations(
                run_ids=target_run_ids if reports else ([] if window.window_type != 'all_time' else None),
                limit=5000,
            )
        ]
        review_entries = [entry for report in reports for entry in self._build_review_entries(report)]
        knowledge_events = self.analytics_repository.list_knowledge_events(
            source_run_ids=report_run_ids if reports else ([] if window.window_type != 'all_time' else None),
            source_review_report_ids=report_ids if reports else ([] if window.window_type != 'all_time' else None),
            limit=5000,
        )
        return {
            'reports': reports,
            'recommendations': recommendations,
            'review_entries': review_entries,
            'knowledge_events': knowledge_events,
        }

    @staticmethod
    def _aggregated_node(node: dict[str, Any]) -> KnowledgeAggregatedNode:
        return KnowledgeAggregatedNode(
            knowledge_id=node['knowledge_id'],
            knowledge_type=node['tier'],
            status=node['status'],
            created_at=node.get('created_at'),
            updated_at=node.get('updated_at'),
        )

    @staticmethod
    def _aggregated_node_from_item(item: KnowledgeCoverageOut) -> KnowledgeAggregatedNode:
        return KnowledgeAggregatedNode(
            knowledge_id=item.knowledge_id,
            knowledge_type=item.tier,
            status=item.status,
            created_at=item.__dict__.get('_analytics_meta', {}).get('created_at'),
            updated_at=item.__dict__.get('_analytics_meta', {}).get('updated_at'),
        )

    def _build_event_metrics(self, events: list[Any]) -> dict[str, dict[str, set[str]]]:
        metrics = defaultdict(lambda: {'promoted_ids': set(), 'demoted_ids': set()})
        for event in events:
            if event.event_type in {'promoted_to_cold', 'promoted_from_hot'}:
                metrics[event.knowledge_id]['promoted_ids'].add(event.event_id)
            if event.event_type in {'demoted_to_hot', 'archived_from_cold', 'archived_hot'}:
                metrics[event.knowledge_id]['demoted_ids'].add(event.event_id)
        return metrics

    def _resolve_representatives(self, inventory: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for node in inventory:
            grouped[node['lineage_id']].append(node)

        representatives: dict[str, dict[str, Any]] = {}
        for lineage_id, nodes in grouped.items():
            candidate = sorted(nodes, key=self._node_sort_key)[0]
            if candidate['status'] == KnowledgeStatus.ARCHIVED:
                continue
            representatives[lineage_id] = candidate
        return representatives

    @staticmethod
    def _knowledge_node_from_row(row, *, tier: KnowledgeTier, lineage_id: str) -> dict[str, Any]:
        return {
            'knowledge_id': row.knowledge_id,
            'lineage_id': lineage_id,
            'tier': tier,
            'status': row.status,
            'text': row.text,
            'category': row.category,
            'applicable_event_tags': normalize_tags(getattr(row, 'applicable_event_tags', [])),
            'applicable_technical_tags': normalize_tags(getattr(row, 'applicable_technical_tags', [])),
            'applicable_market_regimes': normalize_tags(getattr(row, 'applicable_market_regimes', [])),
            'negative_match_tags': normalize_tags(getattr(row, 'negative_match_tags', [])),
            'created_at': getattr(row, 'created_at', None),
            'updated_at': getattr(row, 'updated_at', None),
        }

    @staticmethod
    def _build_recommendation_context(row) -> dict[str, Any]:
        evidence_json = dict(getattr(row, 'evidence_json', {}) or {})
        knowledge_impacts = list(evidence_json.get('knowledge_impact_json', []))
        conflicts_by_knowledge = {
            str(item.get('knowledge_id')): bool(item.get('conflicting_tags'))
            for item in knowledge_impacts
            if item.get('knowledge_id')
        }
        return {
            'recommendation_id': row.recommendation_id,
            'event_tags': normalize_tags(evidence_json.get('normalized_event_tags') or evidence_json.get('event_tags') or []),
            'technical_pattern_tags': normalize_tags(evidence_json.get('technical_pattern_tags', [])),
            'risk_pattern_tags': normalize_tags(evidence_json.get('risk_pattern_tags', [])),
            'market_regime_tags': normalize_tags(evidence_json.get('market_regime_tags', [])),
            'knowledge_ids': KnowledgeAnalyticsService._extract_knowledge_ids(evidence_json),
            'knowledge_conflict_flag': bool(evidence_json.get('knowledge_conflict_flag')),
            'conflicts_by_knowledge': conflicts_by_knowledge,
        }

    @staticmethod
    def _build_review_entries(report) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        verdicts = list((getattr(report, 'verdicts_json', {}) or {}).get('items', []))
        horizon = int(getattr(report, 'horizon', 5))
        return_field = f'actual_return_{horizon}d'
        for verdict in verdicts:
            evidence_json = dict(verdict.get('evidence_json', {}) or {})
            entries.append(
                {
                    'recommendation_id': verdict.get('recommendation_id', ''),
                    'knowledge_ids': KnowledgeAnalyticsService._extract_knowledge_ids(evidence_json),
                    'verdict': verdict.get('verdict', 'insufficient_data'),
                    'selected_return': verdict.get(return_field, verdict.get('actual_return_5d')),
                    'max_drawdown': verdict.get('max_drawdown'),
                    'market_regime_tags': normalize_tags(evidence_json.get('market_regime_tags', [])),
                }
            )
        return entries

    def _build_pruning_candidates(
        self,
        items: list[KnowledgeCoverageOut],
        *,
        trend_signal_map: dict[str, str] | None = None,
        view_mode: str = 'active',
    ) -> list[KnowledgePruningCandidateOut]:
        candidates: list[KnowledgePruningCandidateOut] = []
        for item in items:
            if item.pruning_recommendation == 'keep':
                continue
            series_key = item.lineage_id if view_mode == 'active' else item.knowledge_id
            candidates.append(
                KnowledgePruningCandidateOut(
                    knowledge_id=item.knowledge_id,
                    lineage_id=item.lineage_id,
                    tier=item.tier,
                    status=item.status,
                    category=item.category,
                    recommendation=item.pruning_recommendation,
                    reason=item.pruning_reason,
                    reasons=list(self._item_meta(item).get('pruning_reasons', [])),
                    trend_signal=(trend_signal_map or {}).get(series_key, 'stable'),
                    explanation=item.pruning_explanation,
                    coverage_count=item.coverage_count,
                    match_count=item.match_count,
                    evaluated_match_count=item.evaluated_match_count,
                    hit_rate=item.hit_rate,
                    fail_rate=item.fail_rate,
                    avg_return_after_match=item.avg_return_after_match,
                    avg_max_drawdown=item.avg_max_drawdown,
                    conflict_count=item.conflict_count,
                    promoted_count=item.promoted_count,
                    demoted_count=item.demoted_count,
                    regime_drift_flag=item.regime_drift_flag,
                    observed_market_regimes=item.observed_market_regimes,
                    is_current_active=item.is_current_active,
                    aggregated_from_nodes=item.aggregated_from_nodes,
                )
            )
        return sorted(
            candidates,
            key=lambda row: (
                self._pruning_priority(row.recommendation),
                -row.fail_rate,
                row.coverage_count,
                -row.conflict_count,
                row.knowledge_id,
            ),
        )

    def _evaluate_pruning(
        self,
        item: KnowledgeCoverageOut,
        *,
        window: KnowledgeAnalyticsWindow,
    ) -> tuple[str, str, list[str], KnowledgePruningExplanation]:
        conflict_rate = round(item.conflict_count / item.match_count, 4) if item.match_count else 0.0
        low_coverage = item.coverage_count < self.thresholds.low_coverage
        high_conflict = conflict_rate >= self.thresholds.high_conflict_rate
        warning_conflict = conflict_rate >= self.thresholds.warning_conflict_rate
        low_yield = item.evaluated_match_count > 0 and item.avg_return_after_match <= self.thresholds.low_return_threshold
        deprecate_yield = item.evaluated_match_count > 0 and item.avg_return_after_match <= self.thresholds.deprecate_return_threshold
        high_fail = item.evaluated_match_count > 0 and item.fail_rate >= self.thresholds.high_fail_rate
        archive_fail = item.evaluated_match_count > 0 and item.fail_rate >= self.thresholds.archive_fail_rate

        reasons: list[str] = []
        if low_coverage:
            reasons.append('low_coverage')
        if warning_conflict:
            reasons.append('high_conflict' if high_conflict else 'conflict_watch')
        if low_yield:
            reasons.append('low_return')
        if high_fail:
            reasons.append('high_fail_rate')
        if item.regime_drift_flag:
            reasons.append('regime_drift')
        if item.demoted_count > 0:
            reasons.append('prior_demotion')

        if item.coverage_count == 0 and (item.demoted_count > 0 or item.status == KnowledgeStatus.DEGRADED):
            recommendation = 'archive_candidate'
            primary_reason = 'inactive_after_demotion'
        elif archive_fail and (high_conflict or item.regime_drift_flag or item.status == KnowledgeStatus.DEGRADED):
            recommendation = 'archive_candidate'
            primary_reason = 'persistent_failure'
        elif high_fail or (deprecate_yield and (high_conflict or item.regime_drift_flag)) or (item.regime_drift_flag and item.demoted_count > 0):
            recommendation = 'deprecate'
            primary_reason = 'high_failure_recent_window'
        elif low_coverage or warning_conflict or low_yield:
            recommendation = 'watch'
            primary_reason = reasons[0] if reasons else 'monitor_recent_window'
        else:
            recommendation = 'keep'
            primary_reason = 'stable_recent_window'

        explanation = KnowledgePruningExplanation(
            low_coverage_recent_window=KnowledgePruningSignal(
                triggered=low_coverage,
                threshold=self.thresholds.low_coverage,
                actual_value=item.coverage_count,
                note='Coverage count in the selected window is below the monitoring threshold.',
            ),
            high_conflict_recent_window=KnowledgePruningSignal(
                triggered=warning_conflict,
                threshold=self.thresholds.warning_conflict_rate,
                actual_value=conflict_rate,
                note='Conflict rate is computed as conflict_count / match_count within the selected window.',
            ),
            low_return_recent_window=KnowledgePruningSignal(
                triggered=low_yield,
                threshold=self.thresholds.low_return_threshold,
                actual_value=item.avg_return_after_match,
                note='Average realized return after match in the selected window.',
            ),
            high_failure_recent_window=KnowledgePruningSignal(
                triggered=high_fail,
                threshold=self.thresholds.high_fail_rate,
                actual_value=item.fail_rate,
                note='Failure rate counts underperform + insufficient_data over evaluated matches.',
            ),
            regime_drift_detected=KnowledgePruningSignal(
                triggered=item.regime_drift_flag,
                threshold=self.thresholds.regime_drift_overlap_ratio,
                actual_value=self._compute_regime_overlap(
                    applicable_market_regimes=item.applicable_market_regimes,
                    observed_market_regimes=item.observed_market_regimes,
                ),
                note='Observed market regimes drift away from the knowledge applicable regimes in the selected window.',
            ),
            summary=self._build_explanation_summary(recommendation, item, reasons, window),
        )
        return recommendation, primary_reason, reasons or ['stable_recent_window'], explanation

    def _aggregate(self, items: list[KnowledgeCoverageOut], field_name: str) -> list[KnowledgeCoverageAggregateOut]:
        buckets: dict[str, dict[str, Any]] = {}
        for item in items:
            raw_values = getattr(item, field_name)
            for value in raw_values if isinstance(raw_values, list) else [raw_values]:
                if not value:
                    continue
                bucket = buckets.setdefault(
                    str(value),
                    {
                        'knowledge_ids': set(),
                        'coverage_count': 0,
                        'match_count': 0,
                        'evaluated_match_count': 0,
                        'hit_count': 0,
                        'fail_count': 0,
                        'return_total': 0.0,
                        'drawdown_total': 0.0,
                        'conflict_count': 0,
                        'promoted_count': 0,
                        'demoted_count': 0,
                    },
                )
                bucket['knowledge_ids'].add(item.knowledge_id)
                bucket['coverage_count'] += item.coverage_count
                bucket['match_count'] += item.match_count
                bucket['evaluated_match_count'] += item.evaluated_match_count
                bucket['hit_count'] += item.hit_count
                bucket['fail_count'] += item.fail_count
                bucket['return_total'] += item.avg_return_after_match * item.evaluated_match_count
                bucket['drawdown_total'] += item.avg_max_drawdown * item.evaluated_match_count
                bucket['conflict_count'] += item.conflict_count
                bucket['promoted_count'] += item.promoted_count
                bucket['demoted_count'] += item.demoted_count

        aggregates: list[KnowledgeCoverageAggregateOut] = []
        for key, bucket in buckets.items():
            evaluated_match_count = bucket['evaluated_match_count']
            aggregates.append(
                KnowledgeCoverageAggregateOut(
                    dimension=field_name,
                    key=key,
                    knowledge_count=len(bucket['knowledge_ids']),
                    knowledge_ids=sorted(bucket['knowledge_ids']),
                    coverage_count=bucket['coverage_count'],
                    match_count=bucket['match_count'],
                    evaluated_match_count=evaluated_match_count,
                    hit_count=bucket['hit_count'],
                    fail_count=bucket['fail_count'],
                    hit_rate=round(bucket['hit_count'] / evaluated_match_count, 4) if evaluated_match_count else 0.0,
                    fail_rate=round(bucket['fail_count'] / evaluated_match_count, 4) if evaluated_match_count else 0.0,
                    avg_return_after_match=round(bucket['return_total'] / evaluated_match_count, 4) if evaluated_match_count else 0.0,
                    avg_max_drawdown=round(bucket['drawdown_total'] / evaluated_match_count, 4) if evaluated_match_count else 0.0,
                    conflict_count=bucket['conflict_count'],
                    promoted_count=bucket['promoted_count'],
                    demoted_count=bucket['demoted_count'],
                )
            )
        return sorted(aggregates, key=lambda row: (-row.match_count, -row.coverage_count, row.key))

    def _detect_regime_drift(self, *, applicable_market_regimes: list[str], observed_market_regimes: list[str]) -> bool:
        if not applicable_market_regimes or not observed_market_regimes:
            return False
        return self._compute_regime_overlap(
            applicable_market_regimes=applicable_market_regimes,
            observed_market_regimes=observed_market_regimes,
        ) < self.thresholds.regime_drift_overlap_ratio

    @staticmethod
    def _compute_regime_overlap(*, applicable_market_regimes: list[str], observed_market_regimes: list[str]) -> float:
        if not applicable_market_regimes or not observed_market_regimes:
            return 1.0
        applicable = set(normalize_tags(applicable_market_regimes))
        observed = set(normalize_tags(observed_market_regimes))
        return round(len(applicable & observed) / max(1, len(observed)), 4)

    @staticmethod
    def _extract_knowledge_ids(evidence_json: dict[str, Any]) -> set[str]:
        knowledge_ids: set[str] = set()
        for item in evidence_json.get('knowledge_refs', []) or []:
            if isinstance(item, dict):
                knowledge_id = item.get('ref_id') or item.get('knowledge_id')
                if knowledge_id:
                    knowledge_ids.add(str(knowledge_id))
        for item in evidence_json.get('knowledge_impact_json', []) or []:
            if isinstance(item, dict) and item.get('knowledge_id'):
                knowledge_ids.add(str(item['knowledge_id']))
        return knowledge_ids

    @staticmethod
    def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
        result = list(existing)
        for item in normalize_tags(incoming):
            if item not in result:
                result.append(item)
        return result

    @staticmethod
    def _union_from_items(items: list[KnowledgeCoverageOut], key: str) -> set[str]:
        union: set[str] = set()
        for item in items:
            union |= set(KnowledgeAnalyticsService._item_meta(item).get(key, set()))
        return union

    @staticmethod
    def _merge_evaluation_entries(items: list[KnowledgeCoverageOut]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for item in items:
            for entry in KnowledgeAnalyticsService._item_meta(item).get('evaluation_entries', []):
                merged[entry.get('recommendation_id') or f'missing:{len(merged)}'] = entry
        return list(merged.values())

    @staticmethod
    def _merge_observed_market_regimes(items: list[KnowledgeCoverageOut]) -> list[str]:
        observed: list[str] = []
        for item in items:
            observed = KnowledgeAnalyticsService._merge_unique(observed, item.observed_market_regimes)
        return observed

    def _select_representative_item(self, items: list[KnowledgeCoverageOut]) -> KnowledgeCoverageOut | None:
        ordered = sorted(items, key=self._coverage_item_sort_key)
        candidate = ordered[0] if ordered else None
        if candidate is None or candidate.status == KnowledgeStatus.ARCHIVED:
            return None
        return candidate

    @staticmethod
    def _node_sort_key(node: dict[str, Any]) -> tuple[int, int, int]:
        status_priority = {KnowledgeStatus.ACTIVE: 0, KnowledgeStatus.DEGRADED: 1, KnowledgeStatus.ARCHIVED: 2}
        tier_priority = {KnowledgeTier.COLD: 0, KnowledgeTier.HOT: 1}
        timestamp = int(node['updated_at'].timestamp()) if node.get('updated_at') else 0
        return (status_priority.get(node['status'], 99), tier_priority.get(node['tier'], 99), -timestamp)

    @staticmethod
    def _coverage_item_sort_key(item: KnowledgeCoverageOut) -> tuple[int, int, int, str]:
        status_priority = {KnowledgeStatus.ACTIVE: 0, KnowledgeStatus.DEGRADED: 1, KnowledgeStatus.ARCHIVED: 2}
        tier_priority = {KnowledgeTier.COLD: 0, KnowledgeTier.HOT: 1}
        updated_at = KnowledgeAnalyticsService._item_meta(item).get('updated_at')
        timestamp = int(updated_at.timestamp()) if updated_at else 0
        return (status_priority.get(item.status, 99), tier_priority.get(item.tier, 99), -timestamp, item.knowledge_id)

    @staticmethod
    def _build_explanation_summary(
        recommendation: str,
        item: KnowledgeCoverageOut,
        reasons: list[str],
        window: KnowledgeAnalyticsWindow,
    ) -> str:
        if recommendation == 'archive_candidate':
            return (
                f'{item.knowledge_id} is archive_candidate in {window.window_type}'
                f'({window.window_value}) due to {reasons or ["inactive"]}.'
            )
        if recommendation == 'deprecate':
            return (
                f'{item.knowledge_id} is deprecate in {window.window_type}'
                f'({window.window_value}) due to {reasons} and weak realized return.'
            )
        if recommendation == 'watch':
            return (
                f'{item.knowledge_id} stays watch in {window.window_type}'
                f'({window.window_value}) due to {reasons}.'
            )
        return (
            f'{item.knowledge_id} remains keep in {window.window_type}'
            f'({window.window_value}) because recent window stats stay stable.'
        )

    @staticmethod
    def _pruning_priority(recommendation: str) -> int:
        return {'archive_candidate': 0, 'deprecate': 1, 'watch': 2, 'keep': 3}.get(recommendation, 99)

    @staticmethod
    def _item_meta(item: KnowledgeCoverageOut) -> dict[str, Any]:
        return dict(item.__dict__.get('_analytics_meta', {}))
