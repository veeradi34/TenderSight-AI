import streamlit as st
from cloud_main import main_tender_agent
import os
from dotenv import load_dotenv

# Set page configuration
st.set_page_config(
    page_title="Government Tender AI Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ensure environment variables are loaded
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=dotenv_path)

# Check if OpenRouter API key exists
if not os.getenv("OPENROUTER_API_KEY"):
    st.error("⚠️ OpenRouter API key not found. Please make sure your .env file contains OPENROUTER_API_KEY.")
    st.stop()

# Set up the sidebar
st.sidebar.title("🤖 Government Tender Agent")
st.sidebar.image("https://img.icons8.com/color/96/000000/government.png", width=100)
st.sidebar.markdown("---")
st.sidebar.markdown("""
## About
This AI agent helps companies find relevant government tenders and assess eligibility.

### Features:
- Find tenders matching your company profile
- Analyze eligibility criteria
- Generate application summaries
- Provide next steps
""")
st.sidebar.markdown("---")
st.sidebar.markdown("### How to use")
st.sidebar.markdown("""
1. Enter your company details
2. Include industry and location information
3. Add any specific keywords or requirements
4. Submit and wait for results
""")
st.sidebar.markdown("---")
st.sidebar.info("Powered by Claude 3 Sonnet via OpenRouter")

# Main content
st.title("🎯 Government Tender AI Agent")

# Sample prompts
st.markdown("### 💡 Sample prompts:")
sample_prompts = [
    "We are a tech startup based in Mumbai working on AI solutions for healthcare",
    "Our manufacturing company in Delhi is looking for government contracts in renewable energy",
    "We are a fintech company based in Bangalore with 50 employees and a budget of 20 lakh",
]

# Create columns for sample prompts
cols = st.columns(len(sample_prompts))
for i, col in enumerate(cols):
    if col.button(f"Example {i+1}", key=f"example_{i}"):
        st.session_state.user_input = sample_prompts[i]

# Input form
st.markdown("### 💬 Enter your company details:")
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

user_input = st.text_area(
    "Include your company name, industry, location, and any specific requirements:",
    value=st.session_state.user_input,
    height=150,
    placeholder="Example: We are a tech startup based in Mumbai working on AI solutions for healthcare. We have 20 employees and are looking for government tenders in the range of 10-50 lakh rupees.",
    key="input_area"
)

search_button = st.button("🔍 Find Tenders")

# Process and display results
if search_button and user_input:
    with st.spinner("🔄 Searching for relevant tenders... This may take a minute."):
        try:
            # Save the input to session state
            st.session_state.user_input = user_input
            
            # Call the main tender agent function
            result = main_tender_agent(user_input)
            
            # Display results in a nicely formatted way
            st.markdown("## 📋 Results")
            
            # Display company profile section
            if "TENDER SEARCH RESULTS FOR:" in result:
                profile_section = result.split("TENDER SEARCH RESULTS FOR:")[1].split("\n\n")[0]
                st.markdown(f"### Company Profile")
                st.info(f"**{profile_section.strip()}**")
            
            # Parse and display each tender in its own expander
            tenders = result.split("TENDER ")[1:]
            if tenders:
                st.markdown("### 📊 Matching Tenders")
                
                for i, tender in enumerate(tenders):
                    tender_num = i + 1
                    tender_title = tender.split("\n")[0].split(":")[1].strip() if ":" in tender.split("\n")[0] else "Tender"
                    
                    with st.expander(f"Tender {tender_num}: {tender_title}", expanded=True):
                        tender_details = "TENDER " + tender.strip()
                        
                        # Extract various tender sections
                        source = tender_details.split("SOURCE:")[1].split("\n")[0].strip() if "SOURCE:" in tender_details else "N/A"
                        link = tender_details.split("LINK:")[1].split("\n")[0].strip() if "LINK:" in tender_details else "#"
                        match_score = tender_details.split("MATCH SCORE:")[1].split("\n")[0].strip() if "MATCH SCORE:" in tender_details else "N/A"
                        deadline = tender_details.split("DEADLINE:")[1].split("\n")[0].strip() if "DEADLINE:" in tender_details else "N/A"
                        eligibility = "✅ Eligible" if "✅ Eligible" in tender_details else "❌ Not Eligible"
                        
                        # Create columns for tender info
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Source", source)
                        col2.metric("Match Score", match_score)
                        col3.metric("Deadline", deadline)
                        
                        st.markdown(f"**Eligibility:** {eligibility}")
                        
                        if "REASONS:" in tender_details:
                            reasons = tender_details.split("REASONS:")[1].split("\n\n")[0].strip()
                            st.markdown(f"**Reasons:** {reasons}")
                        
                        if "APPLICATION SUMMARY:" in tender_details:
                            summary = tender_details.split("APPLICATION SUMMARY:")[1].split("---")[0].strip()
                            st.markdown("#### Application Summary")
                            st.text_area("", value=summary, height=200, key=f"summary_{i}")
                        
                        st.markdown(f"[Visit Tender Portal]({link})")
                
                # Display next steps if available
                if "NEXT STEPS:" in result:
                    next_steps = result.split("NEXT STEPS:")[1].strip()
                    st.markdown("### 📝 Next Steps")
                    steps = next_steps.split("\n")
                    for step in steps:
                        if step.strip():
                            st.markdown(f"- {step.strip()}")
            else:
                st.warning("No eligible tenders found matching your profile.")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.error("Please try again with more specific company details.")

# Add footer
st.markdown("---")
st.markdown("#### Need help?")
st.write("Include details about your company's industry, location, size, and specific requirements to get better results.")
