"""Pytest fixtures for Feature Flag service tests."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from Proj_06.src.app import create_app
from Proj_06.src.models import (
    Operator,
    RolloutConfig,
    RolloutVariant,
    RuleCondition,
    TargetingRule,
    Variant,
)
from Proj_06.src.service import FeatureFlagService


@pytest.fixture
def service() -> FeatureFlagService:
    """Fixture providing a fresh FeatureFlagService instance."""
    return FeatureFlagService()


@pytest.fixture
def app(service: FeatureFlagService) -> Flask:
    """Fixture providing a Flask app connected to the service."""
    flask_app = create_app(service)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Fixture providing a test client for REST endpoints."""
    return app.test_client()


@pytest.fixture
def sample_checkout_flag(service: FeatureFlagService):
    """Seed a representative checkout experiment flag with rules and rollout."""
    return service.create_flag(
        key="new_checkout_flow",
        name="New Checkout Flow A/B Test",
        description="Experiment testing 1-step vs 3-step checkout",
        enabled=True,
        variants=[
            Variant(key="control", attachment={"steps": 3, "theme": "classic"}),
            Variant(key="one_step", attachment={"steps": 1, "theme": "modern"}),
            Variant(key="express", attachment={"steps": 1, "express_pay": True}),
        ],
        default_variant="control",
        rules=[
            # VIP beta testers get express
            TargetingRule(
                id="vip_rule",
                description="VIP users receive express checkout",
                variant_key="express",
                conditions=[
                    RuleCondition(attribute="is_vip", operator=Operator.EQUALS, value=True),
                    RuleCondition(attribute="tier", operator=Operator.IN, value=["gold", "platinum"]),
                ],
            ),
            # Internal employees get one_step
            TargetingRule(
                id="internal_rule",
                description="Company employees get modern 1-step",
                variant_key="one_step",
                conditions=[
                    RuleCondition(attribute="email", operator=Operator.ENDS_WITH, value="@company.com"),
                ],
            ),
        ],
        rollout=RolloutConfig(
            variants=[
                RolloutVariant(variant_key="one_step", weight=25.0),
                RolloutVariant(variant_key="control", weight=75.0),
            ]
        ),
    )
