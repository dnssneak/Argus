# pyrefly: ignore [missing-import]
import os
from functools import wraps
from flask import Blueprint, jsonify, request, g, make_response, send_from_directory
import db.database as db_module
from models.models import User, Project, Target, Asset, Service, Technology, Finding, Scan, Relationship, Endpoint, AssetHistory, AssetNote, format_utc_iso
from models.schemas import ProjectCreate, AssetCreate, FindingCreate, UserSignup, UserLogin
from services.auth_service import AuthService
from services.project_service import ProjectService

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


# Helper for DB session management in Flask routes
def get_db():
    return db_module.SessionLocal()


def get_current_user_from_req(db):
    """Helper to extract user from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif request.cookies.get("argus_token"):
        token = request.cookies.get("argus_token")
    elif request.args.get("token"):
        token = request.args.get("token")

    if not token:
        return None

    return AuthService.verify_token(db, token)


def get_user_owner_id(db=None):
    """Helper to extract current authenticated user ID string or return None if unauthenticated."""
    if hasattr(g, "current_user") and g.current_user:
        return str(g.current_user.id)
    if db is not None:
        user = get_current_user_from_req(db)
        if user:
            return str(user.id)
    return None


def require_auth(f):
    """Middleware decorator enforcing authentication for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        db = get_db()
        try:
            user = get_current_user_from_req(db)
            if not user:
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
            g.current_user = user
            return f(*args, **kwargs)
        finally:
            db.close()
    return decorated_function


# --- AUTHENTICATION API ENDPOINTS ---

@api_bp.route("/auth/signup", methods=["POST"])
def auth_signup():
    """Register a new user account."""
    db = get_db()
    try:
        data = request.get_json() or {}
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        user = AuthService.register_user(
            db=db,
            name=name,
            email=email,
            password=password,
            confirm_password=confirm_password
        )

        token = AuthService.generate_token(user)
        response = make_response(jsonify({
            "success": True,
            "message": "Account created successfully.",
            "token": token,
            "user": user.to_dict()
        }), 201)

        response.set_cookie(
            "argus_token",
            token,
            httponly=True,
            samesite="Lax",
            max_age=86400,
            path="/"
        )
        return response

    except ValueError as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": f"Registration failed: {str(e)}"}), 500
    finally:
        db.close()


@api_bp.route("/auth/login", methods=["POST"])
def auth_login():
    """Authenticate user with email and password."""
    db = get_db()
    try:
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        user = AuthService.authenticate_user(db=db, email=email, password=password)
        token = AuthService.generate_token(user)

        response = make_response(jsonify({
            "success": True,
            "message": "Logged in successfully.",
            "token": token,
            "user": user.to_dict()
        }), 200)

        response.set_cookie(
            "argus_token",
            token,
            httponly=True,
            samesite="Lax",
            max_age=86400,
            path="/"
        )
        return response

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 401
    except Exception as e:
        return jsonify({"success": False, "error": f"Authentication failed: {str(e)}"}), 500
    finally:
        db.close()


@api_bp.route("/auth/logout", methods=["POST"])
def auth_logout():
    """Log out current user and invalidate cookie."""
    response = make_response(jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200)
    response.set_cookie("argus_token", "", expires=0, path="/")
    return response


@api_bp.route("/auth/me", methods=["GET"])
@require_auth
def auth_me():
    """Return currently authenticated user profile."""
    db = get_db()
    try:
        user = get_current_user_from_req(db)
        if not user:
            return jsonify({"success": False, "error": "Not authenticated."}), 401
        return jsonify({
            "success": True,
            "user": user.to_dict()
        })
    finally:
        db.close()


# --- PROJECTS API ---

@api_bp.route("/projects", methods=["GET"])
@require_auth
def list_projects():
    db = get_db()
    try:
        search = request.args.get("search")
        status = request.args.get("status")
        owner_id = get_user_owner_id(db)

        projects = ProjectService.list_projects(db, owner_id=owner_id, search=search, status=status)
        return jsonify({"success": True, "count": len(projects), "projects": [p.to_dict() for p in projects]})
    finally:
        db.close()


