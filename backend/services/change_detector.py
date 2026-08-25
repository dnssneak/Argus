from typing import Dict, Any, List, Optional
import json


class ChangeDetector:
    """
    Service for detecting changes between an Asset's previous state and a new scan,
    categorizing changes into ADDED, REMOVED, CHANGED, and UNCHANGED, and comparing
    raw scan results.
    """

    @staticmethod
    def snapshot_asset_state(asset) -> Dict[str, Any]:
        """
        Creates a dictionary snapshot of an Asset's current state before a scan updates it.
        """
        if not asset:
            return {}

        services = []
        for s in (asset.services or []):
            services.append({
                "port": s.port,
                "protocol": (s.protocol or "tcp").lower(),
                "service_name": s.service_name or "unknown",
                "version": s.version or "",
                "state": (s.state or "open").lower()
            })

        technologies = []
        for t in (asset.technologies or []):
            technologies.append({
                "name": t.name,
                "version": t.version or "",
                "category": t.category or "General"
            })

        endpoints = []
        for e in (asset.endpoints or []):
            endpoints.append({
                "method": (e.method or "GET").upper(),
                "path": e.path or "/",
                "status_code": e.status_code
            })

        return {
            "id": asset.id,
            "name": asset.name,
            "ip_address": asset.ip_address or "",
            "status": asset.status or "active",
            "services": services,
            "technologies": technologies,
            "endpoints": endpoints,
            "web_url": asset.web_url or "",
            "web_status_code": asset.web_status_code,
            "web_title": asset.web_title or "",
            "web_server": asset.web_server or "",
            "cert_issuer": asset.cert_issuer or "",
            "cert_sans": asset.cert_sans or ""
        }

    @staticmethod
    def compare_asset_states(prev_snapshot: Dict[str, Any], new_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares an asset's previous state snapshot with parsed scan results.
        Returns detailed list of changes grouped by category (ADDED, REMOVED, CHANGED, UNCHANGED)
        and a formatted text summary.
        """
        changes = []
        added = []
        removed = []
        changed = []
        unchanged = []

        if not prev_snapshot:
            # New asset - everything is new discovery
            return {
                "has_changes": True,
                "summary": "Asset newly discovered",
                "added": added,
                "removed": removed,
                "changed": changed,
                "unchanged": unchanged,
                "changes": changes
            }

        # 1. Compare IP Address
        prev_ip = prev_snapshot.get("ip_address", "")
        # Check ports or subdomain data for new IP
        new_ip = ""
        ports_data = new_results.get("ports", {})
        if isinstance(ports_data, dict) and ports_data.get("ip"):
            new_ip = ports_data.get("ip")
        elif isinstance(new_results.get("subdomain"), dict):
            # Check if current target ip in subdomains list
            for sub in new_results.get("subdomain", {}).get("subdomains", []):
                if isinstance(sub, dict) and sub.get("subdomain") == prev_snapshot.get("name"):
                    if sub.get("ip_address") not in ("Not Resolved", "Unknown", None):
                        new_ip = sub.get("ip_address")

        if new_ip and prev_ip and new_ip != prev_ip:
            item = {"type": "IP Address", "label": f"IP address changed from {prev_ip} to {new_ip}", "category": "CHANGED"}
            changed.append(item)
            changes.append(f"~ IP address changed from {prev_ip} to {new_ip}")
        elif new_ip and not prev_ip:
            item = {"type": "IP Address", "label": f"IP address resolved: {new_ip}", "category": "ADDED"}
            added.append(item)
            changes.append(f"+ IP address resolved: {new_ip}")

        # 2. Compare Ports & Services
        prev_services = {f"{s['port']}/{s['protocol']}": s for s in prev_snapshot.get("services", [])}
        new_services = {}

        if isinstance(ports_data, dict):
            for s in ports_data.get("services", []):
                if isinstance(s, dict) and s.get("port"):
                    p_num = s.get("port")
                    p_proto = (s.get("protocol") or "tcp").lower()
                    key = f"{p_num}/{p_proto}"
                    new_services[key] = {
                        "port": p_num,
                        "protocol": p_proto,
                        "service_name": s.get("service") or "unknown",
                        "version": s.get("version") or "",
                        "state": (s.get("state") or "open").lower()
                    }

        if new_services or prev_services:
            for key, new_s in new_services.items():
                if key not in prev_services:
                    lbl = f"Port {key} opened ({new_s['service_name']})"
                    if new_s.get("version"):
                        lbl += f" v{new_s['version']}"
                    added.append({"type": "Port", "label": lbl, "category": "ADDED"})
                    changes.append(f"+ {lbl}")
                else:
                    prev_s = prev_services[key]
                    # Check version change
                    if new_s["version"] and prev_s["version"] and new_s["version"] != prev_s["version"]:
                        lbl = f"Service on port {key} ({new_s['service_name']}) version changed: {prev_s['version']} -> {new_s['version']}"
                        changed.append({"type": "Service", "label": lbl, "category": "CHANGED"})
                        changes.append(f"~ {lbl}")
                    else:
                        lbl = f"Port {key} ({new_s['service_name']})"
                        unchanged.append({"type": "Port", "label": lbl, "category": "UNCHANGED"})

            for key, prev_s in prev_services.items():
                if key not in new_services and new_services:  # Only count removed if scan actually ran port scan
                    lbl = f"Port {key} closed ({prev_s['service_name']})"
                    removed.append({"type": "Port", "label": lbl, "category": "REMOVED"})
                    changes.append(f"- {lbl}")

        # 3. Compare Technologies
        prev_techs = {t["name"].lower(): t for t in prev_snapshot.get("technologies", [])}
        new_techs = {}
        web_data = new_results.get("web", {})
        if isinstance(web_data, dict):
            for t in web_data.get("technologies", []):
                t_name = t.get("name") if isinstance(t, dict) else str(t)
                if t_name:
                    t_ver = t.get("version") if isinstance(t, dict) else ""
                    new_techs[t_name.lower()] = {"name": t_name, "version": t_ver or ""}

        if new_techs or prev_techs:
            for t_key, new_t in new_techs.items():
                if t_key not in prev_techs:
                    lbl = f"Technology added: {new_t['name']}"
                    if new_t["version"]:
                        lbl += f" ({new_t['version']})"
                    added.append({"type": "Technology", "label": lbl, "category": "ADDED"})
                    changes.append(f"+ {lbl}")
                else:
                    prev_t = prev_techs[t_key]
                    if new_t["version"] and prev_t["version"] and new_t["version"] != prev_t["version"]:
                        lbl = f"Technology version changed: {new_t['name']} {prev_t['version']} -> {new_t['version']}"
                        changed.append({"type": "Technology", "label": lbl, "category": "CHANGED"})
                        changes.append(f"~ {lbl}")
                    else:
                        lbl = f"Technology: {new_t['name']}"
                        unchanged.append({"type": "Technology", "label": lbl, "category": "UNCHANGED"})

            for t_key, prev_t in prev_techs.items():
                if t_key not in new_techs and new_techs:
                    lbl = f"Technology removed: {prev_t['name']}"
                    removed.append({"type": "Technology", "label": lbl, "category": "REMOVED"})
                    changes.append(f"- {lbl}")

        # 4. Compare Web Endpoints & Metadata
        if isinstance(web_data, dict) and web_data:
            prev_status = prev_snapshot.get("web_status_code")
            new_status = web_data.get("status_code")
            if new_status and prev_status and new_status != prev_status:
                lbl = f"HTTP status changed: {prev_status} -> {new_status}"
                changed.append({"type": "Web", "label": lbl, "category": "CHANGED"})
                changes.append(f"~ {lbl}")

            prev_title = prev_snapshot.get("web_title")
            new_title = web_data.get("title")
            if new_title and prev_title and new_title != prev_title:
                lbl = f"Page title changed: '{prev_title}' -> '{new_title}'"
                changed.append({"type": "Web", "label": lbl, "category": "CHANGED"})
                changes.append(f"~ {lbl}")

            prev_eps = {e["path"]: e for e in prev_snapshot.get("endpoints", [])}
            new_eps = {}
            for ep in web_data.get("endpoints", []):
                ep_path = ep.get("path") if isinstance(ep, dict) else str(ep)
                if ep_path:
                    new_eps[ep_path] = ep

            for ep_path in new_eps:
                if ep_path not in prev_eps:
                    lbl = f"Endpoint discovered: {ep_path}"
                    added.append({"type": "Endpoint", "label": lbl, "category": "ADDED"})
                    changes.append(f"+ {lbl}")

        # 5. Compare SSL/TLS Certificate Info
        recon_data = new_results.get("recon", {})
        if isinstance(recon_data, dict):
            cert_info = recon_data.get("certificate_info") or recon_data.get("ssl")
            if isinstance(cert_info, dict):
                new_issuer = str(cert_info.get("issuer", ""))
                prev_issuer = prev_snapshot.get("cert_issuer", "")
                if new_issuer and prev_issuer and new_issuer != prev_issuer:
                    lbl = f"SSL Certificate issuer changed: {prev_issuer} -> {new_issuer}"
                    changed.append({"type": "Certificate", "label": lbl, "category": "CHANGED"})
                    changes.append(f"~ {lbl}")

        # Generate summary string
        summary = ChangeDetector.generate_change_summary(added, removed, changed)

        return {
            "has_changes": len(changes) > 0,
            "summary": summary,
            "added": added,
            "removed": removed,
            "changed": changed,
            "unchanged": unchanged,
            "changes": changes,
            "counts": {
                "added": len(added),
                "removed": len(removed),
                "changed": len(changed),
                "unchanged": len(unchanged),
                "total": len(changes)
            }
        }

    @staticmethod
    def generate_change_summary(added: list, removed: list, changed: list) -> str:
        """Generates a concise bullet point summary of changes."""
        parts = []
        if added:
            parts.append(f"+ {len(added)} added")
        if removed:
            parts.append(f"- {len(removed)} removed")
        if changed:
            parts.append(f"~ {len(changed)} changed")

        if not parts:
            return "No significant changes detected."
        return ", ".join(parts)

    @staticmethod
    def _extract_tech_dict(web_data: dict) -> dict:
        techs = {}
        if not isinstance(web_data, dict):
            return techs
        
        # Check 'technologies' list
        for t in web_data.get("technologies", []):
            if isinstance(t, dict) and t.get("name"):
                techs[t["name"]] = t.get("version", "")
            elif isinstance(t, str) and t.strip():
                techs[t.strip()] = ""

        # Check 'tech_stack' dict
        ts = web_data.get("tech_stack")
        if isinstance(ts, dict):
            for k, v in ts.items():
                if v and str(v).lower() not in ("none detected", "unknown", "none"):
                    label = k.replace("_", " ").title()
                    techs[label] = str(v)

        return techs

    @staticmethod
    def compare_scans(scan_a_dict: dict, scan_b_dict: dict) -> dict:
        """
        Compares raw results of Scan A vs Scan B side-by-side.
        Extracts Subdomains, Ports & Services, Tech Stack, and Web HTTP metadata.
        """
        results_a = scan_a_dict.get("results_parsed") or scan_a_dict.get("results_summary") or {}
        results_b = scan_b_dict.get("results_parsed") or scan_b_dict.get("results_summary") or {}

        if isinstance(results_a, str):
            try:
                results_a = json.loads(results_a)
            except Exception:
                results_a = {}
        if isinstance(results_b, str):
            try:
                results_b = json.loads(results_b)
            except Exception:
                results_b = {}

        # 1. Ports & Services diff
        ports_a = {f"{s.get('port')}/{s.get('protocol','tcp').lower()}": s.get('service') or s.get('name','unknown')
                   for s in results_a.get("ports", {}).get("services", []) if isinstance(s, dict) and s.get('port')}
        ports_b = {f"{s.get('port')}/{s.get('protocol','tcp').lower()}": s.get('service') or s.get('name','unknown')
                   for s in results_b.get("ports", {}).get("services", []) if isinstance(s, dict) and s.get('port')}

        port_matrix = []
        all_ports = sorted(list(set(ports_a.keys()) | set(ports_b.keys())))
        for p in all_ports:
            in_a = p in ports_a
            in_b = p in ports_b
            if in_a and in_b:
                status = "UNCHANGED"
            elif in_b and not in_a:
                status = "ADDED"
            else:
                status = "REMOVED"
            port_matrix.append({
                "item": p,
                "service": ports_b.get(p) or ports_a.get(p),
                "in_scan_a": in_a,
                "in_scan_b": in_b,
                "status": status
            })

        # 2. Tech Stack diff
        tech_a = ChangeDetector._extract_tech_dict(results_a.get("web", {}))
        tech_b = ChangeDetector._extract_tech_dict(results_b.get("web", {}))

        tech_matrix = []
        all_tech = sorted(list(set(tech_a.keys()) | set(tech_b.keys())))
        for t in all_tech:
            in_a = t in tech_a
            in_b = t in tech_b
            val_a = tech_a.get(t, "")
            val_b = tech_b.get(t, "")

            if in_a and in_b:
                status = "CHANGED" if (val_a and val_b and val_a != val_b) else "UNCHANGED"
            elif in_b and not in_a:
                status = "ADDED"
            else:
                status = "REMOVED"
            tech_matrix.append({
                "item": t,
                "version_a": val_a,
                "version_b": val_b,
                "status": status
            })

        # 3. Subdomains diff
        subs_a = {s.get("subdomain"): s.get("ip_address") for s in results_a.get("subdomain", {}).get("subdomains", []) if isinstance(s, dict) and s.get("subdomain")}
        subs_b = {s.get("subdomain"): s.get("ip_address") for s in results_b.get("subdomain", {}).get("subdomains", []) if isinstance(s, dict) and s.get("subdomain")}

        sub_matrix = []
        all_subs = sorted(list(set(subs_a.keys()) | set(subs_b.keys())))
        for sub in all_subs:
            in_a = sub in subs_a
            in_b = sub in subs_b
            if in_a and in_b:
                ip_a = subs_a.get(sub, "")
                ip_b = subs_b.get(sub, "")
                status = "CHANGED" if (ip_a and ip_b and ip_a != ip_b) else "UNCHANGED"
            elif in_b and not in_a:
                status = "ADDED"
            else:
                status = "REMOVED"
            sub_matrix.append({
                "item": sub,
                "ip_a": subs_a.get(sub, "Not Resolved"),
                "ip_b": subs_b.get(sub, "Not Resolved"),
                "status": status
            })

        return {
            "scan_a_id": scan_a_dict.get("id"),
            "scan_b_id": scan_b_dict.get("id"),
            "ports_diff": port_matrix,
            "tech_diff": tech_matrix,
            "subdomains_diff": sub_matrix
        }
