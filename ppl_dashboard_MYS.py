import numpy as np
import streamlit as st
import pandas as pd
import re
import numpy as np
import gspread
import io
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. SHARED RESOURCES ---
@st.cache_resource
def get_gspread_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

def make_url(sheet_id):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"

@st.cache_data(ttl=600)
def load_google_sheet(url, sheet_name=0):
    try:
        client = get_gspread_client()
        sheet = client.open_by_url(url)
        if isinstance(sheet_name, str): worksheet = sheet.worksheet(sheet_name)
        else: worksheet = sheet.get_worksheet(sheet_name)
        data = worksheet.get_all_values()
        return pd.DataFrame(data)
    except Exception as e: 
        print(f"Error loading {sheet_name}: {e}")
        return None

def write_to_sheet(url, sheet_name, df):
    try:
        client = get_gspread_client()
        sh = client.open_by_url(url)
        try: ws = sh.worksheet(sheet_name); ws.clear()
        except: ws = sh.add_worksheet(title=sheet_name, rows=100, cols=20)
        df_str = df.fillna("").astype(str)
        if df.index.name is not None: df_str = df_str.reset_index()
        data = [df_str.columns.values.tolist()] + df_str.values.tolist()
        ws.resize(rows=len(data), cols=len(data[0]))
        ws.update(data)
        return True
    except: return False

def get_saved_reports(url):
    try:
        client = get_gspread_client()
        sh = client.open_by_url(url)
        titles = [ws.title for ws in sh.worksheets()]
        reports = set()
        for t in titles:
            if t.startswith("Rep_"):
                parts = t.split('_') 
                if len(parts) >= 2: reports.add(parts[1])
        return sorted(list(reports), reverse=True)
    except: return []

# --- 2. DATA PROCESSING HELPERS ---
def normalize_store_name(name, report_type='AEON', loc_map=None):
    if pd.isna(name): return "UNKNOWN"
    # Crush any double spaces or invisible tabs into a single space
    name = re.sub(r'\s+', ' ', str(name)).strip().upper()

    if report_type in ['AEON', 'AEON DF']:
        if loc_map and name in loc_map:
            return loc_map[name]
        return name
    
    elif report_type in ['TFP', 'TFP DF']:
        # 1. First, check for an exact match in the Loc tab dictionary
        if loc_map and name in loc_map:
            return loc_map[name]
        
        # 2. If no exact match, see if the name contains a code like "BBT"
        # We look for the code at the start of the string (e.g., "BBT - BIG BATAI")
        if loc_map:
            for code in loc_map.keys():
                # If the name starts with the code (e.g., "BBT"), use that mapped value
                if name.startswith(code):
                    return loc_map[code]

    # elif report_type == 'TFP' or report_type == 'TFP DF':
    #     if name == 'BBT - BIG BATAI': return "VG Ben's Batai (BBT)-KUL"
    #     if name == "VG BEN'S BATAI (BBT)-KUL": return "VG Ben's Batai (BBT)-KUL"
    #     if name == 'BIP - BIG IPC': return "VG Ben's Ipc (BIP)-KUL"
    #     if name == "VG BEN'S IPC (BIP)-KUL": return "VG Ben's Ipc (BIP)-KUL"
    #     if name == 'BLI - BIG THE LINC': return "VG Ben's Linc (BLI)-KUL"
    #     if name == "VG BEN'S LINC (BLI)-KUL": return "VG Ben's Linc (BLI)-KUL"
    #     if name == 'BMM - BIG MALL OF MEDINI': return "VG Ben's Mall (BMM)-JHR"
    #     if name == "VG BEN'S MALL (BMM)-JHR": return "VG Ben's Mall (BMM)-JHR"
    #     if name == 'BPS - BIG PUBLIKA': return "VG Ben's Publika (BPS)-KUL"
    #     if name == "VG BEN'S PUBLIKA (BPS)-KUL": return "VG Ben's Publika (BPS)-KUL"
    #     if name == "VG BEN'S PUBLIKA (BPS)-KUL HC001500-4001": return "VG Ben's Publika (BPS)-KUL"
    #     if name == 'BSC - BSC FINE FOODS': return "VG Ben's (BSC)-KUL"
    #     if name == "VG BEN'S (BSC)-KUL": return "VG Ben's (BSC)-KUL"
    #     if name == "VG BEN'S BATAI (BBT)-KUL HC001500-4002": return "VG Ben's (BSC)-KUL"
    #     if name == "VG BEN'S (BSC)-KUL HC001500-4011" : return "VG Ben's (BSC)-KUL"
    #     if name == "VG Ben's Batai (BBT)-KUL" : return  "VG Ben's (BSC)-KUL"
    #     if name == 'LGC - LEISURE MALL': return 'VG Leisure Mall (LGC)-KUL'
    #     if name == 'VG LEISURE MALL (LGC)-KUL HC001500-3019': return 'VG Leisure Mall (LGC)-KUL'
    #     if name == 'VG LEISURE MALL (LGC)-KUL': return 'VG Leisure Mall (LGC)-KUL'
    #     if name == 'VAD - ARA DAMANSARA': return 'VG Citta Mall (VAD)-KUL'
    #     if name == 'VG CITTA MALL (VAD)-KUL HC001500-3005': return 'VG Citta Mall (VAD)-KUL'
    #     if name == 'VG CITTA MALL (VAD)-KUL': return 'VG Citta Mall (VAD)-KUL'
    #     if name == 'VAK - AVENUE K': return 'VG Avenue K (VAK)-KUL'
    #     if name == 'VG AVENUE K (VAK)-KUL': return 'VG Avenue K (VAK)-KUL'
    #     if name == 'VG AVENUE K (VAK)-KUL HC001500-3006': return 'VG Avenue K (VAK)-KUL'
    #     if name == 'VCJ - CITY JUNCTION': return 'VG City Junction (VCJ)-PNG'
    #     if name == 'VG CITY JUNCTION (VCJ)-PNG': return 'VG City Junction (VCJ)-PNG'
    #     if name == 'VDJ - DAMANSARA JAYA': return 'VG Atria (VDJ)-KUL'
    #     if name == 'VG ATRIA (VDJ)-KUL HC001500-3004': return 'VG Atria (VDJ)-KUL'
    #     if name == 'VG ATRIA (VDJ)-KUL': return 'VG Atria (VDJ)-KUL'
    #     if name == 'VDP - DP ARKADIA': return 'VG Desa Park City (VDP)-KUL'
    #     if name == 'VG DESA PARK CITY (VDP)-KUL': return 'VG Desa Park City (VDP)-KUL'
    #     if name == 'VG DESA PARK CITY (VDP)-KUL HC001500-3008': return 'VG Desa Park City (VDP)-KUL'
    #     if name == 'VEC - EKOCHERAS': return 'VG Eko Cheras (VEC)-KUL'
    #     if name == 'VG EKO CHERAS (VEC)-KUL': return 'VG Eko Cheras (VEC)-KUL'
    #     if name == 'VG EKO CHERAS (VEC)-KUL HC001500-3012': return 'VG Eko Cheras (VEC)-KUL'
    #     if name == 'VEM - EMPIRE CITY': return 'VG Empire City-KUL'
    #     if name == 'VG EMPIRE CITY (VEM)-KUL': return 'VG Empire City-KUL'
    #     if name == 'VGB - BANGSAR VILLAGE': return 'VG Bangsar Village (VGB)-KUL'
    #     if name == 'VG BANGSAR VILLAGE (VGB)-KUL': return 'VG Bangsar Village (VGB)-KUL'
    #     if name == 'VG BANGSAR VILLAGE (VGB)-KUL HC001500-3003': return 'VG Bangsar Village (VGB)-KUL'
    #     if name == '2 VG BANGSAR VILLAGE (VGB)-KUL': return 'VG Bangsar Village (VGB)-KUL'
    #     if name == 'VGG - GIZA': return 'VG Giza (VGG)-KUL'
    #     if name == 'VG GIZA (VGG)-KUL HC001500-3002': return 'VG Giza (VGG)-KUL'
    #     if name == 'VG GIZA (VGG)-KUL': return 'VG Giza (VGG)-KUL'
    #     if name == 'VGO - MONT KIARA': return 'VG Mont Kiara (VGO)-KUL'
    #     if name == 'VG KIARA BAY-KUL': return 'VG Kiara Bay-KUL'
    #     if name == 'VG MONT KIARA (VGO)-KUL': return 'VG Mont Kiara (VGO)-KUL'
    #     if name == 'VG MONT KIARA (VGO)-KUL HC001500-3001': return 'VG Mont Kiara (VGO)-KUL'
    #     if name == '3 VG MONT KIARA (VGO)-KUL': return 'VG Mont Kiara (VGO)-KUL'
    #     if name == 'VHS - HARTAMAS SHOPPING CENTER': return 'VG Sri Hartamas (VHS)-KUL'
    #     if name == 'VG SRI HARTAMAS (VHS)-KUL' : return 'VG Sri Hartamas (VHS)-KUL'
    #     if name == 'VIK - IOI MALL KULAI': return 'VG IOI Mall Kulai (VIK)-JHR'
    #     if name == 'VG IOI Mall Kulai (VIK)-JHR': return 'VG IOI Mall Kulai (VIK)-JHR'
    #     if name == 'VG IOI MALL KULAI (VIK)-JHR': return 'VG IOI Mall Kulai (VIK)-JHR'
    #     if name == 'VIM - IOI MALL PUCHONG': return 'VG Puchong-KUL'
    #     if name == 'VG PUCHONG-KUL': return 'VG Puchong-KUL'
    #     if name == 'VG PUCHONG-KUL HC001500-3025': return 'VG Puchong-KUL'
    #     if name == 'VKB - KIARA BAY': return 'VG Kiara Bay-KUL'
    #     if name == 'VLH - LAMAN SERI HARMONI': return 'VG Laman Seri Harmoni 33 (VLH)-KUL'
    #     if name == 'VG Laman Seri Harmoni 33 (VLH)-KUL': return 'VG Laman Seri Harmoni 33 (VLH)-KUL'
    #     if name == 'VG LAMAN SERI HARMONI 33 (VLH)-KUL': return 'VG Laman Seri Harmoni 33 (VLH)-KUL'
    #     if name == 'VG LAMAN SERI HARMONI 33 (VLH)-KUL HC001500-3035': return 'VG Laman Seri Harmoni 33 (VLH)-KUL'
    #     if name == 'VMN - MYRA NILAI': return 'VG Myra Park Marketplace-KUL'
    #     if name == 'VG MYRA PARK MARKETPLACE-KUL HC001500-4013': return 'VG Myra Park Marketplace-KUL'
    #     if name == 'VG MYRA PARK MARKETPLACE-KUL': return 'VG Myra Park Marketplace-KUL'
    #     if name == 'VMT - MYTOWN': return 'VG My Town-KUL'
    #     if name == 'VG MY TOWN-KUL': return 'VG My Town-KUL'
    #     if name == 'VPM - PARADIGM MALL JB': return 'VG Paradigm Mall (VPM)-JHR'
    #     if name == 'VG PARADIGM MALL (VPM)-JHR': return 'VG Paradigm Mall (VPM)-JHR'
    #     if name == 'VPS - 168 PARK SELAYANG': return 'VG Selayang 168-KUL'
    #     if name == 'VG SELAYANG 168-KUL' : return 'VG Selayang 168-KUL'
    #     if name == 'VQW - QUEENS WATERFRONT PENANG': return 'VG Queen (VQW)-PNG'
    #     if name == 'VG QUEEN (VQW)-PNG': return 'VG Queen (VQW)-PNG'
    #     if name == 'VSK - SOUTHKEY': return 'VG Midvalley Southkey (VSK)-JHR'
    #     if name == 'VG MIDVALLEY SOUTHKEY (VSK)-JHR': return 'VG Midvalley Southkey (VSK)-JHR'
    #     if name == 'VSP - SUBANG PARADE': return 'VG Subang Parade (VSP)-KUL'
    #     if name == 'VG SUBANG PARADE (VSP)-KUL': return 'VG Subang Parade (VSP)-KUL'
    #     if name == '2 VG SUBANG PARADE (VSP)-KUL': return 'VG Subang Parade (VSP)-KUL'
    #     if name == 'VG SUBANG PARADE (VSP)-KUL HC001500-3014' : return 'VG Subang Parade (VSP)-KUL'
    #     if name == 'VSQ - SUNWAY SQUARE': return 'VG Sunway Square Mall (VSQ)-KUL'
    #     if name == 'VG SUNWAY SQUARE MALL (VSQ)-KUL' : return 'VG Sunway Square Mall (VSQ)-KUL'
    #     if name == 'VSS - SIERRA FRESCO': return 'VG Sierras Fresco-KUL'
    #     if name == 'VG SIERRAS FRESCO (VSS)-KUL' : return 'VG Sierras Fresco-KUL'
    #     if name == 'VG SIERRAS FRESCO-KUL' : return 'VG Sierras Fresco-KUL'
    #     if name == 'VTS - TAMARIND SQUARE': return 'VG Tamarind Square (VTS)-KUL'
    #     if name == 'VG TAMARIND SQUARE (VTS)-KUL': return 'VG Tamarind Square (VTS)-KUL'
    #     if name == 'VG TAMARIND SQUARE (VTS)-KUL HC001500-4016': return 'VG Tamarind Square (VTS)-KUL'
    #     if name == 'XXX VG TAMARIND SQUARE (VTS)-KUL': return 'VG Tamarind Square (VTS)-KUL'
    #     if name == 'VBM - BUKIT MERTAJAM': return 'VG Vangohh Eminent (VBM)-PNG'
    #     if name == 'VG VANGOHH EMINENT (VBM)-PNG' : return 'VG Vangohh Eminent (VBM)-PNG'

    #     return name
    
    elif report_type == 'NTUC':
        name = re.sub(r'^\d+\s*-\s*', '', name)
        name = name.replace('FPX-', '').strip()
        if name == 'BUKIT TIMAH PLAZA-PM' : return 'BUKIT TIMAH PLAZA'
        if name == 'CLEMENTI MALL-PM' : return 'CLEMENTI MALL'
        if name == 'FUNAN-PM' : return 'FUNAN'
        if name == 'BALMORAL PLAZA-PM' : return 'BALMORAL PLAZA'
        if name == 'BEDOK MALL-APM' : return 'BEDOK MALL'
        if name == 'CLEMENTI MALL FINEST' : return 'CLEMENTI MALL'
        if name == 'FINEST @ THE WOODLEIGH MALL' : return 'WOODLEIGH MALL'
        if name == 'BEDOK MALL FINEST' : return 'BEDOK MALL'
        if name == 'FINEST @SCOTTS SQUARE' :return 'SCOTTS SQUARE'
        if name == 'WOODLANDS CAUSEWAY POINT' : return 'CAUSEWAY POINT'
        if name == 'HOUGANG A' : return 'HOUGANG A 202'
        if name == 'SENGKANG GRAND' : return 'SENGKANG GRAND MALL'
        if name == 'FINEST @VALLEY POINT' : return 'VALLEY POINT FINEST'
        if name == 'YEW TEE MRT FINEST' : return 'YEW TEE MRT'
        if name == 'ANG MO KIO BLK 712 (B)' : return 'ANG MO KIO BLK712'
        if name == 'CENTURY SQUARE FINEST': return 'CENTURY SQUARE'
        if name == 'RAFFLES HOLLAND V HALL' : return 'RAFFLES HOLLAND V'
        if name == 'DAIRY FARM RESIDENCES FINEST' : return 'DFARM'
        if name == 'JEWEL CHANGI AIRPORT .' : return 'JEWEL'
        if name == 'KOMO SHOPPES FINEST' : return 'KOMO' 
        if name == 'CORONATION PLAZA BUKIT TIMAH': return 'CORONATION PLAZA'
        if name == 'WHITESANDS' : return 'WHITE SANDS'
        if name == 'VIVO CITY HYPER-PM' : return 'VIVO CITY HYPER'
        if name == 'JUNCTION 8-APM' : return 'JUNCTION 8'
        if name == 'PARKWAY PARADE-PM': return 'HYPER PARKWAY PARADE'
        if name == 'ZHONGSHAN PARK': return 'ZHONG SHAN PARK'
        return name
    
    elif report_type == 'CS_DRY':
        if name == 'COMPASS ONE': return 'CS COMPASS ONE'
        if name == 'CS GREAT WORLD CITY-AM' : return 'CS GREAT WORLD CITY'
        if name == 'CS GREAT WORLD CITY-PM' : return 'CS GREAT WORLD CITY'
        if name == 'MP TANGLIN-AM' : return 'MP TANGLIN'
        if name == 'MP TANGLIN-PM' : return 'MP TANGLIN'
        if name == 'CS PARKWAY PARADE-PM' : return 'CS PARKWAY PARADE'
        if name == 'CS I12 KATONG-PM' : return 'CS I12 KATONG'
        if name == 'CS 1 HOLLAND-PM' : return 'CS 1 HOLLAND'
        if name == 'CS CHANCERY COURT 2-PM' : return 'CS CHANCERY COURT'
        if name == 'CHANCERY COURT 2' : return 'CS CHANCERY COURT'
        if name == 'CS ONE HOLLAND VILLAGE-PM' : return 'CS ONE HOLLAND VILLAGE'
        if name == 'ONE HOLLAND VILLAGE' : return 'CS ONE HOLLAND VILLAGE'
        if name == 'ANCHORPOINT 3' :  return 'CS ANCHORPOINT 3'
        if name == 'JOO CHIAT' : return 'CS JOO CHIAT'
        if name == 'JS SENTOSA QUAYSIDE-PM' : return 'JS SENTOSA QUAYSIDE'
        if name == 'CS ALOCASSIA-PM' : return 'CS ALOCASSIA'
        if name == 'CS CLUNY COURT-PM' : return 'CS CLUNY COURT'
        if name == 'CS MARINA ONE-PM' : return 'CS MARINA ONE'
        if name == 'CS GUTHRIE HOUSE-PM' : return 'CS GUTHRIE HOUSE'
        if name == 'CS ORCHARD HOTEL-AM' : return 'CS ORCHARD HOTEL'
        if name == 'CS ORCHARD HOTEL-PM' : return 'CS ORCHARD HOTEL'
        if name == 'CS RAIL MALL-PM' : return 'CS RAIL MALL'
        if name == 'CS RAIL MALL-AM' : return 'CS RAIL MALL'
        if name == 'CS SERANGOON NEX-PM' : return 'CS SERANGOON NEX'
        if name == 'CS UNITED SQUARE-PM' : return 'CS UNITED SQUARE'
        if name == 'MP HILLVIEW-AM' : return 'MP HILLVIEW'
        if name == 'MP HILLVIEW-PM' : return 'MP HILLVIEW'
        if name == 'PASIR RIS MALL' : return 'CS PASIR RIS MALL'
        if name == 'SUNTEC CITY' : return 'CS SUNTEC CITY'
        return name
    
    return name