@api_bp.route("/projects", methods=["POST"])
@require_auth
def create_project():
    db = get_db()
    try:
        data = request.get_json() or {}
        name = data.get("name")
        description = data.get("description")
        status = data.get("status", "ACTIVE")
        owner_id = get_user_owner_id(db)

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
@require_auth
def get_project(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = ProjectService.get_project(db, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        data = project.to_dict()
        data["targets"] = [t.to_dict() for t in project.targets]
        data["assets"] = [a.to_dict() for a in project.assets]
        data["scans"] = [s.to_dict() for s in project.scans]
        return jsonify({"success": True, "project": data})
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>", methods=["PUT"])
@require_auth
def update_project(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        existing_proj = ProjectService.get_project(db, project_id)
        if not existing_proj or existing_proj.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

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
@require_auth
def archive_project(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        existing_proj = ProjectService.get_project(db, project_id)
        if not existing_proj or existing_proj.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        project = ProjectService.archive_project(db, project_id)
        action_str = "archived" if project.status == "ARCHIVED" else "activated"
        return jsonify({"success": True, "project": project.to_dict(), "message": f"Project '{project.name}' {action_str}."})
    except ValueError as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>", methods=["DELETE"])
@require_auth
def delete_project(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        existing_proj = ProjectService.get_project(db, project_id)
        if not existing_proj or existing_proj.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

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
@require_auth
def add_project_target(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        existing_proj = ProjectService.get_project(db, project_id)
        if not existing_proj or existing_proj.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

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
@require_auth
def get_project_dashboard_api(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        existing_proj = ProjectService.get_project(db, project_id)
        if not existing_proj or existing_proj.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        dashboard_data = ProjectService.get_project_dashboard(db, project_id)
        return jsonify({"success": True, "data": dashboard_data})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    finally:
        db.close()


# --- ASSETS API ---

@api_bp.route("/assets", methods=["GET"])
@require_auth
def list_assets():
    db = get_db()
    try:
        from services.risk_engine import RiskEngine

        owner_id = get_user_owner_id(db)
        project_id = request.args.get("project_id", type=int)
        asset_type = request.args.get("type")
        severity_filter = request.args.get("severity")
        search = request.args.get("search")
        min_risk = request.args.get("min_risk", type=int)
        max_risk = request.args.get("max_risk", type=int)
        sort_by = request.args.get("sort_by", "risk_score")  # risk_score, name, last_seen, first_seen
        sort_order = request.args.get("sort_order", "desc")  # desc, asc

        from sqlalchemy.orm import selectinload
        query = db.query(Asset).options(
            selectinload(Asset.services),
            selectinload(Asset.technologies),
            selectinload(Asset.findings),
            selectinload(Asset.endpoints)
        ).join(Project, Asset.project_id == Project.id).filter(Project.owner_id == owner_id)

        if project_id:
            query = query.filter(Asset.project_id == project_id)
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        if min_risk is not None:
            query = query.filter(Asset.risk_score >= min_risk)
        if max_risk is not None:
            query = query.filter(Asset.risk_score <= max_risk)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Asset.name.like(search_pattern)) | 
                (Asset.ip_address.like(search_pattern)) | 
                (Asset.domain.like(search_pattern))
            )

        # Apply database sorting
        if sort_by == "name":
            order_col = Asset.name.asc() if sort_order == "asc" else Asset.name.desc()
        elif sort_by == "last_seen":
            order_col = Asset.last_seen.asc() if sort_order == "asc" else Asset.last_seen.desc()
        elif sort_by == "first_seen":
            order_col = Asset.first_seen.asc() if sort_order == "asc" else Asset.first_seen.desc()
        else:
            order_col = Asset.risk_score.asc() if sort_order == "asc" else Asset.risk_score.desc()

        assets = query.order_by(order_col).all()

        formatted_assets = []
        for a in assets:
            a_dict = a.to_dict()
            sev = RiskEngine.get_severity_level(a.risk_score or 0)
            a_dict["severity"] = sev

            # Filter by severity tier if requested
            if severity_filter and severity_filter.upper() != "ALL" and sev.upper() != severity_filter.upper():
                continue

            formatted_assets.append(a_dict)

        return jsonify({"success": True, "count": len(formatted_assets), "assets": formatted_assets})
    finally:
        db.close()


@api_bp.route("/assets", methods=["POST"])
@require_auth
def create_asset():
    db = get_db()
    try:
        from services.risk_engine import RiskEngine

        owner_id = get_user_owner_id(db)
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        project_id = data.get("project_id")
        asset_type = data.get("asset_type", "Domain")
        ip_address = data.get("ip_address")
        domain = data.get("domain")
        risk_score = data.get("risk_score", 0)

        if not name:
            return jsonify({"success": False, "error": "Asset name is required"}), 400

        # If project_id not provided, assign to default project for current owner
        if not project_id:
            default_proj = db.query(Project).filter_by(owner_id=owner_id, name="Default Project").first()
            if not default_proj:
                default_proj = Project(name="Default Project", description="Default security project", owner_id=owner_id)
                db.add(default_proj)
                db.commit()
                db.refresh(default_proj)
            project_id = default_proj.id
        else:
            proj = db.get(Project, project_id)
            if not proj or proj.owner_id != owner_id:
                return jsonify({"success": False, "error": "Project not found"}), 404

        # Deduplicate asset within project
        existing = db.query(Asset).filter_by(project_id=project_id, name=name).first()
        if existing:
            if ip_address:
                existing.ip_address = ip_address
            if domain:
                existing.domain = domain
            db.commit()
            
            # Recalculate risk using RiskEngine
            RiskEngine.recalculate_and_update_asset_risk(db, existing, trigger_reason="Manual Asset Update")
            db.refresh(existing)
            out_dict = existing.to_dict()
            out_dict["severity"] = RiskEngine.get_severity_level(existing.risk_score)
            return jsonify({"success": True, "asset": out_dict, "message": "Asset updated"}), 200

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

        # Recalculate risk score via RiskEngine
        RiskEngine.recalculate_and_update_asset_risk(db, asset, trigger_reason="Manual Asset Registration")
        db.refresh(asset)

        out_dict = asset.to_dict()
        out_dict["severity"] = RiskEngine.get_severity_level(asset.risk_score)

        return jsonify({"success": True, "asset": out_dict}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>", methods=["GET"])
@require_auth
def get_asset_detail(asset_id):
    db = get_db()
    try:
        from services.risk_engine import RiskEngine

        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        # Compute full risk analysis
        risk_analysis = RiskEngine.calculate_asset_risk(db, asset)
        if asset.risk_score != risk_analysis["score"]:
            asset.risk_score = risk_analysis["score"]
            db.commit()

        data = asset.to_dict()
        data["risk_score"] = risk_analysis["score"]
        data["severity"] = risk_analysis["severity"]
        data["services"] = [s.to_dict() for s in asset.services]
        data["technologies"] = [t.to_dict() for t in asset.technologies]
        data["findings"] = [f.to_dict() for f in asset.findings]
        data["endpoints"] = [e.to_dict() for e in asset.endpoints]
        data["history"] = sorted([h.to_dict() for h in asset.history], key=lambda x: x["created_at"] or "", reverse=True)
        data["notes"] = sorted([n.to_dict() for n in asset.notes], key=lambda x: x["created_at"] or "", reverse=True)
        data["outgoing_relationships"] = [r.to_dict() for r in asset.outgoing_relationships]
        data["incoming_relationships"] = [r.to_dict() for r in asset.incoming_relationships]
        data["risk_factors"] = risk_analysis["summary_factors"]
        data["categorized_risk_factors"] = risk_analysis["contributing_factors"]
        data["risk_explanation"] = risk_analysis

        return jsonify({"success": True, "asset": data})
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>/graph", methods=["GET"])
@require_auth
def get_asset_relationship_graph(asset_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        max_depth = request.args.get("depth", default=2, type=int)
        from services.asset_correlator import AssetCorrelator
        graph_data = AssetCorrelator.get_asset_graph(db, asset_id=asset_id, max_depth=max_depth)
        return jsonify({"success": True, "graph": graph_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/graph", methods=["GET"])
@require_auth
def get_project_relationship_graph(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        from services.asset_correlator import AssetCorrelator
        graph_data = AssetCorrelator.get_project_graph(db, project_id=project_id)
        return jsonify({"success": True, "graph": graph_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/correlate", methods=["POST"])
@require_auth
def trigger_project_correlation(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        from services.asset_correlator import AssetCorrelator
        count = AssetCorrelator.correlate_project_assets(db, project_id=project_id)
        return jsonify({"success": True, "message": f"Correlation pass completed successfully. {count} active relationships established.", "relationship_count": count})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>", methods=["DELETE"])
@require_auth
def delete_asset(asset_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
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
@require_auth
def add_asset_note(asset_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        data = request.get_json() or {}
        content = data.get("content", "").strip()
        author = data.get("author", "Analyst").strip() or "Analyst"

        if not content:
            return jsonify({"success": False, "error": "Content is required"}), 400

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
@require_auth
def update_asset_tags(asset_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        data = request.get_json() or {}
        tags_list = data.get("tags", [])
        tags_str = ",".join([t.strip() for t in tags_list if t.strip()])

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


@api_bp.route("/findings", methods=["GET"])
@require_auth
def list_findings():
    db = get_db()
    try:
        from services.finding_correlator import FindingCorrelator

        owner_id = get_user_owner_id(db)
        project_id = request.args.get("project_id", type=int)
        asset_id = request.args.get("asset_id", type=int)
        severity = request.args.get("severity")
        priority = request.args.get("priority")
        status = request.args.get("status")
        lifecycle_status = request.args.get("lifecycle_status")
        search = request.args.get("search")

        findings = FindingCorrelator.get_prioritized_findings(
            db=db,
            project_id=project_id,
            asset_id=asset_id,
            severity=severity,
            priority=priority,
            status=status,
            lifecycle_status=lifecycle_status,
            search=search,
            owner_id=owner_id
        )

        return jsonify({"success": True, "count": len(findings), "findings": findings})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
@api_bp.route("/projects/<int:project_id>/findings/correlate", methods=["POST"])
@require_auth
def correlate_project_findings_api(project_id):
    db = get_db()
    try:
        from services.finding_correlator import FindingCorrelator
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        findings = FindingCorrelator.correlate_project_findings(db, project_id)
        return jsonify({
            "success": True,
            "message": f"Successfully correlated {len(findings)} security findings across project assets.",
            "count": len(findings)
        })
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/findings/<int:finding_id>", methods=["GET"])
@require_auth
def get_finding_detail(finding_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        finding = db.get(Finding, finding_id)
        if not finding or (finding.asset and finding.asset.project.owner_id != owner_id):
            return jsonify({"success": False, "error": "Finding not found"}), 404

        if not finding.recommendation or not finding.recommendation.strip():
            from services.finding_correlator import FindingCorrelator
            FindingCorrelator.correlate_and_prioritize_finding(db, finding)

        return jsonify({"success": True, "finding": finding.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>/findings", methods=["POST"])
@require_auth
def add_asset_finding(asset_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        data = request.get_json() or {}
        title = data.get("title", "").strip()
        severity = data.get("severity", "Informational").strip()
        cvss_score = data.get("risk_score", 0)
        description = data.get("description")
        evidence = data.get("evidence")
        recommendation = data.get("recommendation")
        cve_id = data.get("cve_id")
        port = data.get("port")
        service_name = data.get("service_name")
        technology = data.get("technology")
        endpoint = data.get("endpoint")

        if not title:
            return jsonify({"success": False, "error": "Finding title is required"}), 400

        parsed_cvss = float(cvss_score) if (cvss_score is not None and str(cvss_score).strip() != "") else None
        if parsed_cvss is not None and parsed_cvss > 10.0:
            parsed_cvss = round(parsed_cvss / 10.0, 1)

        finding = Finding(
            asset_id=asset_id,
            title=title,
            severity=severity,
            risk_score=int(parsed_cvss * 10) if parsed_cvss is not None else 20,
            cvss_score=parsed_cvss,
            description=description,
            evidence=evidence,
            recommendation=recommendation,
            cve_id=cve_id,
            port=port,
            service_name=service_name,
            technology=technology,
            endpoint=endpoint,
            status="open",
            lifecycle_status="NEW"
        )
        db.add(finding)
        db.commit()

        # Recalculate asset risk score using RiskEngine
        from services.risk_engine import RiskEngine
        RiskEngine.recalculate_and_update_asset_risk(db, asset, trigger_reason=f"New {severity} Finding Added")

        # Correlate and calculate contextual priority for finding
        from services.finding_correlator import FindingCorrelator
        FindingCorrelator.correlate_and_prioritize_finding(db, finding, asset)

        db.refresh(finding)
        return jsonify({"success": True, "finding": finding.to_dict()}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/findings/<int:finding_id>/status", methods=["PUT"])
@require_auth
def update_finding_status(finding_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        finding = db.get(Finding, finding_id)
        if not finding or (finding.asset and finding.asset.project.owner_id != owner_id):
            return jsonify({"success": False, "error": "Finding not found"}), 404

        data = request.get_json() or {}
        new_status = data.get("status", "open").lower()
        finding.status = new_status
        db.commit()

        # Recalculate asset risk & finding priority
        asset = db.get(Asset, finding.asset_id)
        if asset:
            from services.risk_engine import RiskEngine
            RiskEngine.recalculate_and_update_asset_risk(db, asset, trigger_reason=f"Finding Status set to {new_status}")

        from services.finding_correlator import FindingCorrelator
        FindingCorrelator.correlate_and_prioritize_finding(db, finding, asset)

        return jsonify({"success": True, "finding": finding.to_dict()})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()




@api_bp.route("/assets/<int:asset_id>/scan", methods=["POST"])
@require_auth
def scan_single_asset(asset_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
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

        db.commit()

        # Recalculate risk score via RiskEngine
        from services.risk_engine import RiskEngine
        RiskEngine.recalculate_and_update_asset_risk(db, asset, trigger_reason="On-Demand Scan Completed")

        db.refresh(asset)

        return jsonify({"success": True, "message": "Scan completed successfully", "asset": asset.to_dict()})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()



# --- DASHBOARD STATS API ---

@api_bp.route("/stats", methods=["GET"])
@require_auth
def get_stats():
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project_id = request.args.get("project_id", type=int)

        asset_query = db.query(Asset).join(Project, Asset.project_id == Project.id).filter(Project.owner_id == owner_id)
        scan_query = db.query(Scan).join(Project, Scan.project_id == Project.id).filter(Project.owner_id == owner_id)
        finding_query = db.query(Finding).join(Asset, Finding.asset_id == Asset.id).join(Project, Asset.project_id == Project.id).filter(Project.owner_id == owner_id)

        if project_id:
            asset_query = asset_query.filter(Asset.project_id == project_id)
            scan_query = scan_query.filter(Scan.project_id == project_id)
            finding_query = finding_query.filter(Asset.project_id == project_id)

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


# --- PROJECT-CENTRIC SCANS API ---

import json
from datetime import datetime, timezone

@api_bp.route("/projects/<int:project_id>/scans", methods=["GET"])
@require_auth
def list_project_scans(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        scans = db.query(Scan).filter_by(project_id=project_id).order_by(Scan.start_time.desc()).all()
        scan_list = []
        for s in scans:
            s_dict = s.to_dict()
            if s.results_summary:
                try:
                    s_dict["results_parsed"] = json.loads(s.results_summary)
                except Exception:
                    s_dict["results_parsed"] = {}
            else:
                s_dict["results_parsed"] = {}
            scan_list.append(s_dict)

        return jsonify({"success": True, "count": len(scan_list), "scans": scan_list})
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/scans/<int:scan_id>", methods=["GET"])
@api_bp.route("/scans/<int:scan_id>", methods=["GET"])
@require_auth
def get_project_scan_detail(scan_id, project_id=None):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        scan = db.get(Scan, scan_id)
        if not scan or scan.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Scan not found"}), 404
        if project_id and scan.project_id != project_id:
            return jsonify({"success": False, "error": "Scan not found"}), 404

        s_dict = scan.to_dict()
        if scan.results_summary:
            try:
                s_dict["results_parsed"] = json.loads(scan.results_summary)
            except Exception:
                s_dict["results_parsed"] = {}
        else:
            s_dict["results_parsed"] = {}

        return jsonify({"success": True, "scan": s_dict})
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/scans", methods=["POST"])
@require_auth
def execute_project_scan(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        data = request.get_json() or {}
        target_str = (data.get("target") or "").strip()
        capabilities = data.get("capabilities") or ["subdomain", "ports", "recon", "web"]
        config = data.get("config") or {}

        if not target_str:
            return jsonify({"success": False, "error": "Target is required for scanning"}), 400

        # Ensure target is registered in Project scope
        target_obj = db.query(Target).filter_by(project_id=project_id, target=target_str).first()
        if not target_obj:
            target_obj = ProjectService.add_target(db, project_id, target_str)

        # Create Scan database entry
        scan_types_str = ", ".join([c.capitalize() for c in capabilities])
        new_scan = Scan(
            project_id=project_id,
            target=target_str,
            scan_type=scan_types_str,
            status="running",
            progress=0,
            current_stage="Initializing selected capabilities",
            logs=f"Started scan for {target_str} with capabilities: {scan_types_str}\n"
        )
        db.add(new_scan)
        db.commit()
        db.refresh(new_scan)

        # Execute existing services sequentially based on selected capabilities
        results = {}
        stage_logs = []
        has_failure = False

        from subdomain import SubdomainFinder
        from scanner import NetworkScanner
        from recon import TargetRecon
        from fingerprint import WebsiteFingerprinter
        from web_security import WebSecurityEngine
        from web_intelligence import WebIntelligenceEngine

        if "subdomain" in capabilities:
            new_scan.current_stage = "Subdomain Discovery"
            new_scan.progress = 15
            db.commit()
            stage_logs.append("Executing Subdomain Discovery...")
            try:
                finder = SubdomainFinder(target_str)
                sub_res = finder.collect()
                results["subdomain"] = sub_res
                stage_logs.append("Subdomain Discovery completed.")
            except Exception as e:
                results["subdomain"] = {"error": str(e), "subdomains": []}
                stage_logs.append(f"Subdomain Discovery failed: {str(e)}")
                has_failure = True

        if "ports" in capabilities:
            new_scan.current_stage = "Port Scanning"
            new_scan.progress = 30
            db.commit()
            stage_logs.append("Executing Port Scan...")
            try:
                port_type = config.get("port_scan_type", "full")
                scanner = NetworkScanner(target_str, port_type)
                port_res = scanner.collect()
                results["ports"] = port_res
                stage_logs.append("Port Scan completed.")
            except Exception as e:
                results["ports"] = {"error": str(e), "open_ports": [], "services": []}
                stage_logs.append(f"Port Scan failed: {str(e)}")
                has_failure = True

        if "recon" in capabilities:
            new_scan.current_stage = "Reconnaissance"
            new_scan.progress = 50
            db.commit()
            stage_logs.append("Executing Reconnaissance...")
            try:
                recon_obj = TargetRecon(target_str)
                recon_res = recon_obj.collect()
                results["recon"] = recon_res
                stage_logs.append("Reconnaissance completed.")
            except Exception as e:
                results["recon"] = {"error": str(e)}
                stage_logs.append(f"Reconnaissance failed: {str(e)}")
                has_failure = True

        if "web" in capabilities:
            new_scan.current_stage = "Web Footprinting"
            new_scan.progress = 70
            db.commit()
            stage_logs.append("Executing Web Footprinting...")
            try:
                web_url = target_str if target_str.startswith("http://") or target_str.startswith("https://") else f"http://{target_str}"
                printer = WebsiteFingerprinter(web_url)
                web_res = printer.collect()
                results["web"] = web_res
                stage_logs.append("Web Footprinting completed.")
            except Exception as e:
                results["web"] = {"error": str(e)}
                stage_logs.append(f"Web Footprinting failed: {str(e)}")
                has_failure = True

        if "web_security" in capabilities or "nikto" in capabilities:
            new_scan.current_stage = "Web Security Engine"
            new_scan.progress = 85
            db.commit()
            stage_logs.append("Executing Web Security Engine (Headers, SSL/TLS, Cookies, CORS, Methods, Dirs & Nikto)...")
            try:
                sec_engine = WebSecurityEngine(target_str)
                sec_res = sec_engine.collect(include_nikto=True)
                results["web_security"] = sec_res
                stage_logs.append("Web Security Engine analysis (including Nikto scan) completed.")
            except Exception as e:
                results["web_security"] = {"error": str(e)}
                stage_logs.append(f"Web Security Engine analysis failed: {str(e)}")
                has_failure = True

        if "web_intelligence" in capabilities:
            new_scan.current_stage = "Web Intelligence Engine"
            new_scan.progress = 95
            db.commit()
            stage_logs.append("Executing Web Intelligence Engine (Scraping, OSINT, Wayback Archives, Documents & Email OSINT)...")
            try:
                intel_engine = WebIntelligenceEngine(target_str)
                intel_res = intel_engine.collect()
                results["web_intelligence"] = intel_res
                stage_logs.append("Web Intelligence Engine OSINT analysis completed successfully.")
            except Exception as e:
                results["web_intelligence"] = {"error": str(e)}
                stage_logs.append(f"Web Intelligence Engine OSINT analysis failed: {str(e)}")
                has_failure = True

        # Finalize scan execution record
        new_scan.status = "completed" if not has_failure else "failed"
        new_scan.progress = 100
        new_scan.current_stage = "Completed" if not has_failure else "Completed with errors"
        new_scan.logs = "\n".join(stage_logs)
        new_scan.results_summary = json.dumps(results)
        new_scan.end_time = datetime.now(timezone.utc)

        # Update target status
        target_obj.status = "scanned"
        db.commit()

        # Automatically resolve and ingest scan results into Asset Inventory
        try:
            from services.asset_processor import AssetProcessor
            AssetProcessor.process_scan_results(db, project_id, target_str, new_scan.id, results)
        except Exception as ae:
            print(f"Asset ingestion warning: {str(ae)}")

        # Log project activity
        ProjectService.log_activity(
            db,
            project_id,
            "Target Scanned",
            f"Executed pipeline scan ({scan_types_str}) against '{target_str}'"
        )

        scan_dict = new_scan.to_dict()
        scan_dict["results_parsed"] = results

        return jsonify({
            "success": True,
            "message": "Project scan completed successfully.",
            "scan": scan_dict
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/scans/<int:scan_id>/report", methods=["POST"])
@require_auth
def generate_project_scan_report(project_id, scan_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        scan = db.get(Scan, scan_id)
        if not scan or scan.project_id != project_id:
            return jsonify({"success": False, "error": "Scan record not found"}), 404

        data = request.get_json() or {}
        report_type = data.get("report_type", "html").lower()

        results = {}
        if scan.results_summary:
            try:
                results = json.loads(scan.results_summary)
            except Exception:
                results = {}

        from report import ReportGenerator
        from recon import SystemInfo

        sys_info = SystemInfo().collect()
        recon_data = results.get("recon")
        scan_data = results.get("ports")
        fingerprint_data = results.get("web")
        subdomain_data = results.get("subdomain")
        web_security_data = results.get("web_security")
        web_intelligence_data = results.get("web_intelligence")

        generator = ReportGenerator(
            system_info=sys_info,
            recon_data=recon_data,
            scan_data=scan_data,
            fingerprint_data=fingerprint_data,
            subdomain_data=subdomain_data,
            web_security_data=web_security_data,
            web_intelligence_data=web_intelligence_data,
            target=scan.target
        )

        if report_type == "txt":
            filepath, filename = generator.generate_txt()
        else:
            filepath, filename = generator.generate_html()

        return jsonify({
            "success": True,
            "download_url": f"/api/v1/projects/{project_id}/scans/{scan_id}/download-report?filename={filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/projects/<int:project_id>/scans/<int:scan_id>/download-report", methods=["GET"])
@require_auth
def download_project_scan_report(project_id, scan_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404
        scan = db.get(Scan, scan_id)
        if not scan or scan.project_id != project_id:
            return jsonify({"success": False, "error": "Scan not found"}), 404
    finally:
        db.close()

    filename = request.args.get("filename")
    if not filename:
        return jsonify({"success": False, "error": "Filename required"}), 400

    from report import ReportGenerator
    report_dir = ReportGenerator().report_dir
    return send_from_directory(report_dir, filename, as_attachment=True)


@api_bp.route("/projects/<int:project_id>/scans", methods=["DELETE"])
@require_auth
def clear_project_scans_history(project_id):
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        project = db.get(Project, project_id)
        if not project or project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Project not found"}), 404

        deleted_count = db.query(Scan).filter_by(project_id=project_id).delete()
        db.commit()

        ProjectService.log_activity(
            db,
            project_id,
            "Scan History Cleared",
            f"Cleared {deleted_count} scan records from project history"
        )

        return jsonify({
            "success": True,
            "message": f"Successfully cleared {deleted_count} scan record(s) from project history.",
            "deleted_count": deleted_count
        })
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


# --- CHANGE DETECTION & ASSET MONITORING API ---

@api_bp.route("/assets/<int:asset_id>/changes", methods=["GET"])
@require_auth
def get_asset_changes(asset_id):
    """
    Get detected change history, monitoring status, and recent change summary for an asset.
    """
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        # Query history events for change detections
        history_events = db.query(AssetHistory).filter_by(
            asset_id=asset_id
        ).order_by(AssetHistory.created_at.desc()).all()

        change_events = []
        latest_summary = "No significant changes detected."
        has_recent_changes = False

        for h in history_events:
            h_dict = h.to_dict()
            if h.event_name in ("Asset change detected", "Port Scan Completed", "Web Footprint Updated", "Reconnaissance Completed", "Asset Discovered"):
                change_events.append(h_dict)
                if h.event_name == "Asset change detected" and not has_recent_changes:
                    has_recent_changes = True
                    lines = (h.event_details or "").split("\n")
                    if lines:
                        latest_summary = lines[0].replace("Scan #", "").strip()

        # Monitoring status
        monitoring_status = "Active Changes" if has_recent_changes else "No Recent Changes"
        if not history_events:
            monitoring_status = "Newly Discovered"

        # Query project scans for scan comparison selection (filtered by asset target scope)
        asset_domain = (asset.domain or asset.name).lower()
        parts = [p for p in asset_domain.split('.') if p]
        root_domain = '.'.join(parts[-2:]) if len(parts) >= 2 else asset_domain

        scans = db.query(Scan).filter_by(project_id=asset.project_id, status="completed").order_by(Scan.start_time.desc()).all()
        target_scans = [s for s in scans if root_domain in s.target.lower() or s.target.lower() in asset_domain]
        if not target_scans:
            target_scans = scans

        scan_list = [{"id": s.id, "target": s.target, "scan_type": s.scan_type, "start_time": format_utc_iso(s.start_time)} for s in target_scans]

        return jsonify({
            "success": True,
            "asset_id": asset_id,
            "asset_name": asset.name,
            "monitoring": {
                "status": monitoring_status,
                "has_recent_changes": has_recent_changes,
                "last_seen": format_utc_iso(asset.last_seen),
                "total_change_events": len([e for e in change_events if e["event_name"] == "Asset change detected"]),
                "latest_summary": latest_summary
            },
            "change_events": change_events,
            "available_scans": scan_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/assets/<int:asset_id>/scans/compare", methods=["GET"])
@require_auth
def compare_asset_scans(asset_id):
    """
    Compare two scans (scan_a vs scan_b) for an asset.
    """
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        asset = db.get(Asset, asset_id)
        if not asset or asset.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Asset not found"}), 404

        scan_a_id = request.args.get("scan_a", type=int)
        scan_b_id = request.args.get("scan_b", type=int)

        if not scan_a_id or not scan_b_id:
            return jsonify({"success": False, "error": "Both scan_a and scan_b query parameters are required"}), 400

        scan_a = db.get(Scan, scan_a_id)
        scan_b = db.get(Scan, scan_b_id)

        if not scan_a or not scan_b or scan_a.project_id != asset.project_id or scan_b.project_id != asset.project_id:
            return jsonify({"success": False, "error": "One or both specified scans were not found"}), 404

        from services.change_detector import ChangeDetector
        comparison = ChangeDetector.compare_scans(scan_a.to_dict(), scan_b.to_dict())

        return jsonify({
            "success": True,
            "asset_id": asset_id,
            "scan_a": {"id": scan_a.id, "target": scan_a.target, "start_time": format_utc_iso(scan_a.start_time)},
            "scan_b": {"id": scan_b.id, "target": scan_b.target, "start_time": format_utc_iso(scan_b.start_time)},
            "comparison": comparison
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()


@api_bp.route("/scans/<int:scan_id>/changes", methods=["GET"])
@require_auth
def get_scan_changes(scan_id):
    """
    Get change summary details detected during a specific scan.
    """
    db = get_db()
    try:
        owner_id = get_user_owner_id(db)
        scan = db.get(Scan, scan_id)
        if not scan or scan.project.owner_id != owner_id:
            return jsonify({"success": False, "error": "Scan not found"}), 404

        # Query history events associated with this scan ID
        scan_tag = f"Scan #{scan_id}"
        history_events = db.query(AssetHistory).filter(
            AssetHistory.event_details.like(f"%{scan_tag}%")
        ).order_by(AssetHistory.created_at.desc()).all()

        events = [h.to_dict() for h in history_events]
        change_events = [e for e in events if e["event_name"] == "Asset change detected"]

        return jsonify({
            "success": True,
            "scan_id": scan_id,
            "target": scan.target,
            "scan_type": scan.scan_type,
            "completed_at": format_utc_iso(scan.end_time),
            "total_changes_detected": len(change_events),
            "change_events": events
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()



