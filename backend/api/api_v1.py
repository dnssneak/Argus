# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, request
from db.database import SessionLocal
from models.models import Project, Asset, Service, Technology, Finding, Scan, Relationship, Endpoint, AssetHistory, AssetNote
from models.schemas import ProjectCreate, AssetCreate, FindingCreate

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


# Helper for DB session management in Flask routes
def get_db():
    return SessionLocal()


from services.project_service import ProjectService


# --- PROJECTS API ---

@api_bp.route("/projects", methods=["GET"])
def list_projects():
    db = get_db()
    try:
        search = request.args.get("search")
        status = request.args.get("status")
        owner_id = request.args.get("owner_id", "local-user")

        projects = ProjectService.list_projects(db, owner_id=owner_id, search=search, status=status)
        return jsonify({"success": True, "count": len(projects), "projects": [p.to_dict() for p in projects]})
    finally:
        db.close()


@api_bp.route("/projects", methods=["POST"])
def create_project():
    db = get_db()
    try:
        data = request.get_json() or {}
        name = data.get("name")
        description = data.get("description")
        status = data.get("status", "ACTIVE")
        owner_id = data.get("owner_id", "local-user")

        project = ProjectService.create_project(
            db=db,
            name=name,
            description=description,
            status=status,
            owner_id=owner_id
        )
        return jsonify({"success": True, "project": project.to_dict()}), 201
    except ValueError as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    db = get_db()
    try:
        project = ProjectService.get_project(db, project_id)
        if not project:
            return jsonify({"success": False, "error": "Project not found"}), 404

        data = project.to_dict()
        data["targets"] = [t.to_dict() for t in project.targets]
        data["assets"] = [a.to_dict() for a in project.assets]
        data["scans"] = [s.to_dict() for s in project.scans]
        return jsonify({"success": True, "project": data})
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    db = get_db()
    try:
        data = request.get_json() or {}
        project = ProjectService.update_project(
            db=db,
            project_id=project_id,
            name=data.get("name"),
            description=data.get("description"),
            status=data.get("status")
        )
        return jsonify({"success": True, "project": project.to_dict()})
    except ValueError as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/archive", methods=["POST"])
def archive_project(project_id):
    db = get_db()
    try:
        project = ProjectService.archive_project(db, project_id)
        return jsonify({"success": True, "project": project.to_dict(), "message": f"Project '{project.name}' archived."})
    except ValueError as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    db = get_db()
    try:
        force = request.args.get("force", "").lower() == "true"
        success, message, counts = ProjectService.delete_project(db, project_id, force=force)

        if not success:
            return jsonify({
                "success": False,
                "error": message,
                "delete_protection": True,
                "counts": counts
            }), 400

        return jsonify({"success": True, "message": message})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/targets", methods=["POST"])
def add_project_target(project_id):
    db = get_db()
    try:
        data = request.get_json() or {}
        target_str = data.get("target")
        target_type = data.get("target_type")

        target = ProjectService.add_target(db, project_id, target_str=target_str, target_type=target_type)
        return jsonify({"success": True, "target": target.to_dict()}), 201
    except ValueError as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/dashboard", methods=["GET"])
def get_project_dashboard_api(project_id):
    db = get_db()
    try:
        dashboard_data = ProjectService.get_project_dashboard(db, project_id)
        return jsonify({"success": True, "data": dashboard_data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    finally:
        db.close()


# --- ASSETS API ---

@api_bp.route("/assets", methods=["GET"])
def list_assets():
    db = get_db()
    try:
        project_id = request.args.get("project_id", type=int)
        asset_type = request.args.get("type")
        search = request.args.get("search")
        min_risk = request.args.get("min_risk", type=int)

        query = db.query(Asset)

        if project_id:
            query = query.filter(Asset.project_id == project_id)
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        if min_risk is not None:
            query = query.filter(Asset.risk_score >= min_risk)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Asset.name.like(search_pattern)) | 
                (Asset.ip_address.like(search_pattern)) | 
                (Asset.domain.like(search_pattern))
            )

        assets = query.order_by(Asset.risk_score.desc(), Asset.last_seen.desc()).all()
        return jsonify({"success": True, "count": len(assets), "assets": [a.to_dict() for a in assets]})
    finally:
        db.close()


