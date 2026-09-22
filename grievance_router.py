"""
Core Grievance Routing Engine using Knowledge Graph
"""

from supabase_client import SupabaseGraphClient
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from config import SCHEME_KEYWORDS, FAILURE_KEYWORDS, SERVICE_KEYWORDS

@dataclass
class RoutingDecision:
    """Output structure for routing decision"""
    primary_owner: str
    primary_owner_id: int
    failure_types: List[str]
    resolution_paths: List[Dict]
    appeal_authorities: List[Dict]
    graph_path: List[Tuple[str, str, str]]
    confidence_score: float
    explanation: str

class GrievanceRouter:
    """Main routing engine"""
    
    def __init__(self):
        self.db = SupabaseGraphClient()
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract relevant entities from grievance text"""
        
        text_lower = text.lower()
        
        entities = {
            'schemes': [],
            'services': [],
            'failure_types': []
        }
        
        # Extract schemes
        for scheme_key, keywords in SCHEME_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities['schemes'].append(scheme_key)
                    break
        
        # Extract services
        for service_key, keywords in SERVICE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities['services'].append(service_key)
                    break
        
        # Extract failure types
        for failure_key, keywords in FAILURE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities['failure_types'].append(failure_key)
                    break
        
        return entities
    
    def route_grievance(self, grievance_text: str) -> RoutingDecision:
        """
        Main routing logic:
        1. Extract entities
        2. Find scheme
        3. Find department
        4. Identify failures
        5. Find resolutions
        6. Build explanation
        """
        
        # Step 1: Extract entities
        entities = self.extract_entities(grievance_text)
        
        # Step 2: Find scheme (default to PM-Kisan if none found)
        scheme = None
        
        if entities['schemes']:
            scheme_keyword = entities['schemes'][0]
            if scheme_keyword == 'pm_kisan':
                scheme = self.db.get_scheme_by_keyword('PM-Kisan')
            elif scheme_keyword == 'dbt':
                scheme = self.db.get_scheme_by_keyword('Direct Benefit')
        
        if not scheme:
            scheme = self.db.get_scheme_by_keyword('PM-Kisan')
        
        if not scheme:
            raise ValueError("No scheme found in grievance")
        
        scheme_id = scheme['id']
        
        # Step 3: Find department
        department = self.db.get_department_by_scheme(scheme_id)
        if not department:
            raise ValueError(f"No department found for scheme {scheme_id}")
        
        dept_id = department['id']
        
        # Step 4: Get services used by scheme
        services = self.db.get_services_by_scheme(scheme_id)
        
        # Step 5: Find failure types
        identified_failures = []
        identified_failure_objs = []
        
        # First try to match extracted failure types
        all_failures = self.db.get_all_failure_types()
        
        for extracted_failure in entities['failure_types']:
            for failure in all_failures:
                if extracted_failure.replace('_', ' ').lower() in failure['name'].lower():
                    identified_failures.append(failure['name'])
                    identified_failure_objs.append(failure)
                    break
        
        # If no failures extracted, infer from services
        if not identified_failures:
            for service in services[:2]:  # Check first 2 services
                service_failures = self.db.get_failures_by_service(service['id'])
                for failure in service_failures[:1]:  # Top failure
                    identified_failures.append(failure['name'])
                    identified_failure_objs.append(failure)
        
        # Step 6: Find resolution paths
        resolution_paths = []
        graph_path = []
        
        for failure_obj in identified_failure_objs[:1]:  # Use first failure for path
            failure_resolutions = self.db.get_resolutions_by_failure(failure_obj['id'])
            
            for resolution in failure_resolutions:
                resolution_authorities = self.db.get_authorities_by_resolution(resolution['id'])
                
                if resolution_authorities:
                    resolution_paths.append({
                        'id': resolution['id'],
                        'name': resolution['name'],
                        'steps': resolution['steps'],
                        'timeToResolve': resolution['time_to_resolve'],
                        'authority': resolution_authorities[0]['name']
                    })
            
            # Build graph path
            if failure_resolutions and resolution_paths:
                graph_path = [
                    (scheme['name'], "uses", services[0]['name'] if services else "Service"),
                    (services[0]['name'] if services else "Service", "can fail with", failure_obj['name']),
                    (failure_obj['name'], "resolved by", resolution_paths[0]['name']),
                    (resolution_paths[0]['name'], "owned by", resolution_paths[0]['authority'])
                ]
        
        # Step 7: Get appeal authorities
        appeal_authorities = self.db.get_authorities_by_department(dept_id)
        
        # Step 8: Calculate confidence
        confidence = self._calculate_confidence(
            len(identified_failures),
            len(resolution_paths),
            len(appeal_authorities)
        )
        
        # Step 9: Build explanation
        explanation = self._build_explanation(
            scheme, department, identified_failures, 
            resolution_paths, appeal_authorities
        )
        
        # Step 10: Log grievance
        self.db.log_grievance(
            grievance_text=grievance_text,
            owner_dept_id=dept_id,
            confidence=confidence,
            failure_types=identified_failures,
            explanation=explanation
        )
        
        return RoutingDecision(
            primary_owner=department['name'],
            primary_owner_id=dept_id,
            failure_types=identified_failures,
            resolution_paths=resolution_paths,
            appeal_authorities=appeal_authorities,
            graph_path=graph_path,
            confidence_score=confidence,
            explanation=explanation
        )
    
    def _calculate_confidence(self, num_failures: int, num_resolutions: int, 
                             num_authorities: int) -> float:
        """Calculate routing confidence score"""
        
        base_score = 0.70
        
        if num_failures >= 1:
            base_score += 0.15
        if num_resolutions >= 1:
            base_score += 0.10
        if num_authorities >= 1:
            base_score += 0.05
        
        return min(base_score, 0.99)
    
    def _build_explanation(self, scheme: Dict, dept: Dict, failures: List[str],
                          resolutions: List[Dict], authorities: List[Dict]) -> str:
        """Build human-readable explanation"""
        
        explanation = f"""
### 🎯 Grievance Routing Analysis

**Your Complaint Concerns:** {scheme['name']} (Scheme)

**Root Causes Identified:**
"""
        
        for i, failure in enumerate(failures, 1):
            explanation += f"\n- {i}. {failure}"
        
        explanation += f"""

**Primary Owner (Department):** {dept['name']}

**Recommended Resolution Steps:**
"""
        
        for i, resolution in enumerate(resolutions, 1):
            explanation += f"""
{i}. **{resolution['name']}**
   - Authority: {resolution['authority']}
   - Expected Time: {resolution['timeToResolve']}
   - Steps: {resolution['steps']}
"""
        
        explanation += "\n**Appeal Path (If Needed):**\n"
        for auth in authorities:
            explanation += f"- {auth['level']}: {auth['name']}\n"
        
        return explanation