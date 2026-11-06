"""Extend the existing collector without changing its risk/decision rules.

One additional yearly balance-sheet request adds working-capital, equity and ROE
context. Core audited fields are never overwritten; supplemental fields merge only
when the fiscal period matches.
"""
from __future__ import annotations
import math
_CACHE={}

def merge_supplemental_history(history, supplemental):
    """Do not join a provider growth denominator to a different reported numerator."""
    hist=dict(history);h=supplemental or {};excluded=[];added=[]
    if not h:return hist
    if h.get('filing_period')!=hist.get('filing_period'):
        hist.update(supplemental_period_status='period_mismatch',supplemental_period=h.get('filing_period'))
        return hist
    if not hist.get('currency') or hist.get('currency')!=h.get('currency'):
        hist['supplemental_period_status']='currency_unverified_or_mismatch'
        return hist
    def same(a,b):
        if isinstance(a,bool) or isinstance(b,bool):return False
        try:
            a,b=float(a),float(b)
            return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=max(1e-6,abs(b)*1e-8)
        except (TypeError,ValueError):return False
    def metric_ok(metric):
        if not same(hist.get(metric),h.get(metric)):return False
        for suffix in ('_previous','_growth'):
            key=metric+suffix
            if hist.get(key) is not None and not same(hist[key],h.get(key)):return False
        return True
    # Add independent current-provider amounts first.  Preserved official None
    # values remain unknown and are not replaced by a provider estimate.
    derived={'roe':('net_income','equity'),'cfo_to_net_income':('cfo','net_income')}
    delayed=[]
    for key,value in h.items():
        if key in hist or value is None:continue
        if key.endswith(('_previous','_growth')) or key in derived or key=='quality_flags':
            delayed.append((key,value))
        else:hist[key]=value;added.append(key)
    for key,value in delayed:
        if key=='quality_flags':
            ok=all(metric_ok(metric) for metric in ('revenue','net_income','cfo','capex','fcf','accounts_receivable','inventory','total_debt_statement') if h.get(metric) is not None)
        elif key in derived:ok=all(metric_ok(metric) for metric in derived[key])
        else:
            metric=key.rsplit('_',1)[0]
            if metric=='total_debt':metric='total_debt_statement'
            ok=metric_ok(metric)
        if ok:hist[key]=value;added.append(key)
        else:excluded.append({'field':key,'reason':'preserved_current_amount_or_comparison_basis_mismatch'})
    hist.update(supplemental_period_status='same_period',supplemental_fields=added,
                supplemental_excluded_fields=excluded,
                supplemental_basis='Yahoo annual supplemental fields; matching period/currency/current amount is necessary; official comparison remains separate')
    return hist

