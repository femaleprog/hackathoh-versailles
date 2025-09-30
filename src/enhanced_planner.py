#!/usr/bin/env python3
"""
Enhanced Query Planner for Versailles Chatbot
Architecture: Planner → Subqueries → Faceted RAG → Synthesizer
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

from dotenv import load_dotenv
from llama_index.llms.mistralai import MistralAI


class Facet(Enum):
    """Different facets for information retrieval"""
    ITINERARY = "itinerary"           # Route planning, timing
    TICKETS = "tickets"               # Pricing, booking, access
    FAMILY = "family"                 # Child-friendly, accessibility
    WEATHER = "weather"               # Weather conditions, seasonal
    HISTORY = "history"               # Historical information
    PRACTICAL = "practical"           # Opening hours, crowds, logistics
    CULTURAL = "cultural"             # Art, architecture, exhibitions


class UserProfile(Enum):
    """User profile types"""
    FAMILY_WITH_KIDS = "family_with_kids"
    FAMILY_WITH_ELDERLY = "family_with_elderly"
    ACCESSIBILITY_NEEDS = "accessibility_needs"
    ELDERLY_GROUP = "elderly_group"
    COUPLE = "couple"
    SOLO_TRAVELER = "solo_traveler"
    GROUP = "group"
    STUDENT = "student"


@dataclass
class UserConstraints:
    """User constraints and preferences"""
    duration: Optional[str] = None          # "2 hours", "half day", "full day"
    budget: Optional[str] = None            # "low", "medium", "high"
    group_size: Optional[int] = None        # Number of people
    has_children: Optional[bool] = None     # Traveling with children
    has_elderly: Optional[bool] = None      # Traveling with elderly people
    has_disabilities: Optional[bool] = None # Has accessibility needs
    season: Optional[str] = None            # "spring", "summer", "autumn", "winter"
    language: Optional[str] = None          # "french", "english", etc.
    outdoor_preference: Optional[bool] = None  # Prefers outdoor activities
    mobility: Optional[str] = None          # "full", "limited", "wheelchair", "walker", "cane"
    accessibility_needs: List[str] = None   # ["wheelchair", "visual_impaired", "hearing_impaired", "cognitive"]
    medical_conditions: Optional[bool] = None # Has medical conditions requiring special care
    rest_frequency: Optional[str] = None    # "frequent", "moderate", "minimal"
    interests: List[str] = None             # ["history", "art", "gardens", "architecture"]
    
    def __post_init__(self):
        if self.interests is None:
            self.interests = []
        if self.accessibility_needs is None:
            self.accessibility_needs = []


@dataclass
class SubQuery:
    """A sub-query for faceted retrieval"""
    facet: Facet
    query: str
    priority: float                         # 0.0 to 1.0
    required_tools: List[str]
    constraints: Dict[str, Any]


@dataclass
class InformationGaps:
    """Missing information that could improve planning"""
    missing_date: bool = False
    missing_group_composition: bool = False  
    missing_duration: bool = False
    missing_budget: bool = False
    suggested_questions: List[str] = None
    
    def __post_init__(self):
        if self.suggested_questions is None:
            self.suggested_questions = []


@dataclass
class Plan:
    """Structured plan for query processing"""
    user_constraints: UserConstraints
    user_profile: UserProfile
    subqueries: List[SubQuery]
    confidence: float
    reasoning: str
    information_gaps: InformationGaps


@dataclass
class EvidenceChunk:
    """Evidence from a specific source"""
    source: str                             # "official_kb", "weather_api", "maps_api", etc.
    content: str
    score: float                           # BM25/vector similarity × authority weight
    authority_weight: float                # Source authority (0.0 to 1.0)
    facet: Facet
    metadata: Dict[str, Any]


@dataclass
class PartialAnswer:
    """Partial answer for a specific facet"""
    facet: Facet
    answer: str
    evidence_chunks: List[EvidenceChunk]
    confidence: float
    constraints_satisfied: List[str]


@dataclass
class FinalAnswer:
    """Final synthesized answer"""
    answer: str
    recommendations: List[str]
    source_citations: List[str]
    constraints_check: Dict[str, bool]
    confidence: float
    reasoning: str
    follow_up_questions: List[str] = None  # Questions to gather missing info
    information_completeness: float = 1.0  # 0.0 to 1.0
    
    def __post_init__(self):
        if self.follow_up_questions is None:
            self.follow_up_questions = []


class EnhancedQueryPlanner:
    """
    Enhanced Query Planner with user profiling and constraint extraction
    """
    
    def __init__(self):
        load_dotenv()
        
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is required")
        
        self.llm = MistralAI(model="mistral-medium-latest", api_key=api_key)
        
        # Authority weights for different sources
        self.authority_weights = {
            "official_kb": 1.0,           # Official Versailles knowledge base
            "weather_api": 0.9,           # Weather APIs
            "maps_api": 0.9,              # Google Maps/Places
            "schedule_api": 0.95,         # Official schedule
            "faq_kb": 0.7,                # FAQ/Experience knowledge base
            "external_web": 0.5           # External web sources
        }
    
    async def extract_user_constraints(self, query: str) -> UserConstraints:
        """Extract user constraints and preferences from natural language"""
        
        # Simple fallback extraction using regex patterns
        constraints = UserConstraints()
        query_lower = query.lower()
        
        # Extract family/group information
        if "family" in query_lower or "families" in query_lower:
            constraints.has_children = True
            constraints.group_size = 4  # Typical family size
        elif "kids" in query_lower or "children" in query_lower:
            constraints.has_children = True
        elif "group" in query_lower:
            constraints.group_size = 6  # Typical group
        
        # Extract elderly/senior information
        elderly_keywords = ["elderly", "senior", "seniors", "老人", "老年人", "grandparents", "grandmother", "grandfather"]
        if any(keyword in query_lower for keyword in elderly_keywords):
            constraints.has_elderly = True
            constraints.rest_frequency = "frequent"
        
        # Extract accessibility needs
        accessibility_needs = []
        mobility_level = "full"
        
        # Wheelchair accessibility
        wheelchair_keywords = ["wheelchair", "轮椅", "fauteuil roulant", "mobility scooter", "rollator"]
        if any(keyword in query_lower for keyword in wheelchair_keywords):
            constraints.has_disabilities = True
            accessibility_needs.append("wheelchair")
            mobility_level = "wheelchair"
        
        # Walking aids
        walking_aid_keywords = ["walker", "walking stick", "cane", "拐杖", "助行器", "canne"]
        if any(keyword in query_lower for keyword in walking_aid_keywords):
            constraints.has_disabilities = True
            accessibility_needs.append("mobility_aid")
            mobility_level = "limited"
        
        # Visual impairment
        visual_keywords = ["blind", "visually impaired", "vision", "sight", "盲人", "视力", "malvoyant", "aveugle"]
        if any(keyword in query_lower for keyword in visual_keywords):
            constraints.has_disabilities = True
            accessibility_needs.append("visual_impaired")
        
        # Hearing impairment
        hearing_keywords = ["deaf", "hearing impaired", "hearing aid", "聋人", "听力", "sourd", "malentendant"]
        if any(keyword in query_lower for keyword in hearing_keywords):
            constraints.has_disabilities = True
            accessibility_needs.append("hearing_impaired")
        
        # Cognitive/mental health
        cognitive_keywords = ["autism", "dementia", "alzheimer", "cognitive", "mental health", "自闭症", "痴呆"]
        if any(keyword in query_lower for keyword in cognitive_keywords):
            constraints.has_disabilities = True
            accessibility_needs.append("cognitive")
        
        # General accessibility mentions
        accessibility_keywords = ["accessibility", "accessible", "disabled", "disability", "handicap", "无障碍", "残疾"]
        if any(keyword in query_lower for keyword in accessibility_keywords):
            constraints.has_disabilities = True
        
        # Medical conditions
        medical_keywords = ["medical condition", "health condition", "chronic", "medication", "疾病", "慢性病"]
        if any(keyword in query_lower for keyword in medical_keywords):
            constraints.medical_conditions = True
            constraints.rest_frequency = "frequent"
        
        # Rest frequency indicators
        if any(word in query_lower for word in ["tired easily", "frequent breaks", "rest often", "容易疲劳"]):
            constraints.rest_frequency = "frequent"
        elif any(word in query_lower for word in ["limited walking", "short distances", "步行困难"]):
            constraints.rest_frequency = "moderate"
        
        constraints.mobility = mobility_level
        constraints.accessibility_needs = accessibility_needs
        
        # Extract duration
        if "half day" in query_lower or "morning" in query_lower:
            constraints.duration = "half day"
        elif "full day" in query_lower or "whole day" in query_lower:
            constraints.duration = "full day"
        elif "hour" in query_lower:
            import re
            hours = re.search(r"(\d+)\s*hours?", query_lower)
            if hours:
                constraints.duration = f"{hours.group(1)} hours"
        
        # Extract budget
        if "budget" in query_lower or "cheap" in query_lower or "affordable" in query_lower:
            constraints.budget = "low"
        elif "luxury" in query_lower or "premium" in query_lower:
            constraints.budget = "high"
        
        # Extract interests
        interests = []
        if "history" in query_lower or "historical" in query_lower:
            interests.append("history")
        if "art" in query_lower or "artistic" in query_lower:
            interests.append("art")
        if "garden" in query_lower or "outdoor" in query_lower:
            interests.append("gardens")
        if "architecture" in query_lower:
            interests.append("architecture")
        
        constraints.interests = interests
        
        return constraints
    
    def analyze_information_completeness(self, query: str, constraints: UserConstraints) -> InformationGaps:
        """Analyze what key information is missing for optimal planning"""
        
        gaps = InformationGaps()
        query_lower = query.lower()
        
        # Check for date information
        date_indicators = [
            "today", "tomorrow", "next week", "this weekend", "monday", "tuesday", "wednesday", 
            "thursday", "friday", "saturday", "sunday", "janvier", "february", "mars", "april",
            "今天", "明天", "下周", "周末", "lundi", "mardi", "mercredi", "jeudi", "vendredi"
        ]
        
        has_date_info = (
            constraints.season is not None or
            any(indicator in query_lower for indicator in date_indicators) or
            any(char.isdigit() for char in query if "/" in query or "-" in query)
        )
        
        if not has_date_info:
            gaps.missing_date = True
            gaps.suggested_questions.append("📅 Quelle date prévoyez-vous pour votre visite ? (Cela m'aidera à vérifier les horaires et l'affluence)")
        
        # Check for group composition
        group_indicators = [
            "family", "kids", "children", "elderly", "senior", "group", "couple", "alone", "solo",
            "famille", "enfants", "personnes âgées", "groupe", "seul", "一家人", "孩子", "老人"
        ]
        
        has_group_info = (
            constraints.group_size is not None or
            constraints.has_children is not None or
            constraints.has_elderly is not None or
            any(indicator in query_lower for indicator in group_indicators)
        )
        
        if not has_group_info:
            gaps.missing_group_composition = True
            gaps.suggested_questions.append("👥 Combien de personnes vous accompagnent ? Y a-t-il des enfants ou des personnes âgées ?")
        
        # Check for duration
        duration_indicators = [
            "hour", "day", "morning", "afternoon", "evening", "half day", "full day",
            "heure", "journée", "matin", "après-midi", "soir", "demi-journée", "小时", "天", "上午"
        ]
        
        has_duration_info = (
            constraints.duration is not None or
            any(indicator in query_lower for indicator in duration_indicators)
        )
        
        if not has_duration_info:
            gaps.missing_duration = True
            gaps.suggested_questions.append("⏰ Combien de temps souhaitez-vous consacrer à votre visite ? (2h, demi-journée, journée complète)")
        
        # Check for budget
        budget_indicators = [
            "budget", "price", "cost", "expensive", "cheap", "affordable", "luxury", "premium",
            "prix", "coût", "cher", "abordable", "luxe", "économique", "预算", "价格", "便宜"
        ]
        
        has_budget_info = (
            constraints.budget is not None or
            any(indicator in query_lower for indicator in budget_indicators)
        )
        
        if not has_budget_info:
            gaps.missing_budget = True
            gaps.suggested_questions.append("💰 Avez-vous un budget particulier en tête ? (Cela m'aidera à recommander les bonnes options de billets)")
        
        return gaps
    
    def determine_user_profile(self, constraints: UserConstraints) -> UserProfile:
        """Determine user profile based on constraints with priority for accessibility needs"""
        
        # Priority 1: Accessibility needs (highest priority)
        if constraints.has_disabilities or constraints.mobility in ["wheelchair", "limited"]:
            return UserProfile.ACCESSIBILITY_NEEDS
        
        # Priority 2: Mixed family groups
        if constraints.has_children and constraints.has_elderly:
            return UserProfile.FAMILY_WITH_ELDERLY
        
        # Priority 3: Specific age groups
        elif constraints.has_elderly or constraints.rest_frequency == "frequent":
            return UserProfile.ELDERLY_GROUP
        elif constraints.has_children:
            return UserProfile.FAMILY_WITH_KIDS
        
        # Priority 4: Group size
        elif constraints.group_size and constraints.group_size > 4:
            return UserProfile.GROUP
        elif constraints.group_size == 2:
            return UserProfile.COUPLE
        
        # Priority 5: Other indicators
        elif "student" in str(constraints.budget).lower():
            return UserProfile.STUDENT
        else:
            return UserProfile.SOLO_TRAVELER
    
    async def generate_subqueries(self, query: str, constraints: UserConstraints, profile: UserProfile) -> List[SubQuery]:
        """Generate faceted sub-queries based on the original query and user profile"""
        
        subqueries = []
        
        # Always include history/cultural facet
        subqueries.append(SubQuery(
            facet=Facet.HISTORY,
            query=f"Historical and cultural information about Versailles for {profile.value}",
            priority=1.0,
            required_tools=["versailles_expert"],
            constraints=asdict(constraints)
        ))
        
        # Add accessibility-specific facet (highest priority)
        if profile == UserProfile.ACCESSIBILITY_NEEDS:
            subqueries.append(SubQuery(
                facet=Facet.PRACTICAL,
                query=f"Wheelchair accessibility, elevator access, accessible restrooms, and mobility assistance at Versailles",
                priority=1.0,
                required_tools=["versailles_expert"],
                constraints=asdict(constraints)
            ))
        
        # Add elderly-specific facet
        if profile in [UserProfile.ELDERLY_GROUP, UserProfile.FAMILY_WITH_ELDERLY]:
            subqueries.append(SubQuery(
                facet=Facet.PRACTICAL,
                query=f"Senior-friendly areas, rest areas, seating, and reduced walking routes at Versailles",
                priority=0.95,
                required_tools=["versailles_expert"],
                constraints=asdict(constraints)
            ))
        
        # Add family-specific facet if needed
        if profile in [UserProfile.FAMILY_WITH_KIDS, UserProfile.FAMILY_WITH_ELDERLY]:
            subqueries.append(SubQuery(
                facet=Facet.FAMILY,
                query=f"Family-friendly activities and appropriate areas at Versailles for mixed age groups",
                priority=0.9,
                required_tools=["versailles_expert"],
                constraints=asdict(constraints)
            ))
        
        # Add practical information if duration/budget specified
        if constraints.duration or constraints.budget:
            subqueries.append(SubQuery(
                facet=Facet.PRACTICAL,
                query=f"Practical information about visiting Versailles including timing and costs",
                priority=0.8,
                required_tools=["get_versailles_schedule", "versailles_expert"],
                constraints=asdict(constraints)
            ))
        
        # Add itinerary if group size specified
        if constraints.group_size and constraints.group_size > 1:
            subqueries.append(SubQuery(
                facet=Facet.ITINERARY,
                query=f"Recommended route and itinerary for group visit to Versailles",
                priority=0.7,
                required_tools=["search_places_versailles", "versailles_expert"],
                constraints=asdict(constraints)
            ))
        
        return subqueries
    
    async def create_plan(self, query: str) -> Plan:
        """Create a comprehensive plan for query processing"""
        
        # Step 1: Extract user constraints
        constraints = await self.extract_user_constraints(query)
        
        # Step 2: Analyze information completeness
        information_gaps = self.analyze_information_completeness(query, constraints)
        
        # Step 3: Determine user profile
        profile = self.determine_user_profile(constraints)
        
        # Step 4: Generate sub-queries
        subqueries = await self.generate_subqueries(query, constraints, profile)
        
        # Step 5: Calculate overall confidence (reduced if missing key info)
        base_confidence = sum(sq.priority for sq in subqueries) / len(subqueries) if subqueries else 0.0
        
        # Reduce confidence based on missing information
        missing_count = sum([
            information_gaps.missing_date,
            information_gaps.missing_group_composition, 
            information_gaps.missing_duration,
            information_gaps.missing_budget
        ])
        
        confidence_penalty = missing_count * 0.1  # 10% penalty per missing piece
        confidence = max(0.0, base_confidence - confidence_penalty)
        
        # Enhanced reasoning
        reasoning_parts = [f"Identified {profile.value} profile with {len(subqueries)} faceted sub-queries"]
        if missing_count > 0:
            reasoning_parts.append(f"Missing {missing_count} key information pieces")
        
        reasoning = " | ".join(reasoning_parts)
        
        return Plan(
            user_constraints=constraints,
            user_profile=profile,
            subqueries=subqueries,
            confidence=confidence,
            reasoning=reasoning,
            information_gaps=information_gaps
        )


class FacetedRAG:
    """
    Faceted RAG system that routes queries to appropriate knowledge sources
    """
    
    def __init__(self):
        self.authority_weights = {
            "official_kb": 1.0,
            "weather_api": 0.9,
            "maps_api": 0.9,
            "schedule_api": 0.95,
            "faq_kb": 0.7,
            "external_web": 0.5
        }
    
    async def retrieve_evidence(self, subquery: SubQuery) -> List[EvidenceChunk]:
        """Retrieve evidence chunks for a specific sub-query"""
        
        evidence_chunks = []
        
        # Route to appropriate sources based on facet
        if subquery.facet == Facet.WEATHER:
            # Use weather API
            evidence = await self._retrieve_from_weather_api(subquery)
            evidence_chunks.extend(evidence)
        
        elif subquery.facet == Facet.ITINERARY:
            # Use maps API and official KB
            evidence = await self._retrieve_from_maps_api(subquery)
            evidence_chunks.extend(evidence)
        
        elif subquery.facet == Facet.PRACTICAL:
            # Use schedule API and official KB
            evidence = await self._retrieve_from_schedule_api(subquery)
            evidence_chunks.extend(evidence)
        
        # Always include official KB for comprehensive information
        official_evidence = await self._retrieve_from_official_kb(subquery)
        evidence_chunks.extend(official_evidence)
        
        return evidence_chunks
    
    async def _retrieve_from_weather_api(self, subquery: SubQuery) -> List[EvidenceChunk]:
        """Retrieve from weather API"""
        try:
            from src.tools.google import get_weather_in_versailles
            
            days = subquery.constraints.get("days", 3)
            weather_data = get_weather_in_versailles(days)
            
            return [EvidenceChunk(
                source="weather_api",
                content=str(weather_data),
                score=0.9,
                authority_weight=self.authority_weights["weather_api"],
                facet=subquery.facet,
                metadata={"api": "google_weather", "days": days}
            )]
        except Exception as e:
            print(f"Weather API error: {e}")
            return []
    
    async def _retrieve_from_maps_api(self, subquery: SubQuery) -> List[EvidenceChunk]:
        """Retrieve from maps/places API"""
        try:
            from src.tools.google import search_places_in_versailles, get_best_route_between_places
            
            evidence = []
            
            # Extract places from query
            if "search_places_versailles" in subquery.required_tools:
                # Simple place extraction (could be enhanced with NLP)
                places = ["Château de Versailles", "Petit Trianon"]  # Default places
                place_data = search_places_in_versailles(places[0])
                
                evidence.append(EvidenceChunk(
                    source="maps_api",
                    content=str(place_data),
                    score=0.8,
                    authority_weight=self.authority_weights["maps_api"],
                    facet=subquery.facet,
                    metadata={"api": "google_places"}
                ))
            
            return evidence
        except Exception as e:
            print(f"Maps API error: {e}")
            return []
    
    async def _retrieve_from_schedule_api(self, subquery: SubQuery) -> List[EvidenceChunk]:
        """Retrieve from schedule API"""
        try:
            from src.tools.schedule_scraper import scrape_versailles_schedule
            
            date = datetime.now().strftime("%Y-%m-%d")
            schedule_data = scrape_versailles_schedule(date)
            
            return [EvidenceChunk(
                source="schedule_api",
                content=str(schedule_data),
                score=0.95,
                authority_weight=self.authority_weights["schedule_api"],
                facet=subquery.facet,
                metadata={"api": "schedule_scraper", "date": date}
            )]
        except Exception as e:
            print(f"Schedule API error: {e}")
            return []
    
    async def _retrieve_from_official_kb(self, subquery: SubQuery) -> List[EvidenceChunk]:
        """Retrieve from official knowledge base"""
        try:
            from src.tools.rag import versailles_expert_tool
            
            kb_result = versailles_expert_tool(subquery.query)
            
            return [EvidenceChunk(
                source="official_kb",
                content=str(kb_result),
                score=1.0,
                authority_weight=self.authority_weights["official_kb"],
                facet=subquery.facet,
                metadata={"kb": "versailles_expert"}
            )]
        except Exception as e:
            print(f"Official KB error: {e}")
            return []
    
    async def generate_partial_answer(self, subquery: SubQuery, evidence_chunks: List[EvidenceChunk]) -> PartialAnswer:
        """Generate partial answer for a facet using evidence chunks"""
        
        if not evidence_chunks:
            return PartialAnswer(
                facet=subquery.facet,
                answer="No information available for this aspect.",
                evidence_chunks=[],
                confidence=0.0,
                constraints_satisfied=[]
            )
        
        # Sort evidence by score
        sorted_evidence = sorted(evidence_chunks, key=lambda x: x.score * x.authority_weight, reverse=True)
        
        # Combine top evidence
        combined_evidence = "\n".join([chunk.content[:200] + "..." for chunk in sorted_evidence[:3]])
        
        # Generate answer using LLM (simplified)
        answer = f"Based on {subquery.facet.value} information: {combined_evidence[:300]}..."
        
        return PartialAnswer(
            facet=subquery.facet,
            answer=answer,
            evidence_chunks=sorted_evidence,
            confidence=sum(chunk.score for chunk in sorted_evidence) / len(sorted_evidence),
            constraints_satisfied=list(subquery.constraints.keys())
        )


class AnswerSynthesizer:
    """
    Synthesizer that combines partial answers into a coherent final response
    """
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("MISTRAL_API_KEY")
        self.llm = MistralAI(model="mistral-medium-latest", api_key=api_key)
    
    async def synthesize(self, plan: Plan, partial_answers: List[PartialAnswer]) -> FinalAnswer:
        """Synthesize partial answers into final coherent response"""
        
        # Step 1: Conflict resolution and deduplication
        resolved_answers = self._resolve_conflicts(partial_answers)
        
        # Step 2: Constraint checking
        constraints_check = self._check_constraints(plan.user_constraints, resolved_answers)
        
        # Step 3: Generate final answer
        final_answer = await self._generate_final_answer(plan, resolved_answers)
        
        # Step 4: Generate recommendations
        recommendations = self._generate_recommendations(plan, resolved_answers)
        
        # Step 5: Create source citations
        citations = self._create_citations(resolved_answers)
        
        # Calculate information completeness
        missing_info_count = sum([
            plan.information_gaps.missing_date,
            plan.information_gaps.missing_group_composition,
            plan.information_gaps.missing_duration, 
            plan.information_gaps.missing_budget
        ])
        
        information_completeness = 1.0 - (missing_info_count * 0.25)  # 25% penalty per missing piece
        
        return FinalAnswer(
            answer=final_answer,
            recommendations=recommendations,
            source_citations=citations,
            constraints_check=constraints_check,
            confidence=sum(pa.confidence for pa in resolved_answers) / len(resolved_answers) if resolved_answers else 0.0,
            reasoning=f"Synthesized from {len(resolved_answers)} faceted answers with {len(citations)} sources",
            follow_up_questions=plan.information_gaps.suggested_questions,
            information_completeness=information_completeness
        )
    
    def _resolve_conflicts(self, partial_answers: List[PartialAnswer]) -> List[PartialAnswer]:
        """Resolve conflicts between different sources"""
        # Prioritize official sources over external ones
        # For now, simple implementation - just return sorted by confidence
        return sorted(partial_answers, key=lambda x: x.confidence, reverse=True)
    
    def _check_constraints(self, constraints: UserConstraints, answers: List[PartialAnswer]) -> Dict[str, bool]:
        """Check if answers satisfy user constraints"""
        checks = {}
        
        if constraints.duration:
            checks["duration_compatible"] = True  # Simplified check
        
        if constraints.has_children:
            checks["child_friendly"] = True  # Simplified check
        
        if constraints.mobility:
            checks["accessibility"] = True  # Simplified check
        
        return checks
    
    async def _generate_final_answer(self, plan: Plan, answers: List[PartialAnswer]) -> str:
        """Generate coherent final answer"""
        
        combined_content = "\n".join([f"{answer.facet.value}: {answer.answer}" for answer in answers])
        
        prompt = f"""
        Create a coherent, helpful response for a Versailles visitor based on these faceted answers:
        
        User Profile: {plan.user_profile.value}
        User Constraints: {asdict(plan.user_constraints)}
        
        Faceted Information:
        {combined_content}
        
        Generate a natural, conversational response that addresses the user's needs while incorporating the relevant information from all facets.
        """
        
        try:
            response = await self.llm.acomplete(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Based on the available information: {combined_content[:500]}..."
    
    def _generate_recommendations(self, plan: Plan, answers: List[PartialAnswer]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Accessibility-first recommendations
        if plan.user_profile == UserProfile.ACCESSIBILITY_NEEDS:
            recommendations.append("🦽 Use the main entrance with elevator access - avoid stairs at secondary entrances")
            recommendations.append("🚻 Accessible restrooms are located on the ground floor near the Hall of Mirrors")
            recommendations.append("🎧 Request audio guides with tactile maps at the information desk")
            if "wheelchair" in plan.user_constraints.accessibility_needs:
                recommendations.append("♿ Wheelchair rental available at entrance - reserve in advance")
            if "visual_impaired" in plan.user_constraints.accessibility_needs:
                recommendations.append("👁️ Tactile tours available on request - contact accessibility services")
        
        # Elderly-specific recommendations  
        if plan.user_profile in [UserProfile.ELDERLY_GROUP, UserProfile.FAMILY_WITH_ELDERLY]:
            recommendations.append("🪑 Take advantage of seating areas in the State Apartments")
            recommendations.append("🚌 Consider the petit train (small train) for garden tours to reduce walking")
            recommendations.append("☕ Plan rest stops at the café near the Grand Trianon")
            if plan.user_constraints.rest_frequency == "frequent":
                recommendations.append("⏰ Plan for 15-minute breaks every hour")
        
        # Family recommendations
        if plan.user_profile in [UserProfile.FAMILY_WITH_KIDS, UserProfile.FAMILY_WITH_ELDERLY]:
            recommendations.append("🏰 Visit the Queen's Hamlet - engaging for all ages")
            recommendations.append("🎒 Bring snacks and water - limited food options inside")
        
        # Duration-based recommendations
        if plan.user_constraints.duration == "half day":
            recommendations.append("⏱️ Focus on the main palace and Hall of Mirrors for a half-day visit")
        elif plan.user_constraints.duration == "full day":
            recommendations.append("🌳 Include the gardens and Trianon palaces for a full-day experience")
        
        # Budget recommendations
        if plan.user_constraints.budget == "low":
            recommendations.append("💰 Gardens are free on weekdays (Nov-Mar) - great budget option")
            recommendations.append("🎫 Consider the basic Palace ticket instead of the Passport")
        
        # Outdoor preferences
        if plan.user_constraints.outdoor_preference:
            recommendations.append("🌺 Spend time in the magnificent gardens and park")
            recommendations.append("🚴 Bike rentals available for exploring the vast grounds")
        
        return recommendations
    
    def _create_citations(self, answers: List[PartialAnswer]) -> List[str]:
        """Create source citations"""
        citations = []
        
        for answer in answers:
            for chunk in answer.evidence_chunks[:2]:  # Top 2 sources per facet
                citation = f"{chunk.source} ({chunk.facet.value})"
                if citation not in citations:
                    citations.append(citation)
        
        return citations


class EnhancedVersaillesAgent:
    """
    Main agent class implementing the enhanced architecture:
    Planner → Subqueries → Faceted RAG → Synthesizer
    """
    
    def __init__(self):
        self.planner = EnhancedQueryPlanner()
        self.faceted_rag = FacetedRAG()
        self.synthesizer = AnswerSynthesizer()
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process query through the enhanced pipeline
        """
        try:
            # Step 1: Create comprehensive plan
            plan = await self.planner.create_plan(query)
            
            # Step 2: Execute faceted retrieval for each sub-query
            partial_answers = []
            for subquery in plan.subqueries:
                evidence_chunks = await self.faceted_rag.retrieve_evidence(subquery)
                partial_answer = await self.faceted_rag.generate_partial_answer(subquery, evidence_chunks)
                partial_answers.append(partial_answer)
            
            # Step 3: Synthesize final answer
            final_answer = await self.synthesizer.synthesize(plan, partial_answers)
            
            return {
                "plan": asdict(plan),
                "partial_answers": [asdict(pa) for pa in partial_answers],
                "final_answer": asdict(final_answer),
                "processing_method": "enhanced_planner"
            }
        
        except Exception as e:
            return {
                "error": str(e),
                "processing_method": "enhanced_planner_failed"
            }
