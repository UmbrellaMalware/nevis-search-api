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
    ),  # noqa: E501
    "water_bill": (
        "Thames Water invoice",
        "Water and sewerage charges for 2026/27 for the property at 3 Riverside Walk, Reading RG1 8DB. Customer: Tom Baker.",
    ),  # noqa: E501
    "bank_statement": (
        "HSBC current account statement",
        "Statement for March 2026. Opening balance 4,210.33, closing balance 3,987.10. Card payments, direct debits and a salary credit from Acme Ltd.",
    ),  # noqa: E501
    "tenancy": (
        "Assured shorthold tenancy agreement",
        "Agreement between landlord Peter Grant and tenant Sarah Mitchell for the flat at 14 Elm Grove, Manchester, for 12 months at 950 GBP per month.",
    ),  # noqa: E501
    "council_tax": (
        "Council tax bill 2026/27",
        "Manchester City Council. Band C property at 14 Elm Grove. Annual charge 1,812 GBP payable in 10 instalments.",
    ),  # noqa: E501
    "mortgage_statement": (
        "Annual mortgage statement",
        "Nationwide mortgage account ending 4471, outstanding balance 212,500 GBP secured on 3 Riverside Walk, Reading. Interest rate 4.29%.",
    ),  # noqa: E501
    # --- KYC: identity ---
    "passport": (
        "Passport scan",
        "Biographical page of a British passport, holder Thomas Baker, date of birth 12/05/1979, expiry 2031.",
    ),  # noqa: E501
    "driving_licence": (
        "Driving licence",
        "Photocard driving licence issued by the DVLA, full categories B and BE, licence number BAKER705129TJ9AB.",
    ),  # noqa: E501
    "national_id": (
        "National identity card",
        "Front and back copy of a German Personalausweis for Anna Schmidt, valid until 2030.",
    ),  # noqa: E501
    # --- Income, source of funds / wealth ---
    "payslip": (
        "Payslip March 2026",
        "Gross salary 7,500 GBP, income tax 1,620, National Insurance 410, net pay 5,470. Employer: Acme Ltd.",
    ),  # noqa: E501
    "employment_contract": (
        "Employment contract",
        "Offer of employment as Head of Engineering at Acme Ltd with a base salary of 90,000 GBP per annum plus an annual bonus.",
    ),  # noqa: E501
    "property_sale": (
        "Completion statement - property sale",
        "Sale of 22 Oak Lane, Bristol completed on 3 February 2026. Net proceeds of 415,000 GBP transferred to the client's account.",
    ),  # noqa: E501
    "probate": (
        "Grant of probate",
        "Probate granted to Anna Schmidt as executor of the estate of the late Helmut Schmidt; estate valued at 1.2 million EUR.",
    ),  # noqa: E501
    "business_sale": (
        "Share purchase agreement",
        "Sale of 100% of the shares in Mitchell Design Ltd to Bright Holdings for 2.3 million GBP, payable on completion.",
    ),  # noqa: E501
    "dividend": (
        "Dividend voucher",
        "Interim dividend of 40,000 GBP paid by Mitchell Design Ltd to shareholder Sarah Mitchell.",
    ),  # noqa: E501
    # --- Tax ---
    "tax_return": (
        "Self assessment tax return 2025",
        "SA100 return showing employment income, rental income from a buy-to-let property and capital gains on shares.",
    ),  # noqa: E501
    "cgt": (
        "Capital gains tax computation",
        "Disposal of 1,200 shares in Unilever plc, gain of 18,400 GBP after the annual exempt amount.",
    ),  # noqa: E501
    "tax_residence": (
        "Certificate of tax residence",
        "HMRC certifies that the client is resident in the United Kingdom for tax purposes for 2025/26.",
    ),  # noqa: E501
    # --- Investments, pensions, planning ---
    "portfolio_review": (
        "Quarterly portfolio review",
        "Portfolio returned 3.2% in Q1. Equity allocation 62%, bonds 30%, cash 8%. We recommend rebalancing towards global bonds.",
    ),  # noqa: E501
    "investment_proposal": (
        "Investment proposal",
        "Proposed allocation for a 500,000 GBP lump sum: 50% global equity index funds, 35% investment-grade bonds, 15% alternatives.",
    ),  # noqa: E501
    "risk_questionnaire": (
        "Risk profile questionnaire",
        "Client answers indicate a balanced attitude to risk, a 15-year time horizon and capacity to tolerate a 20% drawdown.",
    ),  # noqa: E501
    "suitability": (
        "Suitability report",
        "Our recommendation to transfer the client's ISA to a lower-cost platform is suitable given their objectives and risk profile.",
    ),  # noqa: E501
    "isa": (
        "Stocks and shares ISA statement",
        "ISA valuation as of 5 April 2026: 86,420 GBP. Contributions this tax year 20,000 GBP.",
    ),  # noqa: E501
    "pension": (
        "Workplace pension annual statement",
        "Defined contribution pension with Aviva, fund value 312,000 GBP, projected retirement income 18,500 GBP a year at age 67.",
    ),  # noqa: E501
    "sipp": (
        "SIPP transfer request",
        "Request to transfer an existing personal pension into a self-invested personal pension.",
    ),  # noqa: E501
    "fees": (
        "Client fee agreement",
        "Ongoing advice fee of 0.75% per annum of assets under management, charged quarterly, plus a one-off planning fee.",
    ),  # noqa: E501
    "trust": (
        "Discretionary trust deed",
        "Settlement of 1 million GBP into a discretionary trust for the benefit of the settlor's grandchildren; trustees Anna Schmidt and Peter Grant.",
    ),  # noqa: E501
    "will": (
        "Last will and testament",
        "Will of Thomas Baker leaving the residuary estate to his two children in equal shares.",
    ),  # noqa: E501
    "life_insurance": (
        "Life insurance policy schedule",
        "Level term life cover of 750,000 GBP over 20 years with critical illness benefit.",
    ),  # noqa: E501
    "mortgage_offer": (
        "Mortgage offer",
        "Offer of a 350,000 GBP repayment mortgage over 25 years at a fixed rate of 4.1% for five years.",
    ),  # noqa: E501
    "bond_fund": (
        "Corporate bond fund factsheet",
        "The fund invests in sterling investment-grade corporate bonds; yield to maturity 5.1%, duration 6.2 years.",
    ),  # noqa: E501
    "esg": (
        "ESG screening report",
        "Portfolio holdings screened for environmental, social and governance risks; two holdings excluded for thermal coal exposure.",
    ),  # noqa: E501
    "aml": (
        "AML screening result",
        "Name screening against sanctions and politically exposed persons lists returned no matches for the client.",
    ),  # noqa: E501
    "meeting_notes": (
        "Annual review meeting notes",
        "Discussed retirement plans, a planned house purchase next year and gifts to the children to reduce inheritance tax.",
    ),  # noqa: E501
    "complaint": (
        "Client complaint letter",
        "The client is unhappy with the delay in processing the pension transfer and requests compensation.",
    ),  # noqa: E501
    "wire": (
        "Wire transfer instructions",
        "Please transfer 25,000 GBP to IBAN GB29NWBK60161331926819, reference ISA top-up.",
    ),  # noqa: E501
    "valuation": (
        "Property valuation report",
        "RICS valuation of 22 Oak Lane, Bristol at 430,000 GBP as of January 2026.",
    ),  # noqa: E501
    "company_accounts": (
        "Company annual accounts",
        "Mitchell Design Ltd accounts for the year ended 31 December 2025: turnover 1.8 million GBP, profit after tax 310,000 GBP.",
    ),  # noqa: E501
    # --- Distractors (not advice documents) ---
    "gym": (
        "Gym membership renewal",
        "Your annual gym membership renews on 1 May; the monthly fee rises to 45 GBP.",
    ),  # noqa: E501
    "restaurant": (
        "Restaurant booking confirmation",
        "Table for four at 7:30pm on Friday at The Ivy, London.",
    ),  # noqa: E501
    "car_service": (
        "Car service invoice",
        "Annual service and MOT for a 2019 Volkswagen Golf, total 289 GBP.",
    ),  # noqa: E501
    "newsletter": (
        "Market newsletter",
        "Central banks kept rates on hold this month; equity markets rallied on strong earnings.",
    ),  # noqa: E501
}

ADDRESS = {
    "electricity_bill",
    "water_bill",
    "bank_statement",
    "tenancy",
    "council_tax",
    "mortgage_statement",
}  # noqa: E501
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
    },  # noqa: E501
    "source of wealth": {
        "employment_contract",
        "property_sale",
        "probate",
        "business_sale",
        "dividend",
    },  # noqa: E501
    "proof of income": {"payslip", "employment_contract", "dividend", "tax_return"},
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
]  # noqa: E501
