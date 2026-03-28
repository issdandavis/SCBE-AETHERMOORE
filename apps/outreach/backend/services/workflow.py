"""
Aethermoor Outreach -- Workflow generation service.
Returns structured steps per classified intent, specific to Port Angeles, WA.
"""

from typing import Dict, List


WORKFLOWS: Dict[str, List[Dict]] = {
    "start_business": [
        {
            "step_number": 1,
            "description": "Choose business structure (LLC, sole proprietorship, corporation, etc.). LLCs offer liability protection with simpler tax treatment. Sole props are free to register but offer no liability shield.",
            "agency": "WA Secretary of State",
            "estimated_time": "1-2 days (research)",
            "required_docs": "None -- decision stage",
        },
        {
            "step_number": 2,
            "description": "Register business name and entity with the WA Secretary of State. LLC filing fee is $180 online. Sole proprietorships can register a trade name for $5. Corporations are $180.",
            "agency": "WA Secretary of State",
            "estimated_time": "1-3 business days online",
            "required_docs": "Articles of Organization (LLC) or Articles of Incorporation (Corp)",
        },
        {
            "step_number": 3,
            "description": "Apply for a City of Port Angeles business license. Required for all businesses operating within city limits. Fee ranges $50-100/year depending on business type.",
            "agency": "City of Port Angeles -- Finance Dept",
            "estimated_time": "1-2 weeks",
            "required_docs": "State registration confirmation, business address, owner ID",
        },
        {
            "step_number": 4,
            "description": "Contact the Peninsula Small Business Development Center (SBDC) for free business advising. They help with business plans, funding, and regulatory compliance at no cost.",
            "agency": "Peninsula SBDC at Peninsula College",
            "estimated_time": "Schedule within 1 week",
            "required_docs": "None -- advisory meeting",
        },
        {
            "step_number": 5,
            "description": "Open a business bank account. Keeps personal and business finances separate (required for LLCs/Corps, strongly recommended for sole props). Local options: First Federal, Northshore Credit Union.",
            "agency": "Local bank or credit union",
            "estimated_time": "1-2 days",
            "required_docs": "EIN or SSN, state registration docs, business license, photo ID",
        },
        {
            "step_number": 6,
            "description": "Get an Employer Identification Number (EIN) from the IRS. Free and instant online. Required for LLCs with employees, all corporations, and recommended for sole props.",
            "agency": "IRS",
            "estimated_time": "Instant (online)",
            "required_docs": "SSN of responsible party, business name and address",
        },
    ],
    "permit_inquiry": [
        {
            "step_number": 1,
            "description": "Identify the type of permit needed (building, mechanical, plumbing, electrical, land use, etc.). The City of Port Angeles Planning Department can help you determine which permits apply.",
            "agency": "City of Port Angeles -- Planning Dept",
            "estimated_time": "1-2 days (research + call)",
            "required_docs": "Description of proposed work, property address",
        },
        {
            "step_number": 2,
            "description": "Check zoning compatibility. Verify your intended use is allowed in your property's zone. The city zoning map is available at cityofpa.us. Mixed-use zones (C-1, C-2) allow more flexibility.",
            "agency": "City of Port Angeles -- Planning Dept",
            "estimated_time": "Same day (online) to 1 week (if variance needed)",
            "required_docs": "Property address, parcel number, intended use description",
        },
        {
            "step_number": 3,
            "description": "Prepare a site plan. For significant construction, you may need a licensed surveyor. For minor work (interior remodel, fencing), a hand-drawn sketch may suffice.",
            "agency": "Licensed surveyor (if required)",
            "estimated_time": "1-3 weeks (surveyor), same day (sketch)",
            "required_docs": "Property survey, proposed layout, dimensions",
        },
        {
            "step_number": 4,
            "description": "Submit a pre-application or full permit application to the City. Pre-application conferences are recommended for larger projects and are free. Call 360-417-4751 to schedule.",
            "agency": "City of Port Angeles -- Permits",
            "estimated_time": "2-6 weeks for review",
            "required_docs": "Completed application, site plan, construction drawings, fee payment",
        },
        {
            "step_number": 5,
            "description": "Pay fees and await review. Building permit fees vary by project scope ($50 for minor work, several hundred for major construction). Inspections will be scheduled during and after construction.",
            "agency": "City of Port Angeles -- Permits",
            "estimated_time": "Varies by complexity (2 weeks to 3 months)",
            "required_docs": "Fee payment, any additional docs requested during review",
        },
    ],
    "grant_discovery": [
        {
            "step_number": 1,
            "description": "Check NICE (North Olympic Development Council) programs. NODC administers multiple economic development programs for Clallam County including revolving loan funds and technical assistance.",
            "agency": "NODC / NICE",
            "estimated_time": "1-2 days (research + contact)",
            "required_docs": "Business description, funding amount needed",
        },
        {
            "step_number": 2,
            "description": "Review WA State Department of Commerce grants. Programs include Community Development Block Grants, rural business grants, and industry-specific opportunities. Check commerce.wa.gov/grants.",
            "agency": "WA Dept of Commerce",
            "estimated_time": "1-2 weeks (application cycles vary)",
            "required_docs": "Grant application, business plan, financial projections",
        },
        {
            "step_number": 3,
            "description": "Contact the Port of Port Angeles economic development office. The Port offers industrial site options, infrastructure support, and connections to regional economic development resources.",
            "agency": "Port of Port Angeles",
            "estimated_time": "1 week (meeting)",
            "required_docs": "Business concept summary, space/infrastructure needs",
        },
        {
            "step_number": 4,
            "description": "Explore SBA loan programs. The 7(a) loan program and microloans are available through SBA-approved lenders. Check sba.gov/local for Port Angeles area resources.",
            "agency": "U.S. Small Business Administration",
            "estimated_time": "2-8 weeks (application to approval)",
            "required_docs": "Personal financial statement, business plan, tax returns, collateral info",
        },
        {
            "step_number": 5,
            "description": "Check USDA Rural Development programs. Port Angeles qualifies for many USDA rural business programs including Business & Industry Loan Guarantees and Rural Business Development Grants.",
            "agency": "USDA Rural Development",
            "estimated_time": "1-3 months (application cycle)",
            "required_docs": "USDA application forms, business plan, environmental review (if applicable)",
        },
    ],
    "patent_filing": [
        {
            "step_number": 1,
            "description": "Document your invention thoroughly. Write a detailed description including what it does, how it works, what problem it solves, and what makes it different from existing solutions. Include sketches or diagrams.",
            "agency": "Self (inventor documentation)",
            "estimated_time": "1-2 weeks",
            "required_docs": "Invention disclosure, sketches, prior art notes",
        },
        {
            "step_number": 2,
            "description": "Search prior art on USPTO.gov. Use the Patent Full-Text Database (PatFT) and Published Applications database (AppFT). Also check Google Patents. Document what you find and how your invention differs.",
            "agency": "USPTO",
            "estimated_time": "1-3 days",
            "required_docs": "Search results log, comparison notes",
        },
        {
            "step_number": 3,
            "description": "File a provisional patent application with the USPTO. Cost is $160 for micro entities (under $229,087 gross income, not assigned to large entity). This gives you 12 months of 'patent pending' status.",
            "agency": "USPTO",
            "estimated_time": "1-2 days to file",
            "required_docs": "Invention description, drawings, cover sheet, fee payment",
        },
        {
            "step_number": 4,
            "description": "Consider free legal resources. The WA State Bar Association has a patent pro bono program. Seattle and Tacoma have patent clinics. The USPTO has pro se (self-filing) assistance at 800-786-9199.",
            "agency": "WA Bar Association / USPTO Pro Se",
            "estimated_time": "1-4 weeks (to connect with resources)",
            "required_docs": "Provisional application copy, financial qualification docs",
        },
        {
            "step_number": 5,
            "description": "File non-provisional patent application within 12 months of provisional filing. This is the full utility patent application. Micro entity filing fee is approximately $800. Strongly consider professional help.",
            "agency": "USPTO",
            "estimated_time": "12 months deadline from provisional",
            "required_docs": "Full patent specification, claims, drawings, oath/declaration, fees",
        },
    ],
    "general_inquiry": [
        {
            "step_number": 1,
            "description": "Clarify your goal. What civic or business outcome are you trying to achieve? Write a one-sentence summary of what you need.",
            "agency": "Self",
            "estimated_time": "Immediate",
            "required_docs": "None",
        },
        {
            "step_number": 2,
            "description": "Contact the City of Port Angeles general information line at 360-417-4500. They can direct you to the right department for your specific need.",
            "agency": "City of Port Angeles",
            "estimated_time": "Same day",
            "required_docs": "Your question or request summary",
        },
        {
            "step_number": 3,
            "description": "Visit cityofpa.us for online resources, forms, and department contact information. Many common requests can be handled online.",
            "agency": "City of Port Angeles (online)",
            "estimated_time": "Immediate",
            "required_docs": "None",
        },
    ],
}


def generate_workflow(intent: str) -> List[Dict]:
    """
    Generate a structured workflow for the given classified intent.

    Args:
        intent: The classified intent key (e.g. 'start_business')

    Returns:
        List of workflow step dictionaries.
    """
    return WORKFLOWS.get(intent, WORKFLOWS["general_inquiry"])


def get_available_intents() -> List[str]:
    """Return all intent keys that have workflows."""
    return list(WORKFLOWS.keys())
