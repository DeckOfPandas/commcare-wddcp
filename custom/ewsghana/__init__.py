from custom.ewsghana.comparison_report import ProductsCompareReport, LocationsCompareReport,\
    SMSUsersCompareReport, WebUsersCompareReport, SupplyPointsCompareReport
from custom.ewsghana.reports.specific_reports.stock_status_report import StockStatus
from custom.ewsghana.reports.stock_levels_report import StockLevelsReport
from custom.ewsghana.reports.specific_reports.reporting_rates import ReportingRatesReport


TEST = True
LOCATION_TYPES = ["country", "region", "district", "facility"]

CUSTOM_REPORTS = (
    ('Custom reports', (
        StockStatus,
        StockLevelsReport,
        ReportingRatesReport,
    )),
    ('Compare reports', (
        ProductsCompareReport,
        LocationsCompareReport,
        SupplyPointsCompareReport,
        WebUsersCompareReport,
        SMSUsersCompareReport,
    ))
)