def install(engine):
    N=engine.N;core=engine.core;old_collect=engine.collect
    def annual_history(ticker,errors):
        try:
            income=ticker.get_income_stmt(freq='yearly');cash=ticker.get_cashflow(freq='yearly');balance=ticker.get_balance_sheet(freq='yearly')
            if income is None or income.empty:return {}
            dates=sorted(income.columns,reverse=True);end=dates[0];prior=dates[1] if len(dates)>1 else None
            def val(frame,keys,day):
                if frame is None or frame.empty or day is None or day not in frame.columns:return None
                for key in keys:
                    if key in frame.index:return N(frame.loc[key,day])
                return None
            def ch(new,old):return core.change(new,old) if new is not None and old not in (None,0) else None
            rev=val(income,['TotalRevenue','Total Revenue'],end);prev=val(income,['TotalRevenue','Total Revenue'],prior);op=val(income,['OperatingIncome','Operating Income'],end);op0=val(income,['OperatingIncome','Operating Income'],prior);net=val(income,['NetIncomeCommonStockholders','NetIncome','Net Income'],end);net0=val(income,['NetIncomeCommonStockholders','NetIncome','Net Income'],prior);eps=val(income,['DilutedEPS','Diluted EPS'],end);eps0=val(income,['DilutedEPS','Diluted EPS'],prior)
            cfo=val(cash,['OperatingCashFlow','Operating Cash Flow','TotalCashFromOperatingActivities'],end);cfo0=val(cash,['OperatingCashFlow','Operating Cash Flow','TotalCashFromOperatingActivities'],prior);rawcap=val(cash,['CapitalExpenditure','Capital Expenditure'],end);rawcap0=val(cash,['CapitalExpenditure','Capital Expenditure'],prior);cap=abs(rawcap) if rawcap is not None else None;cap0=abs(rawcap0) if rawcap0 is not None else None;fcf=cfo-cap if cfo is not None and cap is not None else None;fcf0=cfo0-cap0 if cfo0 is not None and cap0 is not None else None
            ar=val(balance,['AccountsReceivable','Accounts Receivable','Receivables'],end);ar0=val(balance,['AccountsReceivable','Accounts Receivable','Receivables'],prior);inv=val(balance,['Inventory','Inventories'],end);inv0=val(balance,['Inventory','Inventories'],prior);eq=val(balance,['StockholdersEquity','Stockholders Equity','TotalStockholderEquity','CommonStockEquity'],end);eq0=val(balance,['StockholdersEquity','Stockholders Equity','TotalStockholderEquity','CommonStockEquity'],prior);assets=val(balance,['TotalAssets','Total Assets'],end);assets0=val(balance,['TotalAssets','Total Assets'],prior);debt=val(balance,['TotalDebt','Total Debt'],end);debt0=val(balance,['TotalDebt','Total Debt'],prior)
            rg=ch(rev,prev);arg=ch(ar,ar0);ig=ch(inv,inv0);ratio=cfo/net if cfo is not None and net is not None and net>0 else None;flags=[]
            if net is not None and net>0 and cfo is not None and cfo<=0:flags.append('순이익은 흑자지만 영업현금흐름은 0 이하')
            elif ratio is not None and ratio<.7:flags.append('영업현금흐름이 순이익의 70% 미만')
            if rg is not None and arg is not None and arg-rg>10:flags.append('매출채권 증가율이 매출 성장률보다 10%p 이상 높음')
            if rg is not None and ig is not None and ig-rg>10:flags.append('재고 증가율이 매출 성장률보다 10%p 이상 높음')
            if cap is not None and cap0 not in (None,0) and ch(cap,cap0)>20 and (fcf is None or fcf<=0):flags.append('투자지출이 20% 넘게 늘고 FCF가 양수가 아님')
            if debt is not None and debt0 not in (None,0) and ch(debt,debt0)>20:flags.append('총차입금이 전년보다 20% 넘게 증가')
            out={'filing_period':str(end)[:10],'revenue':rev,'revenue_previous':prev,'revenue_growth':rg,'operating_income':op,'operating_income_previous':op0,'operating_income_growth':ch(op,op0),'operating_margin':op/rev*100 if rev and op is not None else None,'net_income':net,'net_income_previous':net0,'net_income_growth':ch(net,net0),'eps':eps,'eps_previous':eps0,'eps_growth':ch(eps,eps0),'cfo':cfo,'cfo_previous':cfo0,'cfo_growth':ch(cfo,cfo0),'capex':cap,'capex_previous':cap0,'capex_growth':ch(cap,cap0),'fcf':fcf,'fcf_previous':fcf0,'fcf_growth':ch(fcf,fcf0),'accounts_receivable':ar,'accounts_receivable_previous':ar0,'accounts_receivable_growth':arg,'inventory':inv,'inventory_previous':inv0,'inventory_growth':ig,'equity':eq,'equity_previous':eq0,'equity_growth':ch(eq,eq0),'total_assets':assets,'total_assets_previous':assets0,'total_assets_growth':ch(assets,assets0),'total_debt_statement':debt,'total_debt_statement_previous':debt0,'total_debt_growth':ch(debt,debt0),'roe':net/eq*100 if net is not None and eq not in (None,0) and eq>0 else None,'cfo_to_net_income':ratio,'quality_flags':flags,'basis':'Yahoo 연간 재무; EPS는 희석, FCF=CFO-CAPEX. 매출채권·재고·자본은 같은 연말 기준. 공식 원문 대조와 별개.'}
            _CACHE[getattr(ticker,'ticker',None)]=out;return out
        except Exception as e:errors.append({'field':'annual_extended','error':type(e).__name__+': '+str(e)[:120]});return {}
    engine.annual_history=annual_history
    def collect(spec,base,audit,benchmark,now):
        row=old_collect(spec,base,audit,benchmark,now);h=_CACHE.get(spec[4]) or {};hist=row.get('history') or {}
        row['history']=merge_supplemental_history(hist,h);return row
    engine.collect=collect

def add_profile(row,meta):
    """Reuse the metadata request already made by run_stock_research_v9."""
    def n(x):
        if isinstance(x,bool):return None
        try:
            value=float(x)
            return value if math.isfinite(value) else None
        except (TypeError,ValueError):return None
    roe=n(meta.get('returnOnEquity'));roa=n(meta.get('returnOnAssets'))
    forecasts=row.get('forecasts') or {}
    row['valuation']={'trailing_pe':n(meta.get('trailingPE')),'forward_pe':n(forecasts.get('next_fy_pe')),
                     'provider_forward_pe':n(meta.get('forwardPE')),'price_to_book':n(meta.get('priceToBook')),
                     'return_on_equity_pct':roe*100 if roe is not None else None,
                     'annual_end_equity_roe_pct':n((row.get('history') or {}).get('roe')),
                     'return_on_assets_pct':roa*100 if roa is not None else None,
                     'book_value_per_share':n(meta.get('bookValue')),'trailing_eps':n(meta.get('trailingEps')),
                     'forward_eps':n(meta.get('forwardEps')),'enterprise_to_ebitda':n(meta.get('enterpriseToEbitda')),
                     'currency':meta.get('financialCurrency'),'quote_currency':meta.get('currency'),
                     'forward_pe_basis':forecasts.get('next_fy_pe_basis'),
                     'trailing_pe_basis':'provider_trailingPE_snapshot; not recomputed from saved close or annual EPS',
                     'provider_forward_pe_basis':'provider_forwardPE_snapshot; period may differ from plus1y; not used as next FY PE',
                     'return_on_equity_basis':'provider_returnOnEquity_snapshot; period and average-equity basis not independently verified',
                     'annual_end_equity_roe_basis':'annual net income divided by same year-end equity; not average-equity ROE',
                     'basis':'다음 FY 예상 PER만 저장 종가÷동일통화 +1y EPS. 그 외 TTM PER·PBR·ROE는 제공처 스냅샷이며 연간 실적 직접 계산과 구분.'}
    row['business']={'sector':meta.get('sector'),'industry':meta.get('industry'),'summary':str(meta.get('longBusinessSummary') or '')[:1200],'website':meta.get('website'),'employees':n(meta.get('fullTimeEmployees')),'basis':'제공처 기업 프로필. 제품별 매출·고객·원재료는 공식 사업보고서에서 추가 확인.'}
    row.setdefault('sources',{})['profile']='https://finance.yahoo.com/quote/'+row.get('source_symbol',row.get('symbol'))+'/profile/'
