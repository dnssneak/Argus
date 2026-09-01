import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.models import Finding, Asset, Scan, Target, Project, Service, Technology, Endpoint, Relationship, format_utc_iso, utc_now
from services.ai_advisor import AIRemediationAdvisor


class FindingCorrelator:
    """
    Argus 2.0 Finding Correlation & Prioritization Engine.
    Correlates security findings with affected Assets, Scans, Targets, and Projects.
    Calculates contextual urgency priority (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL) 
    while preserving original finding severity. Generates deterministic factor explanations 
    and tracks finding lifecycle (NEW, EXISTING, RECURRING, RESOLVED).
    """

    PRIORITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]

    # Priority Tier Thresholds (0-100 scale)
    PRIORITY_TIERS = [
        (80, "CRITICAL"),
        (60, "HIGH"),
        (40, "MEDIUM"),
        (20, "LOW"),
        (0, "INFORMATIONAL")
    ]

    @staticmethod
    def calculate_finding_priority(
        finding: Finding,
        asset: Optional[Asset] = None,
        db: Optional[Session] = None
    ) -> Tuple[str, int, List[str]]:
        """
        Calculates contextual priority (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL), 
        urgency score (0-100), and a list of applicable contributing factor explanations.
        
        Original finding severity is NEVER overwritten.
        """
        if not asset and finding.asset:
            asset = finding.asset
        elif not asset and db and finding.asset_id:
            asset = db.get(Asset, finding.asset_id)

        factors: List[str] = []
        raw_urgency = 0.0

        # 1. Base Finding Severity
        sev = (finding.severity or "Informational").strip().lower()
        if sev == "critical":
            raw_urgency += 85.0
            factors.append("Critical-severity finding")
        elif sev == "high":
            raw_urgency += 65.0
            factors.append("High-severity finding")
        elif sev == "medium":
            raw_urgency += 45.0
            factors.append("Medium-severity finding")
        elif sev == "low":
            raw_urgency += 25.0
            factors.append("Low-severity finding")
        else:
            raw_urgency += 10.0
            factors.append("Informational observation")

        # 2. CVSS Score (if available)
        cvss = finding.cvss_score
        if cvss is not None and cvss > 10.0:
            cvss = min(10.0, cvss / 10.0)
        elif cvss is None and finding.risk_score and finding.risk_score > 0:
            cvss = float(finding.risk_score) / 10.0 if finding.risk_score > 10 else float(finding.risk_score)

        if cvss is not None and cvss > 0:
            if cvss >= 9.0:
                raw_urgency += 15.0
                factors.append(f"CVSS Score: {cvss:.1f} (Critical)")
            elif cvss >= 7.0:
                raw_urgency += 10.0
                factors.append(f"CVSS Score: {cvss:.1f} (High)")
            elif cvss >= 4.0:
                raw_urgency += 5.0
                factors.append(f"CVSS Score: {cvss:.1f} (Medium)")

        # 3. Asset Risk Score (from Risk Engine)
        if asset:
            risk_score = asset.risk_score or 0
            if risk_score >= 80:
                raw_urgency += 15.0
                factors.append(f"Asset Risk Score: {risk_score}")
            elif risk_score >= 60:
                raw_urgency += 10.0
                factors.append(f"Elevated Asset Risk Score: {risk_score}")
            elif risk_score >= 40:
                raw_urgency += 5.0
                factors.append(f"Asset Risk Score: {risk_score}")

            # 4. Internet Exposure
            exposure = (asset.exposure or "").strip().lower()
            if exposure in ["internet-facing", "publicly accessible", "public"]:
                raw_urgency += 15.0
                factors.append("Internet-facing asset")

            # 5. Asset Criticality
            tags = [t.strip().lower() for t in (asset.tags or "").split(",") if t.strip()]
            if "critical" in tags or asset.asset_type.lower() == "domain":
                raw_urgency += 10.0
                factors.append("High asset criticality")
            elif "high" in tags:
                raw_urgency += 5.0
                factors.append("High business priority asset")

        # 6. Affected Exposed Port / Service
        if finding.port or finding.service_name:
            port_desc = f"{finding.port}" if finding.port else (finding.service_name or "Service")
            raw_urgency += 10.0
            factors.append(f"Affected public service / port: {port_desc}")

        # 7. Affected Endpoint
        if finding.endpoint:
            factors.append(f"Affected endpoint: {finding.endpoint}")

        # 8. Asset Relationship Context
        if asset and db and asset.id:
            rel_count = db.query(Relationship).filter(
                or_(Relationship.source_asset_id == asset.id, Relationship.target_asset_id == asset.id)
            ).count()
            if rel_count >= 3:
                raw_urgency += 5.0
                factors.append(f"Asset has active graph relationships ({rel_count} topology links)")

        # 9. Finding Lifecycle (Newly Discovered vs Recurring)
        lifecycle = (finding.lifecycle_status or "NEW").upper()
        if lifecycle == "RECURRING":
            raw_urgency += 5.0
            factors.append("Recurring finding detected across multiple scans")
        elif lifecycle == "NEW":
            factors.append("Newly discovered finding in recent scan")

        # Final Priority Calculation & Tier Assignment
        final_score = int(round(min(100.0, max(0.0, raw_urgency))))

        priority_level = "INFORMATIONAL"
        for threshold, label in FindingCorrelator.PRIORITY_TIERS:
            if final_score >= threshold:
                priority_level = label
                break

        # Cap Priority Tier based on Finding Severity
        # Prevents Low/Informational findings from being categorized as CRITICAL priority
        max_priority_tier = {
            "informational": "INFORMATIONAL",
            "low": "MEDIUM",
            "medium": "HIGH",
            "high": "CRITICAL",
            "critical": "CRITICAL"
        }.get(sev, "CRITICAL")

        tier_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFORMATIONAL": 0}
        if tier_rank.get(priority_level, 0) > tier_rank.get(max_priority_tier, 4):
            priority_level = max_priority_tier

        return priority_level, final_score, factors

    @staticmethod
    def correlate_and_prioritize_finding(
        db: Session,
        finding: Finding,
        asset: Optional[Asset] = None
    ) -> Finding:
        """
        Calculates priority for a single finding and updates priority fields in the database.
        """
        priority_level, priority_score, factors = FindingCorrelator.calculate_finding_priority(
            finding=finding,
            asset=asset,
            db=db
        )
        
        finding.priority = priority_level
        finding.priority_score = priority_score
        finding.priority_explanation = json.dumps(factors)
        
        # Link target_id if missing
        if not finding.target_id and asset and asset.project_id:
            target_obj = db.query(Target).filter(
                Target.project_id == asset.project_id,
                Target.target == asset.name
            ).first()
            if target_obj:
                finding.target_id = target_obj.id

        # Automatic AI Remediation Advisor Processing Pipeline
        try:
            asset_dict = asset.to_dict() if asset else (finding.asset.to_dict() if finding.asset else {})
            remediation_text, is_enhanced = AIRemediationAdvisor.enhance_or_generate_remediation(
                finding_dict=finding.to_dict(),
                asset_dict=asset_dict,
                baseline_recommendation=finding.recommendation
            )
            finding.recommendation = remediation_text
            finding.ai_enhanced = is_enhanced
        except Exception as err:
            pass

        db.commit()
        db.refresh(finding)
        return finding

    @staticmethod
    def correlate_scan_findings(
        db: Session,
        project_id: int,
        target_name: str,
        scan_id: int,
        results: Dict[str, Any]
    ) -> List[Finding]:
        """
        Correlates scan results with project assets and findings.
        Identifies NEW vs RECURRING findings, links Scan & Target context, 
        and updates finding lifecycle and contextual priority.
        """
        now = datetime.now(timezone.utc)
        scan = db.get(Scan, scan_id)
        target_obj = db.query(Target).filter_by(project_id=project_id, target=target_name.strip()).first()
        target_id = target_obj.id if target_obj else None

        updated_findings = []
        project_assets = db.query(Asset).filter_by(project_id=project_id).all()

        for asset in project_assets:
            for finding in asset.findings:
                # Update correlation links
                if not finding.scan_id:
                    finding.scan_id = scan_id
                if not finding.target_id and target_id:
                    finding.target_id = target_id

                # Update lifecycle status
                if not finding.first_scan_id:
                    finding.first_scan_id = scan_id
                    finding.first_seen = now
                    finding.lifecycle_status = "NEW"
                elif finding.last_scan_id and finding.last_scan_id != scan_id:
                    finding.lifecycle_status = "RECURRING"

                finding.last_scan_id = scan_id
                finding.last_seen = now

                # Calculate contextual priority & explanation
                p_level, p_score, p_factors = FindingCorrelator.calculate_finding_priority(
                    finding=finding,
                    asset=asset,
                    db=db
                )

                finding.priority = p_level
                finding.priority_score = p_score
                finding.priority_explanation = json.dumps(p_factors)

                updated_findings.append(finding)

        db.commit()
        return updated_findings

    @staticmethod
    def correlate_project_findings(db: Session, project_id: Optional[int] = None) -> List[Finding]:
        """
        Runs comprehensive correlation and prioritization pass across project assets.
        Auto-derives security findings from exposed sensitive ports, endpoints, and technologies 
        if not already present, updates finding lifecycles, and recalculates contextual priorities.
        """
        query = db.query(Asset)
        if project_id:
            query = query.filter(Asset.project_id == project_id)
        assets = query.all()

        SENSITIVE_PORTS = {
            21: ("FTP", "High", 7.5),
            22: ("SSH", "Medium", 5.3),
            23: ("Telnet", "High", 7.5),
            25: ("SMTP", "Medium", 5.0),
            80: ("HTTP", "Medium", 5.3),
            443: ("HTTPS", "Informational", 3.5),
            445: ("SMB", "Critical", 9.0),
            1433: ("MSSQL", "High", 8.0),
            1521: ("Oracle DB", "High", 8.0),
            3306: ("MySQL", "Medium", 6.5),
            3389: ("RDP", "High", 8.1),
            5432: ("PostgreSQL", "Medium", 6.5),
            5900: ("VNC", "High", 7.8),
            6379: ("Redis", "High", 8.0),
            8080: ("HTTP-Alt", "Medium", 5.0),
            8443: ("HTTPS-Alt", "Informational", 3.5),
            9200: ("Elasticsearch", "High", 7.5),
            11211: ("Memcached", "Medium", 6.0),
            27017: ("MongoDB", "High", 8.0),
        }

        correlated_list = []

        for asset in assets:
            existing_findings = db.query(Finding).filter_by(asset_id=asset.id).all()
            existing_titles = {f.title.lower() for f in existing_findings}

            # 1. Derive Findings from Services / Open Ports
            for svc in asset.services:
                if svc.port in SENSITIVE_PORTS:
                    svc_name, default_sev, default_cvss = SENSITIVE_PORTS[svc.port]
                    title = f"Exposed Service: {svc_name} (Port {svc.port})"
                    if title.lower() not in existing_titles:
                        f_new = Finding(
                            asset_id=asset.id,
                            title=title,
                            severity=default_sev,
                            cvss_score=default_cvss,
                            risk_score=int(default_cvss),
                            port=svc.port,
                            service_name=svc.service_name or svc_name,
                            description=f"Exposed {svc_name} service detected on port {svc.port} ({asset.name}).",
                            recommendation=f"Restrict access to port {svc.port} using network firewall or VPN.",
                            discovery_source="Service Recon",
                            status="open"
                        )
                        db.add(f_new)
                        db.flush()
                        existing_findings.append(f_new)
                        existing_titles.add(title.lower())
                else:
                    title = f"Exposed Open Port: Port {svc.port}"
                    if title.lower() not in existing_titles:
                        f_new = Finding(
                            asset_id=asset.id,
                            title=title,
                            severity="Low",
                            cvss_score=4.0,
                            risk_score=4,
                            port=svc.port,
                            service_name=svc.service_name or "unknown",
                            description=f"Exposed port {svc.port} detected on asset {asset.name}.",
                            recommendation="Review open port necessity and enforce access control.",
                            discovery_source="Port Scanner",
                            status="open"
                        )
                        db.add(f_new)
                        db.flush()
                        existing_findings.append(f_new)
                        existing_titles.add(title.lower())

            # 2. Derive Findings from Subdomain Attack Surface Name Patterns
            name_parts = asset.name.lower().split('.')
            sub_prefix = name_parts[0] if len(name_parts) > 2 else ""

            if sub_prefix:
                sub_finding_info = None
                if sub_prefix == "admin":
                    sub_finding_info = (f"Exposed Administrative Portal Subdomain ({asset.name})", "High", 7.5, "Administrative subdomains attract targeted brute-force attacks.")
                elif sub_prefix == "git":
                    sub_finding_info = (f"Exposed Source Control Subdomain ({asset.name})", "High", 7.5, "Source control subdomains risk sensitive repository information leakage.")
                elif sub_prefix in ["dev", "stage", "staging", "test", "testing"]:
                    sub_finding_info = (f"Exposed Non-Production Subdomain ({asset.name})", "Medium", 5.5, "Non-production subdomains often contain debug flags or weaker security configs.")
                elif sub_prefix in ["vpn", "secure"]:
                    sub_finding_info = (f"Exposed Gateway Subdomain ({asset.name})", "Medium", 5.0, "Remote access gateway subdomain detected.")
                elif sub_prefix in ["api", "billing", "portal", "mail", "webmail"]:
                    sub_finding_info = (f"Exposed Application/Service Subdomain ({asset.name})", "Low", 4.0, "Active application subdomain exposed on attack surface.")

                if sub_finding_info:
                    s_title, s_sev, s_cvss, s_desc = sub_finding_info
                    if s_title.lower() not in existing_titles:
                        f_sub = Finding(
                            asset_id=asset.id,
                            title=s_title,
                            severity=s_sev,
                            cvss_score=s_cvss,
                            risk_score=int(s_cvss),
                            description=s_desc,
                            recommendation="Ensure multi-factor authentication and strict access policies are applied.",
                            discovery_source="Asset Attack Surface Analysis",
                            status="open"
                        )
                        db.add(f_sub)
                        db.flush()
                        existing_findings.append(f_sub)
                        existing_titles.add(s_title.lower())

            # 3. Derive Findings from Endpoints
            for ep in asset.endpoints:
                p_lower = (ep.path or "").lower()
                if any(kw in p_lower for kw in ["admin", "login", "config", ".env", ".git", "actuator", "swagger"]):
                    is_crit = ".env" in p_lower or ".git" in p_lower or "admin" in p_lower
                    sev = "High" if is_crit else "Medium"
                    cvss = 8.5 if is_crit else 6.0
                    title = f"Exposed Sensitive Endpoint: {ep.path}"
                    if title.lower() not in existing_titles:
                        f_new = Finding(
                            asset_id=asset.id,
                            title=title,
                            severity=sev,
                            cvss_score=cvss,
                            risk_score=int(cvss),
                            endpoint=ep.path,
                            description=f"Potentially sensitive endpoint {ep.path} accessible on asset {asset.name}.",
                            recommendation="Enforce strict authentication & authorization controls on administrative paths.",
                            discovery_source="Web Footprinting",
                            status="open"
                        )
                        db.add(f_new)
                        db.flush()
                        existing_findings.append(f_new)
                        existing_titles.add(title.lower())

            # 4. Correlate and Prioritize All Findings for Asset
            for finding in existing_findings:
                FindingCorrelator.correlate_and_prioritize_finding(db, finding, asset)
                correlated_list.append(finding)

            # Recalculate Asset Risk Score
            from services.risk_engine import RiskEngine
            RiskEngine.recalculate_and_update_asset_risk(db, asset, trigger_reason="Finding Correlation Pass")

        db.commit()
        return correlated_list

    @staticmethod
    def get_prioritized_findings(
        db: Session,
        project_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        search: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries findings across existing assets, ordered by contextual priority tier and priority score.
        Returns serialized findings dictionaries.
        """
        from sqlalchemy.orm import selectinload
        query = db.query(Finding).options(
            selectinload(Finding.asset).selectinload(Asset.project)
        ).join(Asset, Finding.asset_id == Asset.id)

        if owner_id:
            query = query.join(Project, Asset.project_id == Project.id).filter(Project.owner_id == str(owner_id))
        if project_id:
            query = query.filter(Asset.project_id == project_id)
        if asset_id:
            query = query.filter(Finding.asset_id == asset_id)
        if severity and severity.upper() != "ALL":
            query = query.filter(Finding.severity.ilike(severity))
        if priority and priority.upper() != "ALL":
            query = query.filter(Finding.priority.ilike(priority))
        if status and status.upper() != "ALL":
            query = query.filter(Finding.status.ilike(status))
        if lifecycle_status and lifecycle_status.upper() != "ALL":
            query = query.filter(Finding.lifecycle_status.ilike(lifecycle_status))

        if search:
            search_pat = f"%{search}%"
            query = query.filter(
                or_(
                    Finding.title.ilike(search_pat),
                    Finding.description.ilike(search_pat),
                    Finding.cve_id.ilike(search_pat),
                    Asset.name.ilike(search_pat),
                    Asset.ip_address.ilike(search_pat)
                )
            )

        findings = query.all()

        # Prioritization custom sort order: CRITICAL (4) -> HIGH (3) -> MEDIUM (2) -> LOW (1) -> INFORMATIONAL (0)
        tier_weight = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
            "INFORMATIONAL": 0
        }

        # Format and prioritize each finding
        formatted = []
        for f in findings:
            if not f.priority:
                FindingCorrelator.correlate_and_prioritize_finding(db, f)

            f_dict = f.to_dict()
            p_level = (f_dict.get("priority") or "INFORMATIONAL").upper()
            w = tier_weight.get(p_level, 0)
            score = f_dict.get("priority_score") or 0
            formatted.append((w, score, f_dict))

        # Sort descending by priority weight, then by priority score, then by created_at
        formatted.sort(key=lambda x: (x[0], x[1], x[2].get("created_at") or ""), reverse=True)

        return [item[2] for item in formatted]