def clean_id(val):
    if pd.isna(val) or val == '': return "0"
    s = str(val).strip().upper()
    if s == 'NAN' or s == 'NONE': return "0"
    if "HCZX" in s: return "0"
    s = s.split('-')[0].strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def clean_currency(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).strip().replace('$', '').replace(' ', '')
    
    if s.endswith(",000"):
        s = s[:-4]
        if s.count('.') > 1:
            s = s.replace('.', '')
        return float(s)
    
    if ',' in s and '.' not in s:
        s = s.replace(',', '.')
        return float(s)

    if ',' in s and '.' in s:
        if s.rfind(',') < s.rfind('.'):
            s = s.replace(',', '')
        else:
            s = s.replace('.', '').replace(',', '.')

    try:return float(s)
    except: return 0.0 

def parse_uom_factor(uom_str):
    if pd.isna(uom_str): return 1.0
    s = str(uom_str).upper().strip()
    if 'KG' in s: return 1.0
    match = re.search(r'(\d+)G', s)
    if match: return float(match.group(1)) / 1000.0
    return 1.0

def clean_header(header):
    return str(header).replace('\n', ' ').replace('\r', ' ').strip().upper()

def strict_rename(df, map_dict):
    df.columns = [clean_header(c) for c in df.columns]
    new_cols = {}
    used_targets = set()
    for col in df.columns:
        for target, keywords in map_dict.items():
            if target in used_targets: continue
            if target == 'NAV' and "CUSTOMER" in col: continue 
            if any(k.upper() in col for k in keywords):
                keyword_has_desc = any("DESC" in k.upper() for k in keywords)
                if "DESC" in col and not keyword_has_desc: continue
                new_cols[col] = target
                used_targets.add(target)
                break
    # Remove duplicates immediately to prevent Series ambiguity
    temp = df.rename(columns=new_cols)
    return temp.loc[:, ~temp.columns.duplicated()]

def find_correct_header_row(df_in, required_map, source_name="File"):
    if df_in is None: return None
    def check_df(d):
        temp = strict_rename(d.copy(), required_map)
        found = [k for k in required_map.keys() if k in temp.columns]
        if source_name == "DB Sheet":
            return 'Article' in temp.columns and 'NAV' in temp.columns
        return len(found) >= (len(required_map) - 1)

    for r in range(min(20, len(df_in))):
        candidate_header = df_in.iloc[r]
        if not any(isinstance(x, str) and len(x)>1 for x in candidate_header): continue
        candidate_df = df_in.iloc[r+1:].copy()
        candidate_df.columns = candidate_header
        if check_df(candidate_df): return candidate_df
    
    st.error(f"❌ Error: Header not found in {source_name}")
    return None

