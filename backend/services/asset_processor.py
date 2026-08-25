from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.models import Asset, Service, Technology, Endpoint, AssetHistory, Finding


class AssetProcessor:
    """
    Service responsible for ingesting Project scan results into the centralized Asset inventory.
    Resolves/deduplicates assets per project_id and target name, combines multi-service findings,
    preserves asset lifecycle (first_seen vs last_seen), and appends AssetHistory timeline events.
    """

    @staticmethod
    def process_scan_results(
        db: Session,
        project_id: int,
        target: str,
        scan_id: int,
        results: Dict[str, Any]
    ) -> List[Asset]:
        """
        Process scan results dictionary and resolve/create/update assets for project_id.
        """
        processed_assets = []
        now = datetime.utcnow()

        # Capture state snapshots of existing project assets prior to update for change detection
        from services.change_detector import ChangeDetector
        asset_snapshots = {}
        existing_assets = db.query(Asset).filter_by(project_id=project_id).all()
        for a in existing_assets:
            asset_snapshots[a.id] = ChangeDetector.snapshot_asset_state(a)

        # 1. Resolve primary target asset
        primary_asset = AssetProcessor._get_or_create_asset(
            db=db,
            project_id=project_id,
            name=target.strip(),
            source_name="Project Scan Initializer",
            scan_id=scan_id,
            now=now
        )
        processed_assets.append(primary_asset)

        # 2. Process Subdomain Discovery
        subdomain_data = results.get("subdomain", {})
        if isinstance(subdomain_data, dict):
            subdomains = subdomain_data.get("subdomains", [])
            for item in subdomains:
                sub_name = item.get("subdomain") if isinstance(item, dict) else str(item)
                if not sub_name or not sub_name.strip():
                    continue

                sub_name = sub_name.strip()
                resolved_ip = item.get("ip_address") if isinstance(item, dict) else None
                if resolved_ip in ("Not Resolved", "Unknown", "", None):
                    resolved_ip = None

                sub_asset = AssetProcessor._get_or_create_asset(
                    db=db,
                    project_id=project_id,
                    name=sub_name,
                    asset_type="Subdomain" if sub_name != target else "Domain",
                    source_name="Subdomain Discovery",
                    scan_id=scan_id,
                    now=now,
                    ip_address=resolved_ip
                )
                if sub_asset.id not in [a.id for a in processed_assets]:
                    processed_assets.append(sub_asset)

        # 3. Process Port Scanner Results
        ports_data = results.get("ports", {})
        if isinstance(ports_data, dict):
            port_target = ports_data.get("target") or target
            port_asset = AssetProcessor._get_or_create_asset(
                db=db,
                project_id=project_id,
                name=port_target.strip(),
                source_name="Port Scanner",
                scan_id=scan_id,
                now=now
            )
            
            services_list = ports_data.get("services", [])
            open_ports = ports_data.get("open_ports", [])
            
            # Record ports in Service model
            for s in services_list:
                if isinstance(s, dict):
                    port_num = s.get("port")
                    if not port_num:
                        continue
                    svc_name = s.get("service") or "unknown"
                    proto = s.get("protocol") or "tcp"
                    banner = s.get("banner")
                    version = s.get("version")
                    state = s.get("state") or "open"

                    # Check existing service
                    existing_svc = db.query(Service).filter_by(
                        asset_id=port_asset.id,
                        port=port_num,
                        protocol=proto
                    ).first()

                    if not existing_svc:
                        new_svc = Service(
                            asset_id=port_asset.id,
                            port=port_num,
                            protocol=proto,
                            service_name=svc_name,
                            banner=banner,
                            version=version,
                            state=state,
                            discovery_source="Port Scanner"
                        )
                        db.add(new_svc)
                    else:
                        existing_svc.service_name = svc_name
                        if banner:
                            existing_svc.banner = banner
                        if version:
                            existing_svc.version = version
                        existing_svc.state = state

            # Append Port Scan Timeline Event
            if open_ports:
                ports_str = ", ".join(str(p) for p in open_ports)
                AssetProcessor._add_history_event(
                    db=db,
                    asset_id=port_asset.id,
                    event_name="Port Scan Completed",
                    event_details=f"Discovered open ports: {ports_str} (Scan #{scan_id})"
                )

            if port_asset.id not in [a.id for a in processed_assets]:
                processed_assets.append(port_asset)

        # 4. Process Reconnaissance Results
        recon_data = results.get("recon", {})
        if isinstance(recon_data, dict) and recon_data:
            recon_asset = AssetProcessor._get_or_create_asset(
                db=db,
                project_id=project_id,
                name=target.strip(),
                source_name="Reconnaissance",
                scan_id=scan_id,
                now=now
            )

            # SSL/TLS Certificate Ingestion
            cert_info = recon_data.get("certificate_info") or recon_data.get("ssl")
            if isinstance(cert_info, dict):
                if cert_info.get("issuer"):
                    recon_asset.cert_issuer = str(cert_info.get("issuer"))
                if cert_info.get("sans"):
                    sans_val = cert_info.get("sans")
                    recon_asset.cert_sans = ", ".join(sans_val) if isinstance(sans_val, list) else str(sans_val)

            # Add History Event
            AssetProcessor._add_history_event(
                db=db,
                asset_id=recon_asset.id,
                event_name="Reconnaissance Completed",
                event_details=f"OSINT & Reconnaissance data updated (Scan #{scan_id})"
            )

            if recon_asset.id not in [a.id for a in processed_assets]:
                processed_assets.append(recon_asset)

        # 5. Process Web Footprinting Results
        web_data = results.get("web", {})
        if isinstance(web_data, dict) and web_data:
            web_raw_target = web_data.get("url") or target.strip()
            # Clean hostname (e.g. "https://api.example.com:8080/path" -> "api.example.com")
            web_target = web_raw_target.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0].strip()
            if not web_target:
                web_target = target.strip()

            web_asset = AssetProcessor._get_or_create_asset(
                db=db,
                project_id=project_id,
                name=web_target,
                source_name="Web Footprinting",
                scan_id=scan_id,
                now=now
            )

            # Web identity fields
            if web_data.get("url"):
                web_asset.web_url = web_data.get("url")
            if web_data.get("status_code"):
                web_asset.web_status_code = web_data.get("status_code")
            if web_data.get("title"):
                web_asset.web_title = web_data.get("title")
            if web_data.get("server"):
                web_asset.web_server = web_data.get("server")

            # Ingest Technologies
            techs = web_data.get("technologies", [])
            tech_names = []
            for t in techs:
                t_name = t.get("name") if isinstance(t, dict) else str(t)
                if not t_name:
                    continue
                tech_names.append(t_name)
                t_ver = t.get("version") if isinstance(t, dict) else None
                t_cat = t.get("category") if isinstance(t, dict) else "Web"

                existing_tech = db.query(Technology).filter_by(
                    asset_id=web_asset.id,
                    name=t_name
                ).first()

                if not existing_tech:
                    new_tech = Technology(
                        asset_id=web_asset.id,
                        name=t_name,
                        version=t_ver,
                        category=t_cat,
                        detection_source="Web Footprinting"
                    )
                    db.add(new_tech)
                elif t_ver:
                    existing_tech.version = t_ver

            # Ingest Endpoints
            endpoints = web_data.get("endpoints", [])
            for ep in endpoints:
                ep_path = ep.get("path") if isinstance(ep, dict) else str(ep)
                if not ep_path:
                    continue
                ep_method = ep.get("method", "GET") if isinstance(ep, dict) else "GET"
                ep_code = ep.get("status_code") if isinstance(ep, dict) else None

                existing_ep = db.query(Endpoint).filter_by(
                    asset_id=web_asset.id,
                    path=ep_path
                ).first()

                if not existing_ep:
                    new_ep = Endpoint(
                        asset_id=web_asset.id,
                        method=ep_method,
                        path=ep_path,
                        status_code=ep_code,
                        discovery_source="Web Footprinting"
                    )
                    db.add(new_ep)

            # Timeline Event for Web Footprinting
            tech_str = ", ".join(tech_names) if tech_names else "Web stack detected"
            AssetProcessor._add_history_event(
                db=db,
                asset_id=web_asset.id,
                event_name="Web Footprint Updated",
                event_details=f"Technologies: {tech_str} (Scan #{scan_id})"
            )

            if web_asset.id not in [a.id for a in processed_assets]:
                processed_assets.append(web_asset)

        # Change Detection comparison pass for updated assets
        for a in processed_assets:
            prev_snap = asset_snapshots.get(a.id)
            if prev_snap:
                diff = ChangeDetector.compare_asset_states(prev_snap, results)
                if diff.get("has_changes") and diff.get("changes"):
                    change_details = f"Scan #{scan_id} - {diff['summary']}\n" + "\n".join(diff["changes"])
                    AssetProcessor._add_history_event(
                        db=db,
                        asset_id=a.id,
                        event_name="Asset change detected",
                        event_details=change_details
                    )

        db.commit()

        # Execute relationship correlation pass to update graph topology
        try:
            from services.asset_correlator import AssetCorrelator
            AssetCorrelator.correlate_scan_results(db, project_id, target, scan_id, results)
        except Exception as ce:
            print(f"Asset correlation warning: {str(ce)}")

        # Recalculate risk score for processed assets using centralized RiskEngine
        try:
            from services.risk_engine import RiskEngine
            for a in processed_assets:
                RiskEngine.recalculate_and_update_asset_risk(db, a, trigger_reason=f"Scan #{scan_id} Ingestion")
        except Exception as re:
            print(f"Risk recalculation warning: {str(re)}")

        for a in processed_assets:
            db.refresh(a)

        return processed_assets

    @staticmethod
    def _get_or_create_asset(
        db: Session,
        project_id: int,
        name: str,
        source_name: str,
        scan_id: int,
        now: datetime,
        asset_type: str = "Domain",
        ip_address: Optional[str] = None
    ) -> Asset:
        """
        Deduplicates assets per project_id and name.
        If existing: preserves first_seen, updates last_seen, appends discovery_sources.
        If new: creates asset record, sets first_seen & last_seen, appends initial timeline event.
        """
        name_clean = name.strip()
        asset = db.query(Asset).filter(
            Asset.project_id == project_id,
            Asset.name.ilike(name_clean)
        ).first()

        if asset:
            # Asset exists - update last_seen and combine discovery sources
            asset.last_seen = now
            if ip_address and not asset.ip_address:
                asset.ip_address = ip_address
            
            # Combine discovery sources (comma-separated text)
            sources = [s.strip() for s in (asset.discovery_sources or "").split(",") if s.strip()]
            if source_name not in sources:
                sources.append(source_name)
                asset.discovery_sources = ", ".join(sources)

            # Add re-observation timeline event
            AssetProcessor._add_history_event(
                db=db,
                asset_id=asset.id,
                event_name="Asset Observed Again",
                event_details=f"Observed via {source_name} in Scan #{scan_id}"
            )
        else:
            # Create new asset
            asset = Asset(
                project_id=project_id,
                name=name_clean,
                asset_type=asset_type,
                ip_address=ip_address,
                first_seen=now,
                last_seen=now,
                exposure="Internet-Facing",
                discovery_sources=source_name,
                status="active"
            )
            db.add(asset)
            db.flush()  # Generate asset.id

            # Add initial creation timeline event
            AssetProcessor._add_history_event(
                db=db,
                asset_id=asset.id,
                event_name="Asset Discovered",
                event_details=f"Discovered via {source_name} in Scan #{scan_id}"
            )

        return asset

    @staticmethod
    def _add_history_event(db: Session, asset_id: int, event_name: str, event_details: str):
        """Append an event to the existing AssetHistory timeline."""
        event = AssetHistory(
            asset_id=asset_id,
            event_name=event_name,
            event_details=event_details,
            created_at=datetime.utcnow()
        )
        db.add(event)
