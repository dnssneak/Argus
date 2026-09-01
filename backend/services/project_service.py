"""ProjectService — Business logic layer for Argus 2.0 Project Management."""

import re
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, selectinload
from models.models import Project, Target, Activity, Asset, Finding, Scan


class ProjectService:
    ALLOWED_STATUSES = {"ACTIVE", "ARCHIVED"}

    @staticmethod
    def validate_name(name: str) -> str:
        if not name or not name.strip():
            raise ValueError("Project name is required and cannot be empty.")
        clean_name = name.strip()
        if len(clean_name) > 128:
            raise ValueError("Project name must not exceed 128 characters.")
        return clean_name

    @staticmethod
    def validate_status(status: str) -> str:
        upper_status = status.upper() if status else "ACTIVE"
        if upper_status not in ProjectService.ALLOWED_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {list(ProjectService.ALLOWED_STATUSES)}")
        return upper_status

    @staticmethod
    def create_project(
        db: Session,
        name: str,
        description: Optional[str] = None,
        status: str = "ACTIVE",
        owner_id: str = "local-user"
    ) -> Project:
        """Create a new project container with validation and initial activity log."""
        clean_name = ProjectService.validate_name(name)
        clean_status = ProjectService.validate_status(status)

        existing = db.query(Project).filter(Project.name == clean_name).first()
        if existing:
            raise ValueError(f"A project with name '{clean_name}' already exists.")

        project = Project(
            owner_id=owner_id,
            name=clean_name,
            description=description.strip() if description else None,
            status=clean_status
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Log creation activity
        ProjectService.log_activity(db, project.id, "Project Created", f"Created project '{project.name}'")
        return project

    @staticmethod
    def get_project(db: Session, project_id: int) -> Optional[Project]:
        """Fetch project by ID."""
        return db.get(Project, project_id)

    @staticmethod
    def list_projects(
        db: Session,
        owner_id: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Project]:
        """Query projects list with optional search and status filtering."""
        query = db.query(Project).options(
            selectinload(Project.targets),
            selectinload(Project.assets).selectinload(Asset.findings),
            selectinload(Project.scans)
        )

        if owner_id:
            query = query.filter(Project.owner_id == owner_id)

        if status:
            clean_status = status.upper()
            if clean_status in ProjectService.ALLOWED_STATUSES:
                query = query.filter(Project.status == clean_status)

        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                (Project.name.like(search_pattern)) |
                (Project.description.like(search_pattern))
            )

        return query.order_by(Project.created_at.desc()).all()

    @staticmethod
    def update_project(
        db: Session,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Project:
        """Update project metadata."""
        project = db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found.")

        changes = []
        if name is not None:
            clean_name = ProjectService.validate_name(name)
            if clean_name != project.name:
                existing = db.query(Project).filter(Project.name == clean_name, Project.id != project_id).first()
                if existing:
                    raise ValueError(f"A project named '{clean_name}' already exists.")
                project.name = clean_name
                changes.append(f"Name changed to '{clean_name}'")

        if description is not None:
            project.description = description.strip() if description else None
            changes.append("Description updated")

        if status is not None:
            clean_status = ProjectService.validate_status(status)
            if clean_status != project.status:
                project.status = clean_status
                changes.append(f"Status changed to '{clean_status}'")

        db.commit()
        db.refresh(project)

        if changes:
            ProjectService.log_activity(db, project.id, "Project Updated", ", ".join(changes))

        return project

    @staticmethod
    def archive_project(db: Session, project_id: int) -> Project:
        """Toggle project status between ACTIVE and ARCHIVED."""
        project = db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found.")

        if (project.status or "").upper() == "ARCHIVED":
            project.status = "ACTIVE"
            msg = f"Project '{project.name}' status set to ACTIVE."
            ProjectService.log_activity(db, project.id, "Project Activated", msg)
        else:
            project.status = "ARCHIVED"
            msg = f"Project '{project.name}' archived."
            ProjectService.log_activity(db, project.id, "Project Archived", msg)

        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, project_id: int, force: bool = False) -> Tuple[bool, str, Dict[str, int]]:
        """
        Delete project with Delete Protection checks.
        If force=False and project contains assets, findings, scans, or targets, returns False with counts.
        """
        project = db.get(Project, project_id)
        if not project:
            return False, "Project not found.", {}

        asset_count = len(project.assets)
        target_count = len(project.targets)
        scan_count = len(project.scans)
        finding_count = sum(len(a.findings) for a in project.assets)

        counts = {
            "targets": target_count,
            "assets": asset_count,
            "scans": scan_count,
            "findings": finding_count
        }

        has_data = (asset_count > 0 or target_count > 0 or scan_count > 0 or finding_count > 0)

        if has_data and not force:
            warning_msg = (
                f"Delete Protection Active: Project contains {asset_count} Assets, "
                f"{finding_count} Findings, {scan_count} Scans, and {target_count} Targets. "
                "Confirm force deletion or archive instead."
            )
            return False, warning_msg, counts

        db.delete(project)
        db.commit()
        return True, f"Project '{project.name}' deleted successfully.", counts

    @staticmethod
    def add_target(
        db: Session,
        project_id: int,
        target_str: str,
        target_type: Optional[str] = None
    ) -> Target:
        """Add a target scope to a project."""
        project = db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found.")

        if not target_str or not target_str.strip():
            raise ValueError("Target address/domain cannot be empty.")

        clean_target = target_str.strip()

        # Infer target type if not provided
        if not target_type:
            if "/" in clean_target:
                target_type = "CIDR"
            elif clean_target.startswith("http://") or clean_target.startswith("https://"):
                target_type = "URL"
            elif re.match(r"^\d{1,3}(\.\d{1,3}){3}$", clean_target):
                target_type = "IP"
            elif "." in clean_target:
                target_type = "Domain"
            else:
                target_type = "Domain"

        # Check duplicate target in same project
        existing = db.query(Target).filter_by(project_id=project_id, target=clean_target).first()
        if existing:
            return existing

        target = Target(
            project_id=project_id,
            target=clean_target,
            target_type=target_type,
            status="active"
        )
        db.add(target)
        db.commit()
        db.refresh(target)

        ProjectService.log_activity(db, project_id, "Target Added", f"Added target '{clean_target}' ({target_type})")
        return target

    @staticmethod
    def get_project_dashboard(db: Session, project_id: int) -> Dict[str, Any]:
        """Fetch project-specific statistics, targets, scans, assets, and activities for dedicated project view."""
        project = db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found.")

        # Compute statistics based strictly on real data
        targets = [t.to_dict() for t in project.targets]
        assets = [a.to_dict() for a in project.assets]
        scans = [s.to_dict() for s in project.scans]
        
        all_findings = []
        for a in project.assets:
            all_findings.extend([f.to_dict() for f in a.findings])

        activities = db.query(Activity).filter_by(project_id=project_id).order_by(Activity.created_at.desc()).limit(15).all()

        return {
            "project": project.to_dict(),
            "stats": {
                "targets": len(targets),
                "assets": len(assets),
                "scans": len(scans),
                "findings": len(all_findings),
                "internet_facing": sum(1 for a in assets if a.get("ip_address")),
                "high_risk_assets": sum(1 for a in assets if a.get("risk_score", 0) >= 70)
            },
            "targets": targets,
            "scans": scans,
            "assets": assets,
            "findings": all_findings,
            "activities": [act.to_dict() for act in activities]
        }

    @staticmethod
    def log_activity(db: Session, project_id: int, action: str, details: Optional[str] = None):
        """Record an event in the project activity timeline."""
        activity = Activity(
            project_id=project_id,
            action=action,
            details=details
        )
        db.add(activity)
        db.commit()
