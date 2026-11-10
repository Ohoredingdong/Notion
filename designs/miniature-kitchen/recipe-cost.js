/* Read-only recipe estimates from entered totals or dated grocery receipts.
   This module never seeds prices, edits storage or changes actual cash spending. */
(function(root,factory){
  if(typeof module==='object'&&module.exports)module.exports=factory(require('./journey-model.js'));
  else root.KitchenRecipeCost=factory(root.KitchenJourneyModel);
})(typeof window!=='undefined'?window:globalThis,function(J){
  'use strict';
  const round=value=>Math.round(value*1e6)/1e6;
  const amount=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0&&value<=1e9;
  const realDay=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&
    Number.isFinite(Date.parse(value+'T12:00:00Z'))&&new Date(value+'T12:00:00Z').toISOString().slice(0,10)===value;
  const record=value=>value&&typeof value==='object'&&!Array.isArray(value);
  const text=value=>typeof value==='string'&&value.trim().length>0;

  function safeRecipe(recipe){
    const input=record(recipe)?recipe:{};
    return {
      amounts:record(input.amounts)?Object.fromEntries(Object.entries(input.amounts).filter(([name])=>text(name))):{},
      ...Object.fromEntries(['f','s','p'].map(key=>[key,Array.isArray(input[key])?input[key].filter(text):[]]))
    };
  }

  function receiptQuotes(flow,day){
    const quotes=[];
    for(const [expenseIndex,expense] of (Array.isArray(flow.expenses)?flow.expenses:[]).entries()){
      if(!record(expense)||expense.category!=='groceries'||!realDay(expense.day)||expense.day>day||
        !text(expense.id)||!record(expense.receipt)||!Array.isArray(expense.receipt.items))continue;
      const lines=expense.receipt.items,allAmountsKnown=lines.length>0&&lines.every(line=>record(line)&&amount(line.amount));
      const itemAmountsTotal=allAmountsKnown?round(lines.reduce((sum,line)=>sum+line.amount,0)):null;
      const receiptAdjusted=itemAmountsTotal!==null&&amount(expense.amount)&&Math.abs(itemAmountsTotal-expense.amount)>1e-6;
      const receiptUnreconciled=!allAmountsKnown||!amount(expense.amount);
      for(const [itemIndex,line] of lines.entries()){
        if(!record(line)||!text(line.name)||!amount(line.amount))continue;
        const parsed=J.parseQuantity(line.quantity);
        if(!parsed||parsed.baseAmount<=0)continue;
        const unitPrice=line.amount/parsed.baseAmount;
        if(!Number.isFinite(unitPrice)||unitPrice>Number.MAX_SAFE_INTEGER)continue;
        quotes.push({
          name:line.name,quantity:line.quantity,amount:line.amount,baseUnit:parsed.baseUnit,unitPrice,
          source:expense.id,itemId:text(line.id)?line.id:expense.id+'-item-'+itemIndex,
          purchaseId:text(expense.receipt.purchaseId)?expense.receipt.purchaseId:expense.id,
          day:expense.day,receiptAmount:amount(expense.amount)?expense.amount:null,itemAmountsTotal,
          receiptAdjusted,receiptUnreconciled,expenseIndex,itemIndex
        });
      }
    }
    return quotes;
  }

  function latestQuote(quotes,name,baseUnit){
    let latest=null;
    for(const quote of quotes){
      if(quote.baseUnit!==baseUnit||!J.same(name,quote.name))continue;
      if(!latest||quote.day>latest.day||quote.day===latest.day&&
        (quote.expenseIndex>latest.expenseIndex||quote.expenseIndex===latest.expenseIndex&&quote.itemIndex>latest.itemIndex))latest=quote;
    }
    return latest;
  }

  function estimate(recipe,options={}){
    if(!J||typeof J.recipeAvailability!=='function')throw new TypeError('KitchenJourneyModel is required.');
    const {day,portions=1}=options||{},flow=record(options?.flow)?options.flow:{};
    if(!realDay(day))throw new TypeError('A real YYYY-MM-DD day is required.');
    if(typeof portions!=='number'||!Number.isFinite(portions)||portions<=0||portions>100)
      throw new TypeError('Portions must be greater than 0 and at most 100.');
    const facts=record(flow.recipeFacts)&&record(recipe)&&text(recipe.id)?flow.recipeFacts[recipe.id]:null;
    if(record(facts)&&amount(facts.cost)){
      const total=round(facts.cost*portions);
      return {
        kind:'entered',total,knownSubtotal:total,missing:[],rows:[],
        sources:[{kind:'entered',label:'직접 입력한 1회분 재료비',detail:typeof facts.source==='string'?facts.source:''}],
        basisNote:'직접 입력한 1회분 재료비를 '+portions+'배한 값이에요. 재료별로 임의 배분하지 않으며 실제 구매 지출과 별도예요.'
      };
    }
    const demands=J.recipeAvailability(safeRecipe(recipe),{items:[]},{day,portions}).rows;
    const quotes=receiptQuotes(flow,day),rows=[],missing=[],sources=[],seen=new Set();
    for(const demand of demands){
      const row={name:demand.name,required:demand.required,cost:null,source:null,day:null,quantity:null,
        itemId:null,unitPrice:null,baseUnit:demand.baseUnit,receiptAdjusted:false,receiptUnreconciled:false};
      let reason='';
      if(demand.needed===null||demand.needed<=0)reason='필요량의 숫자·단위를 확인해 주세요.';
      else{
        const quote=latestQuote(quotes,demand.name,demand.baseUnit);
        if(!quote)reason='가격과 같은 단위의 구매 내역이 없어요.';
        else{
          const value=demand.needed*quote.unitPrice;
          if(!Number.isFinite(value)||value>Number.MAX_SAFE_INTEGER)reason='계산할 금액의 범위를 확인해 주세요.';
          else{
            Object.assign(row,{cost:round(value),source:quote.source,day:quote.day,quantity:quote.quantity,
              itemId:quote.itemId,unitPrice:quote.unitPrice,receiptAdjusted:quote.receiptAdjusted,receiptUnreconciled:quote.receiptUnreconciled});
            const key=quote.source+'|'+quote.itemId;
            if(!seen.has(key)){
              seen.add(key);
              sources.push({kind:'purchase',expenseId:quote.source,itemId:quote.itemId,purchaseId:quote.purchaseId,
                day:quote.day,name:quote.name,quantity:quote.quantity,amount:quote.amount,baseUnit:quote.baseUnit,
                unitPrice:quote.unitPrice,receiptAmount:quote.receiptAmount,itemAmountsTotal:quote.itemAmountsTotal,
                adjustmentUnallocated:quote.receiptAdjusted,unreconciled:quote.receiptUnreconciled});
            }
          }
        }
      }
      rows.push(row);
      if(reason)missing.push({name:demand.name,required:demand.required,reason});
    }
    const priced=rows.filter(row=>row.cost!==null),sum=priced.reduce((total,row)=>total+row.cost,0);
    if(!Number.isFinite(sum)||sum>Number.MAX_SAFE_INTEGER){
      return {kind:'unknown',total:null,knownSubtotal:null,missing:[{name:'재료비',required:'금액 확인',reason:'계산할 금액의 범위를 확인해 주세요.'}],rows,sources,
        basisNote:'금액의 범위를 확인해 주세요. 실제 구매 지출은 변경하지 않았어요.'};
    }
    const knownSubtotal=priced.length?round(sum):null;
    const complete=rows.length>0&&missing.length===0;
    let basisNote='구매 내역의 품목 금액과 원래 구매 수량으로 계산한 사용분 예상이에요. 실제 구매 지출과 별도예요.';
    if(!priced.length)basisNote='재료비를 계산할 구매 가격·수량·단위를 확인해 주세요. 모르는 금액을 0원으로 처리하지 않아요.';
    else if(!complete)basisNote+=' 가격을 확인하지 못한 재료는 부분 합계에 포함하지 않았어요.';
    if(sources.some(source=>source.adjustmentUnallocated))basisNote+=' 품목 합계와 실제 결제 금액의 차이(할인·추가금)는 재료별로 배분하지 않았어요.';
    if(sources.some(source=>source.unreconciled))basisNote+=' 품목 금액이 모두 확인되지 않아 실제 결제 합계와 대조하지 못한 구매 내역이 있어요.';
    return {kind:complete?'purchase':priced.length?'partial':'unknown',total:complete?knownSubtotal:null,
      knownSubtotal,missing,rows,sources,basisNote};
  }
  function copied(value){
    try{return JSON.parse(JSON.stringify(value));}catch(_){return null;}
  }
  function sourcePresent(value){return text(value)||record(value)&&Object.keys(value).length>0||Array.isArray(value)&&value.length>0;}
  function referenceQuotes(reference,day){
    if(!record(reference)||!realDay(reference.day)||reference.day>day||!Array.isArray(reference.items))return [];
    // The observation date and the date this app could know the reference are
    // different. An optional availability date blocks retrospective leakage.
    if(Object.hasOwn(reference,'availableFrom')&&(!realDay(reference.availableFrom)||reference.availableFrom>day))return [];
    const quotes=[];
    for(const [itemIndex,item] of reference.items.entries()){
      if(!record(item)||!text(item.name)||!amount(item.amount))continue;
      const quoteDay=item.day===undefined?reference.day:item.day;
      if(!realDay(quoteDay)||quoteDay>day)continue;
      const parsed=J.parseQuantity(item.quantity),source=copied(item.source===undefined?reference.source:item.source);
      if(!parsed||parsed.baseAmount<=0||!sourcePresent(source))continue;
      const unitPrice=item.amount/parsed.baseAmount;
      if(!Number.isFinite(unitPrice)||unitPrice>Number.MAX_SAFE_INTEGER)continue;
      quotes.push({name:item.name,quantity:item.quantity,amount:item.amount,baseUnit:parsed.baseUnit,unitPrice,
        day:quoteDay,itemIndex,source,product:text(item.product)?item.product:'',samples:copied(item.samples)});
    }
    return quotes;
  }
  function quantityOptions(raw,portions){
    if(typeof raw!=='string')return [];
    return raw.split(/\s*또는\s*/).map(part=>{
      const parsed=J.parseQuantity(part);
      return parsed&&parsed.baseAmount>0?{parsed,needed:round(parsed.baseAmount*portions),usedQuantity:J.scaleQuantity(part,portions)}:null;
    }).filter(Boolean);
  }
  function newer(quote,previous){
    return !previous||quote.day>previous.day||quote.day===previous.day&&
      ((quote.expenseIndex??0)>(previous.expenseIndex??0)||
       (quote.expenseIndex??0)===(previous.expenseIndex??0)&&quote.itemIndex>previous.itemIndex);
  }
  function selectPurchase(quotes,name,options){
    let picked=null;
    for(const option of options){
      const quote=latestQuote(quotes,name,option.parsed.baseUnit);
      if(quote&&newer(quote,picked?.quote))picked={quote,option,sourceKind:'purchase',assumption:null};
    }
    return picked;
  }
  function selectReference(quotes,name,options,measurements){
    let picked=null;
    // A written recipe alternative, e.g. "1장 또는 20g", is not a density guess.
    for(const option of options)for(const quote of quotes){
      if(quote.baseUnit===option.parsed.baseUnit&&J.same(name,quote.name)&&newer(quote,picked?.quote))
        picked={quote,option,sourceKind:'reference',assumption:null};
    }
    if(picked)return picked;
    // Only the caller's explicit, labelled reference-calculation assumptions
    // may bridge units. They never affect receipt estimates or stock rules.
    for(const measurement of Array.isArray(measurements)?measurements:[]){
      if(!record(measurement)||!text(measurement.name)||!J.same(name,measurement.name)||!text(measurement.label))continue;
      const from=J.parseQuantity(measurement.fromQuantity),to=J.parseQuantity(measurement.toQuantity);
      if(!from||!to||from.baseAmount<=0||to.baseAmount<=0)continue;
      for(const option of options){
        if(option.parsed.baseUnit!==from.baseUnit)continue;
        const needed=round(option.needed/from.baseAmount*to.baseAmount);
        if(!Number.isFinite(needed)||needed<=0)continue;
        for(const quote of quotes){
          if(quote.baseUnit===to.baseUnit&&J.same(name,quote.name)&&newer(quote,picked?.quote))
            picked={quote,option:{parsed:to,needed,usedQuantity:J.formatQuantity(needed,to)},
              sourceKind:'reference',assumption:measurement.label};
        }
      }
    }
    return picked;
  }

  function suggest(recipe,options={}){
    const full=estimate(recipe,options);
    if(full.kind==='entered'||full.kind==='purchase')return {...full,scope:'recipe',excluded:[],assumptions:[],
      rows:full.rows.map(row=>({...row,sourceKind:'purchase',usedQuantity:row.required,assumption:null}))};
    const {day,portions=1,reference}=options||{},flow=record(options?.flow)?options.flow:{};
    const safe=safeRecipe(recipe),primary=[...safe.f,...safe.p].filter((name,index,list)=>!list.slice(0,index).some(old=>J.same(old,name)));
    const excluded=safe.s.filter((name,index,list)=>!list.slice(0,index).some(old=>J.same(old,name)));
    if(!primary.length)return {...full,scope:'recipe',excluded:[],assumptions:[]};
    const main=primary.filter(name=>!excluded.some(spice=>J.same(spice,name)));
    const amounts=Object.fromEntries(Object.entries(safe.amounts).filter(([name])=>main.some(primaryName=>J.same(primaryName,name))));
    const demands=J.recipeAvailability({amounts,f:main,s:[],p:[]},{items:[]},{day,portions}).rows;
    const purchases=receiptQuotes(flow,day),references=referenceQuotes(reference,day),rows=[],missing=[],sources=[],seen=new Set(),assumptions=[];
    for(const demand of demands){
      const raw=Object.entries(amounts).find(([name])=>J.same(name,demand.name))?.[1];
      const quantities=quantityOptions(raw,portions);
      const picked=selectPurchase(purchases,demand.name,quantities)||
        selectReference(references,demand.name,quantities,reference?.measurements);
      const row={name:demand.name,required:demand.required,usedQuantity:null,cost:null,source:null,sourceKind:null,
        day:null,quantity:null,itemId:null,unitPrice:null,baseUnit:null,assumption:null,receiptAdjusted:false,receiptUnreconciled:false};
      let reason=quantities.length?'가격·수량이 확인된 구매 내역이나 같은 단위의 참고 단가가 없어요.':'필요량의 숫자·단위를 확인해 주세요.';
      if(picked){
        const {quote,option,sourceKind,assumption}=picked,value=quote.unitPrice*option.needed;
        if(Number.isFinite(value)&&value<=Number.MAX_SAFE_INTEGER){
          Object.assign(row,{cost:round(value),usedQuantity:option.usedQuantity,source:copied(quote.source),sourceKind,
            day:quote.day,quantity:quote.quantity,itemId:quote.itemId??null,unitPrice:quote.unitPrice,
            baseUnit:option.parsed.baseUnit,assumption,receiptAdjusted:quote.receiptAdjusted||false,
            receiptUnreconciled:quote.receiptUnreconciled||false});
          const key=sourceKind+'|'+(sourceKind==='purchase'?quote.source+'|'+quote.itemId:quote.itemIndex);
          if(!seen.has(key)){
            seen.add(key);
            sources.push(sourceKind==='purchase'?{kind:'purchase',expenseId:quote.source,itemId:quote.itemId,purchaseId:quote.purchaseId,
              day:quote.day,name:quote.name,quantity:quote.quantity,amount:quote.amount,baseUnit:quote.baseUnit,unitPrice:quote.unitPrice,
              receiptAmount:quote.receiptAmount,itemAmountsTotal:quote.itemAmountsTotal,
              adjustmentUnallocated:quote.receiptAdjusted,unreconciled:quote.receiptUnreconciled}:
              {kind:'reference',day:quote.day,name:quote.name,quantity:quote.quantity,amount:quote.amount,
                baseUnit:quote.baseUnit,unitPrice:quote.unitPrice,product:quote.product,source:copied(quote.source),samples:copied(quote.samples)});
          }
          if(assumption&&!assumptions.includes(assumption))assumptions.push(assumption);
          reason='';
        }else reason='계산할 금액의 범위를 확인해 주세요.';
      }
      rows.push(row);
      if(reason)missing.push({name:demand.name,required:demand.required,reason});
    }
    const priced=rows.filter(row=>row.cost!==null),sum=priced.reduce((total,row)=>total+row.cost,0);
    const safeSum=Number.isFinite(sum)&&sum<=Number.MAX_SAFE_INTEGER;
    const knownSubtotal=priced.length&&safeSum?round(sum):null,complete=rows.length>0&&missing.length===0&&safeSum;
    if(!safeSum)missing.push({name:'주재료비',required:'금액 확인',reason:'계산할 금액의 범위를 확인해 주세요.'});
    const kinds=new Set(priced.map(row=>row.sourceKind));
    const kind=complete?(kinds.size>1?'mixed':kinds.has('reference')?'reference':'purchase'):priced.length&&safeSum?'partial':'unknown';
    let basisNote=(priced.length?'주재료만 계산한 사용분 예상이에요.':'확인된 주재료 가격이 없어 예상 금액을 계산하지 않았어요.')+
      ' 양념'+(excluded.length?'('+excluded.join('·')+')':'')+'은 합계에서 제외하며 실제 구매 지출과 별도예요.';
    if(kinds.has('reference'))basisNote+=' 참고 단가는 실시간 가격이나 사용자의 실제 구매 가격이 아니에요.';
    if(priced.length&&!complete)basisNote+=' 가격을 확인하지 못한 주재료는 부분 합계에 포함하지 않았어요.';
    if(!safeSum)basisNote+=' 계산할 금액의 범위를 확인해 주세요.';
    if(assumptions.length)basisNote+=' 표시된 단위 환산은 참고 비용을 위한 계산 가정이며 실제 관측값이 아니에요.';
    if(sources.some(source=>source.adjustmentUnallocated))basisNote+=' 품목 합계와 실제 결제 금액의 차이(할인·추가금)는 재료별로 배분하지 않았어요.';
    if(sources.some(source=>source.unreconciled))basisNote+=' 품목 금액이 모두 확인되지 않아 실제 결제 합계와 대조하지 못한 구매 내역이 있어요.';
    const referenceDays=[...new Set(sources.filter(source=>source.kind==='reference').map(source=>source.day))].sort();
    return {kind,scope:'main',total:complete?knownSubtotal:null,knownSubtotal,missing,rows,sources,excluded,assumptions,basisNote,
      referenceDays,...(referenceDays.length===1?{referenceDay:referenceDays[0]}:{})};
  }
  return Object.freeze({estimate,suggest});
});
