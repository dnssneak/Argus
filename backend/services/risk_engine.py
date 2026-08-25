from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from models.models import Asset, Service, Technology, Finding, Endpoint, Relationship, AssetHistory


class RiskEngine:
    """
    Argus 2.0 Risk Engine & Risk Scoring Service.
    Calculates contextual 0-100 risk score, maps severity level, generates 
    impact-categorized risk explanations, and logs risk transitions in AssetHistory.
    """

    # Severity Level Mapping Thresholds
    # 0-19: INFORMATIONAL, 20-39: LOW, 40-59: MEDIUM, 60-79: HIGH, 80-100: CRITICAL
    SEVERITY_TIERS = [
        (80, "CRITICAL"),
        (60, "HIGH"),
        (40, "MEDIUM"),
        (20, "LOW"),
        (0, "INFORMATIONAL"),
    ]

    SENSITIVE_PORTS = {
        21: "FTP (Unencrypted File Transfer)",
        22: "SSH (Remote Management)",
        23: "Telnet (Insecure Management)",
        445: "SMB (File Sharing)",
        1433: "MSSQL (Database Engine)",
        3306: "MySQL (Database Engine)",
        3389: "RDP (Remote Desktop)",
        5432: "PostgreSQL (Database Engine)",
        5900: "VNC (Remote Control)",
        6379: "Redis (In-Memory Database)",
        9200: "Elasticsearch (Search Engine)",
        11211: "Memcached (Cache Service)",
        27017: "MongoDB (NoSQL Database)",
    }

    SENSITIVE_ENDPOINT_PATTERNS = [
        "/admin", "/login", "/api", "/config", "/.git", "/.env", "/env",
        "/swagger", "/dashboard", "/v1", "/v2", "/auth", "/user", "/settings",
        "/console", "/actuator", "/phpmyadmin", "/wp-admin"
    ]

    LEGACY_OR_VULN_TECHS = [
        "php", "wordpress", "apache http server", "nginx", "jquery",
        "bootstrap", "iis", "openssl", "python", "tomcat", "node.js"
    ]

    @staticmethod
    def get_severity_level(score: int) -> str:
        """Map 0-100 numeric score to 5-tier Severity string."""
        for threshold, label in RiskEngine.SEVERITY_TIERS:
            if score >= threshold:
                return label
        return "INFORMATIONAL"

    @staticmethod
    def calculate_asset_risk(db: Session, asset: Asset) -> Dict[str, Any]:
        """
        Calculates contextual risk score (0-100), severity tier, and categorized 
        contributing risk factors (HIGH, MEDIUM, LOW impact) for a given asset.
        """
        raw_score = 0.0
        high_factors: List[str] = []
        medium_factors: List[str] = []
        low_factors: List[str] = []

        # 1. Internet Exposure
        exposure = (asset.exposure or "").strip().lower()
        if exposure in ["internet-facing", "publicly accessible", "public"]:
            raw_score += 20.0
            high_factors.append("Internet-facing asset directly exposed to public network")
        elif exposure in ["internal", "private"]:
            raw_score += 5.0
            # Internal exposure is positive/low factor, no penalty
        else:
            # Unknown exposure: treat safely, no assumption of vulnerability
            pass

        # 2. Open Ports & Sensitive Services
        services = asset.services or []
        open_services = [s for s in services if (s.state or "").lower() == "open"]
        sensitive_open = []
        general_open_count = 0

        for svc in open_services:
            port = svc.port
            if port in RiskEngine.SENSITIVE_PORTS:
                sensitive_open.append((port, svc.service_name or RiskEngine.SENSITIVE_PORTS[port]))
            else:
                general_open_count += 1

        if sensitive_open:
            port_penalty = len(sensitive_open) * 12.0
            raw_score += port_penalty
            port_desc = ", ".join([f"{p}/{name}" for p, name in sensitive_open[:3]])
            high_factors.append(f"Exposed sensitive management/database service(s): {port_desc}")

        if general_open_count > 0:
            gen_penalty = min(20.0, general_open_count * 4.0)
            raw_score += gen_penalty
            if general_open_count >= 3:
                medium_factors.append(f"Multiple exposed network ports ({len(open_services)} total open services)")
            else:
                low_factors.append(f"{general_open_count} standard open port(s) detected")

        # 3. Vulnerabilities / Findings
        findings = asset.findings or []
        open_findings = [f for f in findings if (f.status or "").lower() != "resolved"]
        
        crit_count = 0
        high_count = 0
        med_count = 0
        low_count = 0

        for f in open_findings:
            sev = (f.severity or "").lower()
            cvss = f.risk_score or 0.0

            if sev == "critical":
                crit_count += 1
                raw_score += max(35.0, cvss * 3.5 if cvss > 0 else 35.0)
            elif sev == "high":
                high_count += 1
                raw_score += max(20.0, cvss * 2.0 if cvss > 0 else 20.0)
            elif sev == "medium":
                med_count += 1
                raw_score += max(10.0, cvss * 1.0 if cvss > 0 else 10.0)
            elif sev == "low":
                low_count += 1
                raw_score += 4.0

        if crit_count > 0:
            high_factors.append(f"Critical vulnerability detected ({crit_count} unresolved critical finding(s))")
        if high_count > 0:
            high_factors.append(f"High severity vulnerability detected ({high_count} unresolved high finding(s))")
        if med_count > 0:
            medium_factors.append(f"Medium severity vulnerability detected ({med_count} finding(s))")
        if low_count > 0:
            low_factors.append(f"Low severity security observation(s) ({low_count} finding(s))")

        # 4. Technology Risk
        technologies = asset.technologies or []
        vuln_tech_names = []
        for tech in technologies:
            t_name = (tech.name or "").lower()
            t_ver = tech.version
            # Only evaluate technology risk if version information is known/available
            if t_ver and any(kw in t_name for kw in RiskEngine.LEGACY_OR_VULN_TECHS):
                vuln_tech_names.append(f"{tech.name} {t_ver}")

        if vuln_tech_names:
            tech_penalty = min(20.0, len(vuln_tech_names) * 8.0)
            raw_score += tech_penalty
            low_factors.append(f"Outdated/legacy software stack version detected ({', '.join(vuln_tech_names[:2])})")

        # 5. Sensitive Endpoints & Authentication
        endpoints = asset.endpoints or []
        sensitive_eps = []
        unauth_eps = []

        for ep in endpoints:
            path_lower = (ep.path or "").lower()
            if any(p in path_lower for p in RiskEngine.SENSITIVE_ENDPOINT_PATTERNS):
                sensitive_eps.append(ep.path)
            # If endpoint status or discovery indicates unauthenticated access
            if "unauth" in path_lower or (ep.status_code and ep.status_code == 200 and ("admin" in path_lower or "api" in path_lower)):
                unauth_eps.append(ep.path)

        if unauth_eps:
            raw_score += 15.0
            high_factors.append(f"Unauthenticated sensitive endpoint discovered ({unauth_eps[0]})")
        elif sensitive_eps:
            raw_score += min(20.0, len(sensitive_eps) * 6.0)
            medium_factors.append(f"Sensitive web/API endpoint discovered ({', '.join(sensitive_eps[:2])})")

        # 6. Asset Criticality (from tags / metadata)
        tags = [t.strip().lower() for t in (asset.tags or "").split(",") if t.strip()]
        criticality_multiplier = 1.0
        if "critical" in tags or asset.asset_type.lower() == "domain":
            criticality_multiplier = 1.2
            medium_factors.append("High business criticality target scope")
        elif "high" in tags:
            criticality_multiplier = 1.1
        elif "low" in tags:
            criticality_multiplier = 0.85

        # Apply criticality multiplier to calculated base score
        score_after_criticality = raw_score * criticality_multiplier

        # 7. Relationship Context
        # Query relationships connected to this asset
        rel_count = 0
        if asset.id:
            rel_count = db.query(Relationship).filter(
                (Relationship.source_asset_id == asset.id) | (Relationship.target_asset_id == asset.id)
            ).count()

        if rel_count >= 5:
            score_after_criticality += 10.0
            low_factors.append(f"High graph relationship interconnectivity ({rel_count} topology connections)")
        elif rel_count >= 2:
            score_after_criticality += 5.0

        # Final score clamping: 0 to 100
        final_score = int(round(min(100.0, max(0.0, score_after_criticality))))
        severity = RiskEngine.get_severity_level(final_score)

        return {
            "score": final_score,
            "severity": severity,
            "contributing_factors": {
                "high": high_factors,
                "medium": medium_factors,
                "low": low_factors
            },
            "summary_factors": high_factors + medium_factors + low_factors
        }

    @staticmethod
    def recalculate_and_update_asset_risk(
        db: Session,
        asset: Asset,
        trigger_reason: str = None
    ) -> bool:
        """
        Recalculates asset risk score, updates asset.risk_score, and records 
        meaningful risk changes in AssetHistory timeline.
        """
        if not asset:
            return False

        old_score = asset.risk_score or 0
        old_severity = RiskEngine.get_severity_level(old_score)

        calc_result = RiskEngine.calculate_asset_risk(db, asset)
        new_score = calc_result["score"]
        new_severity = calc_result["severity"]

        asset.risk_score = new_score

        # Log timeline history event if score or severity changed meaningfully
        if old_score != new_score or old_severity != new_severity:
            details_str = f"Risk score updated: {old_score} → {new_score} ({old_severity} → {new_severity})"
            if trigger_reason:
                details_str += f" [{trigger_reason}]"

            history_event = AssetHistory(
                asset_id=asset.id,
                event_name="Risk Score Recalculated",
                event_details=details_str,
                created_at=datetime.utcnow()
            )
            db.add(history_event)

        db.commit()
        return True