@api_bp.route("/assets", methods=["POST"])
def create_asset():
    db = get_db()
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        project_id = data.get("project_id")
        asset_type = data.get("asset_type", "Domain")
        ip_address = data.get("ip_address")
        domain = data.get("domain")
        risk_score = data.get("risk_score", 0)

        if not name:
            return jsonify({"success": False, "error": "Asset name is required"}), 400

        # If project_id not provided, assign to default project
        if not project_id:
            default_proj = db.query(Project).filter_by(name="Default Project").first()
            if not default_proj:
                default_proj = Project(name="Default Project", description="Default security project")
                db.add(default_proj)
                db.commit()
                db.refresh(default_proj)
            project_id = default_proj.id

        # Deduplicate asset within project
        existing = db.query(Asset).filter_by(project_id=project_id, name=name).first()
        if existing:
            # Update last_seen
            existing.risk_score = max(existing.risk_score, risk_score)
            if ip_address:
                existing.ip_address = ip_address
            if domain:
                existing.domain = domain
            db.commit()
            db.refresh(existing)
            return jsonify({"success": True, "asset": existing.to_dict(), "message": "Asset updated"}), 200

        asset = Asset(
            project_id=project_id,
            name=name,
            asset_type=asset_type,
            ip_address=ip_address,
            domain=domain,
            risk_score=risk_score
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        return jsonify({"success": True, "asset": asset.to_dict()}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


def compute_risk_factors(asset):
    factors = []
    if asset.exposure == "Internet-Facing":
        factors.append("Internet-facing endpoint exposure")
    if asset.risk_score >= 80:
        factors.append("Critical risk priority threshold exceeded")
    
    # Open services
    if asset.services:
        factors.append(f"{len(asset.services)} open network services detected")
        for s in asset.services:
            if s.port in [22, 23, 21, 3389]:
                factors.append(f"Exposed management service: {s.service_name} ({s.port}/{s.protocol})")
                
    # Security findings
    if asset.findings:
        criticals = sum(1 for f in asset.findings if f.severity.lower() == "critical")
        highs = sum(1 for f in asset.findings if f.severity.lower() == "high")
        if criticals:
            factors.append(f"{criticals} unresolved Critical vulnerabilities")
        if highs:
            factors.append(f"{highs} unresolved High vulnerabilities")
            
    if not factors:
        factors.append("Default security baseline risk criteria")
    return factors


@api_bp.route("/assets/<int:asset_id>", methods=["GET"])
def get_asset_detail(asset_id):
    db = get_db()
    try:
        asset = db.get(Asset, asset_id)
        if not asset:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        data = asset.to_dict()
        data["services"] = [s.to_dict() for s in asset.services]
        data["technologies"] = [t.to_dict() for t in asset.technologies]
        data["findings"] = [f.to_dict() for f in asset.findings]
        data["endpoints"] = [e.to_dict() for e in asset.endpoints]
        data["history"] = sorted([h.to_dict() for h in asset.history], key=lambda x: x["created_at"] or "", reverse=True)
        data["notes"] = sorted([n.to_dict() for n in asset.notes], key=lambda x: x["created_at"] or "", reverse=True)
        data["outgoing_relationships"] = [r.to_dict() for r in asset.outgoing_relationships]
        data["incoming_relationships"] = [r.to_dict() for r in asset.incoming_relationships]
        data["risk_factors"] = compute_risk_factors(asset)

        return jsonify({"success": True, "asset": data})
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>", methods=["DELETE"])
def delete_asset(asset_id):
    db = get_db()
    try:
        asset = db.get(Asset, asset_id)
        if not asset:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        db.delete(asset)
        db.commit()
        return jsonify({"success": True, "message": "Asset deleted successfully"})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>/notes", methods=["POST"])
def add_asset_note(asset_id):
    db = get_db()
    try:
        data = request.get_json() or {}
        content = data.get("content", "").strip()
        author = data.get("author", "Analyst").strip() or "Analyst"

        if not content:
            return jsonify({"success": False, "error": "Content is required"}), 400

        asset = db.get(Asset, asset_id)
        if not asset:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        note = AssetNote(asset_id=asset_id, author=author, content=content)
        db.add(note)

        # Add to asset history
        history_event = AssetHistory(
            asset_id=asset_id,
            event_name="Analyst Note Added",
            event_details=f"Note by {author}: '{content[:50]}'"
        )
        db.add(history_event)

        db.commit()
        db.refresh(note)

        return jsonify({"success": True, "note": note.to_dict()}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>/tags", methods=["POST"])
def update_asset_tags(asset_id):
    db = get_db()
    try:
        data = request.get_json() or {}
        tags_list = data.get("tags", [])
        tags_str = ",".join([t.strip() for t in tags_list if t.strip()])

        asset = db.get(Asset, asset_id)
        if not asset:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        old_tags = asset.tags or ""
        asset.tags = tags_str

        # Add history entry
        history_event = AssetHistory(
            asset_id=asset_id,
            event_name="Asset Tags Updated",
            event_details=f"Updated tags from '{old_tags}' to '{tags_str}'"
        )
        db.add(history_event)

        db.commit()
        return jsonify({"success": True, "tags": [t.strip() for t in tags_str.split(",") if t.strip()]})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>/scan", methods=["POST"])
def scan_single_asset(asset_id):
    db = get_db()
    try:
        asset = db.get(Asset, asset_id)
        if not asset:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        from recon import TargetRecon
        from scanner import NetworkScanner
        from fingerprint import WebsiteFingerprinter

        # Add Scan History Start Event
        db.add(AssetHistory(
            asset_id=asset_id,
            event_name="On-Demand Scan Started",
            event_details="Initializing target reconnaissance and service discovery."
        ))
        db.commit()

        # 1. Target Recon
        recon = TargetRecon(asset.name)
        recon_data = recon.collect()
        if recon_data.get("resolved_ip"):
            asset.ip_address = recon_data.get("resolved_ip")

        # 2. Port scan
        scanner = NetworkScanner(asset.name, "full")
        scan_data = scanner.collect()

        if scan_data.get("error"):
            # Add to history and return scan execution failure
            db.add(AssetHistory(
                asset_id=asset_id,
                event_name="On-Demand Scan Failed",
                event_details=scan_data.get("error")
            ))
            db.commit()
            return jsonify({"success": False, "error": scan_data.get("error")}), 500

        # Clear existing services for this asset to avoid duplicates
        db.query(Service).filter_by(asset_id=asset_id).delete()

        for s in scan_data.get("services", []):
            srv = Service(
                asset_id=asset_id,
                port=s.get("port"),
                protocol=s.get("protocol").lower(),
                service_name=s.get("name"),
                version=s.get("version"),
                state="Open",
                discovery_source="Network Scan"
            )
            db.add(srv)

        # 3. Fingerprint if it's a website or runs on HTTP/HTTPS
        is_web = asset.asset_type.lower() in ["website", "api"] or any(s.get("port") in [80, 443, 8080, 8443] for s in scan_data.get("services", []))
        if is_web:
            if asset.asset_type.lower() not in ["website", "api"]:
                asset.asset_type = "Website"
            
            url = f"https://{asset.name}" if any(s.get("port") in [443, 8443] for s in scan_data.get("services", [])) else f"http://{asset.name}"
            printer = WebsiteFingerprinter(url)
            fp_data = printer.collect()
            
            asset.web_url = url
            asset.web_status_code = fp_data.get("http_status")
            asset.web_title = fp_data.get("title")
            asset.web_server = fp_data.get("server_header")
            
            # Clear and insert technologies
            db.query(Technology).filter_by(asset_id=asset_id).delete()
            for tech_name, tech_ver in fp_data.get("technologies", {}).items():
                tech = Technology(
                    asset_id=asset_id,
                    name=tech_name,
                    version=tech_ver or None,
                    category="Web Tech",
                    detection_source="Web Fingerprint",
                    confidence=90
                )
                db.add(tech)

        # Add to history
        db.add(AssetHistory(
            asset_id=asset_id,
            event_name="On-Demand Scan Completed",
            event_details=f"Discovered {len(scan_data.get('services', []))} ports, enriched web status indicators."
        ))

        # Exposure and source updates
        asset.exposure = "Internet-Facing" if asset.ip_address else "Internal"
        sources = set(asset.discovery_sources.split(",") if asset.discovery_sources else [])
        sources.add("HTTP Probe")
        sources.add("Port Scan")
        asset.discovery_sources = ",".join(filter(None, sources))

        # Adjust risk score based on open services and findings
        new_score = min(100, 20 + len(asset.services) * 10 + len(asset.findings) * 20)
        if asset.exposure == "Internet-Facing":
            new_score = min(100, new_score + 15)
        asset.risk_score = new_score

        db.commit()
        db.refresh(asset)

        return jsonify({"success": True, "message": "Scan completed successfully", "asset": asset.to_dict()})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()



# --- DASHBOARD STATS API ---

@api_bp.route("/stats", methods=["GET"])
def get_stats():
    db = get_db()
    try:
        project_id = request.args.get("project_id", type=int)

        asset_query = db.query(Asset)
        scan_query = db.query(Scan)
        finding_query = db.query(Finding)

        if project_id:
            asset_query = asset_query.filter(Asset.project_id == project_id)
            scan_query = scan_query.filter(Scan.project_id == project_id)
            finding_query = finding_query.join(Asset).filter(Asset.project_id == project_id)

        total_assets = asset_query.count()
        internet_facing = asset_query.filter(Asset.ip_address.isnot(None)).count()
        high_risk_assets = asset_query.filter(Asset.risk_score >= 70).count()

        findings = finding_query.all()
        critical_count = sum(1 for f in findings if f.severity.lower() == "critical")
        high_count = sum(1 for f in findings if f.severity.lower() == "high")
        medium_count = sum(1 for f in findings if f.severity.lower() == "medium")
        low_count = sum(1 for f in findings if f.severity.lower() == "low")
        info_count = sum(1 for f in findings if f.severity.lower() == "informational")

        active_scans = scan_query.filter(Scan.status.in_(["pending", "running"])).count()

        return jsonify({
            "success": True,
            "stats": {
                "total_assets": total_assets,
                "internet_facing": internet_facing,
                "high_risk_assets": high_risk_assets,
                "active_scans": active_scans,
                "findings_summary": {
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "low": low_count,
                    "informational": info_count,
                    "total": len(findings)
                }
            }
        })
    finally:
        db.close()
