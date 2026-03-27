"""External API adapters for Legal MCP."""

from .base import AdapterError, BaseAdapter, CACHE_TTL_SECONDS
# ── Core adapters ──
from .auleg import AULegAdapter
from .caleg import CALegAdapter
from .canlii import CanLIIAdapter
from .court_stats import CourtStatsAdapter
from .courtlistener import CourtListenerAdapter
from .destatis import DeStaatisAdapter
from .egov import EGovAdapter
from .enforcement import EnforcementAdapter
from .cnipa_stats import CNIPAStatsAdapter
from .epo_stats import EPOStatsAdapter
from .euipo_stats import EUIPOStatsAdapter
from .gii_stats import GIIStatsAdapter
from .jpo_stats import JPOStatsAdapter
from .kipo_stats import KIPOStatsAdapter
from .oecd_ip import OECDIPAdapter
from .uspto_stats import USPTOStatsAdapter
from .wipo_stats import WIPOStatsAdapter
from .worldbank_ip import WorldBankIPAdapter
from .eurlex import EurLexAdapter
from .gipc_index import GIPCIndexAdapter
from .hudoc import HUDOCAdapter
from .icj import ICJAdapter
from .indiankanoon import IndianKanoonAdapter
from .jpcourts import JPCourtsAdapter
from .legifrance import LegifranceAdapter
# ── Europe ──
from .atleg import ATLegAdapter
from .czleg import CZLegAdapter
from .delaw import DELawAdapter
from .eeleg import EELegAdapter
from .esleg import ESLegAdapter
from .hrleg import HRLegAdapter
from .itleg import ITLegAdapter
from .ltleg import LTLegAdapter
from .lvleg import LVLegAdapter
from .nlleg import NLLegAdapter
from .noleg import NOLegAdapter
from .plleg import PLLegAdapter
from .ptlaw import PTLawAdapter
from .ptleg import PTLegAdapter
from .roleg import ROLegAdapter
from .seleg import SELegAdapter
from .ukleg import UKLegAdapter
# ── Asia-Pacific ──
from .bdlaw import BDLawAdapter
from .lklaw import LKLawAdapter
from .mylaw import MYLawAdapter
from .nzleg import NZLegAdapter
from .phleg import PHLegAdapter
from .pklaw import PKLawAdapter
from .twleg import TWLegAdapter
# ── Americas ──
from .arleg import ARLegAdapter
from .brleg import BRLegAdapter
from .coleg import COLegAdapter
# ── Africa ──
from .africanlii import AfricanLIIAdapter
from .etlaw import ETLawAdapter
from .ghlaw import GHLawAdapter
from .kelaw import KELawAdapter
from .lslaw import LSLawAdapter
from .mwlaw import MWLawAdapter
from .nalaw import NALawAdapter
from .nglaw import NGLawAdapter
from .rwlaw import RWLawAdapter
from .sclaw import SCLawAdapter
from .sllaw import SLLawAdapter
from .tzlaw import TZLawAdapter
from .uglaw import UGLawAdapter
from .zalaw import ZALawAdapter
from .zmlaw import ZMLawAdapter
from .zwlaw import ZWLawAdapter
# ── Multi-region ──
from .paclii import PacLIIAdapter
from .trleg import TRLegAdapter
# ── New IP-specialized adapters ──
from .autm import AUTMAdapter
from .cipo import CIPOAdapter
from .deip_courts import DEIPCourtsAdapter
from .epo_opposition import EPOOppositionAdapter
from .euipo_opposition import EUIPOOppositionAdapter
from .ieee_sa import IEEESAAdapter
from .inpi_brazil import INPIBrazilAdapter
from .ip_australia import IPAustraliaAdapter
from .ip_india import IPIndiaAdapter
from .ipos_singapore import IPOSSingaporeAdapter
from .itc337 import ITC337Adapter
from .krleg import KRLegAdapter
from .oecd_counterfeit import OECDCounterfeitAdapter
from .ptab import PTABAdapter
from .sep_frand import SEPFRANDAdapter
from .upc import UPCAdapter
from .upov import UPOVAdapter
from .uscode import USCodeAdapter
from .us_copyright import USCopyrightAdapter
from .ustr301 import USTR301Adapter
from .wipo_adr import WIPOADRAdapter
from .wipo_copyright_treaties import WIPOCopyrightTreatiesAdapter
from .wipo_hague import WIPOHagueAdapter
from .wipo_lex import WIPOLexAdapter
from .wipo_lisbon import WIPOLisbonAdapter
from .wipo_madrid import WIPOMadridAdapter
from .wipo_tech_trends import WIPOTechTrendsAdapter
from .wto_trips import WTOTRIPSAdapter

