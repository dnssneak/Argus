import os
import logging
import requests

logger = logging.getLogger(__name__)

def _load_env_file():
    """Auto-load .env file if present."""
    for p in ['.env', '../.env', 'backend/.env']:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() not in os.environ:
                                os.environ[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass

_load_env_file()

class AIRemediationAdvisor:
    """
    AI / LLM Remediation Advisor Engine for Argus 2.0.
    
    Automatically processes security findings during correlation/ingestion:
    - Case A (Baseline Fix Exists): Enhances and refines baseline check fix with AI reasoning.
    - Case B (Unseen / Novel Finding): Scans finding details & asset context to synthesize complete fix strategy.
    
    Supports:
    1. Live LLM Providers (Google Gemini API / OpenAI API via environment variables).
    2. Built-in Local Heuristic AI Synthesizer (Zero-dependency fallback when offline or no API key set).
    """

    @classmethod
    def enhance_or_generate_remediation(cls, finding_dict: dict, asset_dict: dict = None, baseline_recommendation: str = None) -> tuple[str, bool]:
        """
        Processes finding remediation automatically.
        Returns: (remediation_text, is_ai_enhanced)
        """
        asset_dict = asset_dict or {}
        title = finding_dict.get("title", "Security Finding")
        severity = finding_dict.get("severity", "Medium")
        port = finding_dict.get("port")
        service = finding_dict.get("service_name")
        endpoint = finding_dict.get("endpoint")
        asset_name = asset_dict.get("name") or finding_dict.get("asset_name", "Target Asset")
        exposure = asset_dict.get("exposure") or finding_dict.get("exposure", "Internal")
        tech_stack = asset_dict.get("technology_stack") or finding_dict.get("technology", "")

        # If baseline recommendation was already written in recommendation section, use it clean
        if baseline_recommendation and baseline_recommendation.strip():
            return cls._clean_ai_text(baseline_recommendation), False

        # Try Live LLM provider (LiteRouter / OpenRouter) if API key configured for unseen/missing cases
        generic_api_key = os.environ.get("API_KEY") or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LITE_ROUTER_KEY")
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("ARGUS_LLM_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if generic_api_key:
            live_result = cls._call_openrouter_api(generic_api_key, title, severity, port, service, endpoint, asset_name, exposure, tech_stack, None)
            if live_result:
                return live_result, True

        if gemini_key:
            live_result = cls._call_gemini_api(gemini_key, title, severity, port, service, endpoint, asset_name, exposure, tech_stack, None)
            if live_result:
                return live_result, True

        if openai_key:
            live_result = cls._call_openai_api(openai_key, title, severity, port, service, endpoint, asset_name, exposure, tech_stack, None)
            if live_result:
                return live_result, True

        # Fallback to Local Heuristic AI Synthesizer for cases API could not handle
        heuristic_result = cls._synthesize_heuristic_remediation(title, severity, port, service, endpoint, asset_name, exposure, tech_stack, None)
        return cls._clean_ai_text(heuristic_result), True

    @classmethod
    def _clean_ai_text(cls, text: str) -> str:
        """Strip all markdown headers (#) and asterisks (*) from AI responses."""
        if not text:
            return ""
        lines = []
        for line in text.splitlines():
            # Strip leading markdown header markers
            l_str = line.lstrip('#').strip()
            # Convert markdown bullets (* or -) to clean dot bullets
            if l_str.startswith('* ') or l_str.startswith('- '):
                l_str = '• ' + l_str[2:].strip()
            # Remove all remaining '#' and '*' symbols
            l_str = l_str.replace('*', '').replace('#', '')
            if l_str:
                lines.append(l_str)
        return '\n'.join(lines)

    @classmethod
    def _call_openrouter_api(cls, api_key: str, title: str, severity: str, port: str, service: str, endpoint: str, asset_name: str, exposure: str, tech_stack: str, baseline: str) -> str:
        """Call LiteRouter / OpenRouter API with gemma-3-27b-it:free or configured model."""
        import time
        try:
            custom_base = os.environ.get("LITE_ROUTER_URL") or os.environ.get("OPENAI_BASE_URL") or os.environ.get("API_BASE_URL")
            if custom_base:
                custom_base = custom_base.rstrip('/')
                url = custom_base if custom_base.endswith("/chat/completions") else f"{custom_base}/chat/completions"
            else:
                url = "https://openrouter.ai/api/v1/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:5000",
                "X-Title": "Argus 2.0 Security Platform"
            }
            prompt = cls._build_llm_prompt(title, severity, port, service, endpoint, asset_name, exposure, tech_stack, baseline)
            model = os.environ.get("LLM_MODEL") or "gemma-3-27b-it:free"
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are an expert cybersecurity remediation advisor. Do NOT use markdown headers (# or ##) or bold/italic asterisk markers (* or **). Output clean, plain text bullet points or paragraphs only."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.2
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["message"]["content"].strip()
                    return cls._clean_ai_text(text)
            else:
                logger.warning(f"LiteRouter API status {resp.status_code}, falling back to Heuristic AI advisor.")
        except Exception as e:
            logger.warning(f"LiteRouter API call failed: {e}. Falling back to Heuristic AI advisor.")
        return None

    @classmethod
    def _call_gemini_api(cls, api_key: str, title: str, severity: str, port: str, service: str, endpoint: str, asset_name: str, exposure: str, tech_stack: str, baseline: str) -> str:
        """Call Google Gemini REST API."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            prompt = cls._build_llm_prompt(title, severity, port, service, endpoint, asset_name, exposure, tech_stack, baseline)
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}
            }
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return cls._clean_ai_text(text)
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}. Falling back to Heuristic AI advisor.")
        return None

    @classmethod
    def _call_openai_api(cls, api_key: str, title: str, severity: str, port: str, service: str, endpoint: str, asset_name: str, exposure: str, tech_stack: str, baseline: str) -> str:
        """Call OpenAI Chat Completions API."""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            prompt = cls._build_llm_prompt(title, severity, port, service, endpoint, asset_name, exposure, tech_stack, baseline)
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "system", "content": "You are an expert cybersecurity remediation advisor for enterprise attack surface management."},
                             {"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.2
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                return cls._clean_ai_text(text)
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back to Heuristic AI advisor.")
        return None

    @classmethod
    def _build_llm_prompt(cls, title: str, severity: str, port: str, service: str, endpoint: str, asset_name: str, exposure: str, tech_stack: str, baseline: str) -> str:
        """Build structured LLM prompt."""
        context = f"Finding: '{title}' (Severity: {severity})\nAsset: {asset_name} ({exposure})\n"
        if port: context += f"Port: {port}\n"
        if service: context += f"Service: {service}\n"
        if endpoint: context += f"Endpoint: {endpoint}\n"
        if tech_stack: context += f"Technologies: {tech_stack}\n"

        return f"{context}\nTask: Provide a concise, highly specific, 2-bullet actionable security remediation guide for this finding."

    @classmethod
    def _synthesize_heuristic_remediation(cls, title: str, severity: str, port: str, service: str, endpoint: str, asset_name: str, exposure: str, tech_stack: str, baseline: str) -> str:
        """
        Local Heuristic AI Synthesizer.
        Dynamically analyzes vulnerability type, protocols, exposure, and baseline checks.
        """
        t_lower = title.lower()
        p_val = str(port) if port else ""

        # Specific finding category rules
        if "http (port 80)" in t_lower or p_val == "80":
            core_fix = f"Configure HTTP 301 redirection to HTTPS (Port 443) and enforce TLS 1.3 encryption on {asset_name}"
        elif "https (port 443)" in t_lower or p_val == "443":
            core_fix = f"Harden TLS cipher suites, enforce HTTP Strict Transport Security (HSTS), and mandate WAF inspection on {asset_name}"
        elif "admin" in t_lower:
            core_fix = f"Enforce strict IP whitelisting, Multi-Factor Authentication (MFA), and rate limiting on administrative portal {asset_name}"
        elif "git" in t_lower:
            core_fix = f"Restrict public access to source control repository on {asset_name}; enforce SAML/SSO authentication"
        elif "dev" in t_lower or "stage" in t_lower or "test" in t_lower:
            core_fix = f"Isolate non-production environment ({asset_name}) behind enterprise VPN gateway"
        elif "api" in t_lower:
            core_fix = f"Enforce OAuth2/JWT API token authentication, rate limiting, and CORS restrictions on {asset_name}"
        elif p_val in ["22", "21", "23", "3389", "445"]:
            core_fix = f"Restrict public exposure of port {p_val} ({service or 'management listener'}) via host firewall or private VPN"
        elif p_val in ["3306", "5432", "1433", "27017", "6379", "9200"]:
            core_fix = f"Isolate database listener on port {p_val} to internal loopback/VPC; mandate TLS certificate authentication on {asset_name}"
        elif endpoint or "endpoint" in t_lower:
            core_fix = f"Enforce strict authorization & role-based access control (RBAC) on path {endpoint or 'sensitive endpoint'}"
        elif baseline and len(baseline) > 10:
            core_fix = baseline.rstrip('.')
        else:
            core_fix = f"Enforce least-privilege access controls and strict security policies on {asset_name}"

        # Context Enhancement
        if exposure == "Internet-Facing":
            enhanced_step2 = "Verify perimeter firewall rules (AWS Security Group / Cloudflare / WAF) to block unauthorized external traffic."
        else:
            enhanced_step2 = "Audit internal network segmentation and enforce zero-trust network access policies."

        if enhanced_step2.lower() in core_fix.lower():
            return core_fix + "."
        return f"{core_fix}. {enhanced_step2}"
