"""Hand-labelled evaluation set for semantic search: a wealth-advisor document corpus.

Documents are written the way real ones read: they rarely name their own category
(a utility bill never says "proof of address"). Relevance labels are binary and were set by hand.
Queries are split by whether their concept is in the synonym glossary (migration 0002), so the
glossary's effect can be measured separately on concepts it does and does not cover.
"""

# id -> (title, content)
DOCS: dict[str, tuple[str, str]] = {
    # --- KYC: address ---
    "electricity_bill": (
        "British Gas bill",
        "Electricity and gas charges for 1 Jan - 31 Mar 2026. Account holder Sarah Mitchell, 14 Elm Grove, Manchester M14 6PQ. Amount due 182.40 GBP.",
    ),
    "water_bill": (
        "Thames Water invoice",
        "Water and sewerage charges for 2026/27 for the property at 3 Riverside Walk, Reading RG1 8DB. Customer: Tom Baker.",
    ),
    "bank_statement": (
        "HSBC current account statement",
        "Statement for March 2026. Opening balance 4,210.33, closing balance 3,987.10. Card payments, direct debits and a salary credit from Acme Ltd.",
    ),
    "tenancy": (
        "Assured shorthold tenancy agreement",
        "Agreement between landlord Peter Grant and tenant Sarah Mitchell for the flat at 14 Elm Grove, Manchester, for 12 months at 950 GBP per month.",
    ),
    "council_tax": (
        "Council tax bill 2026/27",
        "Manchester City Council. Band C property at 14 Elm Grove. Annual charge 1,812 GBP payable in 10 instalments.",
    ),
    "mortgage_statement": (
        "Annual mortgage statement",
        "Nationwide mortgage account ending 4471, outstanding balance 212,500 GBP secured on 3 Riverside Walk, Reading. Interest rate 4.29%.",
    ),
    # --- KYC: identity ---
    "passport": (
        "Passport scan",
        "Biographical page of a British passport, holder Thomas Baker, date of birth 12/05/1979, expiry 2031.",
    ),
    "driving_licence": (
        "Driving licence",
        "Photocard driving licence issued by the DVLA, full categories B and BE, licence number BAKER705129TJ9AB.",
    ),
    "national_id": (
        "National identity card",
        "Front and back copy of a German Personalausweis for Anna Schmidt, valid until 2030.",
    ),
    # --- Income, source of funds / wealth ---
    "payslip": (
        "Payslip March 2026",
        "Gross salary 7,500 GBP, income tax 1,620, National Insurance 410, net pay 5,470. Employer: Acme Ltd.",
    ),
    "employment_contract": (
        "Employment contract",
        "Offer of employment as Head of Engineering at Acme Ltd with a base salary of 90,000 GBP per annum plus an annual bonus.",
    ),
    "property_sale": (
        "Completion statement - property sale",
        "Sale of 22 Oak Lane, Bristol completed on 3 February 2026. Net proceeds of 415,000 GBP transferred to the client's account.",
    ),
    "probate": (
        "Grant of probate",
        "Probate granted to Anna Schmidt as executor of the estate of the late Helmut Schmidt; estate valued at 1.2 million EUR.",
    ),
    "business_sale": (
        "Share purchase agreement",
        "Sale of 100% of the shares in Mitchell Design Ltd to Bright Holdings for 2.3 million GBP, payable on completion.",
    ),
    "dividend": (
        "Dividend voucher",
        "Interim dividend of 40,000 GBP paid by Mitchell Design Ltd to shareholder Sarah Mitchell.",
    ),
    # --- Tax ---
    "tax_return": (
        "Self assessment tax return 2025",
        "SA100 return showing employment income, rental income from a buy-to-let property and capital gains on shares.",
    ),
    "cgt": (
        "Capital gains tax computation",
        "Disposal of 1,200 shares in Unilever plc, gain of 18,400 GBP after the annual exempt amount.",
    ),
    "tax_residence": (
        "Certificate of tax residence",
        "HMRC certifies that the client is resident in the United Kingdom for tax purposes for 2025/26.",
    ),
    # --- Investments, pensions, planning ---
    "portfolio_review": (
        "Quarterly portfolio review",
        "Portfolio returned 3.2% in Q1. Equity allocation 62%, bonds 30%, cash 8%. We recommend rebalancing towards global bonds.",
    ),
    "investment_proposal": (
        "Investment proposal",
        "Proposed allocation for a 500,000 GBP lump sum: 50% global equity index funds, 35% investment-grade bonds, 15% alternatives.",
    ),
    "risk_questionnaire": (
        "Risk profile questionnaire",
        "Client answers indicate a balanced attitude to risk, a 15-year time horizon and capacity to tolerate a 20% drawdown.",
    ),
    "suitability": (
        "Suitability report",
        "Our recommendation to transfer the client's ISA to a lower-cost platform is suitable given their objectives and risk profile.",
    ),
    "isa": (
        "Stocks and shares ISA statement",
        "ISA valuation as of 5 April 2026: 86,420 GBP. Contributions this tax year 20,000 GBP.",
    ),
    "pension": (
        "Workplace pension annual statement",
        "Defined contribution pension with Aviva, fund value 312,000 GBP, projected retirement income 18,500 GBP a year at age 67.",
    ),
    "sipp": (
        "SIPP transfer request",
        "Request to transfer an existing personal pension into a self-invested personal pension.",
    ),
    "fees": (
        "Client fee agreement",
        "Ongoing advice fee of 0.75% per annum of assets under management, charged quarterly, plus a one-off planning fee.",
    ),
    "trust": (
        "Discretionary trust deed",
        "Settlement of 1 million GBP into a discretionary trust for the benefit of the settlor's grandchildren; trustees Anna Schmidt and Peter Grant.",
    ),
    "will": (
        "Last will and testament",
        "Will of Thomas Baker leaving the residuary estate to his two children in equal shares.",
    ),
    "life_insurance": (
        "Life insurance policy schedule",
        "Level term life cover of 750,000 GBP over 20 years with critical illness benefit.",
    ),
    "mortgage_offer": (
        "Mortgage offer",
        "Offer of a 350,000 GBP repayment mortgage over 25 years at a fixed rate of 4.1% for five years.",
    ),
    "bond_fund": (
        "Corporate bond fund factsheet",
        "The fund invests in sterling investment-grade corporate bonds; yield to maturity 5.1%, duration 6.2 years.",
    ),
    "esg": (
        "ESG screening report",
        "Portfolio holdings screened for environmental, social and governance risks; two holdings excluded for thermal coal exposure.",
    ),
    "aml": (
        "AML screening result",
        "Name screening against sanctions and politically exposed persons lists returned no matches for the client.",
    ),
    "meeting_notes": (
        "Annual review meeting notes",
        "Discussed retirement plans, a planned house purchase next year and gifts to the children to reduce inheritance tax.",
    ),
    "complaint": (
        "Client complaint letter",
        "The client is unhappy with the delay in processing the pension transfer and requests compensation.",
    ),
    "wire": (
        "Wire transfer instructions",
        "Please transfer 25,000 GBP to IBAN GB29NWBK60161331926819, reference ISA top-up.",
    ),
    "valuation": (
        "Property valuation report",
        "RICS valuation of 22 Oak Lane, Bristol at 430,000 GBP as of January 2026.",
    ),
    "company_accounts": (
        "Company annual accounts",
        "Mitchell Design Ltd accounts for the year ended 31 December 2025: turnover 1.8 million GBP, profit after tax 310,000 GBP.",
    ),
    # --- Distractors (not advice documents) ---
    "gym": (
        "Gym membership renewal",
        "Your annual gym membership renews on 1 May; the monthly fee rises to 45 GBP.",
    ),
    "restaurant": (
        "Restaurant booking confirmation",
        "Table for four at 7:30pm on Friday at The Ivy, London.",
    ),
    "car_service": (
        "Car service invoice",
        "Annual service and MOT for a 2019 Volkswagen Golf, total 289 GBP.",
    ),
    "newsletter": (
        "Market newsletter",
        "Central banks kept rates on hold this month; equity markets rallied on strong earnings.",
    ),
}

