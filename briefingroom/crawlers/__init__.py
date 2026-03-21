from .fsc import crawl_fsc
from .fss import crawl_fss
from .moef import crawl_moef
from .moe import crawl_moe
from .molit import crawl_molit
from .mohw import crawl_mohw
from .unikorea import crawl_unikorea
from .moj import crawl_moj
from .mcst import crawl_mcst
from .mois import crawl_mois
from .me import crawl_me
from .moel import crawl_moel
from .mafra import crawl_mafra
from .mss import crawl_mss
from .ftc import crawl_ftc
from .pipc import crawl_pipc
from .acrc import crawl_acrc
from .motie import crawl_motie
from .mofa import crawl_mofa
from .mof import crawl_mof
from .mogef import crawl_mogef
from .mpva import crawl_mpva
from .moleg import crawl_moleg
from .mpm import crawl_mpm
from .msit import crawl_msit
from .mnd import crawl_mnd
from .bok import crawl_bok

CRAWLERS = [
    ("금융위원회", crawl_fsc),
    ("금융감독원", crawl_fss),
    ("기획재정부", crawl_moef),
    ("교육부", crawl_moe),
    ("국토교통부", crawl_molit),
    ("보건복지부", crawl_mohw),
    ("통일부", crawl_unikorea),
    ("법무부", crawl_moj),
    ("문화체육관광부", crawl_mcst),
    ("행정안전부", crawl_mois),
    ("환경부", crawl_me),
    ("고용노동부", crawl_moel),
    ("농림축산식품부", crawl_mafra),
    ("중소벤처기업부", crawl_mss),
    ("공정거래위원회", crawl_ftc),
    ("개인정보보호위원회", crawl_pipc),
    ("국민권익위원회", crawl_acrc),
    ("산업통상자원부", crawl_motie),
    ("외교부", crawl_mofa),
    ("해양수산부", crawl_mof),
    ("성평등가족부", crawl_mogef),
    ("국가보훈부", crawl_mpva),
    ("법제처", crawl_moleg),
    ("인사혁신처", crawl_mpm),
    ("과학기술정보통신부", crawl_msit),
    ("국방부", crawl_mnd),
    ("한국은행", crawl_bok),
]

CRAWLER_MAP = {name: crawler for name, crawler in CRAWLERS}
CRAWLER_ALIASES = {
    "fsc": "금융위원회",
    "fsc": "금융위원회",
    "fss": "금융감독원",
    "fss": "금융감독원",
    "moef": "기획재정부",
    "moef": "기획재정부",
    "moe": "교육부",
    "moe": "교육부",
    "molit": "국토교통부",
    "molit": "국토교통부",
    "mohw": "보건복지부",
    "mohw": "보건복지부",
    "unikorea": "통일부",
    "unikorea": "통일부",
    "moj": "법무부",
    "moj": "법무부",
    "mcst": "문화체육관광부",
    "mcst": "문화체육관광부",
    "mois": "행정안전부",
    "mois": "행정안전부",
    "me": "환경부",
    "me": "환경부",
    "moel": "고용노동부",
    "moel": "고용노동부",
    "mafra": "농림축산식품부",
    "mafra": "농림축산식품부",
    "mss": "중소벤처기업부",
    "mss": "중소벤처기업부",
    "ftc": "공정거래위원회",
    "ftc": "공정거래위원회",
    "pipc": "개인정보보호위원회",
    "pipc": "개인정보보호위원회",
    "acrc": "국민권익위원회",
    "acrc": "국민권익위원회",
    "motie": "산업통상자원부",
    "motie": "산업통상자원부",
    "mofa": "외교부",
    "mofa": "외교부",
    "mof": "해양수산부",
    "mof": "해양수산부",
    "mogef": "성평등가족부",
    "mogef": "성평등가족부",
    "mpva": "국가보훈부",
    "mpva": "국가보훈부",
    "moleg": "법제처",
    "moleg": "법제처",
    "mpm": "인사혁신처",
    "mpm": "인사혁신처",
    "msit": "과학기술정보통신부",
    "msit": "과학기술정보통신부",
    "mnd": "국방부",
    "mnd": "국방부",
    "bok": "한국은행",
    "bok": "한국은행",
}
