from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from models.models import (
    Asset, Service, Technology, Endpoint, Finding, Scan, Target, Project, Relationship, utc_now
)


class AssetCorrelator:
    """
    Correlation engine that automatically discovers and updates connections between
    Assets, Services, Ports, Technologies, Endpoints, Certificates, Findings, Scans,
    Targets, and Projects using existing scan and profile data.
    """

    @staticmethod
    def correlate_project_assets(db: Session, project_id: int) -> int:
        """
        Builds/refreshes all relationships for a given project based on existing database records.
        Returns total number of active relationships.
        """
        now = datetime.now(timezone.utc)
        observed_rel_keys = set()

        assets = db.query(Asset).filter_by(project_id=project_id).all()
        targets = db.query(Target).filter_by(project_id=project_id).all()
        scans = db.query(Scan).filter_by(project_id=project_id).all()

        asset_map_by_name = {a.name.lower(): a for a in assets}

        # 1. Target -> Asset (Target -> Asset linkage)
        for t in targets:
            t_name = t.target.strip().lower()
            if t_name in asset_map_by_name:
                matched_asset = asset_map_by_name[t_name]
                key = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"target:{t.id}",
                    source_type="Target",
                    source_label=f"Target: {t.target}",
                    source_asset_id=None,
                    target_id=f"asset:{matched_asset.id}",
                    target_type="Asset",
                    target_label=matched_asset.name,
                    target_asset_id=matched_asset.id,
                    relationship_type="BELONGS_TO_TARGET",
                    discovery_source="Project Scope",
                    now=now
                )
                observed_rel_keys.add(key)

        # Iterate assets for domain hierarchy, IPs, services, tech, endpoints, certs, findings
        for asset in assets:
            a_name_lower = asset.name.lower()

            # 2. Domain -> Subdomain (Asset -> Asset hierarchy)
            # Find candidate parent domain (e.g., api.example.com -> example.com)
            parts = a_name_lower.split(".")
            if len(parts) > 2:
                parent_domain_name = ".".join(parts[1:])
                if parent_domain_name in asset_map_by_name:
                    parent_asset = asset_map_by_name[parent_domain_name]
                    key = AssetCorrelator._upsert_relationship(
                        db=db,
                        project_id=project_id,
                        source_id=f"asset:{parent_asset.id}",
                        source_type="Domain",
                        source_label=parent_asset.name,
                        source_asset_id=parent_asset.id,
                        target_id=f"asset:{asset.id}",
                        target_type="Subdomain",
                        target_label=asset.name,
                        target_asset_id=asset.id,
                        relationship_type="SUBDOMAIN_OF",
                        discovery_source="DNS / Subdomain Discovery",
                        now=now
                    )
                    observed_rel_keys.add(key)

            # 3. Subdomain -> IP (Asset -> IP Asset or IP entity)
            if asset.ip_address:
                ip_clean = asset.ip_address.strip()
                target_asset_id = None
                target_id_str = f"ip:{ip_clean}"
                target_label_str = ip_clean

                # Check if IP exists as an independent Asset record
                if ip_clean.lower() in asset_map_by_name:
                    ip_asset = asset_map_by_name[ip_clean.lower()]
                    target_asset_id = ip_asset.id
                    target_id_str = f"asset:{ip_asset.id}"
                    target_label_str = ip_asset.name

                key = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"asset:{asset.id}",
                    source_type=asset.asset_type,
                    source_label=asset.name,
                    source_asset_id=asset.id,
                    target_id=target_id_str,
                    target_type="IP",
                    target_label=target_label_str,
                    target_asset_id=target_asset_id,
                    relationship_type="RESOLVES_TO",
                    discovery_source="DNS Resolution",
                    now=now
                )
                observed_rel_keys.add(key)

            # 4. IP -> Port & Port -> Service
            for svc in asset.services:
                port_id_str = f"asset:{asset.id}:port:{svc.port}"
                port_label_str = f"Port {svc.port}/{svc.protocol.upper()}"
                
                # Asset / IP -> Port
                key_port = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"asset:{asset.id}",
                    source_type=asset.asset_type,
                    source_label=asset.name,
                    source_asset_id=asset.id,
                    target_id=port_id_str,
                    target_type="Port",
                    target_label=port_label_str,
                    target_asset_id=None,
                    relationship_type="HAS_PORT",
                    discovery_source=svc.discovery_source or "Port Scanner",
                    now=now
                )
                observed_rel_keys.add(key_port)

                # Port -> Service
                svc_name = (svc.service_name or "unknown").upper()
                svc_id_str = f"service:{svc.id}"
                svc_label_str = f"{svc_name} (v{svc.version})" if svc.version else svc_name

                key_svc = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=port_id_str,
                    source_type="Port",
                    source_label=port_label_str,
                    source_asset_id=None,
                    target_id=svc_id_str,
                    target_type="Service",
                    target_label=svc_label_str,
                    target_asset_id=None,
                    relationship_type="RUNS_SERVICE",
                    discovery_source=svc.discovery_source or "Port Scanner",
                    now=now
                )
                observed_rel_keys.add(key_svc)

            # 5. Asset -> Technology
            for tech in asset.technologies:
                tech_id_str = f"tech:{tech.id}"
                tech_label_str = f"{tech.name} {tech.version}".strip() if tech.version else tech.name

                key_tech = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"asset:{asset.id}",
                    source_type=asset.asset_type,
                    source_label=asset.name,
                    source_asset_id=asset.id,
                    target_id=tech_id_str,
                    target_type="Technology",
                    target_label=tech_label_str,
                    target_asset_id=None,
                    relationship_type="USES_TECH",
                    discovery_source=tech.detection_source or "Web Footprinting",
                    now=now
                )
                observed_rel_keys.add(key_tech)

            # 6. Asset -> Web Endpoint
            for ep in asset.endpoints:
                ep_id_str = f"endpoint:{ep.id}"
                ep_label_str = f"{ep.method} {ep.path}"

                key_ep = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"asset:{asset.id}",
                    source_type=asset.asset_type,
                    source_label=asset.name,
                    source_asset_id=asset.id,
                    target_id=ep_id_str,
                    target_type="Endpoint",
                    target_label=ep_label_str,
                    target_asset_id=None,
                    relationship_type="HAS_ENDPOINT",
                    discovery_source=ep.discovery_source or "Web Footprinting",
                    now=now
                )
                observed_rel_keys.add(key_ep)

            # 7. Asset -> Certificate
            if asset.cert_issuer:
                cert_id_str = f"cert:asset:{asset.id}"
                cert_label_str = f"TLS Cert ({asset.cert_issuer})"

                key_cert = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"asset:{asset.id}",
                    source_type=asset.asset_type,
                    source_label=asset.name,
                    source_asset_id=asset.id,
                    target_id=cert_id_str,
                    target_type="Certificate",
                    target_label=cert_label_str,
                    target_asset_id=None,
                    relationship_type="HAS_CERTIFICATE",
                    discovery_source="Reconnaissance / SSL Probe",
                    now=now
                )
                observed_rel_keys.add(key_cert)

            # 8. Asset -> Finding
            for finding in asset.findings:
                finding_id_str = f"finding:{finding.id}"
                finding_label_str = f"[{finding.severity}] {finding.title}"

                key_finding = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"asset:{asset.id}",
                    source_type=asset.asset_type,
                    source_label=asset.name,
                    source_asset_id=asset.id,
                    target_id=finding_id_str,
                    target_type="Finding",
                    target_label=finding_label_str,
                    target_asset_id=None,
                    relationship_type="HAS_FINDING",
                    discovery_source="Security Scanner",
                    now=now
                )
                observed_rel_keys.add(key_finding)

        # 9. Asset -> Scan (Asset linked to project scans)
        for s in scans:
            s_target_clean = s.target.strip().lower()
            matching_asset = asset_map_by_name.get(s_target_clean)
            if matching_asset:
                scan_id_str = f"scan:{s.id}"
                scan_label_str = f"Scan #{s.id}"

                key_scan = AssetCorrelator._upsert_relationship(
                    db=db,
                    project_id=project_id,
                    source_id=f"asset:{matching_asset.id}",
                    source_type=matching_asset.asset_type,
                    source_label=matching_asset.name,
                    source_asset_id=matching_asset.id,
                    target_id=scan_id_str,
                    target_type="Scan",
                    target_label=scan_label_str,
                    target_asset_id=None,
                    relationship_type="DISCOVERED_IN_SCAN",
                    source_scan_id=s.id,
                    discovery_source="Scan History",
                    now=now
                )
                observed_rel_keys.add(key_scan)

        # Purge stale relationships not present in current correlation pass
        all_db_rels = db.query(Relationship).filter_by(project_id=project_id).all()
        for rel in all_db_rels:
            rel_key = f"{rel.source_id}->{rel.relationship_type}->{rel.target_id}"
            if rel_key not in observed_rel_keys:
                db.delete(rel)
            else:
                rel.status = "active"

        db.commit()

        # Recalculate risk for project assets based on updated relationship context
        try:
            from services.risk_engine import RiskEngine
            for a in assets:
                RiskEngine.recalculate_and_update_asset_risk(db, a, trigger_reason="Graph Correlation Pass")
        except Exception as re:
            print(f"Correlation risk recalculation warning: {str(re)}")

        return len(observed_rel_keys)

    @staticmethod
    def correlate_scan_results(
        db: Session,
        project_id: int,
        target: str,
        scan_id: int,
        results: Dict[str, Any]
    ):
        """
        Invoked immediately after scan execution to run correlation and establish graph connections.
        """
        # Run project-level correlation to update graph model
        AssetCorrelator.correlate_project_assets(db, project_id)

    @staticmethod
    def get_asset_graph(db: Session, asset_id: int, max_depth: int = 2) -> Dict[str, Any]:
        """
        Retrieves graph nodes and edges centered around a given asset_id.
        """
        asset = db.get(Asset, asset_id)
        if not asset:
            return {"nodes": [], "edges": []}

        # Run correlation on asset's project to ensure fresh edges
        if asset.project_id:
            AssetCorrelator.correlate_project_assets(db, asset.project_id)

        nodes_dict = {}
        edges_list = []
        visited_nodes = set()

        root_node_id = f"asset:{asset.id}"
        nodes_dict[root_node_id] = {
            "id": root_node_id,
            "label": asset.name,
            "type": asset.asset_type,
            "is_asset": True,
            "asset_id": asset.id,
            "risk_score": asset.risk_score,
            "status": asset.status,
            "ip_address": asset.ip_address,
            "exposure": asset.exposure,
            "details": asset.to_dict()
        }

        # Fetch relevant relationships for this asset (both outgoing and incoming)
        queue = [(root_node_id, 0)]
        visited_nodes.add(root_node_id)

        while queue:
            curr_node_id, curr_depth = queue.pop(0)
            if curr_depth >= max_depth:
                continue

            # Query DB relationships where curr_node_id is source or target
            rels = db.query(Relationship).filter(
                Relationship.status == "active",
                (Relationship.source_id == curr_node_id) | (Relationship.target_id == curr_node_id)
            ).all()

            for r in rels:
                # Add edge
                edge_dict = r.to_dict()
                edges_list.append(edge_dict)

                # Determine neighbor node ID
                neighbor_id = r.target_id if r.source_id == curr_node_id else r.source_id
                neighbor_type = r.target_type if r.source_id == curr_node_id else r.source_type
                neighbor_label = r.target_label if r.source_id == curr_node_id else r.source_label
                neighbor_asset_id = r.target_asset_id if r.source_id == curr_node_id else r.source_asset_id

                if neighbor_id not in nodes_dict:
                    # Construct neighbor node payload
                    node_payload = {
                        "id": neighbor_id,
                        "label": neighbor_label,
                        "type": neighbor_type,
                        "is_asset": neighbor_asset_id is not None or neighbor_type in ["Domain", "Subdomain", "IP", "Website", "API"],
                        "asset_id": neighbor_asset_id,
                        "status": r.status
                    }
                    
                    # Enrich node details if it's a real asset
                    if neighbor_asset_id:
                        n_asset = db.get(Asset, neighbor_asset_id)
                        if n_asset:
                            node_payload["risk_score"] = n_asset.risk_score
                            node_payload["exposure"] = n_asset.exposure
                            node_payload["ip_address"] = n_asset.ip_address
                            node_payload["details"] = n_asset.to_dict()

                    nodes_dict[neighbor_id] = node_payload

                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    queue.append((neighbor_id, curr_depth + 1))

        # Deduplicate edges
        unique_edges = []
        seen_edge_ids = set()
        for e in edges_list:
            if e["id"] not in seen_edge_ids:
                seen_edge_ids.add(e["id"])
                unique_edges.append(e)

        return {
            "root_asset_id": asset_id,
            "root_node_id": root_node_id,
            "nodes": list(nodes_dict.values()),
            "edges": unique_edges
        }

    @staticmethod
    def get_project_graph(db: Session, project_id: int) -> Dict[str, Any]:
        """
        Retrieves project-wide relationship graph topology for active targets.
        """
        # Ensure fresh correlation pass
        AssetCorrelator.correlate_project_assets(db, project_id)

        project = db.get(Project, project_id)
        if not project:
            return {"nodes": [], "edges": []}

        # Query active targets for this project
        active_targets = db.query(Target).filter_by(project_id=project_id).all()
        active_target_strings = [t.target.strip().lower() for t in active_targets]

        nodes_dict = {}
        # Root Project Node
        proj_node_id = f"project:{project.id}"
        nodes_dict[proj_node_id] = {
            "id": proj_node_id,
            "label": f"Project: {project.name}",
            "type": "Project",
            "is_asset": False,
            "project_id": project.id,
            "details": project.to_dict()
        }

        # Query ONLY active project relationships
        rels = db.query(Relationship).filter_by(project_id=project_id, status="active").all()
        edges_list = [r.to_dict() for r in rels]

        # Filter assets to those matching active target scope
        assets = db.query(Asset).filter_by(project_id=project_id).all()
        for a in assets:
            a_name_lower = a.name.lower()
            matches_active = False
            if not active_target_strings:
                matches_active = True
            else:
                for t_str in active_target_strings:
                    t_clean = t_str.replace("https://", "").replace("http://", "").split("/")[0]
                    if a_name_lower == t_clean or a_name_lower.endswith("." + t_clean) or t_clean.endswith("." + a_name_lower):
                        matches_active = True
                        break
            if matches_active:
                a_node_id = f"asset:{a.id}"
                nodes_dict[a_node_id] = {
                    "id": a_node_id,
                    "label": a.name,
                    "type": a.asset_type,
                    "is_asset": True,
                    "asset_id": a.id,
                    "risk_score": a.risk_score,
                    "ip_address": a.ip_address,
                    "exposure": a.exposure,
                    "details": a.to_dict()
                }

        # Add target & non-asset nodes from active relationships
        for r in rels:
            for n_id, n_type, n_label, n_asset_id in [
                (r.source_id, r.source_type, r.source_label, r.source_asset_id),
                (r.target_id, r.target_type, r.target_label, r.target_asset_id)
            ]:
                if n_id not in nodes_dict:
                    nodes_dict[n_id] = {
                        "id": n_id,
                        "label": n_label,
                        "type": n_type,
                        "is_asset": n_asset_id is not None,
                        "asset_id": n_asset_id,
                        "status": r.status
                    }

        return {
            "project_id": project_id,
            "nodes": list(nodes_dict.values()),
            "edges": edges_list
        }

    @staticmethod
    def _upsert_relationship(
        db: Session,
        project_id: int,
        source_id: str,
        source_type: str,
        source_label: str,
        source_asset_id: Optional[int],
        target_id: str,
        target_type: str,
        target_label: str,
        target_asset_id: Optional[int],
        relationship_type: str,
        discovery_source: str,
        now: datetime,
        source_scan_id: Optional[int] = None,
        confidence: float = 1.0
    ) -> str:
        """
        Creates or updates a Relationship record without duplicates.
        Returns unique string key for observation tracking.
        """
        rel_key = f"{source_id}->{relationship_type}->{target_id}"

        existing = db.query(Relationship).filter(
            Relationship.project_id == project_id,
            Relationship.source_id == source_id,
            Relationship.target_id == target_id,
            Relationship.relationship_type == relationship_type
        ).first()

        if existing:
            existing.status = "active"
            existing.last_seen = now
            existing.confidence = confidence
            if source_label:
                existing.source_label = source_label
            if target_label:
                existing.target_label = target_label
            if discovery_source:
                existing.discovery_source = discovery_source
            if source_scan_id:
                existing.source_scan_id = source_scan_id
        else:
            rel = Relationship(
                project_id=project_id,
                source_id=source_id,
                source_type=source_type,
                source_label=source_label,
                source_asset_id=source_asset_id,
                target_id=target_id,
                target_type=target_type,
                target_label=target_label,
                target_asset_id=target_asset_id,
                relationship_type=relationship_type,
                confidence=confidence,
                source_scan_id=source_scan_id,
                discovery_source=discovery_source,
                status="active",
                first_seen=now,
                last_seen=now
            )
            db.add(rel)

        return rel_key
