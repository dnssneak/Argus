from flask import Blueprint, jsonify, request
from db.database import SessionLocal
from models.models import Project, Asset, Service, Technology, Finding, Scan, Relationship
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
        data["outgoing_relationships"] = [r.to_dict() for r in asset.outgoing_relationships]
        data["incoming_relationships"] = [r.to_dict() for r in asset.incoming_relationships]

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
