(async () => {
  const status = document.querySelector('#chart-status');
  const format = value => new Intl.NumberFormat(({GBP:'en-GB',USD:'en-US',INR:'en-IN'})[document.body.dataset.currency], {style:'currency',currency:document.body.dataset.currency}).format(value / 100);
  try {
    const response = await fetch('/api/charts?month=' + encodeURIComponent(status.dataset.month));
    if (!response.ok) throw new Error('Chart data unavailable');
    const data = await response.json();
    const colors = ['#E78B45','#A73514','#D4AE91','#8F6A58','#F5E9DD','#785348','#BE7149','#AF9F82','#69483C'];
    const breakdown = document.querySelector('#category-breakdown'); breakdown.replaceChildren();
    const total = data.categories.values.reduce((a,b)=>a+b,0);
    if (!total) { const p=document.createElement('p'); p.className='empty'; p.textContent='No spending this month. Add an expense to see category insights.'; breakdown.append(p); }
    data.categories.labels.forEach((label,index)=>{
      const row=document.createElement('div'); row.className='category-row';
      const top=document.createElement('div'); const name=document.createElement('span'); name.textContent=label;
      const amount=document.createElement('strong'); amount.textContent=format(data.categories.values[index]);
      top.append(name,amount); const track=document.createElement('div'); track.className='progress';
      const fill=document.createElement('span'); fill.style.width=(100*data.categories.values[index]/total)+'%'; fill.style.background=colors[index%colors.length];
      track.append(fill); row.append(top,track); breakdown.append(row);
    });
    if (typeof Chart === 'undefined') throw new Error('Chart library unavailable. Category totals remain available.');
    Chart.defaults.color='#B8AAA1'; Chart.defaults.borderColor='rgba(245,233,221,.07)'; Chart.defaults.font.family='Segoe UI, sans-serif';
    const options = () => ({responsive:true,maintainAspectRatio:false,animation:!matchMedia('(prefers-reduced-motion: reduce)').matches,plugins:{legend:{position:'bottom',labels:{usePointStyle:true,padding:20,boxWidth:7}},tooltip:{callbacks:{label:ctx=>`${ctx.dataset.label || ctx.label}: ${format(ctx.parsed.y ?? ctx.parsed)}`}}},scales:{x:{grid:{display:false}},y:{beginAtZero:true,ticks:{callback:value=>format(value)}}}});
    new Chart(document.querySelector('#trendChart'),{type:'line',data:{labels:data.daily.labels,datasets:[{label:'Income',data:data.daily.income,borderColor:'#D4AE91',backgroundColor:'rgba(212,174,145,.06)',fill:true,tension:.35,pointRadius:3},{label:'Expenses',data:data.daily.expense,borderColor:'#E78B45',backgroundColor:'rgba(231,139,69,.08)',fill:true,tension:.35,pointRadius:3}]},options:options()});
    new Chart(document.querySelector('#categoryChart'),{type:'doughnut',data:{labels:data.categories.labels,datasets:[{data:data.categories.values,backgroundColor:colors,borderWidth:3,borderColor:'#1c1511',hoverOffset:7}]},options:{responsive:true,maintainAspectRatio:false,animation:!matchMedia('(prefers-reduced-motion: reduce)').matches,cutout:'74%',plugins:{legend:{position:'bottom',labels:{usePointStyle:true,boxWidth:7,padding:15}},tooltip:{callbacks:{label:ctx=>ctx.label+': '+format(ctx.parsed)}}}}});
    new Chart(document.querySelector('#monthlyChart'),{type:'bar',data:{labels:data.monthly.labels,datasets:[{label:'Income',data:data.monthly.income,backgroundColor:'#D4AE91',borderRadius:5},{label:'Expenses',data:data.monthly.expense,backgroundColor:'#A73514',borderRadius:5}]},options:options()});
    status.textContent = !total ? 'No expenses in this month. Charts update as you add transactions.' : data.daily.labels.length === 1 ? 'All entries are on one date. Add transactions on another date to see a daily trend.' : '';
  } catch (error) { status.textContent='Unable to load charts. '+error.message+' Refresh to retry.'; status.className='notice error'; }
})();