# --- 3. MAIN PROCESS DATA FUNCTION ---
@st.cache_data
def process_data(df_sales_raw, df_db_raw, df_dist_raw, df_waste_raw, report_type,df_uom_raw=None,df_dist2_raw=None,df_loc_raw=None):
    master_name_map = {}
    df_dist2 = pd.DataFrame()
    nav_to_article_map = {} 

    if report_type =="AEON":
        db_cols = {'Article': ['ITEM CODE', 'ITEMCODE'], 'NAV': ['NAV code', 'NAV_CODE', 'No.'], 'ArtDesc': ['NAV Description', 'Description'], 'NavDesc': ['Aeon Item code', 'ArticleDesc'],'UOM': ['UOM PKT/KG (NAV)', 'UOM']}
        sales_cols ={'Article': ['Article', 'ITEM CODE'], 'Qty': ['SALES QTY','QTY','SALESQTY','Billed Quantity'], 'Val': ['TOTAL SALES','SALESAMOUNT','Total Amount'], 'Store': ['STORE NAME'], 'Date': ['SELLING DATE'], 'Name': ['ITEM DESCRIPTION']}
        # Fixed Dist to catch the AEON headers
        #dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure', 'UOM'], 'Name': ['USOFT product description', 'Description', 'Name'], 'Cost': ['Price','COST','Unit Price'], 'Date': ['Posting Date','Date'], 'Chain': ['External Doc No.']}
        dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure Code'], 'Name': ['USOFT product description'], 'Cost': ['Price','COST','Unit Price'], 'Date': ['Posting Date'], 'Chain': ['Your Reference主key']}
        waste_cols = {'NAV': ['NAV', 'NAV_CODE'], 'Qty': ['QTY', 'Quantity'], 'Weight': ['WEIGHT'], 'Store': ['Store', 'LONG_NAME'], 'Val': ['Amount', 'TOT_AMT'], 'Date': ['DATE', 'Date'], 'Chain': ['MAIN_CODE']}

    elif report_type == "AEON DF":
        db_cols = {'Article': ['ITEM CODE', 'ITEMCODE'], 'NAV': ['NAV code', 'NAV_CODE', 'No.'], 'ArtDesc': ['NAV Description', 'Description'], 'NavDesc': ['Aeon Item code', 'ArticleDesc'],'UOM': ['UOM PKT/KG (NAV)', 'UOM'], 'RSP': ['RSP']}
        sales_cols ={'Article': ['Article', 'ITEM CODE'], 'Qty': ['SALES QTY','QTY','SALESQTY','Billed Quantity'], 'Val': ['TOTAL SALES','SALESAMOUNT','Total Amount'], 'Store': ['STORE NAME'], 'Date': ['SELLING DATE'], 'Name': ['ITEM DESCRIPTION']}
        dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure Code'], 'Name': ['USOFT product description'], 'Cost': ['Price','COST','Unit Price'], 'Date': ['Posting Date'], 'Chain': ['Your Reference主key']}
        waste_cols = {'NAV': ['NAV', 'NAV_CODE'], 'Qty': ['QTY', 'Quantity'], 'Weight': ['WEIGHT'], 'Store': ['Store', 'LONG_NAME'], 'Val': ['Amount', 'TOT_AMT'], 'Date': ['DATE', 'Date'], 'Chain': ['MAIN_CODE']}

    elif report_type =="TFP" :
        db_cols = {'Article': ['CODE SKU', 'cno_sku'], 'NAV': ['NAV CODE', 'id'], 'ArtDesc': ['Description', 'name1'], 'NavDesc': ['Item No/SKU', 'name2'], 'UOM': ['UOM']}
        sales_cols = {'Article': ['SKU NO', '1st Column'], 'Qty': ['Qty Sold', 'Quantity'], 'Val': ['Net Excl Tax', 'Amount'], 'Store': ['Location'], 'Date': ['Sales Date', 'TRXDATE'], 'Name': ['Item']}
        dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure Code'], 'Name': ['USOFT product description'], 'Cost': ['Price','COST','Unit Price'], 'Date': ['Posting Date'], 'Chain': ['Your Reference主key']}
        waste_cols = {'NAV': ['NAV_CODE', 'NAV'], 'Qty': ['QTY', 'Quantity'], 'Weight': ['WEIGHT'], 'Store': ['LONG_NAME', 'Store'], 'Val': ['TOT_AMT', 'Amount'], 'Date': ['DATE', 'Date'], 'Chain': ['MAIN_CODE']}
    elif report_type =="TFP DF" :
        db_cols = {'Article': ['CODE SKU', 'cno_sku'], 'NAV': ['NAV CODE', 'id'], 'ArtDesc': ['Description', 'name1'], 'NavDesc': ['Item No/SKU', 'name2'], 'UOM': ['UOM']}
        sales_cols = {'Article': ['SKU NO', '1st Column'], 'Qty': ['Qty Sold', 'Quantity'], 'Val': ['Net Excl Tax', 'Amount'], 'Store': ['Location'], 'Date': ['Sales Date', 'TRXDATE'], 'Name': ['Item']}
        dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure Code'], 'Name': ['USOFT product description'], 'Cost': ['Price','COST','Unit Price'], 'Date': ['Posting Date'], 'Chain': ['Your Reference主key']}
        waste_cols = {'NAV': ['NAV_CODE', 'NAV'], 'Qty': ['QTY', 'Quantity'], 'Weight': ['WEIGHT'], 'Store': ['LONG_NAME', 'Store'], 'Val': ['TOT_AMT', 'Amount'], 'Date': ['DATE', 'Date'], 'Chain': ['MAIN_CODE']}
    
    elif report_type == "CS_DRY":
        db_cols = {'Article': ['cno_sku'], 'NAV': ['partno'], 'ArtDesc': ['name2'], 'NavDesc': ['name2']}
        sales_cols ={'Article': ['Article', 'ITEMCODE'], 'Qty': ['Quantity','QTY','SALESQTY','Billed Quantity'], 'Val': ['Amount','SALESAMOUNT','Total Amount'], 'Store': ['STOREDESC', 'Store name'], 'Date': ['TRXDATE','Date'], 'Name': ['ITEMDESC', 'Description', 'Name']}
        dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure', 'UOM'], 'Name': ['USOFT product description', 'Description', 'Name'], 'Cost': ['Unit Price Excl. GST'], 'Date': ['Posting Date','Date'], 'Chain': ['Customer']}

    elif report_type == "SS_DRY":
        db_cols = {'Article': ['cno_sku'], 'NAV': ['partno'], 'ArtDesc': ['name2'], 'NavDesc': ['name2']}
        sales_cols = {'Article': ['ITEMCODE', 'Article'], 'Qty': ['QTY', 'Quantity'], 'Val': ['SALES BEF GST', 'Total Amount', 'Amount'], 'Store': ['OUTLET', 'Store'], 'Date': ['YEAR', 'TRXDATE'], 'Name': ['DESCRIPTION', 'Name']}
        dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure', 'UOM'], 'Name': ['USOFT product description', 'Description', 'Name'], 'Cost': ['Unit Price Excl. GST'], 'Date': ['Posting Date','Date'], 'Chain': ['Transfer-to Code']}

    elif report_type == "NTUC_DRY":
        db_cols = {'Article': ['cno_sku'], 'NAV': ['partno'], 'ArtDesc': ['name2'], 'NavDesc': ['name2']}
        sales_cols = {'Store': ['1st Column'], 'Raw_Item': ['2nd Column']}
        dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['External Doc No.'], 'UOM': ['Unit of Measure', 'UOM'], 'Name': ['USOFT product description', 'Description', 'Name'], 'Cost': ['Unit Price Excl. GST'], 'Date': ['Posting Date','Date'], 'Chain': ['Transfer-to Code']}
        # No wastage file for CS_DRY
    # Common Maps
    # dist_cols = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['Your Reference', 'key'], 'UOM': ['Unit of Measure', 'UOM'], 'Name': ['USOFT product description', 'Description', 'Name'], 'Cost': ['Price','COST','Unit Price'], 'Date': ['Posting Date','Date'], 'Chain': ['External Doc No.']}
    # waste_cols = {'NAV': ['NAV', 'NAV_CODE'], 'Qty': ['QTY', 'Quantity'], 'Weight': ['WEIGHT'], 'Store': ['Store', 'LONG_NAME'], 'Val': ['Amount', 'TOT_AMT'], 'Date': ['DATE', 'Date'], 'Chain': ['MAIN_CODE']}



    # --- A. DATABASE ---
    df_db = find_correct_header_row(df_db_raw,db_cols, "DB Sheet")
    if df_db is None: return None
    df_db = strict_rename(df_db, db_cols)

    if report_type == "NTUC":
        df_db['NAV'] = df_db['NAV'].astype(str).apply(lambda x: x.split('-')[0] if '-' in x else x)

    df_db['Article'] = df_db['Article'].apply(clean_id)
    df_db['NAV'] = df_db['NAV'].apply(clean_id)
    df_db = df_db[df_db['NAV'] != "0"].drop_duplicates('Article')
    
    db_mapping_forward = df_db.set_index('Article')['NAV'].to_dict()
    df_valid_db = df_db[df_db['NAV'] != "0"]
    nav_to_article_map = df_valid_db.drop_duplicates('NAV').set_index('NAV')['Article'].to_dict()


    if 'ArtDesc' in df_db.columns:
        df_db['Final_Name'] = df_db['ArtDesc']
        if 'NavDesc' in df_db.columns:
            df_db['Final_Name'] = df_db['Final_Name'].fillna(df_db['NavDesc'])
        df_db['Final_Name'] = df_db['Final_Name'].fillna("Unknown DB Item")
        master_name_map.update(df_db.set_index('NAV')['Final_Name'].to_dict())
    uom_mapping = {}
    if 'UOM' in df_db.columns:
        uom_mapping = df_db.set_index('NAV')['UOM'].to_dict()
    
    # aeon_loc_map = {}
    # if (report_type == "AEON" or report_type == "AEON DF") and df_loc_raw is not None:
    #     loc_sheet_cols = {'RawLoc': ['AEON NAME'], 'NavLoc': ['NAV LOC NAME']}
    #     df_loc = find_correct_header_row(df_loc_raw, loc_sheet_cols, "Loc")
        
    #     if df_loc is not None:
    #         df_loc = strict_rename(df_loc, loc_sheet_cols)
    #         df_loc = df_loc.dropna(subset=['RawLoc', 'NavLoc'])
    #         # Build dictionary: Uppercase the raw name so it matches reliably
    #         for _, row in df_loc.iterrows():
    #             k = str(row['RawLoc']).strip()
    #             v = str(row['NavLoc']).strip()
                
    #             # if k and k not in ["NAN", "NONE", ""]: 
    #             aeon_loc_map[k] = v

    loc_map = {}
    if report_type in ["AEON", "AEON DF", "TFP", "TFP DF"] and df_loc_raw is not None:
        if "AEON" in report_type:
            loc_sheet_cols = {'RawLoc': ['AEON NAME'], 'NavLoc': ['NAV LOC NAME']}
            sheet_title = "Loc"
        else:
            loc_sheet_cols = {'RawLoc': ['Loc'], 'NavLoc': ['Name']}
            sheet_title = "3 - DATABASE LOCATION"
            
        df_loc = find_correct_header_row(df_loc_raw, loc_sheet_cols, sheet_title)
        
        if df_loc is not None:
            df_loc = strict_rename(df_loc, loc_sheet_cols)
            df_loc = df_loc.dropna(subset=['RawLoc', 'NavLoc'])
            for _, row in df_loc.iterrows():
                k = str(row['RawLoc']).strip()
                v = str(row['NavLoc']).strip()
                # if k and k not in ["NAN", "NONE", ""]: 
                loc_map[k] = v
    
    rsp_mapping = {}  
    if (report_type == "AEON" or report_type == "AEON DF") and df_uom_raw is not None:
        # Find headers for UOM sheet
        uom_sheet_cols = {'Desc': ['Item Description'], 'RSP': ['RSP']}
        df_uom = find_correct_header_row(df_uom_raw, uom_sheet_cols, "UOM Sheet")
        
        if df_uom is not None:
            df_uom = strict_rename(df_uom, uom_sheet_cols)
            df_uom = df_uom.dropna(subset=['Desc', 'RSP'])
            # Create a dictionary: {'Org Papaya MYS': 9.5, 'Org Tomato MYS': 22.0}
            rsp_mapping = df_uom.set_index('Desc')['RSP'].apply(clean_currency).to_dict()
    
    print("\n--- DB MAPPING PREVIEW ---")
    print(df_db[['Article', 'NAV', 'Final_Name']].head(5))
    print("--------------------------\n")

    # --- B. SALES ---
    if report_type == "NTUC" or report_type == "NTUC_DRY":
        id_vars = ['Store', 'Raw_Item']
        melt_val = pd.DataFrame()
        melt_qty = pd.DataFrame()

        try:
            client = get_gspread_client()
            sales_url = st.session_state['urls']['s'] 
            sh = client.open_by_url(sales_url)

            # 1. FETCH & PROCESS "Quantity" TAB
            try:
                ws_qty = sh.worksheet("Quantity")
                df_qty_raw = pd.DataFrame(ws_qty.get_all_values())
                df_qty_clean = find_correct_header_row(df_qty_raw, sales_cols, "Qty Sheet")
                df_qty_clean = strict_rename(df_qty_clean, sales_cols)
                
                # Exclude 'METRIC' column explicitly to avoid data corruption
                date_cols_q = [c for c in df_qty_clean.columns if c not in id_vars and 'METRIC' not in str(c).upper()]
                melt_qty = df_qty_clean.melt(id_vars=id_vars, value_vars=date_cols_q, var_name='Date', value_name='Qty')
            except Exception as e:
                st.warning(f"Error loading Quantity tab: {e}")

            # 2. FETCH & PROCESS "Sales" TAB (Value)
            try:
                try: ws_val = sh.worksheet("Sales") 
                except: ws_val = sh.get_worksheet(0)
                
                df_val_raw = pd.DataFrame(ws_val.get_all_values())
                df_val_clean = find_correct_header_row(df_val_raw, sales_cols, "Sales Sheet")
                df_val_clean = strict_rename(df_val_clean, sales_cols) # FIX: Use df_val_clean here
                
                # Exclude 'METRIC' column explicitly
                date_cols_v = [c for c in df_val_clean.columns if c not in id_vars and 'METRIC' not in str(c).upper()]
                melt_val = df_val_clean.melt(id_vars=id_vars, value_vars=date_cols_v, var_name='Date', value_name='Val')
            except Exception as e:
                st.warning(f"Error loading Sales tab: {e}")

        except Exception as e:
            st.error(f"Critical GSheet Error: {e}")
            return None

        # 3. Handle Empty Dataframes
        if melt_val.empty: 
            st.error("Could not fetch Sales Value data.")
            return None
        if melt_qty.empty:
            melt_qty = melt_val.copy()[id_vars + ['Date']]
            melt_qty['Qty'] = 0

        # 4. Cleanup & Merge 
        # Clean currency symbols just in case ($) and convert to numeric
        melt_val['Val'] = melt_val['Val'].apply(clean_currency)
        
        melt_qty['Qty'] = pd.to_numeric(melt_qty['Qty'], errors='coerce').fillna(0)
        
        # Standardize Date formats 
        melt_val['Date'] = pd.to_datetime(melt_val['Date'], dayfirst=True, errors='coerce')
        melt_qty['Date'] = pd.to_datetime(melt_qty['Date'], dayfirst=True, errors='coerce')
        
        # Filter out invalid dates (e.g. if 'Metric' column slipped in)
        melt_val = melt_val.dropna(subset=['Date'])
        melt_qty = melt_qty.dropna(subset=['Date'])

        df_sales = pd.merge(melt_val, melt_qty, on=['Store', 'Raw_Item', 'Date'], how='outer').fillna(0)

        # 5. Extract Article Code
        df_sales['Article'] = df_sales['Raw_Item'].astype(str).str.extract(r'(\d+)\s*$')
        df_sales['Name'] = df_sales['Raw_Item'].astype(str).str.rsplit('-', n=1).str[0].str.strip()

    else:
        # Standard Logic (CS / SS)
        df_sales = find_correct_header_row(df_sales_raw, sales_cols, "Sales Sheet")
        if df_sales is None: return None
        df_sales = strict_rename(df_sales, sales_cols)

    # For SS_DRY, set Sales_Qty and Sales_Val to 0.0 if Store is 'TOTAL'
    if report_type == "SS_DRY" and 'Store' in df_sales.columns:
        mask_total = df_sales['Store'].astype(str).str.upper() == 'TOTAL'
        df_sales.loc[mask_total, 'Qty'] = 0.0
        df_sales.loc[mask_total, 'Val'] = 0.0
    
    df_sales['Article'] = df_sales['Article'].apply(clean_id)
    #df_sales['NAV'] = df_sales['Article'].map(db_mapping_forward).fillna("0")
    df_sales['NAV'] = df_sales['Article'].map(db_mapping_forward).fillna(df_sales['Article'])

    print("\n--- SALES MAPPING PREVIEW ---")
    print(df_sales[['Store', 'Article', 'NAV', 'Qty', 'Val','Date']].head(5))
    print("-----------------------------\n")
    #if 'Name' in df_sales.columns:
    #   sales_names = df_sales[df_sales['NAV'] != "0"].set_index('NAV')['Name'].to_dict()
    if 'Name' in df_sales.columns:
        # Grab the names for ALL items, even unmapped ones
        sales_names = df_sales.set_index('NAV')['Name'].to_dict()
        for k, v in sales_names.items():
            if k not in master_name_map: master_name_map[k] = v
     
    #df_sales = df_sales[df_sales['NAV'] != "0"]
    df_sales['Store'] = df_sales['Store'].apply(lambda x: normalize_store_name(x, report_type,loc_map))
    df_sales['Qty'] = df_sales['Qty'].apply(clean_currency)
    df_sales['Val'] = df_sales['Val'].apply(clean_currency)
    if report_type == 'AEON' or report_type == 'AEON DF' or report_type == 'TFP' or report_type == 'TFP DF':
        # Map the UOM string from the database using the NAV code
        df_sales['UOM_Str'] = df_sales['NAV'].map(uom_mapping).fillna('KG')
        df_sales['DB_Item_Name'] = df_sales['NAV'].map(df_db.set_index('NAV')['Final_Name'].to_dict())
        df_sales['RSP_Val'] = df_sales['DB_Item_Name'].map(rsp_mapping).fillna(0.0)
        # Use your existing parse_uom_factor function to convert strings like '300GEA' into 0.3
        def calc_aeon_qty(row):
            # If it's a KG item AND we found its price
            if row['UOM_Str'] == 'KG' and row['RSP_Val'] > 0:
                # Qty = Total Sales RM / Retail Price RM
                return row['Val'] / row['RSP_Val']
            else:
                # Otherwise, it's a packet, so multiply by UOM factor (e.g. 300g = 0.3)
                factor = parse_uom_factor(row['UOM_Str'])
                return row['Qty'] * factor
        df_sales['Qty'] = df_sales.apply(calc_aeon_qty, axis=1)
        df_sales = df_sales.drop(columns=['UOM_Str', 'RSP_Val', 'DB_Item_Name'], errors='ignore')
        # df_sales['UOM_Factor'] = df_sales['UOM_Str'].apply(parse_uom_factor)
        # # Multiply original Qty by the factor to get KG
        # df_sales['Qty'] = df_sales['Qty'] * df_sales['UOM_Factor']
    
            # Cold Storage: 2025.12.31 (Year.Month.Day)
    # Handle Sales Dates
    if 'Date' in df_sales.columns:
        if report_type == 'SS_DRY':
            df_sales['Year'] = df_sales['Date'].astype(str).replace(r'\.0$', '', regex=True)
            df_sales['Date'] = pd.to_datetime(df_sales['Year'] + "-01-01", errors='coerce') # Dummy date
        elif report_type == 'AEON' or report_type == 'AEON DF' or report_type == 'TFP' or report_type == 'TFP DF':
            # --- AEON STRICT DATE PARSING ---
            # AEON CSV dates look like '25/02/2026' (DD/MM/YYYY)
            df_sales['Date'] = pd.to_datetime(df_sales['Date'], format='%d/%m/%Y', errors='coerce')
            
            # Extract attributes only for rows where date parsing succeeded
            df_sales['Year'] = df_sales['Date'].dt.year.astype('Int64').astype(str)
            df_sales['Month'] = df_sales['Date'].dt.month_name().str[:3]
            df_sales['Week'] = df_sales['Date'].apply(lambda x: f"{x.strftime('%Y')}-W{(int(x.strftime('%U')) + 1):02d}" if pd.notnull(x) else None)
        elif report_type == 'SS':
            # Sheng Siong: 09-12-2025 (Day-Month-Year)
            df_sales['Date'] = pd.to_datetime(df_sales['Date'], dayfirst=True, errors='coerce')
            df_sales['Year'] = df_sales['Date'].dt.year.astype(str).str.replace(r'\.0$', '', regex=True)
            df_sales['Month'] = df_sales['Date'].dt.month_name().str[:3]
            df_sales['Week'] = df_sales['Date'].dt.strftime('%Y-W%U')
        else:
            # Cold Storage: 2025.12.31 (Year.Month.Day)
            df_sales['Date'] = pd.to_datetime(df_sales['Date'], format='%Y.%m.%d', errors='coerce')
            if df_sales['Date'].isnull().all():
                 df_sales['Date'] = pd.to_datetime(df_sales['Date'], dayfirst=True, errors='coerce')
            df_sales['Year'] = df_sales['Date'].dt.year.astype(str).str.replace(r'\.0$', '', regex=True)
            df_sales['Month'] = df_sales['Date'].dt.month_name().str[:3]
            df_sales['Week'] = df_sales['Date'].dt.strftime('%Y-W%U')
    else:
        df_sales['Year'] = "2025" 
        df_sales['Month'] = "ALL"
        df_sales['Week'] = "ALL"

   
    if report_type == 'SS_DRY':
        df_sales['Month'] = "Annual"
        df_sales['Week'] = "Annual"

    # --- C. DISTRIBUTION -
    # d_map = {'NAV': ['No.', 'M Code'], 'Qty': ['Quantity', 'QTY'], 'Store': ['Your Reference', 'key'], 'UOM': ['Unit of Measure', 'UOM'], 'Name': ['USOFT product description', 'Description', 'Name'], 'Cost': ['Price','COST','Unit Price'], 'Date': ['Posting Date','Date'], 'Chain': ['Customer']}
    
    df_dist = find_correct_header_row(df_dist_raw, dist_cols, "Dist Sheet")
    if df_dist is None: return None
    df_dist = strict_rename(df_dist, dist_cols)
    

    if 'Date' in df_dist.columns:
        df_dist['Date'] = pd.to_datetime(df_dist['Date'], errors='coerce', dayfirst=False)

    # 2. Process the second Distribution Sheet (Item Ledger Entries)
    if df_dist2_raw is not None and not df_dist2_raw.empty:
        # ⚠️ CRITICAL: Only map 'Location Name' to Store so it doesn't grab the empty 'Ship-to Name'
        dist2_cols = {
            'NAV': ['Item No.'], 
            'Qty': ['Quantity'], 
            'Store': ['Location Name'], 
            'UOM': ['Unit of Measure Code'], 
            'Name': ['Item Description'], 
            'Cost': ['Cost Amount (Actual)'], 
            'Date': ['Posting Date'], 
            'Chain': ['Source No.']
        }
        
        df_dist2 = find_correct_header_row(df_dist2_raw, dist2_cols, "Dist Sheet 2")
        
        if df_dist2 is not None:
            df_dist2 = strict_rename(df_dist2, dist2_cols)
            if 'Date' in df_dist2.columns:
                df_dist2['Date'] = pd.to_datetime(df_dist2['Date'], format='%m/%d/%Y', errors='coerce')
            if 'Qty' in df_dist2.columns:
                df_dist2['Qty'] = pd.to_numeric(df_dist2['Qty'], errors='coerce').abs()
            if 'Cost' in df_dist2.columns:
                df_dist2['Cost'] = df_dist2['Cost'].apply(clean_currency)/df_dist2['Qty'].replace(0, 1)
            df_dist = pd.concat([df_dist, df_dist2], ignore_index=True)
    
    if 'Store' in df_dist.columns:
        if report_type =='AEON' or report_type == 'AEON DF':
            mask = df_dist['Store'].astype(str).str.upper().str.contains('AEON|JUSCO|MAXVALU', regex=True, na=False)
            df_dist=df_dist[mask]
        elif report_type == 'TFP' or report_type == 'TFP DF':
            mask = df_dist['Store'].astype(str).str.upper().str.contains('VG|BIP|BBT|BSC', regex=True, na=False)
            df_dist=df_dist[mask]
        elif report_type == 'NTUC':
            mask = df_dist['Chain'].astype(str).str.upper().str.contains(r'NTUC', regex=True, na=False)
            df_dist = df_dist[mask]
        elif report_type == 'CS_DRY':
            mask = df_dist['Store'].astype(str).str.upper().str.contains('CS |COLD STORAGE|CS_|COMPASS ONE|MP |NOVENA |JS |MARINA |GT |FAR ', regex=True, na=False)
            df_dist = df_dist[mask]
        elif report_type == 'SS_DRY':
            mask = df_dist['Chain'].astype(str).str.upper().str.contains(r'^Sheng Siong|^SS|^SS_', regex=True, na=False)
            df_dist=df_dist[mask]
        elif report_type == 'NTUC_DRY':
            mask = df_dist['Chain'].astype(str).str.upper().str.contains(r'NC', regex=True, na=False)
            df_dist = df_dist[mask]

    
    if 'Chain' in df_dist.columns and 'Store' not in df_dist.columns:
         mask_chain = df_dist['Chain'].astype(str).str.upper().str.contains('HX|', na=False)
         if mask_chain.sum() > 0: df_dist = df_dist[mask_chain]
    
    df_dist['NAV'] = df_dist['NAV'].apply(clean_id)
    if 'Name' in df_dist.columns:
        dist_names = df_dist[df_dist['NAV'] != "0"].set_index('NAV')['Name'].to_dict()
        for k, v in dist_names.items():
            if k not in master_name_map: master_name_map[k] = v

    df_dist['Store'] = df_dist['Store'].apply(lambda x: normalize_store_name(x, report_type,loc_map))
    df_dist['Date'] = pd.to_datetime(df_dist['Date'], errors='coerce')
    df_dist['Year'] = df_dist['Date'].dt.year.astype(str).str.replace(r'\.0$', '', regex=True)
    df_dist['Month'] = df_dist['Date'].dt.month_name().str[:3]
    df_dist['Week'] = df_dist['Date'].apply(lambda x: f"{x.strftime('%Y')}-W{(int(x.strftime('%U')) + 1):02d}" if pd.notnull(x) else None)
    df_dist['Qty'] = df_dist['Qty'].apply(clean_currency)
    print("\n--- Distribution MAPPING PREVIEW ---")
    print(df_dist[['Store', 'NAV', 'Qty','Date']].head(5))
    print("-----------------------------\n")
    

    
        # Other systems use the Cost column
    cost = df_dist['Cost'].apply(clean_currency) if 'Cost' in df_dist.columns else 0.0
    if report_type == 'SS_DRY':
        df_dist['Month'] = "Annual"
        df_dist['Week'] = "Annual"
        
    
    if 'UOM' in df_dist.columns:
        raw_qty = pd.to_numeric(df_dist['Qty'], errors='coerce').fillna(0)
        uom_factor = df_dist['UOM'].apply(parse_uom_factor)
        df_dist['Qty'] = raw_qty * uom_factor 
        cost = df_dist['Cost'].apply(clean_currency) if 'Cost' in df_dist.columns else 0
        df_dist['Val'] = df_dist['Qty'] * (cost/2)
   

    # --- D. WASTAGE ---
    if report_type == "CS_DRY" or report_type == "SS_DRY" or report_type== "NTUC_DRY":
        # No wastage file for CS_DRY
        df_waste = pd.DataFrame(columns=["NAV", "Qty", "Val", "Store", "Date", "Year", "Month", "Week", "Weight", "Chain"])
    else:
        # w_map = {'NAV': ['NAV', 'NAV_CODE'], 'Qty': ['QTY', 'Quantity'], 'Weight': ['WEIGHT'], 'Store': ['Store', 'LONG_NAME'], 'Val': ['Amount', 'TOT_AMT'], 'Date': ['DATE', 'Date'], 'Chain': ['MAIN_CODE']}
        df_waste = find_correct_header_row(df_waste_raw, waste_cols, "Waste Sheet")
        if df_waste is None: return None
        df_waste = strict_rename(df_waste, waste_cols)
        if 'Chain' in df_waste.columns: 
            if report_type == 'AEON' or report_type == 'AEON DF':
                mask = df_waste['Chain'].astype(str).str.upper().str.contains('HC000020|AEON|JUSCO|MAXVALU', regex=True, na=False)
                df_waste = df_waste[mask]
            elif report_type == 'SS':
                mask = df_waste['Chain'].astype(str).str.upper().str.contains(r'^SHENG SHIONG|^SS|^SS_|S.SIONG', regex=True, na=False)
                df_waste = df_waste[mask]
            elif report_type == 'NTUC':
                mask = df_waste['Chain'].astype(str).str.upper().str.contains('NTUC', regex=True, na=False)
                df_waste = df_waste[mask]
        df_waste['NAV'] = df_waste['NAV'].apply(clean_id)
        df_waste['Store'] = df_waste['Store'].apply(lambda x: normalize_store_name(x, report_type,loc_map))
        df_waste['Date'] = pd.to_datetime(df_waste['Date'], dayfirst=True, errors='coerce')
        df_waste['Year'] = df_waste['Date'].dt.year.astype(str).replace(r'\.0$', '', regex=True)
        df_waste['Month'] = df_waste['Date'].dt.month_name().str[:3]
        df_waste['Week'] = df_waste['Date'].apply(lambda x: f"{x.strftime('%Y')}-W{(int(x.strftime('%U')) + 1):02d}" if pd.notnull(x) else None)
        qty_units = df_waste['Qty'].apply(clean_currency)
        weight_kg = df_waste['Weight'].apply(clean_currency)
        df_waste['Qty'] = qty_units * weight_kg
        df_waste['Val'] = df_waste['Val'].apply(clean_currency)

    def get_max_date(dframe):
        try:
            if not dframe.empty and 'Date' in dframe.columns:
                return dframe['Date'].max().strftime('%d %b %Y')
        except: pass
        return "N/A"

    update_info = {
        "Sales": get_max_date(df_sales),
        "Dist": get_max_date(df_dist),
        "Dist2": get_max_date(df_dist2) if not df_dist2.empty else "N/A",
        "Waste": get_max_date(df_waste)
    }

    return df_sales, df_dist, df_waste, master_name_map, nav_to_article_map, [], update_info
