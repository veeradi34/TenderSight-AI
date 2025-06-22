"""
A simplified version of main.py for cloud deployment
that doesn't rely on browser automation.
"""

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import Dict, List
import json
import re
import os

# Ensure environment variables are loaded
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

# Check for API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY not found. Please add it to your .env file or set it as an environment variable. "
        "For Streamlit Cloud deployment, add it to your secrets."
    )

try:
    llm = ChatOpenAI(
        model="anthropic/claude-3-sonnet",
        temperature=0,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
    )
except Exception as e:
    raise ConnectionError(
        f"Error initializing LLM with OpenRouter: {str(e)}. "
        "Please check your API key and internet connection."
    ) from e

def parse_user_profile(user_input: str) -> Dict:
    """Extracts company profile information from user input."""
    profile_data = {
        "company_name": None,
        "industry": None,
        "location": None,
        "budget_range": None,
        "company_size": None,
        "keywords": [],
        "preferences": {},
    }
    
    # Extract company name
    company_patterns = [
        r"company[:\s]+([^\n,]+)",
        r"startup[:\s]+([^\n,]+)",
        r"organization[:\s]+([^\n,]+)",
        r"firm[:\s]+([^\n,]+)",
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            profile_data["company_name"] = match.group(1).strip()
            break
    
    # Identify industry
    industry_keywords = [
        "tech", "healthcare", "fintech", "agriculture", "manufacturing",
        "education", "retail", "logistics", "renewable energy", "ai", "blockchain",
    ]
    
    found_industries = []
    for keyword in industry_keywords:
        if keyword.lower() in user_input.lower():
            found_industries.append(keyword)
    
    if found_industries:
        profile_data["industry"] = found_industries[0]
        profile_data["keywords"].extend(found_industries)
    
    # Extract location
    location_patterns = [
        r"location[:\s]+([^\n,]+)",
        r"based in[:\s]+([^\n,]+)",
        r"from[:\s]+([^\n,]+)",
        r"city[:\s]+([^\n,]+)",
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            profile_data["location"] = match.group(1).strip()
            break
    
    # Extract budget
    budget_patterns = [
        r"budget[:\s]+([0-9,]+(?:\s*(?:lakh|crore|million|k))?)",
        r"funding[:\s]+([0-9,]+(?:\s*(?:lakh|crore|million|k))?)",
        r"investment[:\s]+([0-9,]+(?:\s*(?:lakh|crore|million|k))?)",
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            profile_data["budget_range"] = match.group(1).strip()
            break
    
    # Add additional keywords
    additional_keywords = re.findall(
        r"\b(?:innovation|research|development|prototype|pilot|scale|growth)\b",
        user_input,
        re.IGNORECASE,
    )
    profile_data["keywords"].extend([kw.lower() for kw in additional_keywords])
    profile_data["keywords"] = list(set(profile_data["keywords"]))
    
    return profile_data

def get_sample_tenders(keywords: str, location: str = None) -> List[Dict]:
    """Returns sample tenders based on keywords - for use in cloud environments."""
    portals = [
        "https://gem.gov.in",
        "https://eprocure.gov.in",
        "https://www.startupindia.gov.in",
    ]
    
    tender_data = []
    
    # Generate sample data based on keywords
    keywords_list = keywords.split()
    
    # Government e-Marketplace tenders
    tender_data.append({
        "title": f"{keywords.title()} Solutions for Government Sector",
        "deadline": "Check Portal for Details",
        "link": "https://gem.gov.in",
        "source": "GeM",
        "keywords_matched": keywords,
        "description": f"A tender for {keywords} solutions across government departments."
    })
    
    # eProcure tenders
    tender_data.append({
        "title": f"Request for Proposals: {keywords.title()} Implementation",
        "deadline": "Check Portal for Details",
        "link": "https://eprocure.gov.in",
        "source": "eProcure",
        "keywords_matched": keywords,
        "description": f"Government initiative seeking {keywords} solutions for enhancing public services."
    })
    
    # Startup India tender
    tender_data.append({
        "title": f"Innovation Grant for {keywords.title()} Startups",
        "deadline": "Check Portal for Details",
        "link": "https://www.startupindia.gov.in",
        "source": "Startup India",
        "keywords_matched": keywords,
        "description": f"Funding opportunity for startups working in {keywords} sector."
    })
    
    # Add location-specific tender if location is provided
    if location:
        tender_data.append({
            "title": f"Local {keywords.title()} Initiative in {location}",
            "deadline": "Check Portal for Details",
            "link": "https://gem.gov.in",
            "source": "GeM",
            "keywords_matched": f"{keywords} {location}",
            "description": f"Local government tender for {keywords} solutions in {location} region."
        })
    
    return tender_data

def parse_tender_document(tender_content: str) -> Dict:
    """Extract key information from tender document using LLM."""
    prompt = f"""
    Extract key information from this tender document and return as JSON:
    
    {tender_content[:2000]}
    
    Extract:
    - title
    - description  
    - deadline
    - budget_range
    - eligibility_criteria
    - application_requirements
    - contact_details
    - tender_id
    
    Return only valid JSON format.
    """
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        parsed_data = json.loads(content)
        return parsed_data
    except:
        return {
            "title": "Document Parse Error",
            "description": tender_content[:200] + "...",
            "deadline": None,
            "budget_range": None,
            "eligibility_criteria": "Review document manually",
            "application_requirements": "Review document manually",
            "contact_details": None,
            "tender_id": None
        }

def check_eligibility(tender_data: dict, user_profile: dict) -> Dict:
    """Check if company is eligible for tender using LLM."""
    prompt = f"""
    Analyze if this company profile matches the tender requirements:
    
    COMPANY PROFILE:
    - Name: {user_profile.get('company_name', 'N/A')}
    - Industry: {user_profile.get('industry', 'N/A')}
    - Location: {user_profile.get('location', 'N/A')}
    - Budget: {user_profile.get('budget_range', 'N/A')}
    - Keywords: {user_profile.get('keywords', [])}
    
    TENDER DETAILS:
    - Title: {tender_data.get('title', 'N/A')}
    - Eligibility: {tender_data.get('eligibility_criteria', 'N/A')}
    - Budget: {tender_data.get('budget_range', 'N/A')}
    - Requirements: {tender_data.get('application_requirements', 'N/A')}
    
    Return JSON with:
    - eligible: true/false
    - match_score: 0-100
    - reasons: list of reasons
    - missing_requirements: list
    """
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        result = json.loads(content)
        return result
    except:
        return {
            "eligible": True,
            "match_score": 75,
            "reasons": ["General eligibility assumed"],
            "missing_requirements": ["Manual review required"],
        }

def generate_application_summary(tender_details: dict, company_profile: dict) -> str:
    """Generate application summary using LLM."""
    prompt = f"""
    Generate a professional application summary for this tender:
    
    TENDER: {tender_details.get('title', 'N/A')}
    REQUIREMENTS: {tender_details.get('application_requirements', 'N/A')}
    
    COMPANY: {company_profile.get('company_name', 'N/A')}
    INDUSTRY: {company_profile.get('industry', 'N/A')}
    CAPABILITIES: {', '.join(company_profile.get('keywords', []))}
    
    Write a 200-word application summary highlighting company strengths relevant to this tender.
    """
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        return content.strip()
    except:
        return f"Application summary for {company_profile.get('company_name', 'Company')} applying to {tender_details.get('title', 'tender')}. Manual completion required."

def main_tender_agent(query: str) -> str:
    """Main function to process user input and generate tender recommendations."""
    user_profile = parse_user_profile(query)
    
    if not user_profile.get("keywords"):
        return "Please provide more details about your company, industry, and location to find relevant tenders."
    
    keywords = " ".join(user_profile["keywords"][:2])
    location = user_profile.get("location", "")
    
    # Use the cloud-friendly get_sample_tenders instead of web scraping
    tenders = get_sample_tenders(keywords, location)
    
    if not tenders:
        return f"No tenders found for keywords: {keywords}. Try different search terms."
    
    results = []
    for i, tender in enumerate(tenders[:3]):
        parsed_tender = parse_tender_document(str(tender))
        eligibility = check_eligibility(parsed_tender, user_profile)
        
        if eligibility.get("eligible", True):
            app_summary = generate_application_summary(parsed_tender, user_profile)
            
            result = f"""
TENDER {i+1}: {tender['title']}
SOURCE: {tender['source']}
LINK: {tender['link']}
MATCH SCORE: {eligibility.get('match_score', 'N/A')}%
DEADLINE: {tender.get('deadline', 'Check Portal')}

ELIGIBILITY: {'✅ Eligible' if eligibility.get('eligible') else '❌ Not Eligible'}
REASONS: {', '.join(eligibility.get('reasons', ['Review required']))}

APPLICATION SUMMARY:
{app_summary[:300]}...

---
"""
            results.append(result)
    
    if not results:
        return "No eligible tenders found matching your profile."
    
    return f"""
TENDER SEARCH RESULTS FOR: {user_profile.get('company_name', 'Your Company')}
INDUSTRY: {user_profile.get('industry', 'N/A')}
LOCATION: {user_profile.get('location', 'N/A')}

{''.join(results)}

📋 NEXT STEPS:
1. Visit the portal links to get complete tender documents
2. Review eligibility criteria carefully
3. Prepare required documents
4. Submit before deadline
"""

if __name__ == "__main__":
    print("🤖 Government Tender AI Agent Started!")
    print("Enter your company details to find relevant tenders...")
    
    while True:
        user_input = input("\n💬 You: ")
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("👋 Goodbye!")
            break
            
        try:
            response = main_tender_agent(user_input)
            print(f"\n🎯 Agent: {response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again with different input.")
