"""
Supabase Database Client for Knowledge Graph
"""

import os
import streamlit as st
from supabase import create_client, Client
from typing import List, Dict, Optional


class SupabaseGraphClient:
    """Interface with Supabase PostgreSQL Knowledge Graph"""

    def __init__(self):
        # 1. Fetch credentials safely from st.secrets or environment variables
        if "supabase" in st.secrets:
            self.url = st.secrets["supabase"].get("SUPABASE_URL")
            self.key = st.secrets["supabase"].get("SUPABASE_KEY")
        else:
            self.url = os.environ.get("SUPABASE_URL")
            self.key = os.environ.get("SUPABASE_KEY")

        # Fallback to imported config variables if not found above
        if not self.url or not self.key:
            try:
                from config import SUPABASE_URL, SUPABASE_KEY
                self.url = self.url or SUPABASE_URL
                self.key = self.key or SUPABASE_KEY
            except ImportError:
                pass

        # Validate presence of keys
        if not self.url or not self.key:
            st.error("❌ Supabase credentials missing. Check your .streamlit/secrets.toml file.")
            st.stop()

        # Clean strings to prevent unexpected quotes, spaces, or newlines
        self.url = str(self.url).strip().strip("'").strip('"')
        self.key = str(self.key).strip().strip("'").strip('"')

        # Initialize client
        try:
            self.client: Client = create_client(self.url, self.key)
        except Exception as e:
            st.error(f"❌ Failed to connect to Supabase: {str(e)}")
            st.stop()

    # ==================== READ OPERATIONS ====================

    def get_scheme_by_keyword(self, keyword: str) -> Optional[Dict]:
        """Find scheme by keyword"""
        response = self.client.table("schemes").select("*").execute()
        schemes = response.data

        keyword_lower = keyword.lower()
        for scheme in schemes:
            if keyword_lower in scheme["name"].lower():
                return scheme

        return None

    def get_all_schemes(self) -> List[Dict]:
        """Get all schemes"""
        response = self.client.table("schemes").select("*").execute()
        return response.data

    def get_services_by_scheme(self, scheme_id: int) -> List[Dict]:
        """Get services used by a scheme"""
        response = (
            self.client.table("scheme_service")
            .select("service_id, services(id, name, service_type)")
            .eq("scheme_id", scheme_id)
            .execute()
        )
        return [item["services"] for item in response.data if item.get("services")]

    def get_failures_by_service(self, service_id: int) -> List[Dict]:
        """Get possible failure types for a service"""
        response = (
            self.client.table("service_failure")
            .select("failure_id, failure_types(id, name, severity, category)")
            .eq("service_id", service_id)
            .execute()
        )
        return [item["failure_types"] for item in response.data if item.get("failure_types")]

    def get_resolutions_by_failure(self, failure_id: int) -> List[Dict]:
        """Get resolution paths for a failure"""
        response = (
            self.client.table("failure_resolution")
            .select("resolution_id, resolution_paths(id, name, steps, time_to_resolve, authority)")
            .eq("failure_id", failure_id)
            .execute()
        )
        return [item["resolution_paths"] for item in response.data if item.get("resolution_paths")]

    def get_authorities_by_resolution(self, resolution_id: int) -> List[Dict]:
        """Get authorities responsible for resolution"""
        response = (
            self.client.table("resolution_authority")
            .select("authority_id, appeal_authorities(id, name, level, contact)")
            .eq("resolution_id", resolution_id)
            .execute()
        )
        return [item["appeal_authorities"] for item in response.data if item.get("appeal_authorities")]

    def get_authorities_by_department(self, department_id: int) -> List[Dict]:
        """Get appeal authorities for a department"""
        response = (
            self.client.table("department_authority")
            .select("authority_id, appeal_authorities(id, name, level, contact)")
            .eq("department_id", department_id)
            .execute()
        )
        return [item["appeal_authorities"] for item in response.data if item.get("appeal_authorities")]

    def get_department_by_scheme(self, scheme_id: int) -> Optional[Dict]:
        """Get department administering a scheme"""
        response = (
            self.client.table("schemes")
            .select("department_id, departments(id, name, state)")
            .eq("id", scheme_id)
            .execute()
        )

        if response.data and response.data[0].get("departments"):
            return response.data[0]["departments"]
        return None

    def get_all_failure_types(self) -> List[Dict]:
        """Get all possible failure types"""
        response = self.client.table("failure_types").select("*").execute()
        return response.data

    # ==================== WRITE OPERATIONS ====================

    def log_grievance(
        self,
        grievance_text: str,
        owner_dept_id: int,
        confidence: float,
        failure_types: List[str],
        explanation: str,
    ) -> Dict:
        """Log routed grievance for audit trail"""
        response = (
            self.client.table("grievance_audit")
            .insert(
                {
                    "grievance_text": grievance_text,
                    "owner_department_id": owner_dept_id,
                    "confidence_score": confidence,
                    "failure_types": failure_types,
                    "explanation": explanation,
                }
            )
            .execute()
        )

        return response.data[0] if response.data else {}

    # ==================== ANALYTICS ====================

    def get_audit_summary(self) -> Dict:
        """Get summary statistics of routed grievances"""
        response = self.client.table("grievance_audit").select("*").execute()
        audits = response.data

        if not audits:
            return {
                "total": 0,
                "avg_confidence": 0,
                "by_department": {},
                "by_failure_type": {},
            }

        by_dept = {}
        by_failure = {}

        for audit in audits:
            dept_id = audit.get("owner_department_id")
            if dept_id is not None:
                by_dept[dept_id] = by_dept.get(dept_id, 0) + 1

            if audit.get("failure_types"):
                for failure in audit["failure_types"]:
                    by_failure[failure] = by_failure.get(failure, 0) + 1

        avg_confidence = sum(a.get("confidence_score", 0) for a in audits) / len(audits)

        return {
            "total": len(audits),
            "avg_confidence": avg_confidence,
            "by_department": by_dept,
            "by_failure_type": by_failure,
        }

    def get_audit_history(self, limit: int = 50) -> List[Dict]:
        """Get recent grievance audit logs"""
        response = (
            self.client.table("grievance_audit")
            .select("*")
            .order("submitted_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data