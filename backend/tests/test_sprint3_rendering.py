"""
Sprint 3 Tests -- Diagram-Type Detection, AST->DSL Compilers, and Kroki Rendering.

Covers:
  - Unit tests for MermaidCompiler (flowchart, sequence)
  - Unit tests for PlantUMLCompiler (erd, class)
  - Unit tests for GraphvizCompiler (architecture, state_machine)
  - Diagram-Type Detection & Renderer Selection rules
  - Kroki Client with mocked and error scenarios
  - RenderingService fallback mechanism
  - API endpoint: POST /api/diagrams/render
  - End-to-end pipeline: POST /api/diagrams/generate returns renderer, dsl_code, svg_content
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.compilers.mermaid_compiler import MermaidCompiler
from app.services.compilers.plantuml_compiler import PlantUMLCompiler
from app.services.compilers.graphviz_compiler import GraphvizCompiler
from app.services.compilers.erd_compiler import ErdCompiler
from app.services.compilers.nwdiag_compiler import NwdiagCompiler
from app.services.compilers import get_compiler
from app.services.scope_guard import scope_guard
from app.services.kroki_client import (
    KrokiClient,
    KrokiConnectionError,
    KrokiRenderError,
    KrokiTimeoutError,
)
from app.services.renderer_detector import renderer_detector
from app.services.rendering_service import RenderingService, rendering_service


client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Fixtures & Sample Payloads
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_flowchart_json():
    return {
        "diagram_type": "flowchart",
        "nodes": [
            {"id": "user", "label": "End User", "type": "actor"},
            {"id": "api_gateway", "label": "API Gateway", "type": "gateway"},
            {"id": "db", "label": "Postgres DB", "type": "database"},
        ],
        "edges": [
            {"id": "e1", "source": "user", "target": "api_gateway", "label": "requests", "type": "calls"},
            {"id": "e2", "source": "api_gateway", "target": "db", "label": "reads", "type": "sync"},
        ],
        "attributes": {
            "title": "Web Architecture",
            "description": "Simple request flow.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


@pytest.fixture
def sample_sequence_json():
    return {
        "diagram_type": "sequence",
        "nodes": [
            {"id": "client", "label": "Client App", "type": "client"},
            {"id": "auth_svc", "label": "Auth Service", "type": "service"},
        ],
        "edges": [
            {"id": "e1", "source": "client", "target": "auth_svc", "label": "POST /login", "type": "calls"},
            {"id": "e2", "source": "auth_svc", "target": "client", "label": "200 JWT Token", "type": "reply"},
        ],
        "attributes": {
            "title": "Auth Flow",
            "description": "Token exchange.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


@pytest.fixture
def sample_erd_json():
    return {
        "diagram_type": "erd",
        "nodes": [
            {"id": "users", "label": "Users", "type": "entity"},
            {"id": "orders", "label": "Orders", "type": "entity"},
        ],
        "edges": [
            {"id": "e1", "source": "users", "target": "orders", "label": "places", "type": "one_to_many"},
        ],
        "attributes": {
            "title": "E-Commerce Schema",
            "description": "User orders relation.",
            "allows_disconnected": False,
            "direction": "auto",
        },
    }


@pytest.fixture
def sample_class_json():
    return {
        "diagram_type": "class",
        "nodes": [
            {"id": "Vehicle", "label": "Vehicle", "type": "class"},
            {"id": "Car", "label": "Car", "type": "class"},
        ],
        "edges": [
            {"id": "e1", "source": "Car", "target": "Vehicle", "label": "extends", "type": "inherits"},
        ],
        "attributes": {
            "title": "Vehicle Hierarchy",
            "description": "OOP Class model.",
            "allows_disconnected": False,
            "direction": "TB",
        },
    }


@pytest.fixture
def sample_architecture_json():
    return {
        "diagram_type": "architecture",
        "nodes": [
            {"id": "web", "label": "Web App", "type": "service"},
            {"id": "cache", "label": "Redis Cache", "type": "cache"},
            {"id": "db", "label": "PostgreSQL", "type": "database"},
        ],
        "edges": [
            {"id": "e1", "source": "web", "target": "cache", "label": "reads", "type": "calls"},
            {"id": "e2", "source": "web", "target": "db", "label": "writes", "type": "calls"},
        ],
        "attributes": {
            "title": "Cloud Backend",
            "description": "Service with cache & DB.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


@pytest.fixture
def sample_state_machine_json():
    return {
        "diagram_type": "state_machine",
        "nodes": [
            {"id": "idle", "label": "Idle State", "type": "initial_state"},
            {"id": "processing", "label": "Processing", "type": "state"},
            {"id": "done", "label": "Completed", "type": "terminal_state"},
        ],
        "edges": [
            {"id": "e1", "source": "idle", "target": "processing", "label": "start", "type": "transition"},
            {"id": "e2", "source": "processing", "target": "done", "label": "finish", "type": "transition"},
        ],
        "attributes": {
            "title": "Job Lifecycle",
            "description": "State transition model.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


# ---------------------------------------------------------------------------
# 1. Compiler Unit Tests
# ---------------------------------------------------------------------------


class TestMermaidCompiler:
    def test_flowchart_compilation(self, sample_flowchart_json):
        compiler = MermaidCompiler()
        dsl = compiler.compile(sample_flowchart_json)

        assert "flowchart LR" in dsl
        assert 'user(["End User"])' in dsl
        assert 'db[("Postgres DB")]' in dsl
        assert 'user -->|"requests"| api_gateway' in dsl

    def test_sequence_compilation(self, sample_sequence_json):
        compiler = MermaidCompiler()
        dsl = compiler.compile(sample_sequence_json)

        assert "sequenceDiagram" in dsl
        assert "autonumber" in dsl
        assert "actor client as Client App" in dsl
        assert "participant auth_svc as Auth Service" in dsl
        assert "client->>auth_svc: POST /login" in dsl
        assert "auth_svc-->>client: 200 JWT Token" in dsl


class TestPlantUMLCompiler:
    def test_erd_compilation(self, sample_erd_json):
        compiler = PlantUMLCompiler()
        dsl = compiler.compile(sample_erd_json)

        assert "@startuml" in dsl
        assert "!theme plain" in dsl
        assert "hide circle" in dsl
        assert "entity users {" in dsl
        assert "entity orders {" in dsl
        assert 'users ||--o{ orders : "places"' in dsl
        assert "@enduml" in dsl

    def test_class_compilation(self, sample_class_json):
        compiler = PlantUMLCompiler()
        dsl = compiler.compile(sample_class_json)

        assert "@startuml" in dsl
        assert "class Vehicle {" in dsl
        assert "class Car {" in dsl
        assert 'Car --|> Vehicle : "extends"' in dsl
        assert "@enduml" in dsl


class TestGraphvizCompiler:
    def test_architecture_compilation(self, sample_architecture_json):
        compiler = GraphvizCompiler()
        dsl = compiler.compile(sample_architecture_json)

        assert "digraph Architecture {" in dsl
        assert 'rankdir="LR"' in dsl
        assert 'shape="cylinder"' in dsl
        assert 'web -> cache' in dsl
        assert 'web -> db' in dsl

    def test_state_machine_compilation(self, sample_state_machine_json):
        compiler = GraphvizCompiler()
        dsl = compiler.compile(sample_state_machine_json)

        assert "digraph StateMachine {" in dsl
        assert "idle" in dsl
        assert "processing" in dsl
        assert "done" in dsl
        assert 'idle -> processing [label="start"]' in dsl


# ---------------------------------------------------------------------------
# 2. Diagram-Type Detection & Renderer Selection
# ---------------------------------------------------------------------------


class TestRendererDetector:
    def test_explicit_mappings(self):
        assert renderer_detector.get_renderer_for_type("flowchart") == "mermaid"
        assert renderer_detector.get_renderer_for_type("sequence") == "mermaid"
        assert renderer_detector.get_renderer_for_type("erd") == "erd"
        assert renderer_detector.get_renderer_for_type("network") == "nwdiag"
        assert renderer_detector.get_renderer_for_type("class") == "plantuml"
        assert renderer_detector.get_renderer_for_type("architecture") == "graphviz"
        assert renderer_detector.get_renderer_for_type("state_machine") == "graphviz"
        assert renderer_detector.get_renderer_for_type("generic") == "graphviz"

    def test_structural_heuristic_detection(self):
        # Implicit ERD
        erd_data = {
            "diagram_type": "generic",
            "nodes": [{"id": "u", "label": "User", "type": "entity"}],
            "edges": [{"id": "e", "source": "u", "target": "u", "label": "rel", "type": "has_many"}],
        }
        dtype, renderer = renderer_detector.select_renderer(erd_data)
        assert dtype == "erd"
        assert renderer == "erd"

        # Implicit State Machine
        sm_data = {
            "diagram_type": "",
            "nodes": [{"id": "s1", "label": "Init", "type": "state"}],
            "edges": [{"id": "e", "source": "s1", "target": "s1", "label": "ev", "type": "transitions_to"}],
        }
        dtype, renderer = renderer_detector.select_renderer(sm_data)
        assert dtype == "state_machine"
        assert renderer == "graphviz"


# ---------------------------------------------------------------------------
# 3. Kroki Client & Rendering Service
# ---------------------------------------------------------------------------


class TestKrokiClientAndService:
    def test_kroki_client_success(self):
        client = KrokiClient()
        fake_svg = '<svg xmlns="http://www.w3.org/2000/svg"><circle r="10"/></svg>'

        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = fake_svg
            mock_post.return_value = mock_resp

            result_svg = client.render_sync("mermaid", "flowchart LR\nA-->B")
            assert result_svg == fake_svg

    def test_kroki_client_error(self):
        client = KrokiClient()

        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.text = "Syntax error in diagram"
            mock_post.return_value = mock_resp

            with pytest.raises(KrokiRenderError):
                client.render_sync("mermaid", "bad syntax")

    def test_rendering_service_fallback_on_unreachable(self, sample_flowchart_json):
        mock_client = MagicMock()
        mock_client.render_sync.side_effect = KrokiConnectionError("Connection refused")

        svc = RenderingService(client=mock_client)
        result = svc.render_diagram(sample_flowchart_json)

        assert result.renderer == "mermaid"
        assert result.diagram_type == "flowchart"
        assert "flowchart LR" in result.dsl_code
        # Must produce fallback SVG without throwing unhandled exception
        assert "<svg" in result.svg_content
        assert "Web Architecture" in result.svg_content


# ---------------------------------------------------------------------------
# 4. API Endpoints
# ---------------------------------------------------------------------------


class TestDiagramAPIEndpoints:
    def test_post_render_endpoint(self, sample_flowchart_json):
        with patch.object(rendering_service.client, "render_sync") as mock_render:
            mock_render.return_value = '<svg id="kroki-rendered"></svg>'

            response = client.post(
                "/api/diagrams/render",
                json={"structured_json": sample_flowchart_json},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["renderer"] == "mermaid"
            assert data["diagram_type"] == "flowchart"
            assert "flowchart LR" in data["dsl_code"]
            assert data["svg_content"] == '<svg id="kroki-rendered"></svg>'
            assert data["dslCode"] == data["dsl_code"]
            assert data["svgContent"] == data["svg_content"]

    def test_generate_endpoint_includes_rendering_fields(self, sample_flowchart_json, monkeypatch):
        from app.services.generation_service import GenerationResult

        fake_gen_result = GenerationResult(
            request_id="11111111-2222-3333-4444-555555555555",
            status="validated",
            source="fresh",
            prompt="create a web architecture",
            preprocessed_prompt="create a web architecture",
            diagram_type="flowchart",
            structured_json=sample_flowchart_json,
            renderer="mermaid",
            dsl_code="flowchart LR\n    user --> api_gateway",
            svg_content='<svg id="test-gen"></svg>',
            spacy_enabled=False,
            candidates_count=0,
        )

        with patch("app.services.generation_service.generation_service.run_pipeline", return_value=fake_gen_result):
            response = client.post(
                "/api/diagrams/generate",
                json={"prompt": "create a web architecture"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["renderer"] == "mermaid"
            assert data["dsl_code"] == "flowchart LR\n    user --> api_gateway"
            assert data["svg_content"] == '<svg id="test-gen"></svg>'
            assert data["dslCode"] == data["dsl_code"]
            assert data["svgContent"] == data["svg_content"]


class TestNativeKrokiCompilers:
    def test_erd_compiler(self, sample_erd_json):
        compiler = ErdCompiler()
        dsl = compiler.compile(sample_erd_json)

        assert "[users]" in dsl
        assert "[orders]" in dsl
        assert "*id" in dsl
        assert "users 1--* orders" in dsl

    def test_nwdiag_compiler(self):
        sample_nw_json = {
            "diagram_type": "network",
            "nodes": [
                {"id": "gw", "label": "API Gateway", "type": "gateway"},
                {"id": "svc", "label": "User Service", "type": "service"},
                {"id": "db", "label": "User DB", "type": "database"},
            ],
            "edges": [
                {"id": "e1", "source": "gw", "target": "svc", "label": "routes", "type": "calls"},
            ],
        }
        compiler = NwdiagCompiler()
        dsl = compiler.compile(sample_nw_json)

        assert "nwdiag {" in dsl
        assert "network external_dmz {" in dsl
        assert "gw;" in dsl
        assert "network database_subnet {" in dsl
        assert "db;" in dsl


class TestScopeGuard:
    def test_out_of_scope_civil(self):
        res = scope_guard.check_scope("Design a 3-bedroom house floor plan with kitchen and bathroom")
        assert res.is_in_scope is False
        assert "civil" in res.detected_domain.lower() or "architectural" in res.detected_domain.lower()
        assert "out of scope" in res.rejection_reason.lower()

    def test_out_of_scope_mechanical(self):
        res = scope_guard.check_scope("Create a mechanical gearbox assembly with pistons and crankshaft")
        assert res.is_in_scope is False
        assert "mechanical" in res.detected_domain.lower()

    def test_out_of_scope_artwork(self):
        res = scope_guard.check_scope("Draw an oil painting landscape portrait of a sunset")
        assert res.is_in_scope is False

    def test_in_scope_cs_it(self):
        res = scope_guard.check_scope("Microservices e-commerce architecture with Redis and Postgres")
        assert res.is_in_scope is True

        res2 = scope_guard.check_scope("ER Diagram for school management system with student and course entities")
        assert res2.is_in_scope is True

