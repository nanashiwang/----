from __future__ import annotations

from sqlalchemy import select

from core.enums import KnowledgeStatus
from core.ids import generate_prefixed_id
from domain.taxonomy import normalize_tags
from infrastructure.db.postgres.models import ColdKnowledgeORM, HotKnowledgeORM, KnowledgeEventORM
from infrastructure.repositories._base import SQLAlchemyRepository


class KnowledgeRepository(SQLAlchemyRepository):
    def get_hot(self, knowledge_id: str):
        return self._one_or_none(HotKnowledgeORM, HotKnowledgeORM.knowledge_id == knowledge_id)

    def get_cold(self, knowledge_id: str):
        return self._one_or_none(ColdKnowledgeORM, ColdKnowledgeORM.knowledge_id == knowledge_id)

    def get_knowledge_node(self, knowledge_id: str):
        hot = self.get_hot(knowledge_id)
        if hot is not None:
            return hot, 'hot'
        cold = self.get_cold(knowledge_id)
        if cold is not None:
            return cold, 'cold'
        return None, None

    def resolve_lineage_id(self, knowledge_id: str) -> str | None:
        row, _ = self.get_knowledge_node(knowledge_id)
        if row is None:
            return None
        return getattr(row, 'lineage_id', None) or getattr(row, 'source_hot_knowledge_id', None) or knowledge_id

    def get_hot_by_signature(self, text: str, category: str):
        return self._one_or_none(
            HotKnowledgeORM,
            HotKnowledgeORM.text == text,
            HotKnowledgeORM.category == category,
        )

    def list_lineage_nodes(self, lineage_id: str):
        with self.session_manager.session_scope() as session:
            hot_stmt = select(HotKnowledgeORM).where(HotKnowledgeORM.lineage_id == lineage_id)
            cold_stmt = select(ColdKnowledgeORM).where(ColdKnowledgeORM.lineage_id == lineage_id)
            hot_rows = list(session.execute(hot_stmt).scalars().all())
            cold_rows = list(session.execute(cold_stmt).scalars().all())
        return {
            'hot': hot_rows,
            'cold': cold_rows,
            'all': hot_rows + cold_rows,
        }

    def list_lineage_events(self, lineage_id: str, descending: bool = False, limit: int = 500):
        nodes = self.list_lineage_nodes(lineage_id)
        knowledge_ids = [row.knowledge_id for row in nodes['all']]
        if not knowledge_ids:
            return []
        with self.session_manager.session_scope() as session:
            stmt = select(KnowledgeEventORM).where(KnowledgeEventORM.knowledge_id.in_(knowledge_ids))
            if descending:
                stmt = stmt.order_by(KnowledgeEventORM.created_at.desc())
            else:
                stmt = stmt.order_by(KnowledgeEventORM.created_at.asc())
            if limit > 0:
                stmt = stmt.limit(limit)
            return list(session.execute(stmt).scalars().all())

    def create_hot_knowledge(
        self,
        item: dict,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        event_type: str = 'hot_created',
    ):
        normalized_tags = self._normalize_knowledge_tags(item)
        knowledge_id = item.get('knowledge_id') or generate_prefixed_id('knowledge')
        lineage_id = item.get('lineage_id') or item.get('source_hot_knowledge_id') or knowledge_id
        instance = HotKnowledgeORM(
            knowledge_id=knowledge_id,
            lineage_id=lineage_id,
            text=item['text'],
            category=item['category'],
            source_run_ids=list(item.get('source_run_ids', [])),
            source_recommendation_ids=list(item.get('source_recommendation_ids', [])),
            tests_survived=int(item.get('tests_survived', 0)),
            pass_count=int(item.get('pass_count', 0)),
            fail_count=int(item.get('fail_count', 0)),
            pass_rate=float(item.get('pass_rate', 0.0)),
            applicable_event_tags=normalized_tags['applicable_event_tags'],
            applicable_technical_tags=normalized_tags['applicable_technical_tags'],
            applicable_market_regimes=normalized_tags['applicable_market_regimes'],
            negative_match_tags=normalized_tags['negative_match_tags'],
            status=self._coerce_status(item.get('status', KnowledgeStatus.ACTIVE)),
            evidence_json=dict(item.get('evidence_json', {})),
        )
        with self.session_manager.session_scope() as session:
            session.add(instance)
            self._append_event_in_session(
                session=session,
                knowledge_id=instance.knowledge_id,
                knowledge_type='hot',
                event_type=event_type,
                source_run_id=source_run_id,
                source_review_report_id=source_review_report_id,
                details_json=self._build_event_details(
                    details_json={
                        'category': instance.category,
                        'lineage_id': instance.lineage_id,
                        'applicable_event_tags': instance.applicable_event_tags,
                        'applicable_technical_tags': instance.applicable_technical_tags,
                        'applicable_market_regimes': instance.applicable_market_regimes,
                        'negative_match_tags': instance.negative_match_tags,
                    },
                    after_status=instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(instance),
                ),
            )
        return instance

    def update_hot_knowledge_stats(
        self,
        knowledge_id: str,
        item: dict,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
    ):
        with self.session_manager.session_scope() as session:
            instance = session.get(HotKnowledgeORM, knowledge_id)
            if instance is None:
                return None
            previous_status = instance.status
            instance.source_run_ids = self._merge_unique_lists(instance.source_run_ids, item.get('source_run_ids', []))
            instance.source_recommendation_ids = self._merge_unique_lists(
                instance.source_recommendation_ids,
                item.get('source_recommendation_ids', []),
            )
            normalized_tags = self._normalize_knowledge_tags(item)
            instance.tests_survived += int(item.get('tests_survived', 0))
            instance.pass_count += int(item.get('pass_count', 0))
            instance.fail_count += int(item.get('fail_count', 0))
            instance.lineage_id = item.get('lineage_id') or instance.lineage_id or instance.knowledge_id
            total_tests = instance.pass_count + instance.fail_count
            instance.tests_survived = max(instance.tests_survived, total_tests)
            instance.pass_rate = round(instance.pass_count / instance.tests_survived, 4) if instance.tests_survived else 0.0
            instance.applicable_event_tags = self._merge_unique_lists(
                instance.applicable_event_tags,
                normalized_tags['applicable_event_tags'],
            )
            instance.applicable_technical_tags = self._merge_unique_lists(
                instance.applicable_technical_tags,
                normalized_tags['applicable_technical_tags'],
            )
            instance.applicable_market_regimes = self._merge_unique_lists(
                instance.applicable_market_regimes,
                normalized_tags['applicable_market_regimes'],
            )
            instance.negative_match_tags = self._merge_unique_lists(
                instance.negative_match_tags,
                normalized_tags['negative_match_tags'],
            )
            instance.status = self._coerce_status(item.get('status', instance.status))
            instance.evidence_json = self._merge_evidence(instance.evidence_json, item.get('evidence_json', {}))
            session.add(instance)
            self._append_event_in_session(
                session=session,
                knowledge_id=instance.knowledge_id,
                knowledge_type='hot',
                event_type='hot_updated',
                source_run_id=source_run_id,
                source_review_report_id=source_review_report_id,
                details_json=self._build_event_details(
                    details_json={
                        'lineage_id': instance.lineage_id,
                        'applicable_event_tags': instance.applicable_event_tags,
                        'applicable_technical_tags': instance.applicable_technical_tags,
                        'applicable_market_regimes': instance.applicable_market_regimes,
                        'negative_match_tags': instance.negative_match_tags,
                    },
                    before_status=previous_status,
                    after_status=instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(instance),
                ),
            )
        return instance

    def upsert_hot(
        self,
        item: dict,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
    ):
        existing = self.get_hot_by_signature(item['text'], item['category'])
        if existing is None:
            return self.create_hot_knowledge(
                item,
                source_run_id=source_run_id,
                source_review_report_id=source_review_report_id,
            )
        return self.update_hot_knowledge_stats(
            existing.knowledge_id,
            item,
            source_run_id=source_run_id,
            source_review_report_id=source_review_report_id,
        )

    def list_hot(self, limit: int = 100):
        with self.session_manager.session_scope() as session:
            stmt = (
                select(HotKnowledgeORM)
                .where(HotKnowledgeORM.status != KnowledgeStatus.ARCHIVED)
                .order_by(HotKnowledgeORM.updated_at.desc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

    def list_promotable_hot_knowledge(
        self,
        min_tests: int = 10,
        min_pass_rate: float = 0.65,
        min_market_regimes: int = 2,
        limit: int = 100,
    ):
        candidates = self._all(
            HotKnowledgeORM,
            HotKnowledgeORM.tests_survived >= min_tests,
            HotKnowledgeORM.pass_rate >= min_pass_rate,
            HotKnowledgeORM.status != KnowledgeStatus.ARCHIVED,
            order_by=HotKnowledgeORM.updated_at.desc(),
        )
        promotable = []
        for item in candidates:
            regimes = set(item.applicable_market_regimes or [])
            if len(regimes) >= min_market_regimes:
                promotable.append(item)
        return promotable[:limit]

    def get_active_cold_knowledge(
        self,
        category: str | None = None,
        market_regime: str | None = None,
        limit: int = 100,
    ):
        with self.session_manager.session_scope() as session:
            stmt = (
                select(ColdKnowledgeORM)
                .where(ColdKnowledgeORM.status == KnowledgeStatus.ACTIVE)
                .order_by(ColdKnowledgeORM.updated_at.desc())
                .limit(limit)
            )
            if category:
                stmt = stmt.where(ColdKnowledgeORM.category == category)
            rows = list(session.execute(stmt).scalars().all())
        if market_regime:
            normalized_market_regime = normalize_tags([market_regime])
            if normalized_market_regime:
                rows = [row for row in rows if normalized_market_regime[0] in (row.applicable_market_regimes or [])]
        return rows

    def promote_to_cold(
        self,
        knowledge_id: str,
        promotion_reason: str,
        promotion_run_id: str,
        source_review_report_id: str | None = None,
    ):
        with self.session_manager.session_scope() as session:
            hot_instance = session.get(HotKnowledgeORM, knowledge_id)
            if hot_instance is None:
                return None
            hot_instance.lineage_id = hot_instance.lineage_id or hot_instance.knowledge_id
            hot_before_status = hot_instance.status

            stmt = (
                select(ColdKnowledgeORM)
                .where(ColdKnowledgeORM.source_hot_knowledge_id == knowledge_id)
                .order_by(ColdKnowledgeORM.version.desc())
            )
            previous = session.execute(stmt).scalars().first()
            version = (previous.version + 1) if previous else 1
            cold_instance = ColdKnowledgeORM(
                knowledge_id=generate_prefixed_id('cold'),
                lineage_id=hot_instance.lineage_id or hot_instance.knowledge_id,
                source_hot_knowledge_id=hot_instance.knowledge_id,
                text=hot_instance.text,
                category=hot_instance.category,
                promotion_reason=promotion_reason,
                promotion_run_id=promotion_run_id,
                source_run_ids=list(hot_instance.source_run_ids or []),
                source_recommendation_ids=list(hot_instance.source_recommendation_ids or []),
                tests_survived=hot_instance.tests_survived,
                pass_count=hot_instance.pass_count,
                fail_count=hot_instance.fail_count,
                pass_rate=hot_instance.pass_rate,
                applicable_event_tags=list(hot_instance.applicable_event_tags or []),
                applicable_technical_tags=list(hot_instance.applicable_technical_tags or []),
                applicable_market_regimes=list(hot_instance.applicable_market_regimes or []),
                negative_match_tags=list(hot_instance.negative_match_tags or []),
                invalid_conditions={'consecutive_failures': 0, 'demote_threshold': 3},
                status=KnowledgeStatus.ACTIVE,
                version=version,
            )
            hot_instance.status = KnowledgeStatus.ARCHIVED
            hot_instance.evidence_json = self._merge_evidence(
                hot_instance.evidence_json,
                {
                    'promotion_reason': promotion_reason,
                    'promoted_cold_knowledge_id': cold_instance.knowledge_id,
                },
            )
            session.add(hot_instance)
            session.add(cold_instance)
            self._append_event_in_session(
                session=session,
                knowledge_id=hot_instance.knowledge_id,
                knowledge_type='hot',
                event_type='promoted_to_cold',
                source_run_id=promotion_run_id,
                source_review_report_id=source_review_report_id,
                details_json=self._build_event_details(
                    details_json={'cold_knowledge_id': cold_instance.knowledge_id, 'reason': promotion_reason},
                    before_status=hot_before_status,
                    after_status=hot_instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(hot_instance),
                ),
            )
            self._append_event_in_session(
                session=session,
                knowledge_id=cold_instance.knowledge_id,
                knowledge_type='cold',
                event_type='promoted_from_hot',
                source_run_id=promotion_run_id,
                source_review_report_id=source_review_report_id,
                details_json=self._build_event_details(
                    details_json={
                        'source_hot_knowledge_id': hot_instance.knowledge_id,
                        'reason': promotion_reason,
                        'lineage_id': cold_instance.lineage_id,
                        'applicable_market_regimes': cold_instance.applicable_market_regimes,
                    },
                    after_status=cold_instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(cold_instance),
                ),
            )
        return cold_instance

    def record_cold_validation(
        self,
        cold_knowledge_id: str,
        passed: bool,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        details_json: dict | None = None,
    ):
        with self.session_manager.session_scope() as session:
            instance = session.get(ColdKnowledgeORM, cold_knowledge_id)
            if instance is None:
                return None
            previous_status = instance.status
            instance.tests_survived += 1
            if passed:
                instance.pass_count += 1
            else:
                instance.fail_count += 1
            total_tests = instance.pass_count + instance.fail_count
            instance.pass_rate = round(instance.pass_count / total_tests, 4) if total_tests else 0.0
            invalid_conditions = dict(instance.invalid_conditions or {})
            consecutive_failures = 0 if passed else int(invalid_conditions.get('consecutive_failures', 0)) + 1
            invalid_conditions['consecutive_failures'] = consecutive_failures
            invalid_conditions['last_validation_result'] = 'pass' if passed else 'fail'
            instance.invalid_conditions = invalid_conditions
            session.add(instance)
            self._append_event_in_session(
                session=session,
                knowledge_id=instance.knowledge_id,
                knowledge_type='cold',
                event_type='validated_pass' if passed else 'validated_fail',
                source_run_id=source_run_id,
                source_review_report_id=source_review_report_id,
                details_json=self._build_event_details(
                    details_json=self._merge_evidence(details_json, {'consecutive_failures': consecutive_failures}),
                    before_status=previous_status,
                    after_status=instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(instance),
                ),
            )
        return instance

    def demote_cold_knowledge(
        self,
        knowledge_id: str,
        reason: str,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        archive: bool = False,
    ):
        with self.session_manager.session_scope() as session:
            cold_instance = session.get(ColdKnowledgeORM, knowledge_id)
            if cold_instance is None:
                return None
            cold_before_status = cold_instance.status

            hot_instance = session.get(HotKnowledgeORM, cold_instance.source_hot_knowledge_id)
            hot_before_status = hot_instance.status if hot_instance is not None else None
            if hot_instance is None:
                hot_instance = HotKnowledgeORM(
                    knowledge_id=cold_instance.source_hot_knowledge_id,
                    lineage_id=cold_instance.lineage_id or cold_instance.source_hot_knowledge_id,
                    text=cold_instance.text,
                    category=cold_instance.category,
                    source_run_ids=list(cold_instance.source_run_ids or []),
                    source_recommendation_ids=list(cold_instance.source_recommendation_ids or []),
                    tests_survived=cold_instance.tests_survived,
                    pass_count=cold_instance.pass_count,
                    fail_count=cold_instance.fail_count,
                    pass_rate=cold_instance.pass_rate,
                    applicable_event_tags=list(cold_instance.applicable_event_tags or []),
                    applicable_technical_tags=list(cold_instance.applicable_technical_tags or []),
                    applicable_market_regimes=list(cold_instance.applicable_market_regimes or []),
                    negative_match_tags=list(cold_instance.negative_match_tags or []),
                    status=KnowledgeStatus.DEGRADED,
                    evidence_json={
                        'market_regimes': list(cold_instance.applicable_market_regimes or []),
                        'demotion_reason': reason,
                    },
                )
            else:
                hot_instance.source_run_ids = self._merge_unique_lists(hot_instance.source_run_ids, cold_instance.source_run_ids)
                hot_instance.lineage_id = hot_instance.lineage_id or cold_instance.lineage_id or hot_instance.knowledge_id
                hot_instance.source_recommendation_ids = self._merge_unique_lists(
                    hot_instance.source_recommendation_ids,
                    cold_instance.source_recommendation_ids,
                )
                hot_instance.tests_survived = max(hot_instance.tests_survived, cold_instance.tests_survived)
                hot_instance.pass_count = max(hot_instance.pass_count, cold_instance.pass_count)
                hot_instance.fail_count = max(hot_instance.fail_count, cold_instance.fail_count)
                total_tests = hot_instance.pass_count + hot_instance.fail_count
                hot_instance.pass_rate = round(hot_instance.pass_count / total_tests, 4) if total_tests else 0.0
                hot_instance.applicable_event_tags = self._merge_unique_lists(
                    hot_instance.applicable_event_tags,
                    cold_instance.applicable_event_tags,
                )
                hot_instance.applicable_technical_tags = self._merge_unique_lists(
                    hot_instance.applicable_technical_tags,
                    cold_instance.applicable_technical_tags,
                )
                hot_instance.applicable_market_regimes = self._merge_unique_lists(
                    hot_instance.applicable_market_regimes,
                    cold_instance.applicable_market_regimes,
                )
                hot_instance.negative_match_tags = self._merge_unique_lists(
                    hot_instance.negative_match_tags,
                    cold_instance.negative_match_tags,
                )
                hot_instance.status = KnowledgeStatus.ARCHIVED if archive else KnowledgeStatus.DEGRADED
                hot_instance.evidence_json = self._merge_evidence(
                    hot_instance.evidence_json,
                    {
                        'market_regimes': list(cold_instance.applicable_market_regimes or []),
                        'demotion_reason': reason,
                    },
                )

            cold_instance.status = KnowledgeStatus.ARCHIVED if archive else KnowledgeStatus.DEGRADED
            cold_instance.invalid_conditions = self._merge_evidence(
                cold_instance.invalid_conditions,
                {'demotion_reason': reason},
            )
            session.add(cold_instance)
            session.add(hot_instance)
            self._append_event_in_session(
                session=session,
                knowledge_id=cold_instance.knowledge_id,
                knowledge_type='cold',
                event_type='archived_from_cold' if archive else 'demoted_to_hot',
                source_run_id=source_run_id,
                source_review_report_id=source_review_report_id,
                details_json=self._build_event_details(
                    details_json={'reason': reason, 'source_hot_knowledge_id': hot_instance.knowledge_id},
                    before_status=cold_before_status,
                    after_status=cold_instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(cold_instance),
                ),
            )
            self._append_event_in_session(
                session=session,
                knowledge_id=hot_instance.knowledge_id,
                knowledge_type='hot',
                event_type='restored_from_cold' if not archive else 'archived_after_cold_failure',
                source_run_id=source_run_id,
                source_review_report_id=source_review_report_id,
                details_json=self._build_event_details(
                    details_json={
                        'reason': reason,
                        'cold_knowledge_id': cold_instance.knowledge_id,
                        'lineage_id': hot_instance.lineage_id,
                    },
                    before_status=hot_before_status,
                    after_status=hot_instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(hot_instance),
                ),
            )
        return {'cold': cold_instance, 'hot': hot_instance}

    def append_knowledge_event(
        self,
        knowledge_id: str,
        knowledge_type: str,
        event_type: str,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        details_json: dict | None = None,
    ):
        with self.session_manager.session_scope() as session:
            return self._append_event_in_session(
                session=session,
                knowledge_id=knowledge_id,
                knowledge_type=knowledge_type,
                event_type=event_type,
                source_run_id=source_run_id,
                source_review_report_id=source_review_report_id,
                details_json=details_json,
            )

    def list_knowledge_events(
        self,
        knowledge_id: str | None = None,
        knowledge_type: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ):
        with self.session_manager.session_scope() as session:
            stmt = select(KnowledgeEventORM).order_by(KnowledgeEventORM.created_at.desc()).limit(limit)
            if knowledge_id:
                stmt = stmt.where(KnowledgeEventORM.knowledge_id == knowledge_id)
            if knowledge_type:
                stmt = stmt.where(KnowledgeEventORM.knowledge_type == knowledge_type)
            if event_type:
                stmt = stmt.where(KnowledgeEventORM.event_type == event_type)
            return list(session.execute(stmt).scalars().all())

    def get_recent_event_window(self, knowledge_id: str, knowledge_type: str, limit: int = 10):
        return self.list_knowledge_events(knowledge_id=knowledge_id, knowledge_type=knowledge_type, limit=limit)

    def archive(self, knowledge_id: str, reason: str):
        with self.session_manager.session_scope() as session:
            instance = session.get(HotKnowledgeORM, knowledge_id)
            if instance is None:
                return None
            previous_status = instance.status
            instance.status = KnowledgeStatus.ARCHIVED
            instance.evidence_json = self._merge_evidence(instance.evidence_json, {'archive_reason': reason})
            session.add(instance)
            self._append_event_in_session(
                session=session,
                knowledge_id=instance.knowledge_id,
                knowledge_type='hot',
                event_type='archived_hot',
                details_json=self._build_event_details(
                    details_json={'reason': reason},
                    before_status=previous_status,
                    after_status=instance.status,
                    metrics_snapshot=self._knowledge_metrics_snapshot(instance),
                ),
            )
        return instance

    def _append_event_in_session(
        self,
        session,
        knowledge_id: str,
        knowledge_type: str,
        event_type: str,
        source_run_id: str | None = None,
        source_review_report_id: str | None = None,
        details_json: dict | None = None,
    ):
        event = KnowledgeEventORM(
            event_id=generate_prefixed_id('event'),
            knowledge_id=knowledge_id,
            knowledge_type=knowledge_type,
            event_type=event_type,
            source_run_id=source_run_id,
            source_review_report_id=source_review_report_id,
            details_json=dict(details_json or {}),
        )
        session.add(event)
        return event

    @staticmethod
    def _merge_unique_lists(existing: list | None, incoming: list | None) -> list:
        result = list(existing or [])
        for item in incoming or []:
            if item and item not in result:
                result.append(item)
        return result

    @staticmethod
    def _merge_evidence(existing: dict | None, incoming: dict | None) -> dict:
        merged = dict(existing or {})
        for key, value in (incoming or {}).items():
            if isinstance(value, list):
                current = list(merged.get(key, []))
                for item in value:
                    if item not in current:
                        current.append(item)
                merged[key] = current
            elif isinstance(value, dict) and isinstance(merged.get(key), dict):
                nested = dict(merged.get(key, {}))
                nested.update(value)
                merged[key] = nested
            else:
                merged[key] = value
        return merged

    @classmethod
    def _build_event_details(
        cls,
        *,
        details_json: dict | None = None,
        before_status: KnowledgeStatus | str | None = None,
        after_status: KnowledgeStatus | str | None = None,
        metrics_snapshot: dict | None = None,
    ) -> dict:
        payload = dict(details_json or {})
        if before_status is not None:
            payload['before_status'] = before_status.value if isinstance(before_status, KnowledgeStatus) else str(before_status)
        if after_status is not None:
            payload['after_status'] = after_status.value if isinstance(after_status, KnowledgeStatus) else str(after_status)
        if metrics_snapshot:
            payload['metrics_snapshot'] = dict(metrics_snapshot)
        return payload

    @staticmethod
    def _knowledge_metrics_snapshot(instance) -> dict:
        snapshot = {}
        for key in ('tests_survived', 'pass_count', 'fail_count', 'pass_rate', 'version'):
            value = getattr(instance, key, None)
            if value is not None:
                snapshot[key] = value
        return snapshot

    @staticmethod
    def _normalize_knowledge_tags(item: dict) -> dict[str, list[str]]:
        evidence_json = dict(item.get('evidence_json', {}))
        return {
            'applicable_event_tags': normalize_tags(
                item.get('applicable_event_tags')
                or evidence_json.get('normalized_event_tags')
                or evidence_json.get('event_tags')
                or []
            ),
            'applicable_technical_tags': normalize_tags(
                item.get('applicable_technical_tags')
                or evidence_json.get('technical_pattern_tags')
                or []
            ),
            'applicable_market_regimes': normalize_tags(
                item.get('applicable_market_regimes')
                or evidence_json.get('market_regime_tags')
                or evidence_json.get('market_regimes')
                or []
            ),
            'negative_match_tags': normalize_tags(
                item.get('negative_match_tags')
                or evidence_json.get('risk_pattern_tags')
                or []
            ),
        }

    @staticmethod
    def _coerce_status(value) -> KnowledgeStatus:
        if isinstance(value, KnowledgeStatus):
            return value
        return KnowledgeStatus(str(value))
