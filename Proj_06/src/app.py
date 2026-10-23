"""Flask REST API adapter for the Feature Flag & Experiments service."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from flask import Flask, jsonify, request

from .exceptions import (
    FeatureFlagError,
    FlagAlreadyExistsError,
    FlagNotFoundError,
    InvalidVariantError,
    ValidationError,
)
from .models import (
    Operator,
    RolloutConfig,
    RolloutVariant,
    RuleCondition,
    TargetingRule,
    UserContext,
    Variant,
)
from .service import FeatureFlagService


def create_app(service: Optional[FeatureFlagService] = None) -> Flask:
    """Application factory for the Feature Flag REST API."""
    app = Flask(__name__)
    svc = service if service is not None else FeatureFlagService()

    # -------------------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------------------

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> Tuple[Any, int]:
        return jsonify({"status": "error", "type": "ValidationError", "message": str(error)}), 400

    @app.errorhandler(InvalidVariantError)
    def handle_invalid_variant(error: InvalidVariantError) -> Tuple[Any, int]:
        return jsonify({"status": "error", "type": "InvalidVariantError", "message": str(error)}), 400

    @app.errorhandler(FlagNotFoundError)
    def handle_not_found(error: FlagNotFoundError) -> Tuple[Any, int]:
        return jsonify({"status": "error", "type": "FlagNotFoundError", "message": str(error)}), 404

    @app.errorhandler(FlagAlreadyExistsError)
    def handle_conflict(error: FlagAlreadyExistsError) -> Tuple[Any, int]:
        return jsonify({"status": "error", "type": "FlagAlreadyExistsError", "message": str(error)}), 409

    # -------------------------------------------------------------------------
    # Payload Parsers
    # -------------------------------------------------------------------------

    def parse_variants(raw_variants: list) -> list[Variant]:
        if not isinstance(raw_variants, list):
            raise ValidationError("'variants' must be a list.")
        parsed = []
        for v in raw_variants:
            if isinstance(v, str):
                parsed.append(Variant(key=v))
            elif isinstance(v, dict) and "key" in v:
                parsed.append(Variant(key=v["key"], attachment=v.get("attachment")))
            else:
                raise ValidationError("Variant must be a string or object with 'key'.")
        return parsed

    def parse_rules(raw_rules: Optional[list]) -> Optional[list[TargetingRule]]:
        if raw_rules is None:
            return None
        if not isinstance(raw_rules, list):
            raise ValidationError("'rules' must be a list.")
        parsed_rules = []
        for r in raw_rules:
            if not isinstance(r, dict):
                raise ValidationError("Each rule must be an object.")
            conditions = []
            for c in r.get("conditions", []):
                conditions.append(
                    RuleCondition(
                        attribute=c["attribute"],
                        operator=Operator(c["operator"]),
                        value=c["value"],
                    )
                )
            parsed_rules.append(
                TargetingRule(
                    id=r.get("id", f"rule_{len(parsed_rules)+1}"),
                    conditions=conditions,
                    variant_key=r["variant_key"],
                    description=r.get("description", ""),
                )
            )
        return parsed_rules

    def parse_rollout(raw_rollout: Optional[dict]) -> Optional[RolloutConfig]:
        if raw_rollout is None:
            return None
        if not isinstance(raw_rollout, dict):
            raise ValidationError("'rollout' must be an object.")
        variants = []
        for rv in raw_rollout.get("variants", []):
            variants.append(
                RolloutVariant(
                    variant_key=rv["variant_key"],
                    weight=float(rv["weight"]),
                )
            )
        return RolloutConfig(variants=variants)

    # -------------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------------

    @app.route("/api/flags", methods=["POST"])
    def create_flag() -> Tuple[Any, int]:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        key = payload.get("key")
        name = payload.get("name")
        variants_raw = payload.get("variants")
        default_variant = payload.get("default_variant")
        description = payload.get("description", "")
        enabled = payload.get("enabled", True)

        if not key or not name or variants_raw is None or not default_variant:
            raise ValidationError("Payload missing required fields: key, name, variants, default_variant.")

        variants = parse_variants(variants_raw)
        rules = parse_rules(payload.get("rules"))
        rollout = parse_rollout(payload.get("rollout"))

        flag = svc.create_flag(
            key=key,
            name=name,
            variants=variants,
            default_variant=default_variant,
            description=description,
            enabled=enabled,
            rules=rules,
            rollout=rollout,
        )
        return jsonify({"status": "success", "data": flag.to_dict()}), 201

    @app.route("/api/flags", methods=["GET"])
    def list_flags() -> Tuple[Any, int]:
        flags = svc.list_flags()
        return jsonify({"status": "success", "count": len(flags), "data": [f.to_dict() for f in flags]}), 200

    @app.route("/api/flags/<flag_key>", methods=["GET"])
    def get_flag(flag_key: str) -> Tuple[Any, int]:
        flag = svc.get_flag(flag_key)
        return jsonify({"status": "success", "data": flag.to_dict()}), 200

    @app.route("/api/flags/<flag_key>", methods=["PUT"])
    def update_flag(flag_key: str) -> Tuple[Any, int]:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        name = payload.get("name")
        description = payload.get("description")
        enabled = payload.get("enabled")
        variants_raw = payload.get("variants")
        default_variant = payload.get("default_variant")

        variants = parse_variants(variants_raw) if variants_raw is not None else None
        rules = parse_rules(payload.get("rules")) if "rules" in payload else None
        rollout = parse_rollout(payload.get("rollout")) if "rollout" in payload else None

        updated = svc.update_flag(
            flag_key=flag_key,
            name=name,
            description=description,
            enabled=enabled,
            variants=variants,
            default_variant=default_variant,
            rules=rules,
            rollout=rollout,
        )
        return jsonify({"status": "success", "data": updated.to_dict()}), 200

    @app.route("/api/flags/<flag_key>", methods=["DELETE"])
    def delete_flag(flag_key: str) -> Tuple[Any, int]:
        svc.delete_flag(flag_key)
        return jsonify({"status": "success", "message": f"Flag '{flag_key}' deleted."}), 200

    @app.route("/api/flags/<flag_key>/evaluate", methods=["POST"])
    def evaluate_flag_endpoint(flag_key: str) -> Tuple[Any, int]:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        user_id = payload.get("user_id")
        if not user_id:
            raise ValidationError("Evaluation payload must include 'user_id'.")
        context = UserContext(user_id=str(user_id), attributes=payload.get("attributes", {}))
        result = svc.evaluate(flag_key, context)
        return jsonify({"status": "success", "data": result.to_dict()}), 200

    @app.route("/api/evaluate", methods=["POST"])
    def evaluate_all_endpoint() -> Tuple[Any, int]:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        user_id = payload.get("user_id")
        if not user_id:
            raise ValidationError("Evaluation payload must include 'user_id'.")
        context = UserContext(user_id=str(user_id), attributes=payload.get("attributes", {}))
        results = svc.evaluate_all(context)
        return (
            jsonify({"status": "success", "data": {k: v.to_dict() for k, v in results.items()}}),
            200,
        )

    @app.route("/api/stats", methods=["GET"])
    def get_stats() -> Tuple[Any, int]:
        return jsonify({"status": "success", "data": svc.get_stats()}), 200

    return app
