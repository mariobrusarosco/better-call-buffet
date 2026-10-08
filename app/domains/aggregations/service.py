import uuid
from datetime import datetime
from typing import Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.error_handlers import NotFoundError, ValidationError
from app.domains.aggregations.constants import MAX_AGGREGATION_DEPTH, MAX_NODES_PER_VIEW
from app.domains.aggregations.models import (
    AggregationNode,
    AggregationNodeCondition,
    AggregationView,
)
from app.domains.aggregations.repository import AggregationRepository
from app.domains.aggregations.schemas import (
    AggregationConditionCreate,
    AggregationConditionResponse,
    AggregationNodeCreate,
    AggregationNodeResponse,
    AggregationNodeResult,
    AggregationNodeUpdate,
    AggregationViewCreate,
    AggregationViewResponse,
    AggregationViewResult,
    AggregationViewUpdate,
)
from app.domains.tags.repository import TagRepository
from app.domains.transactions.constants import MovementType


class AggregationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AggregationRepository(db)
        self.tag_repository = TagRepository(db)

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip().casefold()

    def create_view(
        self, data: AggregationViewCreate, user_id: UUID
    ) -> AggregationView:
        normalized_name = self._normalize_name(data.name)
        if self.repository.get_view_by_normalized_name(normalized_name, user_id):
            raise ValidationError(
                message=f"Aggregation view '{data.name}' already exists",
                error_code="AGGREGATION_VIEW_ALREADY_EXISTS",
            )
        view = AggregationView(
            user_id=user_id,
            name=data.name,
            normalized_name=normalized_name,
            description=data.description,
        )
        self.db.add(view)
        self.db.commit()
        self.db.refresh(view)
        return view

    def list_views(self, user_id: UUID) -> List[AggregationView]:
        return self.repository.list_views(user_id)

    def get_view(self, view_id: UUID, user_id: UUID) -> AggregationView:
        view = self.repository.get_view(view_id, user_id)
        if not view:
            raise NotFoundError(
                message="Aggregation view not found",
                error_code="AGGREGATION_VIEW_NOT_FOUND",
            )
        return view

    def get_view_response(
        self, view_id: UUID, user_id: UUID
    ) -> AggregationViewResponse:
        view = self.get_view(view_id, user_id)
        return AggregationViewResponse(
            id=view.id,
            user_id=view.user_id,
            name=view.name,
            description=view.description,
            created_at=view.created_at,
            updated_at=view.updated_at,
            nodes=self._build_node_responses(view.nodes),
        )

    def update_view(
        self, view_id: UUID, data: AggregationViewUpdate, user_id: UUID
    ) -> AggregationView:
        view = self.get_view(view_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            normalized_name = self._normalize_name(update_data["name"])
            duplicate = self.repository.get_view_by_normalized_name(
                normalized_name, user_id
            )
            if duplicate and duplicate.id != view.id:
                raise ValidationError(
                    message=f"Aggregation view '{update_data['name']}' already exists",
                    error_code="AGGREGATION_VIEW_ALREADY_EXISTS",
                )
            view.name = update_data["name"]
            view.normalized_name = normalized_name
        if "description" in update_data:
            view.description = update_data["description"]
        self.db.commit()
        self.db.refresh(view)
        return view

    def delete_view(self, view_id: UUID, user_id: UUID) -> None:
        view = self.get_view(view_id, user_id)
        self.db.delete(view)
        self.db.commit()

    def create_node(
        self,
        view_id: UUID,
        data: AggregationNodeCreate,
        user_id: UUID,
    ) -> AggregationViewResponse:
        view = self.get_view(view_id, user_id)
        if len(view.nodes) >= MAX_NODES_PER_VIEW:
            raise ValidationError(
                message=f"A view may contain at most {MAX_NODES_PER_VIEW} nodes",
                error_code="AGGREGATION_NODE_LIMIT_EXCEEDED",
            )
        self._validate_condition_tags(data.conditions, user_id)

        node = AggregationNode(
            id=uuid.uuid4(),
            view_id=view.id,
            parent_id=data.parent_id,
            name=data.name,
            display_order=data.display_order,
            conditions=self._make_conditions(data.conditions),
        )
        view.nodes.append(node)
        try:
            self._validate_tree(view.nodes)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get_view_response(view_id, user_id)

    def update_node(
        self,
        view_id: UUID,
        node_id: UUID,
        data: AggregationNodeUpdate,
        user_id: UUID,
    ) -> AggregationViewResponse:
        view = self.get_view(view_id, user_id)
        nodes_by_id = {node.id: node for node in view.nodes}
        node = nodes_by_id.get(node_id)
        if not node:
            raise NotFoundError(
                message="Aggregation node not found",
                error_code="AGGREGATION_NODE_NOT_FOUND",
            )

        update_data = data.model_dump(exclude_unset=True)
        try:
            if "name" in update_data:
                node.name = update_data["name"]
            if "parent_id" in data.model_fields_set:
                node.parent_id = data.parent_id
            if "display_order" in update_data:
                node.display_order = update_data["display_order"]
            if data.conditions is not None:
                self._validate_condition_tags(data.conditions, user_id)
                node.conditions = self._make_conditions(data.conditions)

            self._validate_tree(view.nodes)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get_view_response(view_id, user_id)

    def delete_node(
        self, view_id: UUID, node_id: UUID, user_id: UUID
    ) -> AggregationViewResponse:
        view = self.get_view(view_id, user_id)
        node = next((item for item in view.nodes if item.id == node_id), None)
        if not node:
            raise NotFoundError(
                message="Aggregation node not found",
                error_code="AGGREGATION_NODE_NOT_FOUND",
            )
        self.db.delete(node)
        self.db.commit()
        return self.get_view_response(view_id, user_id)

    def get_results(
        self,
        view_id: UUID,
        user_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        movement_types: Optional[Sequence[MovementType]] = None,
    ) -> AggregationViewResult:
        view = self.get_view(view_id, user_id)
        movement_values = [
            value.value if isinstance(value, MovementType) else str(value)
            for value in (movement_types or [MovementType.EXPENSE])
        ]
        nodes_by_parent = self._nodes_by_parent(view.nodes)

        def build_result(
            node: AggregationNode,
            inherited: Dict[UUID, str],
        ) -> AggregationNodeResult:
            effective = dict(inherited)
            for condition in node.conditions:
                effective[condition.tag_id] = condition.operator
            total, count = self.repository.aggregate_transactions(
                user_id,
                effective,
                date_from,
                date_to,
                movement_values,
            )
            children = [
                build_result(child, effective)
                for child in nodes_by_parent.get(node.id, [])
            ]
            return AggregationNodeResult(
                node_id=node.id,
                name=node.name,
                total=total,
                transaction_count=count,
                children=children,
            )

        roots = [build_result(node, {}) for node in nodes_by_parent.get(None, [])]
        return AggregationViewResult(view_id=view.id, name=view.name, nodes=roots)

    def _validate_condition_tags(
        self, conditions: Sequence[AggregationConditionCreate], user_id: UUID
    ) -> None:
        tag_ids = [condition.tag_id for condition in conditions]
        if len(set(tag_ids)) != len(tag_ids):
            raise ValidationError(
                message="A node cannot contain multiple conditions for the same tag",
                error_code="DUPLICATE_AGGREGATION_CONDITION",
            )
        tags = self.tag_repository.get_tags_by_ids(tag_ids, user_id, active_only=True)
        if len(tags) != len(tag_ids):
            raise ValidationError(
                message="Every condition must reference an active tag owned by the user",
                error_code="INVALID_AGGREGATION_TAG",
            )

    @staticmethod
    def _make_conditions(
        conditions: Sequence[AggregationConditionCreate],
    ) -> List[AggregationNodeCondition]:
        return [
            AggregationNodeCondition(
                tag_id=condition.tag_id,
                operator=condition.operator.value,
            )
            for condition in conditions
        ]

    def _validate_tree(self, nodes: Sequence[AggregationNode]) -> None:
        if len(nodes) > MAX_NODES_PER_VIEW:
            raise ValidationError(
                message=f"A view may contain at most {MAX_NODES_PER_VIEW} nodes",
                error_code="AGGREGATION_NODE_LIMIT_EXCEEDED",
            )

        nodes_by_id = {node.id: node for node in nodes}
        sibling_names: Dict[Optional[UUID], set[str]] = {}
        for node in nodes:
            if node.parent_id is not None and node.parent_id not in nodes_by_id:
                raise ValidationError(
                    message="Parent node must belong to the same aggregation view",
                    error_code="INVALID_AGGREGATION_PARENT",
                )
            normalized_name = self._normalize_name(node.name)
            names = sibling_names.setdefault(node.parent_id, set())
            if normalized_name in names:
                raise ValidationError(
                    message="Sibling aggregation nodes must have unique names",
                    error_code="DUPLICATE_AGGREGATION_NODE_NAME",
                )
            names.add(normalized_name)

        effective_cache: Dict[UUID, Dict[UUID, str]] = {}
        depth_cache: Dict[UUID, int] = {}

        def visit(node_id: UUID, path: set[UUID]) -> None:
            if node_id in path:
                raise ValidationError(
                    message="Aggregation nodes cannot form a cycle",
                    error_code="AGGREGATION_NODE_CYCLE",
                )
            if node_id in depth_cache:
                return

            node = nodes_by_id[node_id]
            next_path = set(path)
            next_path.add(node_id)
            if node.parent_id is None:
                depth = 1
                effective: Dict[UUID, str] = {}
            else:
                visit(node.parent_id, next_path)
                depth = depth_cache[node.parent_id] + 1
                effective = dict(effective_cache[node.parent_id])

            if depth > MAX_AGGREGATION_DEPTH:
                raise ValidationError(
                    message=(
                        f"Aggregation depth cannot exceed {MAX_AGGREGATION_DEPTH}"
                    ),
                    error_code="AGGREGATION_DEPTH_EXCEEDED",
                )

            for condition in node.conditions:
                existing = effective.get(condition.tag_id)
                if existing is not None and existing != condition.operator:
                    raise ValidationError(
                        message="A node path cannot both include and exclude the same tag",
                        error_code="CONTRADICTORY_AGGREGATION_CONDITIONS",
                    )
                effective[condition.tag_id] = condition.operator

            depth_cache[node_id] = depth
            effective_cache[node_id] = effective

        for node_id in nodes_by_id:
            visit(node_id, set())

    @staticmethod
    def _nodes_by_parent(
        nodes: Sequence[AggregationNode],
    ) -> Dict[Optional[UUID], List[AggregationNode]]:
        result: Dict[Optional[UUID], List[AggregationNode]] = {}
        for node in nodes:
            result.setdefault(node.parent_id, []).append(node)
        for children in result.values():
            children.sort(key=lambda item: (item.display_order, item.name.casefold()))
        return result

    def _build_node_responses(
        self, nodes: Sequence[AggregationNode]
    ) -> List[AggregationNodeResponse]:
        nodes_by_parent = self._nodes_by_parent(nodes)

        def build(node: AggregationNode) -> AggregationNodeResponse:
            return AggregationNodeResponse(
                id=node.id,
                view_id=node.view_id,
                parent_id=node.parent_id,
                name=node.name,
                display_order=node.display_order,
                conditions=[
                    AggregationConditionResponse.model_validate(condition)
                    for condition in node.conditions
                ],
                children=[build(child) for child in nodes_by_parent.get(node.id, [])],
                created_at=node.created_at,
                updated_at=node.updated_at,
            )

        return [build(node) for node in nodes_by_parent.get(None, [])]
