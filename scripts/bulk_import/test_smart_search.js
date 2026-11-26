'use strict';
const assert=require('node:assert/strict');
const {search}=require('../../assets/smart-search.js');
const now=Date.parse('2026-11-26T20:00:00+05:30');
const base={verified:true,category:'latest-jobs',startDate:'2026-11-20',deadline:'2026-12-10T17:00:00+05:30',applyUrl:'https://example.gov.in/'};
const rows=[
 {...base,id:'twelve',title:'Clerk',qualification:'10+2'},
 {...base,id:'graduate',title:'Officer',qualification:'Graduate'},
 {...base,id:'old',title:'Clerk',qualification:'12th',deadline:'2026-11-25T17:00:00+05:30'},
 {...base,id:'future',title:'Clerk',qualification:'12th',startDate:'2026-12-01'},
 {...base,id:'pending',title:'Clerk',qualification:'12th',verificationPending:true},
 {verified:true,id:'scheme',category:'yojana',title:'PM Kisan',benefit:'Farmer support'},
 {verified:true,id:'result',category:'results',title:'Exam result',deadline:'Declared 26 Nov 2026'}
];
assert.deepEqual(search(rows,'12वीं पास सरकारी नौकरी','','open',now).map(x=>x.id),['twelve']);
assert.deepEqual(search(rows,'किसान योजना','','',now).map(x=>x.id),['scheme']);
assert.deepEqual(search(rows,'result','','',now).map(x=>x.id),['result']);
assert.deepEqual(search(rows,'graduate jobs','','',now).map(x=>x.id),['graduate']);
console.log('4 smart search checks passed');