ADDRESS = {
    "electricity_bill",
    "water_bill",
    "bank_statement",
    "tenancy",
    "council_tax",
    "mortgage_statement",
}
IDENTITY = {"passport", "driving_licence", "national_id"}

# Concepts present in the glossary (migration 0002).
GLOSSARY_QUERIES: dict[str, set[str]] = {
    "address proof": ADDRESS,
    "proof of address for new client": ADDRESS,
    "identity document": IDENTITY,
    "photo id": IDENTITY,
    "source of funds": {
        "payslip",
        "employment_contract",
        "property_sale",
        "probate",
        "business_sale",
        "dividend",
        "bank_statement",
    },
    "source of wealth": {
        "employment_contract",
        "property_sale",
        "probate",
        "business_sale",
        "dividend",
    },
    "proof of income": {"payslip", "employment_contract", "dividend", "tax_return"},
}

# Held-out paraphrases: the SAME concepts as GLOSSARY_QUERIES, worded so that no glossary term
# appears in them. The glossary does not fire here, which shows how it does on wordings it was
# not written for (the benchmark asserts that none of these trigger an expansion).
HELDOUT_QUERIES: dict[str, set[str]] = {
    "documents confirming where the client lives": GLOSSARY_QUERIES["address proof"],
    "evidence of residence": GLOSSARY_QUERIES["address proof"],
    "verify client home address": GLOSSARY_QUERIES["address proof"],
    "verify who the client is": GLOSSARY_QUERIES["identity document"],
    "government issued photo identification": GLOSSARY_QUERIES["identity document"],
    "where does the client's money come from": GLOSSARY_QUERIES["source of funds"],
    "how did the client become wealthy": GLOSSARY_QUERIES["source of wealth"],
    "evidence of earnings": GLOSSARY_QUERIES["proof of income"],
}

# Concepts the glossary knows nothing about.
OTHER_QUERIES: dict[str, set[str]] = {
    "retirement savings": {"pension", "sipp", "isa"},
    "pension": {"pension", "sipp"},
    "client risk appetite": {"risk_questionnaire", "suitability"},
    "investment recommendations": {"portfolio_review", "investment_proposal", "suitability"},
    "asset allocation": {"portfolio_review", "investment_proposal"},
    "capital gains": {"tax_return", "cgt"},
    "tax residency": {"tax_residence"},
    "estate planning": {"trust", "will", "meeting_notes", "probate"},
    "inheritance tax": {"meeting_notes", "trust", "will", "probate"},
    "life cover": {"life_insurance"},
    "home loan": {"mortgage_offer", "mortgage_statement"},
    "advisory fees": {"fees"},
    "sanctions screening": {"aml"},
    "PEP check": {"aml"},
    "property value": {"valuation"},
    "company financials": {"company_accounts"},
    "sustainable investing": {"esg"},
    "bond fund yield": {"bond_fund"},
    "selling the business": {"business_sale"},
    "rental agreement": {"tenancy"},
    "electricity bill": {"electricity_bill"},
    "pension transfer complaint": {"complaint"},
    "ISA": {"isa", "suitability"},
}

# Nothing in the corpus is relevant: these must not produce confident matches.
NOISE_QUERIES = [
    "weather forecast",
    "football results",
    "cooking recipe",
    "learn guitar",
    "flight delay",
]