__all__ = [
    "AdapterError", "BaseAdapter", "CACHE_TTL_SECONDS",
    # Core
    "AULegAdapter", "CALegAdapter", "CanLIIAdapter", "CNIPAStatsAdapter",
    "CourtListenerAdapter",
    "CourtStatsAdapter", "DeStaatisAdapter", "EGovAdapter", "EnforcementAdapter",
    "EPOStatsAdapter", "EUIPOStatsAdapter", "EurLexAdapter",
    "GIIStatsAdapter", "GIPCIndexAdapter", "HUDOCAdapter",
    "JPOStatsAdapter", "KIPOStatsAdapter",
    "ICJAdapter", "IndianKanoonAdapter", "JPCourtsAdapter",
    "LegifranceAdapter", "OECDIPAdapter",
    "USPTOStatsAdapter", "WIPOStatsAdapter", "WorldBankIPAdapter",
    # Europe
    "ATLegAdapter", "CZLegAdapter", "DELawAdapter",
    "EELegAdapter", "ESLegAdapter",
    "HRLegAdapter", "ITLegAdapter", "LTLegAdapter",
    "LVLegAdapter", "NLLegAdapter", "NOLegAdapter", "PLLegAdapter",
    "PTLawAdapter", "PTLegAdapter",
    "ROLegAdapter", "SELegAdapter", "UKLegAdapter",
    # Asia-Pacific
    "BDLawAdapter", "LKLawAdapter", "MYLawAdapter",
    "NZLegAdapter", "PHLegAdapter", "PKLawAdapter",
    "TWLegAdapter",
    # Americas
    "ARLegAdapter", "BRLegAdapter", "COLegAdapter",
    # Africa
    "AfricanLIIAdapter", "ETLawAdapter", "GHLawAdapter", "KELawAdapter", "LSLawAdapter",
    "MWLawAdapter", "NALawAdapter", "NGLawAdapter", "RWLawAdapter",
    "SCLawAdapter", "SLLawAdapter", "TZLawAdapter", "UGLawAdapter",
    "ZALawAdapter", "ZMLawAdapter", "ZWLawAdapter",
    # Multi-region
    "PacLIIAdapter", "TRLegAdapter",
    # New IP-specialized adapters
    "AUTMAdapter", "CIPOAdapter", "DEIPCourtsAdapter",
    "EPOOppositionAdapter", "EUIPOOppositionAdapter",
    "IEEESAAdapter", "INPIBrazilAdapter", "IPAustraliaAdapter",
    "IPIndiaAdapter", "IPOSSingaporeAdapter", "ITC337Adapter",
    "KRLegAdapter", "OECDCounterfeitAdapter", "PTABAdapter",
    "SEPFRANDAdapter", "UPCAdapter", "UPOVAdapter",
    "USCodeAdapter", "USCopyrightAdapter", "USTR301Adapter",
    "WIPOADRAdapter", "WIPOCopyrightTreatiesAdapter",
    "WIPOHagueAdapter", "WIPOLexAdapter", "WIPOLisbonAdapter",
    "WIPOMadridAdapter", "WIPOTechTrendsAdapter", "WTOTRIPSAdapter",
]
