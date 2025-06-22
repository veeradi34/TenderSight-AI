from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import StructuredTool
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from playwright.sync_api import sync_playwright
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import json
import re
import os
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Ensure dotenv is loaded from the correct path
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

# Check for API key from various sources (environment or .env file)
# Streamlit Cloud uses secrets.toml which sets environment variables
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


class UserProfileInput(BaseModel):
    user_input: str


class ScrapeInput(BaseModel):
    keywords: str
    location: str = None


class TenderContent(BaseModel):
    tender_content: str


class EligibilityInput(BaseModel):
    tender_data: dict
    user_profile: dict


class ApplicationInput(BaseModel):
    tender_details: dict
    company_profile: dict


def parse_user_profile(user_input: str) -> Dict:
    profile_data = {
        "company_name": None,
        "industry": None,
        "location": None,
        "budget_range": None,
        "company_size": None,
        "keywords": [],
        "preferences": {},
    }

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

    industry_keywords = [
        "tech",
        "healthcare",
        "fintech",
        "agriculture",
        "manufacturing",
        "education",
        "retail",
        "logistics",
        "renewable energy",
        "ai",
        "blockchain",
    ]

    found_industries = []
    for keyword in industry_keywords:
        if keyword.lower() in user_input.lower():
            found_industries.append(keyword)

    if found_industries:
        profile_data["industry"] = found_industries[0]
        profile_data["keywords"].extend(found_industries)

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

    additional_keywords = re.findall(
        r"\b(?:innovation|research|development|prototype|pilot|scale|growth)\b",
        user_input,
        re.IGNORECASE,
    )
    profile_data["keywords"].extend([kw.lower() for kw in additional_keywords])
    profile_data["keywords"] = list(set(profile_data["keywords"]))

    return profile_data


def scrape_tender_portals(keywords: str, location: str = None) -> List[Dict]:
    tender_data = []

    portals = [
        "https://gem.gov.in",
        "https://eprocure.gov.in",
        "https://www.startupindia.gov.in",
    ]

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                for portal in portals:
                    try:
                        page.goto(portal, timeout=30000)
                        page.wait_for_load_state("networkidle")

                        if "gem.gov.in" in portal:
                            search_selectors = [
                                'input[placeholder*="search" i]',
                                'input[name*="search" i]',
                                "#searchBox",
                            ]

                            for selector in search_selectors:
                                try:
                                    page.fill(selector, keywords)
                                    page.press(selector, "Enter")
                                    break
                                except:
                                    continue

                            page.wait_for_load_state("networkidle")
                            time.sleep(2)

                            result_selectors = [
                                ".tender-item",
                                ".result-item",
                                ".tender-card",
                                'tr[class*="row"]',
                            ]

                            for selector in result_selectors:
                                results = page.query_selector_all(selector)
                                if results:
                                    for result in results[:5]:
                                        title = result.query_selector(
                                            "a, .title, .tender-title"
                                        )
                                        if title:
                                            tender_data.append(
                                                {
                                                    "title": title.inner_text().strip()[:100],
                                                    "deadline": "Check Portal",
                                                    "link": portal,
                                                    "source": "GeM",
                                                    "keywords_matched": keywords,
                                                }
                                            )
                                    break

                        elif "eprocure.gov.in" in portal:
                            try:
                                page.fill('input[type="text"]', keywords)
                                page.click('input[value*="Search" i], button[type="submit"]')
                                page.wait_for_load_state("networkidle")

                                rows = page.query_selector_all("tr")
                                for row in rows[:3]:
                                    cells = row.query_selector_all("td")
                                    if len(cells) >= 2:
                                        tender_data.append(
                                            {
                                                "title": cells[0].inner_text().strip()[:100],
                                                "deadline": "Check Portal",
                                                "link": portal,
                                                "source": "eProcure",
                                                "keywords_matched": keywords,
                                            }
                                        )
                            except:
                                tender_data.append(
                                    {
                                        "title": f"Tenders available for {keywords}",
                                        "deadline": "Check Portal",
                                        "link": portal,
                                        "source": "eProcure",
                                        "keywords_matched": keywords,
                                    }
                                )

                        elif "startupindia.gov.in" in portal:
                            try:
                                page.fill('input[placeholder*="Search" i]', keywords)
                                page.press('input[placeholder*="Search" i]', "Enter")
                                page.wait_for_load_state("networkidle")

                                results = page.query_selector_all(".result, .grant, .scheme")
                                for result in results[:3]:
                                    title_elem = result.query_selector("h3, .title, a")
                                    if title_elem:
                                        tender_data.append(
                                            {
                                                "title": title_elem.inner_text().strip()[:100],
                                                "deadline": "Check Portal",
                                                "link": portal,
                                                "source": "Startup India",
                                                "keywords_matched": keywords,
                                            }
                                        )
                            except:
                                tender_data.append(
                                    {
                                        "title": f"Startup grants available for {keywords}",
                                        "deadline": "Check Portal",
                                        "link": portal,
                                        "source": "Startup India",
                                        "keywords_matched": keywords,
                                    }
                                )

                        time.sleep(1)

                    except Exception as e:
                        tender_data.append(
                            {
                                "title": f'Error accessing {portal.split("//")[1]}',
                                "deadline": "N/A",
                                "link": portal,
                                "source": portal.split("//")[1],
                                "error": str(e),
                            }
                        )

                browser.close()
            except Exception as browser_error:
                # Handle browser initialization errors (common in cloud environments)
                for portal in portals:
                    tender_data.append(
                        {
                            "title": f"Sample tender for {keywords} on {portal.split('//')[1]}",
                            "deadline": "Check Portal",
                            "link": portal,
                            "source": portal.split("//")[1],
                            "keywords_matched": keywords,
                            "note": "Using sample data (browser automation unavailable)"
                        }
                    )
    except ImportError:
        # In case Playwright is not available
        for portal in portals:
            tender_data.append(
                {
                    "title": f"Tendor opportunities for {keywords} on {portal.split('//')[1]}",
                    "deadline": "Check Portal",
                    "link": portal,
                    "source": portal.split("//")[1],
                    "keywords_matched": keywords,
                    "note": "Using fallback data (Playwright not available)"
                }
            )

    # Ensure we have at least some data to work with
    if not tender_data:
        tender_data = [
            {
                "title": f"Government tenders related to {keywords}",
                "deadline": "Check Available Portals",
                "link": "https://gem.gov.in",
                "source": "Tender Portal",
                "keywords_matched": keywords,
                "note": "Sample data only"
            }
        ]

    return tender_data