# --- 4. MAIN APP LOGIC ---
def main_app_interface(authenticator, name, permissions):
    st.title("PPL Report")
    with st.sidebar:
        st.write(f"👤 User: **{name}**")
        authenticator.logout('Logout', 'sidebar')
        st.divider()
        st.header("⚙️ Configuration")
        
        if 'urls' not in st.session_state: st.session_state['urls'] = None

        # Check Permissions
        my_systems = permissions.get("systems", [])
        def can_view(sys_code): return "ALL" in my_systems or sys_code in my_systems

        b1, b2 = st.sidebar.columns(2)
        with b1:
            if can_view("AEON") and st.button("AEON Vege"):
                st.session_state['report_type'] = "AEON"
                st.session_state['urls'] = {
                    's': make_url(st.secrets["sheet_ids"]["aeon_sales"]),
                    'db': make_url(st.secrets["sheet_ids"]["aeon_db"]),
                    'd': make_url(st.secrets["sheet_ids"]["aeon_dist"]),
                    'w': make_url(st.secrets["sheet_ids"]["aeon_waste"]),
                    'h': make_url(st.secrets["sheet_ids"]["aeon_history"])
                }
                st.rerun()
        with b2:
            if can_view("AEON") and st.button("AEON DF"):
                st.session_state['report_type'] = "AEON DF"
                st.session_state['urls'] = {
                    's': make_url(st.secrets["sheet_ids"]["aeon_dry_sales"]),
                    'db': make_url(st.secrets["sheet_ids"]["aeon_dry_db"]),
                    'd': make_url(st.secrets["sheet_ids"]["aeon_dry_dist"]),
                    'd2': make_url(st.secrets["sheet_ids"]["aeon_dry_dist_2"]),
                    'w': make_url(st.secrets["sheet_ids"]["aeon_dry_waste"]),
                    'h': make_url(st.secrets["sheet_ids"]["aeon_dry_history"])
                }
                st.rerun()
        
        b3, b4 = st.sidebar.columns(2)
        with b3:
            if can_view("TFP") and st.button("TFP Vege"):
                st.session_state['report_type'] = "TFP"
                st.session_state['urls'] = { 
                    's': make_url(st.secrets["sheet_ids"]["tfp_sales"]),
                    'db': make_url(st.secrets["sheet_ids"]["tfp_db"]),
                    'd': make_url(st.secrets["sheet_ids"]["tfp_dist"]),
                    'w': make_url(st.secrets["sheet_ids"]["tfp_waste"]),
                    'h': make_url(st.secrets["sheet_ids"]["tfp_history"])
                }
                st.rerun()
        with b4:
            if can_view("TFP") and st.button("TFP DF"):
                st.session_state['report_type'] = "TFP DF"
                st.session_state['urls'] = {
                    's': make_url(st.secrets["sheet_ids"]["tfp_dry_sales"]),
                    'db': make_url(st.secrets["sheet_ids"]["tfp_dry_db"]),
                    'd': make_url(st.secrets["sheet_ids"]["tfp_dry_dist"]),
                    'd2': make_url(st.secrets["sheet_ids"]["aeon_dry_dist_2"]),
                    'w': make_url(st.secrets["sheet_ids"]["tfp_dry_waste"]),
                    'h': make_url(st.secrets["sheet_ids"]["tfp_dry_history"])                
                    }
                st.rerun()

        # b5, b6 = st.sidebar.columns(2)
        # with b5:
        #      if can_view("SS_DRY") and st.button("SS DRY"):
        #         st.session_state['report_type'] = "SS_DRY"
        #         st.session_state['urls'] = {
        #             's': make_url(st.secrets["sheet_ids"]["ss_dry_sales"]),
        #             'db': make_url(st.secrets["sheet_ids"]["ss_dry_db"]),
        #             'd': make_url(st.secrets["sheet_ids"]["ss_dry_dist"]),
        #             'w': make_url(st.secrets["sheet_ids"]["ss_dry_waste"]),
        #             'h': make_url(st.secrets["sheet_ids"]["ss_dry_history"])
        #         }
        #         st.rerun()
        # with b6:
        #    if can_view("NTUC_DRY") and st.button("NTUC DRY"):
        #         st.session_state['report_type'] = "NTUC_DRY"
        #         st.session_state['urls'] = {
        #             's': make_url(st.secrets["sheet_ids"]["ntuc_dry_sales"]),
        #             'db': make_url(st.secrets["sheet_ids"]["ntuc_dry_db"]),
        #             'd': make_url(st.secrets["sheet_ids"]["ntuc_dry_dist"]),
        #             'w': make_url(st.secrets["sheet_ids"]["ntuc_dry_waste"]),
        #             'h': make_url(st.secrets["sheet_ids"]["ntuc_dry_history"])
        #         }
        #         st.rerun()
        
        st.markdown("---")
        app_mode = st.radio("Mode:", ["📡 Live Analysis", "🗄️ Saved Reports"])
    
    
    if st.session_state['urls'] is None:
        st.info("👈 Please select a Report System from the sidebar to begin.")
        return

    urls = st.session_state['urls']
    rpt = st.session_state['report_type']
    st.caption(f"Active System: {rpt}")

    if app_mode == "📡 Live Analysis":
        with st.spinner("Fetching Live Data for {rpt}..."):

            r_s = load_google_sheet(urls['s'])
            r_db = load_google_sheet(urls['db'])
            r_d = load_google_sheet(urls['d'])
            r_d2 = load_google_sheet(urls['d2']) if 'd2' in urls and urls['d2'] else None
            # Only load wastage file if not CS_DRY
            r_uom = load_google_sheet(urls['db'], "UOM") if rpt == "AEON" or rpt == "AEON DF" else None
            if rpt in ["AEON", "AEON DF"]:
                r_loc = load_google_sheet(urls['db'], "Loc")
            elif rpt in ["TFP", "TFP DF"]:
                r_loc = load_google_sheet(urls['db'], "3 - DATABASE LOCATION")
            else:
                r_loc = None
            r_w = None if rpt == "CS_DRY" or rpt == "SS_DRY" else load_google_sheet(urls['w'])

            if r_s is not None and r_d is not None:
                res = process_data(r_s, r_db, r_d, r_w, rpt, r_uom, r_d2, r_loc)
                if res:
                    # 1. Variables are defined here
                    df_s, df_d, df_w, map_name, map_art, _, update_info = res
                    
                    my_stores = permissions.get("stores", [])
                    if "ALL" not in my_stores:
                        if not df_s.empty: df_s = df_s[df_s['Store'].isin(my_stores)]
                        if not df_d.empty: df_d = df_d[df_d['Store'].isin(my_stores)]
                        if not df_w.empty: df_w = df_w[df_w['Store'].isin(my_stores)]
                        st.warning(f"🔒 View restricted to assigned stores.")

                    
                    st.caption(f"""
                    **Last Data Updates:** 🛒 Sales: **{update_info['Sales']}** | 🚚 Dist: **{update_info['Dist']}** | 📝 Ledger: **{update_info.get('Dist2', 'N/A')}** | 🗑️ Waste: **{update_info['Waste']}**
                    """)
                    
                    st.sidebar.markdown("---")
                    st.sidebar.header("Filters")

                    
                    all_years = sorted(list(set(df_s['Year'].dropna()) | set(df_d['Year'].dropna()) | set(df_w['Year'].dropna() if not df_w.empty else [])), reverse=True)
                    if not all_years: all_years = ["2025"] 
                    sel_year = st.sidebar.selectbox("Select Year", all_years)
                    if sel_year:
                        df_s = df_s[df_s['Year'] == sel_year]
                        df_d = df_d[df_d['Year'] == sel_year]
                        if not df_w.empty:
                            df_w = df_w[df_w['Year'] == sel_year]

                    # Filter
                    ft = st.sidebar.radio("Filter:", ["Month", "Week"])
                    if ft == "Month":
                        group_col = "Month"
                        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        opts = sorted(list(set(df_s['Month']) | set(df_d['Month']) | set(df_w['Month'] if not df_w.empty else [])), key=lambda x: month_order.index(x) if x in month_order else 99)
                        if opts:
                            default_opts = opts[-2:] if len(opts) > 1 else opts
                        else:
                            default_opts = []
                        sel = st.sidebar.multiselect("Select", opts, default=default_opts)
                        if sel:
                            df_s = df_s[df_s['Month'].isin(sel)]
                            df_d = df_d[df_d['Month'].isin(sel)]
                            if not df_w.empty:
                                df_w = df_w[df_w['Month'].isin(sel)]
                    else:
                        group_col = "Week" # Dynamic grouping variable
                        opts = sorted(list(set(df_s['Week']) | set(df_d['Week']) | set(df_w['Week'] if not df_w.empty else [])), reverse=True)
                        sel = st.sidebar.multiselect("Select", opts, default=opts[:4] if len(opts)>0 else opts) # Default to last 4 weeks
                        if sel:
                            df_s = df_s[df_s['Week'].isin(sel)]
                            df_d = df_d[df_d['Week'].isin(sel)]
                            if not df_w.empty:
                                df_w = df_w[df_w['Week'].isin(sel)]

                    # Calculation
                    s_grp = df_s.groupby([group_col,'Store', 'NAV'])[['Qty', 'Val']].sum().reset_index().rename(columns={'Qty': 'Sales_Qty', 'Val': 'Sales_Val'})
                    d_grp = df_d.groupby([group_col,'Store', 'NAV'])[['Qty', 'Val']].sum().reset_index().rename(columns={'Qty': 'Dist_Qty', 'Val': 'Dist_Val'})
                    if not df_w.empty:
                        w_grp = df_w.groupby([group_col,'Store', 'NAV'])[['Qty', 'Val']].sum().reset_index().rename(columns={'Qty': 'Waste_Qty', 'Val': 'Waste_Val'})
                    else:
                        w_grp = pd.DataFrame(columns=[group_col, 'Store', 'NAV', 'Waste_Qty', 'Waste_Val'])

                    df = pd.merge(d_grp, s_grp, on=[group_col,'Store', 'NAV'], how='outer').fillna(0)
                    if not w_grp.empty:
                        df = pd.merge(df, w_grp, on=[group_col,'Store', 'NAV'], how='outer').fillna(0)
                    else:
                        df['Waste_Qty'] = 0
                        df['Waste_Val'] = 0
                    
                    df['Article_Code'] = df['NAV'].map(map_art).fillna("0")
                    df.loc[df['Article_Code'] == "0", 'Article_Code'] = "Unmapped (NAV " + df['NAV'].astype(str) + ")"

                    df['Item_Name'] = df['NAV'].map(map_name).fillna("Unknown Item")
                    mask_unknown = df['Item_Name'] == "Unknown Item"
                    df.loc[mask_unknown, 'Item_Name'] = "Item " + df.loc[mask_unknown, 'NAV'].astype(str)
                    if rpt == 'AEON' or rpt == 'TFP':
                        # For AEON Vege: REMOVE any item starting with "SN "
                        df = df[~df['Item_Name'].astype(str).str.upper().str.startswith(('SN ','SNBG '))]
                    
                    elif rpt == 'AEON DF' or rpt == 'TFP DF':
                        # For AEON Dry (when you add the button later): KEEP ONLY "SN " items
                        mask_is_sn = df['Item_Name'].astype(str).str.upper().str.startswith(('SN ', 'SNBG '))
                        
                        # 2. Second, create a mask for the specific item you want to EXCLUDE
                        # Use upper case since we are comparing against .str.upper()
                        mask_not_egg = ~df['Item_Name'].astype(str).str.upper().str.contains('SELENIUM EGG MYS PAPER TRAY', na=False)
   
                        # 3. Combine them using the bitwise & operator
                        df = df[mask_is_sn & mask_not_egg]
                    df['Item_Name'] = df['NAV'].map(map_name).fillna("Unknown Item")
                    mask_unknown = df['Item_Name'] == "Unknown Item"
                    df.loc[mask_unknown, 'Item_Name'] = "Item " + df.loc[mask_unknown, 'NAV'].astype(str)
                    df['Profit'] = df['Sales_Val'] - df['Dist_Val']
                    #df['Profit_Qty'] = df['Sales_Qty'] - df ['Dist_Qty']
                    df['Balance Stock'] = df['Dist_Qty'] - df['Sales_Qty']
                    
                    #Display whether Wastage or Balance Stock in tabs
                    is_dry = rpt in ["CS_DRY","SS_DRY", "NTUC_DRY"]

                    if is_dry:
                        qty_display_list = ['Dist_Qty','Sales_Qty','Balance Stock']
                        val_display_list = ['Dist_Val','Sales_Val','Profit']
                    else:
                        qty_display_list =['Dist_Qty','Sales_Qty','Waste_Qty']
                        val_display_list =['Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']

                    # Views
                    v_s_qty = df.groupby([group_col,'Store'])[qty_display_list].sum()
                    v_s_qty['STR%'] = (v_s_qty['Sales_Qty']/ v_s_qty['Dist_Qty'])*100
                    v_s_qty['STR%'] = v_s_qty['STR%'].replace([np.inf, -np.inf], 0).fillna(0).round(0)
                    v_s_val = df.groupby([group_col,'Store'])[val_display_list].sum()
                    v_i_qty = df.groupby([group_col,'Article_Code', 'Item_Name'])[qty_display_list].sum()
                    v_i_qty['STR%'] = (v_i_qty['Sales_Qty'] / v_i_qty['Dist_Qty'] * 100).replace([np.inf, -np.inf], 0).fillna(0).round(0)
                    v_i_qty = v_i_qty.sort_values('Dist_Qty', ascending=False)
                    v_i_val = df.groupby([group_col,'Article_Code', 'Item_Name'])[['Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']].sum().sort_values('Dist_Val', ascending=False)
                    v_top10_all = df.groupby('Item_Name')[['Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']].sum().reset_index()



                    st.subheader(f"📊 {rpt} Live Report ({sel_year}-{ft})")
                    t1, t2, t3, t4, t5, t6 = st.tabs(["📦 QTY (Store)", "💰 $ (Store)", "📦 QTY (Item)", "💰 $ (Item)", "🏆 Top 10", "📉 Bottom 10"])

                    def display_drilldown(tab, main_df, detail_cols, sort_col, fmt, time_col):
                        with tab:
                            if main_df.empty:
                                st.info("No data.")
                                return
                            # 1. Store Summary
                            summary = main_df.unstack(level=0, fill_value=0)
                            # Calculate Totals
                            metrics = summary.columns.get_level_values(0).unique()
                            for m in metrics:
                                m_cols = summary.loc[:, (m, slice(None))].columns
                                for c in m_cols:
                                    summary[c] = pd.to_numeric(summary[c], errors='coerce').fillna(0)
                                summary[(m, 'TOTAL')] = summary[m_cols].sum(axis=1)
                            if (sort_col, 'TOTAL') in summary.columns:
                                summary = summary.sort_values((sort_col, 'TOTAL'), ascending=False)
                            st.markdown(f"### 🏢 Store Summary")
                            f_dict = {c: "{:,.0f}" if 'STR%' in str(c) else fmt for c in summary.columns}
                            st.dataframe(summary.style.format(f_dict), height=400, use_container_width=True)
                            st.divider()
                            # 2. FAST DRILL-DOWN (Selectbox instead of Loop)
                            st.markdown("### 🔍 Select Store to View Details")
                            store_options = [f"{s}" for s in summary.index]

                            for store in summary.index:
                                val = summary.loc[store, (sort_col, 'TOTAL')]
                                store_options.append(f"{store} | Total {sort_col}: {val:,.2f}")
                            sel_store_str = st.selectbox(f"Select Store ({sort_col})", options=store_options, key=f"sel_{sort_col}")
                            if sel_store_str:
                                selected_store = sel_store_str.split(" | ")[0]
                                store_mask = df['Store'] == selected_store
                                # Check if time_col in df columns for groupby
                                if time_col not in df.columns:
                                    st.warning(f"Cannot drill down: '{time_col}' not found in data columns.")
                                    return
                                detail_view = df[store_mask].groupby(['Item_Name', time_col])[detail_cols].sum().unstack(level=1, fill_value=0)
                                d_metrics = detail_view.columns.get_level_values(0).unique()
                                for m in d_metrics:
                                    m_cols = detail_view.loc[:, (m, slice(None))].columns
                                    for c in m_cols:
                                        detail_view[c] = pd.to_numeric(detail_view[c], errors='coerce').fillna(0)
                                    detail_view[(m, 'TOTAL')] = detail_view[m_cols].sum(axis=1)
                                if (sort_col, 'TOTAL') in detail_view.columns:
                                    detail_view = detail_view.sort_values((sort_col, 'TOTAL'), ascending=False)
                                st.markdown(f"#### 📦 Items in {selected_store}")
                                f_det = {c: "{:,.0f}" if 'STR%' in str(c) else fmt for c in detail_view.columns}
                                st.dataframe(detail_view.style.format(f_det), width='stretch')
                    
                    display_drilldown(
                        t1, 
                        v_s_qty, 
                        qty_display_list, # Columns to show in detail
                        'Sales_Qty', # Column to sort by
                        "{:,.2f}",group_col
                    ) 

                    # Tab 2: Store Val (Drilldown shows Dist, Sales, Waste)
                    display_drilldown(
                        t2, 
                        v_s_val, 
                        val_display_list, # Columns to show in detail
                        'Sales_Val', # Column to sort by
                        "{:,.2f}",group_col
                    )
                    def display_item_drilldown(tab, detail_cols, sort_col, fmt, time_col):
                        with tab:
                            
                            summary = df.groupby(['Item_Name', time_col])[detail_cols].sum().unstack(level=1, fill_value=0)
                            if summary.empty:
                                st.info("No data.")
                                return
                            # Calculate Totals
                            metrics = summary.columns.get_level_values(0).unique()
                            for m in metrics:
                                m_cols = summary.loc[:, (m, slice(None))].columns
                                for c in m_cols:
                                    summary[c] = pd.to_numeric(summary[c], errors='coerce').fillna(0)
                                summary[(m, 'TOTAL')] = summary[m_cols].sum(axis=1)

                            if 'Sales_Qty' in metrics and 'Dist_Qty' in metrics:
                                sales_total = summary[('Sales_Qty', 'TOTAL')]
                                dist_total =summary[('Dist_Qty','TOTAL')]
                                str_vals = (sales_total/dist_total * 100).replace([float('inf'), -float('inf')], 0)
                                summary[('STR%', 'TOTAL')] = str_vals.round(0)
                            if (sort_col, 'TOTAL') in summary.columns:
                                summary = summary.sort_values((sort_col, 'TOTAL'), ascending=False)
                            st.markdown(f"### 📦 Item Summary")
                            f_dict = {c: "{:,.0f}" if 'STR%' in str(c) else fmt for c in summary.columns}
                            st.dataframe(summary.style.format(f_dict), height=400, use_container_width=True)
                            st.divider()
                            # 2. FAST DRILL-DOWN
                            st.markdown("### 🔍 Select Item to View Stores")
                            limit_list = summary.index[:2000]
                            item_options = []
                            for item in limit_list:
                                val = summary.loc[item, (sort_col, 'TOTAL')]
                                item_options.append(f"{item} | Total {sort_col}: {val:,.2f}")
                            sel_item_str = st.selectbox(f"Select Item ({sort_col})", options=item_options, key=f"sel_item_{sort_col}")
                            if sel_item_str:
                                selected_item = sel_item_str.split(" | ")[0]
                                item_mask = df['Item_Name'] == selected_item
                                if time_col not in df.columns:
                                    st.warning(f"Cannot drill down: '{time_col}' not found in data columns.")
                                    return
                                item_view = df[item_mask].groupby(['Store', time_col])[detail_cols].sum().unstack(level=1, fill_value=0)
                                d_metrics = item_view.columns.get_level_values(0).unique()
                                for m in d_metrics:
                                    m_cols = item_view.loc[:, (m, slice(None))].columns
                                    for c in m_cols:
                                        item_view[c] = pd.to_numeric(item_view[c], errors='coerce').fillna(0)
                                    item_view[(m, 'TOTAL')] = item_view[m_cols].sum(axis=1)
                                if (sort_col, 'TOTAL') in item_view.columns:
                                    item_view = item_view.sort_values((sort_col, 'TOTAL'), ascending=False)
                                st.markdown(f"#### 📍 Stores selling {selected_item}")
                                f_det = {c: "{:,.0f}" if 'STR%' in str(c) else fmt for c in item_view.columns}
                                st.dataframe(item_view.sort_index(axis=1).style.format(f_det), width='stretch')

                    # Tab 3 & 4: Item Views (Keep as simple Pivot)
                    def display_simple_pivot(tab, df_in, fmt,time_col):
                        with tab:
                            try:
                                p = df_in.unstack(level=time_col, fill_value=0)
                                p['Total'] = p.sum(axis=1)
                                p = p.sort_values('Total', ascending=False).drop(columns=['Total'])
                                st.dataframe(p.style.format(fmt))

                                st.markdown("---")
                                st.markdown("### 🔍 Store Details (Click to Expand)")
                                
                            except: st.info("No data")

                    display_item_drilldown(
                        t3, 
                        qty_display_list, 
                        'Sales_Qty', "{:,.2f}",group_col
                    )

                    # Tab 4: Item Val (Item -> Stores) - NEW LOGIC
                    display_item_drilldown(
                        t4,
                        val_display_list, 
                        'Sales_Val', "{:,.2f}",group_col
                    )

                    with t5:
                        if not v_top10_all.empty:
                            valid_items_df = v_top10_all[(~v_top10_all['Item_Name'].str.startswith('Item ')) & (v_top10_all['Item_Name'] != 'Unknown Item')]
                            top10_df = valid_items_df.nlargest(10, 'Sales_Val')
                            
                            # Create a display copy and add the Grand Total row
                            disp_top10 = top10_df.copy()
                            disp_top10.loc['Grand Total'] = disp_top10[['Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']].sum()
                            disp_top10.at['Grand Total', 'Item_Name'] = 'GRAND TOTAL'
                            
                            st.dataframe(disp_top10.style.format({c: "{:,.2f}" for c in ['Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']}), hide_index=True, use_container_width=True)
                            st.bar_chart(top10_df.set_index('Item_Name')['Sales_Val']) # Use original df for chart
                        else:
                            st.info("No Sales Data available for Top 10.")
                    
                    with t6:
                        if not v_top10_all.empty:
                            bottom10_df = valid_items_df.nsmallest(10, 'Sales_Val')
                            
                            # Create a display copy and add the Grand Total row
                            disp_bot10 = bottom10_df.copy()
                            disp_bot10.loc['Grand Total'] = disp_bot10[['Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']].sum()
                            disp_bot10.at['Grand Total', 'Item_Name'] = 'GRAND TOTAL'
                            
                            st.dataframe(disp_bot10.style.format({c: "{:,.2f}" for c in ['Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']}), hide_index=True, use_container_width=True)
                            st.bar_chart(bottom10_df.set_index('Item_Name')['Sales_Val']) # Use original df for chart
                        else:
                            st.info("No valid sales data for Bottom 10.")
                    st.divider()
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        workbook = writer.book
                        
                        # --- Custom Excel Formats ---
                        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'color': '#1F497D'})
                        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
                        num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'valign': 'vcenter'})
                        total_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'valign': 'vcenter'})
                        int_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1, 'valign': 'vcenter'})
                        total_int_fmt = workbook.add_format({'num_format': '#,##0', 'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'valign': 'vcenter'})
                        total_num_fmt = workbook.add_format({'num_format': '#,##0.00', 'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'valign': 'vcenter'})
                        
                        # --- Header Color Formats ---
                        header_base = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'font_color': 'black'})
                        fmt_dist = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#B4C6E7', 'font_color': 'black'}) # Light Blue
                        fmt_sales = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F8CBAD', 'font_color': 'black'}) # Light Orange
                        fmt_waste = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#C6E0B4', 'font_color': 'black'}) # Light Green
                        fmt_calc = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#FFE699', 'font_color': 'black'}) # Light Yellow
                        
                        # Helper to pick the right color
                        def get_fmt(metric_name):
                            m = str(metric_name).upper()
                            if 'DIST' in m: return fmt_dist
                            if 'SALES' in m: return fmt_sales
                            if 'WASTE' in m: return fmt_waste
                            if 'STR' in m or 'PROFIT' in m or 'BALANCE' in m: return fmt_calc
                            return header_base

                        def format_pivot(df, sheet_name, title, col_w=20):
                            if df.empty: return
                            
                            # 1. Calculate Grand Total
                            totals = df.sum(numeric_only=True)
                            
                            # 2. Write Data to Excel
                            df.to_excel(writer, sheet_name=sheet_name, startrow=2)
                            ws = writer.sheets[sheet_name]
                            
                            # 3. Add Title
                            ws.write(0, 0, title, title_fmt)
                            
                            # 4. Apply column widths
                            idx_cols = df.index.nlevels
                            num_cols = len(df.columns)
                            hdr_rows = df.columns.nlevels
                            total_row = 2 + hdr_rows + len(df.index) 
                            
                            ws.set_column(0, idx_cols - 1, col_w, cell_fmt)
                            for c_idx, col_tuple in enumerate(df.columns):
                                excel_c = idx_cols + c_idx
                                metric = col_tuple[0] if isinstance(col_tuple, tuple) else col_tuple
                                c_fmt = int_fmt if 'STR%' in str(metric).upper() else num_fmt
                                ws.set_column(excel_c, excel_c, 14, c_fmt)
                            
                            # 5. Paint Dynamic Colored Headers
                            # Format the Index headers (e.g. Store, Item Name)
                            for i, idx_name in enumerate(df.index.names):
                                name = str(idx_name) if idx_name else ""
                                for r in range(2, 2 + hdr_rows):
                                    val = name if r == 2 + hdr_rows - 1 else ""
                                    ws.write(r, i, val, header_base)

                            # Format the Data headers based on the Metric name
                            for c_idx, col_tuple in enumerate(df.columns):
                                excel_c = idx_cols + c_idx
                                metric = col_tuple[0] if isinstance(col_tuple, tuple) else col_tuple
                                c_fmt = get_fmt(metric)
                                
                                if isinstance(col_tuple, tuple):
                                    for r_idx, val in enumerate(col_tuple):
                                        ws.write(2 + r_idx, excel_c, str(val), c_fmt)
                                else:
                                    ws.write(2, excel_c, str(col_tuple), c_fmt)
                                
                            # 6. Format Grand Total Row
                            ws.set_row(total_row, 20, total_fmt)
                            if idx_cols > 1:
                                ws.merge_range(total_row, 0, total_row, idx_cols - 1, "GRAND TOTAL", total_fmt)
                            else:
                                ws.write_string(total_row, 0, "GRAND TOTAL", total_fmt)
                                
                            for col in range(idx_cols, idx_cols + num_cols):
                                val = totals.iloc[col - idx_cols]
                                col_tuple = df.columns[col - idx_cols]
                                metric = col_tuple[0] if isinstance(col_tuple, tuple) else col_tuple
                                t_fmt = total_int_fmt if 'STR%' in str(metric).upper() else total_num_fmt
                                ws.write_number(total_row, col, val, t_fmt)

                        # --- 1. Store Qty ---
                        qty_pivot = v_s_qty.unstack(level=0).fillna(0)
                        metrics = qty_pivot.columns.get_level_values(0).unique()
                        for m in metrics:
                            m_cols = qty_pivot.loc[:, (m, slice(None))].columns
                            for c in m_cols: qty_pivot[c] = pd.to_numeric(qty_pivot[c], errors='coerce').fillna(0)
                            qty_pivot[(m, 'TOTAL')] = qty_pivot[m_cols].sum(axis=1)
                        if ('Sales_Qty', 'TOTAL') in qty_pivot.columns:
                            qty_pivot = qty_pivot.sort_values(('Sales_Qty', 'TOTAL'), ascending=False)
                        format_pivot(qty_pivot, 'Store Qty', "📊 STORE QUANTITY ANALYSIS", col_w=35)

                        # --- 2. Store Value ---
                        val_pivot = v_s_val.unstack(level=0).fillna(0)
                        metrics = val_pivot.columns.get_level_values(0).unique()
                        for m in metrics:
                            m_cols = val_pivot.loc[:, (m, slice(None))].columns
                            for c in m_cols: val_pivot[c] = pd.to_numeric(val_pivot[c], errors='coerce').fillna(0)
                            val_pivot[(m, 'TOTAL')] = val_pivot[m_cols].sum(axis=1)
                        if ('Sales_Val', 'TOTAL') in val_pivot.columns:
                            val_pivot = val_pivot.sort_values(('Sales_Val', 'TOTAL'), ascending=False)
                        format_pivot(val_pivot, 'Store $', "💰 STORE VALUE ANALYSIS", col_w=35)

                        # --- 3. Item Qty Summary ---
                        item_qty_pivot = v_i_qty.unstack(level=0).fillna(0)
                        metrics = item_qty_pivot.columns.get_level_values(0).unique()
                        for m in metrics:
                            m_cols = item_qty_pivot.loc[:, (m, slice(None))].columns
                            for c in m_cols: item_qty_pivot[c] = pd.to_numeric(item_qty_pivot[c], errors='coerce').fillna(0)
                            item_qty_pivot[(m, 'TOTAL')] = item_qty_pivot[m_cols].sum(axis=1)
                        if ('Sales_Qty', 'TOTAL') in item_qty_pivot.columns:
                            item_qty_pivot = item_qty_pivot.sort_values(('Sales_Qty', 'TOTAL'), ascending=False)
                        format_pivot(item_qty_pivot, 'Item Qty', "📦 ITEM QUANTITY SUMMARY", col_w=30)

                        # --- 4. Item Value Summary ---
                        item_val_pivot = v_i_val.unstack(level=0).fillna(0)
                        metrics = item_val_pivot.columns.get_level_values(0).unique()
                        for m in metrics:
                            m_cols = item_val_pivot.loc[:, (m, slice(None))].columns
                            for c in m_cols: item_val_pivot[c] = pd.to_numeric(item_val_pivot[c], errors='coerce').fillna(0)
                            item_val_pivot[(m, 'TOTAL')] = item_val_pivot[m_cols].sum(axis=1)
                        if ('Sales_Val', 'TOTAL') in item_val_pivot.columns:
                            item_val_pivot = item_val_pivot.sort_values(('Sales_Val', 'TOTAL'), ascending=False)
                        format_pivot(item_val_pivot, 'Item $', "💵 ITEM VALUE SUMMARY", col_w=30)

                        # --- 5. Combined Top & Bottom 10 ---
                        if not v_top10_all.empty:
                            ws5 = workbook.add_worksheet('TOP&BTM 10')
                            
                            valid_items_df = v_top10_all[(~v_top10_all['Item_Name'].str.startswith('Item ')) & (v_top10_all['Item_Name'] != 'Unknown Item')]
                            
                            top10_df = valid_items_df.nlargest(10, 'Sales_Val')
                            top10_df.columns = ['Top 10 Items', 'Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']
                            
                            bottom10_df = valid_items_df.nsmallest(10, 'Sales_Val')
                            bottom10_df.columns = ['Bottom 10 Items', 'Dist_Val', 'Sales_Val', 'Waste_Val', 'Profit']
                            
                            ws5.write(0, 0, "🏆 TOP 10 ITEMS BY SALES", title_fmt)
                            top10_df.to_excel(writer, sheet_name='TOP&BTM 10', startrow=2, index=False)
                            
                            ws5.write(15, 0, "📉 BOTTOM 10 ITEMS BY SALES", title_fmt)
                            bottom10_df.to_excel(writer, sheet_name='TOP&BTM 10', startrow=17, index=False)
                            
                            # Format Column widths
                            ws5.set_column('A:A', 40, cell_fmt)
                            ws5.set_column('B:E', 15, num_fmt)
                            
                            # Loop through both tables to apply Colors AND Grand Totals
                            tables = [
                                (2, 'Top 10 Items', top10_df), 
                                (17, 'Bottom 10 Items', bottom10_df)
                            ]
                            
                            for start_r, title, df_subset in tables:
                                # Apply Color-Coded Headers
                                ws5.write(start_r, 0, title, header_base)
                                ws5.write(start_r, 1, 'Dist_Val', fmt_dist)    # Light Blue
                                ws5.write(start_r, 2, 'Sales_Val', fmt_sales)  # Light Orange
                                ws5.write(start_r, 3, 'Waste_Val', fmt_waste)  # Light Green
                                ws5.write(start_r, 4, 'Profit', fmt_calc)      # Light Yellow
                                
                                # Add Grand Total Row dynamically at the bottom of the table
                                total_row = start_r + len(df_subset) + 1
                                ws5.write_string(total_row, 0, "GRAND TOTAL", total_fmt)
                                ws5.write_number(total_row, 1, df_subset['Dist_Val'].sum(), total_num_fmt)
                                ws5.write_number(total_row, 2, df_subset['Sales_Val'].sum(), total_num_fmt)
                                ws5.write_number(total_row, 3, df_subset['Waste_Val'].sum(), total_num_fmt)
                                ws5.write_number(total_row, 4, df_subset['Profit'].sum(), total_num_fmt)
                        # --- 6. Master Data ---
                        df.to_excel(writer, sheet_name='Master Data Raw', index=False)

                    excel_data = output.getvalue()
                    
                    col_d1, col_d2 = st.columns([2,1])
                    with col_d1:
                         st.download_button(
                            label="📥 Download Full Excel Report",
                            data=excel_data,
                            file_name=f"Report_{sel_year}_{rpt}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Downloads a multi-tab Excel file with all summaries."
                        )

                    c1, c2 = st.columns([3, 1])
                    rep_name = c1.text_input("Report Name (e.g. Week48)", "")
                    if c2.button("💾 Save All to History"):
                        if urls['h'] and rep_name:
                            with st.spinner("Saving..."):
                                write_to_sheet(urls['h'], f"Rep_{rep_name}_StoreQty", v_s_qty)
                                write_to_sheet(urls['h'], f"Rep_{rep_name}_StoreVal", v_s_val)
                                write_to_sheet(urls['h'], f"Rep_{rep_name}_ItemQty", v_i_qty)
                                write_to_sheet(urls['h'], f"Rep_{rep_name}_ItemVal", v_i_val)
                                write_to_sheet(urls['h'], f"Rep_{rep_name}_Top10", v_top10_all)
                                write_to_sheet(urls['h'], f"Rep_{rep_name}_Master", df)
                                st.success("✅ Saved!")
                        else: st.error("Need URL & Name")

    elif app_mode == "🗄️ Saved Reports":
        if urls['h']:
            reps = get_saved_reports(urls['h'])
            if reps:
                sel = st.selectbox("Select Report:", reps)
                
                if sel:
                    # 1. LOAD DATA FIRST (Inside Spinner)
                    loaded_data = {}
                    sheet_tabs = ["StoreQty", "StoreVal", "ItemQty", "ItemVal", "Top10", "Master"]
                    
                    with st.spinner("Downloading Report Data..."):
                        try:
                            client = get_gspread_client()
                            sh = client.open_by_url(urls['h'])
                            
                            # Pre-fetch all necessary tabs to avoid UI lag later
                            for tab_name in sheet_tabs:
                                try:
                                    full_data = sh.worksheet(f"Rep_{sel}_{tab_name}").get_all_values()
                                    if full_data:
                                        header = full_data[0]
                                        rows = full_data[1:]
                                        loaded_data[tab_name] = pd.DataFrame(rows, columns=header)
                                    else:
                                        loaded_data[tab_name] = pd.DataFrame()
                                except:
                                    loaded_data[tab_name] = pd.DataFrame()
                                    
                        except Exception as e:
                            st.error(f"Connection Error: {e}")
                            st.stop()

                    # 2. RENDER UI (Outside Spinner - Prevents White Screen Error)
                    if loaded_data:
                        # Create Tabs
                        t1, t2, t3, t4, t5, t6 = st.tabs([
                            "📦 Store Qty", 
                            "💰 Store Val", 
                            "📦 Item Qty", 
                            "💰 Item Val", 
                            "🏆 Top 10", 
                            "📝 Master Data"
                        ])

                        # Render Dataframes safely
                        with t1: 
                            st.dataframe(loaded_data.get("StoreQty", pd.DataFrame()), use_container_width=True)
                        
                        with t2: 
                            st.dataframe(loaded_data.get("StoreVal", pd.DataFrame()), use_container_width=True)
                        
                        with t3: 
                            st.dataframe(loaded_data.get("ItemQty", pd.DataFrame()), use_container_width=True)
                        
                        with t4: 
                            st.dataframe(loaded_data.get("ItemVal", pd.DataFrame()), use_container_width=True)
                        
                        with t5: 
                            df_top = loaded_data.get("Top10", pd.DataFrame())
                            st.dataframe(df_top, use_container_width=True)
                            # Try to render chart if data exists
                            if not df_top.empty and 'Total Sales' in df_top.columns:
                                try:
                                    # Ensure numeric for chart
                                    df_top['Total Sales'] = pd.to_numeric(df_top['Total Sales'], errors='coerce')
                                    st.bar_chart(df_top.set_index(df_top.columns[0])['Total Sales'])
                                except: pass

                        with t6: 
                            st.dataframe(loaded_data.get("Master", pd.DataFrame()), use_container_width=True)
