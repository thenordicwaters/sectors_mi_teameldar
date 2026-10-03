"""Sectors v2 paths and documented credit costs. Do not guess new paths."""

# Structured screener: 1 credit per page, max 200 rows. Natural-language q=: 3 credits.
COMPANIES_SCREENER_PATH = "/v2/companies/"
COMPANIES_SCREENER_CREDITS_PER_PAGE = 1
COMPANIES_SCREENER_NATURAL_LANGUAGE_CREDITS = 3
COMPANIES_SCREENER_MAX_PAGE_SIZE = 200

# Full-universe foreign flow: 1 credit per page, max 30 rows (~20–25 pages).
FOREIGN_FLOW_PATH = "/v2/foreign-flow/"
FOREIGN_FLOW_CREDITS_PER_PAGE = 1
FOREIGN_FLOW_MAX_PAGE_SIZE = 30

# Confirmed for later phases — not called in Phase 1 snapshots.
COMPANY_REPORT_PATH_TEMPLATE = "/v2/company/report/{ticker_symbol}/"
COMPANY_REPORT_CREDITS_PER_SECTION = 1
TOP_CHANGES_PATH = "/v2/companies/top-changes/"
TOP_CHANGES_CREDITS_PER_CLASSIFICATION_AND_PERIOD = 1
CLOSE_UNIVERSE_PATH = "/v2/close/"
CLOSE_UNIVERSE_CREDITS_PER_PAGE = 1
CLOSE_UNIVERSE_MAX_PAGE_SIZE = 30

# IDX insider filings: 1 credit per page, max 30 rows.
FILINGS_PATH = "/v2/filings/"
FILINGS_CREDITS_PER_PAGE = 1
FILINGS_MAX_PAGE_SIZE = 30

# Daily closes: 1 credit per request, max 90 days. Do not loop the universe.
DAILY_PATH_TEMPLATE = "/v2/daily/{symbol}/"
DAILY_CREDITS = 1
INDEX_DAILY_PATH_TEMPLATE = "/v2/index-daily/{index_code}/"
INDEX_DAILY_CREDITS = 1
DAILY_MAX_DAYS = 90
IHSG_INDEX_CODE = "ihsg"
# Documented earliest index-daily date.
IHSG_EARLIEST = "2019-01-02"