def parse_tender_document(tender_content: str) -> Dict:
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
            "tender_id": None,
        }


def check_eligibility(tender_data: dict, user_profile: dict) -> Dict:
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


def load_and_parse_pdf(pdf_url: str) -> str:
    try:
        loader = WebBaseLoader(pdf_url)
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)

        content = ""
        for split in splits[:5]:
            content += split.page_content + "\n"

        return content
    except:
        return "Unable to load PDF content. Manual review required."


def main_tender_agent(query: str) -> str:
    user_profile = parse_user_profile(query)

    if not user_profile.get("keywords"):
        return "Please provide more details about your company, industry, and location to find relevant tenders."

    keywords = " ".join(user_profile["keywords"][:2])
    location = user_profile.get("location", "")

    tenders = scrape_tender_portals(keywords, location)

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


profile_tool = StructuredTool.from_function(
    func=parse_user_profile,
    name="parse_user_profile",
    description="Parse user company profile information",
    args_schema=UserProfileInput,
)

scrape_tool = StructuredTool.from_function(
    func=scrape_tender_portals,
    name="scrape_tender_portals",
    description="Search government portals for relevant tenders",
    args_schema=ScrapeInput,
)

parse_tool = StructuredTool.from_function(
    func=parse_tender_document,
    name="parse_tender_document",
    description="Extract key information from tender documents",
    args_schema=TenderContent,
)

eligibility_tool = StructuredTool.from_function(
    func=check_eligibility,
    name="check_eligibility",
    description="Check if company is eligible for specific tender",
    args_schema=EligibilityInput,
)

application_tool = StructuredTool.from_function(
    func=generate_application_summary,
    name="generate_application_summary",
    description="Generate application summary for tender",
    args_schema=ApplicationInput,
)

tools = [profile_tool, scrape_tool, parse_tool, eligibility_tool, application_tool]

# Initialize chat message history
chat_history = ChatMessageHistory()

# Initialize memory with the updated format
memory = ConversationBufferMemory(
    chat_memory=chat_history,
    memory_key="chat_history",
    return_messages=True
)

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,
)

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
