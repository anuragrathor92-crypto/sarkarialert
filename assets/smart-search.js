'use strict';
(function () {
  const jobs = new Set(['latest-jobs','10th-iti','outsourcing']);
  const norm = s => String(s ?? '').normalize('NFKC').toLowerCase().replace(/\s+/g,' ').trim();
  const group = [
    [/सरकारी\s*(नौकरी|भर्ती)|sarkari\s*(job|naukri)|government\s*jobs?|\bjobs?\b|भर्ती|नौकरी/gu,'jobs'],
    [/सरकारी\s*योजना|sarkari\s*yojana|\bschemes?\b|योजना/gu,'yojana'],
    [/\bresults?\b|परिणाम|रिजल्ट/gu,'results'],
    [/admit\s*cards?|प्रवेश\s*पत्र|एडमिट\s*कार्ड/gu,'admit-card'],
    [/\badmissions?\b|एडमिशन|दाखिला/gu,'admission'],
    [/scholarships?|छात्रवृत्ति/gu,'scholarship']
  ];
  const quals = [
    [/12\s*(?:वीं|वी|th)|10\s*\+\s*2|इंटरमीडिएट|\bintermediate\b|\b12th\b|बारहवीं|बारहवी/gu,/12\s*(?:वीं|वी|th)|10\s*\+\s*2|इंटरमीडिएट|\bintermediate\b|बारहवीं|\bhsc\b|higher secondary/u],
    [/10\s*(?:वीं|वी|th)|दसवीं|मैट्रिक|\bsslc\b|\bmatric\b/gu,/10\s*(?:वीं|वी|th)|दसवीं|मैट्रिक|\bsslc\b|\bmatric\b/u],
    [/\biti\b|आईटीआई/gu,/\biti\b|आईटीआई/u],
    [/\bdiploma\b|डिप्लोमा/gu,/\bdiploma\b|डिप्लोमा/u],
    [/\bgraduate\b|\bgraduation\b|स्नातक/gu,/\bgraduate\b|\bgraduation\b|स्नातक|\bb\.?a\b|\bb\.?sc\b|\bb\.?com\b|\bb\.?tech\b|\bb\.?e\b|\bdegree\b/u]
  ];
  const synonyms = {'किसान':['farmer','kisan','किसान','कृषि','agriculture'],'रेलवे':['railway','rrb','rrc','रेलवे'],'पुलिस':['police','पुलिस'],'आंगनवाड़ी':['anganwadi','icds','आंगनवाड़ी','आंगनवाडी'],'यूपी':['uttar pradesh','upsssc','uppsc','उत्तर प्रदेश','up'],'एसएससी':['ssc'],'बैंक':['bank','sbi','ibps','बैंक'],'यूपीएससी':['upsc']};
  function current(r, now) {
    if (r.applicationStatus === 'EXPIRED') return false;
    const end=Date.parse(r.deadline || '');
    return !Number.isFinite(end) || end >= now;
  }
  function openWindow(r, now) {
    const start=Date.parse(r.startDate ? r.startDate+'T00:00:00+05:30' : '');
    const end=Date.parse(r.deadline || '');
    return jobs.has(r.category) && Number.isFinite(start) && Number.isFinite(end) && start<=now && now<=end && !r.verificationPending && Boolean(r.applyUrl);
  }
  function search(records, raw, cat, status, now=Date.now()) {
    let q=norm(raw);
    let implicit='';
    for (const [rx,c] of group) {
      const cleaned=q.replace(rx,' ');
      if(cleaned!==q){if(!implicit) implicit=c;q=cleaned;}
    }
    const wanted=[];
    for(const [rx,match] of quals){const cleaned=q.replace(rx,' ');if(cleaned!==q){wanted.push(match);q=cleaned;}}
    const words=q.replace(/पास|योग्यता|चाहिए|बताओ|के लिए|वाली|वाले|\bpass(?:ed)?\b|\bfor\b|\bthe\b|\bfind\b/gu,' ').trim().split(/\s+/).filter(Boolean);
    const category=cat||implicit;
    return records.filter(r=>{
      if(!r.verified || !current(r,now))return false;
      if(category==='jobs'?!jobs.has(r.category):category && r.category!==category)return false;
      if(status==='open'&&!openWindow(r,now))return false;
      if(wanted.length&&!wanted.every(rx=>rx.test(norm(r.qualification))))return false;
      const hay=norm([r.title,r.titleHi,r.department,r.qualification,r.noticeId,r.summary,r.eligibility,r.benefit,r.state,r.stateOrUt,r.theme,r.rows?.flat().join(' ')].filter(Boolean).join(' '));
      return words.every(w=>(synonyms[w]||[w]).some(v=>hay.includes(v)));
    });
  }
  if(typeof module==='object'&&module.exports){module.exports={search,openWindow};return;}
  const form=document.getElementById('smart-form');if(!form)return;
  const summary=document.getElementById('smart-summary'),list=document.getElementById('smart-results'),more=document.getElementById('smart-more');
  let records=[],matched=[],shown=0,ready=false;
  const el=(tag,value)=>{const n=document.createElement(tag);n.textContent=value;return n;};
  function appendResults(){
    for(const r of matched.slice(shown,shown+25)){
      const item=el('li',''),h=el('h2',''),a=el('a',r.titleHi||r.title);
      if(!/^[a-z0-9][a-z0-9-]{1,100}$/.test(r.id))continue;
      a.href='../posts/'+r.id+'/';h.append(a);item.append(h);
      item.append(el('p',[r.department,r.category].filter(Boolean).join(' · ')));
      const info=[r.vacancies!=null?'पद: '+r.vacancies:'',r.qualification?'योग्यता: '+r.qualification:'',r.lastDate?'अंतिम तिथि: '+r.lastDate:'',r.verifiedOn?'स्रोत समीक्षा: '+r.verifiedOn:''].filter(Boolean);
      if(info.length)item.append(el('p',info.join(' | ')));
      if(r.verificationPending)item.append(el('p','आवेदन / बाहरी लिंक की पुष्टि लंबित है।'));
      if(r.benefit||r.summary)item.append(el('p',r.benefit||r.summary));
      const detail=el('a','पूरी जानकारी और आधिकारिक लिंक');detail.href=a.href;item.append(detail);list.append(item);
    }
    shown=Math.min(shown+25,matched.length);more.hidden=shown>=matched.length;
  }
  function run(){if(!ready)return;matched=search(records,document.getElementById('smart-query').value,document.getElementById('smart-category').value,document.getElementById('smart-status').value);shown=0;list.replaceChildren();summary.textContent=matched.length+' रिकॉर्ड मिले'+(matched.length?'':' — दूसरे शब्द या श्रेणी से खोजें।');appendResults();}
  form.addEventListener('submit',e=>{e.preventDefault();run();});more.addEventListener('click',appendResults);
  document.getElementById('smart-query').value=(new URLSearchParams(location.search).get('q')||'').slice(0,180);
  fetch('../data/public-search.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(data=>{if(data.schemaVersion!==1||!Array.isArray(data.records))throw new Error('schema');records=data.records;ready=true;run();}).catch(()=>{summary.textContent='Search डेटा अभी उपलब्ध नहीं है। मुख्य वेबसाइट से खोजें।';});
})();
