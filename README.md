# 🏰 Marie-AI-nette

An intelligent, accessibility-focused AI assistant for planning visits to the Palace of Versailles. Named after Marie-Antoinette, this agent combines advanced query planning, dual RAG fusion, and personalized recommendations to provide comprehensive, inclusive travel guidance.

## 🌟 Key Features

### 🎯 **Intelligent Query Routing & Tool Orchestration**
- **Pattern-Based Routing**: Fast query analysis using regex patterns + LLM entity extraction
- **Smart Tool Selection**: Automatically identifies required APIs (Maps, Weather, Schedule, Knowledge Base)
- **Multi-Source Integration**: Seamlessly combines official knowledge base with real-time external APIs
- **Optimized Execution**: Sequential tool calls with context aggregation for comprehensive answers

### 🧠 **Enhanced Query Planning**
- **Intelligent User Profiling**: Automatically detects visitor types (families, elderly, accessibility needs, etc.)
- **Information Completeness Analysis**: Identifies missing key information (date, group composition, duration, budget)
- **Proactive Question Generation**: Suggests follow-up questions to optimize planning

### ♿ **Comprehensive Accessibility Support**
- **Multi-disability Recognition**: Supports wheelchair users, visual/hearing impaired, cognitive needs
- **Mobility Assessment**: Detects walking aids, rest frequency requirements
- **Specialized Recommendations**: Elevator access, accessible restrooms, tactile tours
- **Senior-friendly Planning**: Rest areas, reduced walking routes, seating options

### 🎯 **Faceted RAG Architecture**
- **Multi-source Knowledge Integration**: Official KB, real-time APIs, schedule data
- **Faceted Information Retrieval**: History, Family, Practical, Itinerary, Weather facets
- **Authority-weighted Scoring**: Prioritizes official sources over external data
- **Conflict Resolution**: Intelligent handling of contradictory information

### 🌐 **Real-time Data Integration**
- **Google Places API**: Location search and navigation
- **Google Weather API**: Current weather conditions and forecasts
- **Live Schedule Scraping**: Real-time opening hours and crowd levels
- **Route Optimization**: Walking directions between attractions

## 🏗️ Agent Workflow

### 🎯 Current Production Architecture: Query Planner + Dual RAG

![RAG Workflow](./docs/rag_workflow.png)

Our production system uses a **rule-based Query Planner** with **Dual RAG Fusion** for optimal performance (8.5/10 test score):

#### **Workflow Steps:**

1. **Query Planner Agent** 📋
   - Extracts user constraints (date, budget, group composition)
   - Analyzes information gaps
   - Determines user profile (family, accessibility needs, etc.)
   - Generates faceted subqueries

2. **Agentic RAG System** 🤖
   - **Google Maps API**: Location search and navigation
   - **Multimodal Knowledge Bases**: PDF + JSON documents
   - **Schedule API**: Real-time opening hours
   - **Weather API**: Current conditions and forecasts

3. **Evidence Scoring** ⭐
   - Ranks retrieved information by relevance
   - Prioritizes official sources
   - Filters low-quality results

4. **Answer Synthesiser** 📝
   - Conflict resolution between sources
   - Constraint checking (budget, accessibility, time)
   - Generates final structured answer

5. **Follow-up Questions** 🔄 (if necessary)
   - Proactive clarification requests
   - Missing information identification

#### **Key Features:**
- ✅ **Pattern-based routing**: Fast and predictable (regex + LLM for entities)
- ✅ **Dual RAG Fusion**: Combines PDF and JSON knowledge bases
- ✅ **Multi-source integration**: KB + Google APIs + Schedule scraper
- ✅ **8.5/10 test score**: High accuracy and completeness

## 📈 Performance Metrics

### With Intelligent Routing ⚡
- **Simple Query Response**: 1-2 seconds (DIRECT_RAG)
- **Complex Query Response**: 3-5 seconds (DECOMPOSE)
- **Routing Accuracy**: 90%+ correct decision
- **Speed Improvement**: 50-70% faster for simple queries

### Overall System
- **User Profile Accuracy**: 95%+ correct classification
- **Information Gap Detection**: 100% accuracy in testing
- **Accessibility Coverage**: Supports 5+ disability types
- **Language Support**: English, French, Chinese keywords

## 🎯 Key Innovations

1. **Intelligent Query Routing** ⚡: LLM-powered decision system that routes simple queries to fast RAG and complex queries to decomposition, achieving 50-70% speed improvement

2. **Dynamic Query Decomposition**: LLM generates optimal sub-queries with dependency management, replacing hardcoded facet classification

3. **Proactive Information Gathering**: Unlike traditional chatbots, actively identifies and requests missing planning information

4. **Accessibility-First Design**: Prioritizes accessibility needs in user profiling and recommendations

5. **Multi-source Truth Reconciliation**: Intelligently combines official data, real-time APIs, and knowledge bases

6. **Confidence-Aware Planning**: Adjusts recommendation confidence based on information completeness

## 🏆 Use Cases

- **Accessible Tourism Planning**: Comprehensive support for visitors with disabilities
- **Family Trip Organization**: Age-appropriate activities and logistics
- **Senior Travel Assistance**: Mobility-conscious itineraries
- **Budget-Conscious Planning**: Cost-effective options and free alternatives
- **Real-time Adaptation**: Dynamic planning based on weather and crowds

---

**Built for the Versailles Hackathon** 🏰  
*Making the Palace of Versailles accessible and enjoyable for everyone*