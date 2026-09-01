import unittest
from datetime import datetime, timezone
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import Base, engine, SessionLocal
from models.models import Project, Target, Asset, Service, Technology, Endpoint, Finding, Scan, Relationship
from services.asset_correlator import AssetCorrelator
from services.asset_processor import AssetProcessor


class TestAssetCorrelator(unittest.TestCase):

    def setUp(self):
        from db.database import init_db
        init_db()
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

        # Clean up existing test project
        test_proj = self.db.query(Project).filter_by(name="Test Correlation Project").first()
        if test_proj:
            self.db.delete(test_proj)
            self.db.commit()

        # Create test project & target
        self.project = Project(name="Test Correlation Project", description="Test campaign for correlation engine")
        self.db.add(self.project)
        self.db.commit()
        self.db.refresh(self.project)

        self.target = Target(project_id=self.project.id, target="example.com", target_type="Domain")
        self.db.add(self.target)
        self.db.commit()

    def tearDown(self):
        if hasattr(self, "project") and self.project:
            try:
                p_id = self.project.id
                self.db.query(Relationship).filter_by(project_id=p_id).delete()
                asset_ids = [a.id for a in self.db.query(Asset.id).filter_by(project_id=p_id).all()]
                if asset_ids:
                    self.db.query(AssetHistory).filter(AssetHistory.asset_id.in_(asset_ids)).delete(synchronize_session=False)
                    self.db.query(Finding).filter(Finding.asset_id.in_(asset_ids)).delete(synchronize_session=False)
                    self.db.query(Service).filter(Service.asset_id.in_(asset_ids)).delete(synchronize_session=False)
                    self.db.query(Technology).filter(Technology.asset_id.in_(asset_ids)).delete(synchronize_session=False)
                    self.db.query(Endpoint).filter(Endpoint.asset_id.in_(asset_ids)).delete(synchronize_session=False)
                    self.db.query(Asset).filter_by(project_id=p_id).delete()
                self.db.query(Scan).filter_by(project_id=p_id).delete()
                self.db.query(Target).filter_by(project_id=p_id).delete()
                self.db.query(Project).filter_by(id=p_id).delete()
                self.db.commit()
            except Exception:
                self.db.rollback()
        self.db.close()

    def test_correlation_pipeline(self):
        # 1. Process simulated scan results via AssetProcessor
        scan = Scan(
            project_id=self.project.id,
            target="example.com",
            scan_type="Full Scan",
            status="completed"
        )
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)

        simulated_results = {
            "subdomain": {
                "subdomains": [
                    {"subdomain": "example.com", "ip_address": "203.0.113.10"},
                    {"subdomain": "api.example.com", "ip_address": "203.0.113.10"},
                    {"subdomain": "dev.example.com", "ip_address": "203.0.113.20"}
                ]
            },
            "ports": {
                "target": "api.example.com",
                "open_ports": [443, 8080],
                "services": [
                    {"port": 443, "protocol": "tcp", "service": "https", "version": "TLSv1.3"},
                    {"port": 8080, "protocol": "tcp", "service": "http-proxy", "version": "Nginx"}
                ]
            },
            "recon": {
                "certificate_info": {
                    "issuer": "Let's Encrypt Authority X3",
                    "sans": ["example.com", "api.example.com"]
                }
            },
            "web": {
                "url": "https://api.example.com",
                "status_code": 200,
                "title": "API Gateway",
                "server": "Nginx 1.18.0",
                "technologies": [
                    {"name": "Nginx", "version": "1.18.0", "category": "Web Server"},
                    {"name": "Node.js", "version": "16.14.0", "category": "Backend Framework"}
                ],
                "endpoints": [
                    {"path": "/api/users", "method": "GET", "status_code": 200},
                    {"path": "/api/login", "method": "POST", "status_code": 200}
                ]
            }
        }

        # Run asset ingestion & correlation
        processed = AssetProcessor.process_scan_results(
            db=self.db,
            project_id=self.project.id,
            target="example.com",
            scan_id=scan.id,
            results=simulated_results
        )

        self.assertTrue(len(processed) >= 3)

        # 2. Verify Relationships were created in database
        relationships = self.db.query(Relationship).filter_by(project_id=self.project.id).all()
        self.assertTrue(len(relationships) > 0, "Relationships should be populated")

        rel_types = set(r.relationship_type for r in relationships)
        self.assertIn("SUBDOMAIN_OF", rel_types)
        self.assertIn("RESOLVES_TO", rel_types)
        self.assertIn("HAS_PORT", rel_types)
        self.assertIn("RUNS_SERVICE", rel_types)
        self.assertIn("USES_TECH", rel_types)
        self.assertIn("HAS_ENDPOINT", rel_types)
        self.assertIn("HAS_CERTIFICATE", rel_types)

        # 3. Test Graph Generation
        api_asset = self.db.query(Asset).filter_by(project_id=self.project.id, name="api.example.com").first()
        self.assertIsNotNone(api_asset)

        graph_payload = AssetCorrelator.get_asset_graph(self.db, asset_id=api_asset.id, max_depth=2)
        self.assertIsNotNone(graph_payload)
        self.assertEqual(graph_payload["root_asset_id"], api_asset.id)
        self.assertTrue(len(graph_payload["nodes"]) > 0)
        self.assertTrue(len(graph_payload["edges"]) > 0)

        # 4. Verify No Duplicate Assets were created
        all_assets = self.db.query(Asset).filter_by(project_id=self.project.id).all()
        asset_names = [a.name.lower() for a in all_assets]
        self.assertEqual(len(asset_names), len(set(asset_names)), "Asset names must be unique per project")


if __name__ == "__main__":
    unittest.main()
