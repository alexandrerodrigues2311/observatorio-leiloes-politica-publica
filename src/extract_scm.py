"""Extrato independente PP. Identificadores pessoais não são exportados ao painel."""
from pathlib import Path
import csv,io,zipfile,json,re,sys,collections,unicodedata
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]; D=json.loads((R/'data/raw/analitico_preservado.json').read_text(encoding='utf-8'))
def proc(s):
 s=str(s).strip().replace('.','');m=re.fullmatch(r'(\d{1,6})/(\d{4})',s)
 if not m:return ''
 a=m[1].zfill(6);return a[:3]+'.'+a[3:]+'/'+m[2]
def fold(s):return ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c)).upper()
z=zipfile.ZipFile(R/'data/raw/scm.zip')
def rows(n):
 path=next(x for x in z.namelist() if x.replace('\\','/').split('/')[-1]==n+'.txt')
 with io.TextIOWrapper(z.open(path),encoding='cp1252',errors='replace',newline='') as f:
  yield from csv.DictReader(f,delimiter=';')
events={r['IDEvento']:r['DSEvento'] for r in rows('Evento')}
types={r['IDTipoAssociacao']:r['DSTipoAssociacao'] for r in rows('TipoAssociacao')}
phase={r['IDFaseProcesso']:r['DSFaseProcesso'] for r in rows('FaseProcesso')}
origins={r['origem'] for r in D['rows']}|{r['origin'] for r in D['socialRound6']['inventory']}
offers=list(csv.DictReader((R/'data/raw/ResultadoRodadaDisponibilidade.csv').open(encoding='utf-8-sig'),delimiter=';'))
origins|={proc(r['ProcessoMinerario']) for r in offers};origins.discard('')
graph=collections.defaultdict(list)
for r in rows('ProcessoAssociacao'):
 a,b=proc(r['DSProcesso']),proc(r['DSProcessoAssociado'])
 if a and b and a!=b:graph[a].append({'source':a,'target':b,'type':r['IDTipoAssociacao'],'date':r['DTAssociacao'][:10],'end':r['DTDesassociacao'][:10]})
seen=set(origins);q=collections.deque(origins);links=[]
while q:
 a=q.popleft()
 for e in graph[a]:
  # Encadeamento explícito de disponibilidade, cessão parcial, desmembramento e mudança de regime.
  if e['type'] not in ['2','3','8','9']:continue
  links.append(e)
  if e['target'] not in seen:seen.add(e['target']);q.append(e['target'])
print('origens/processos/links',len(origins),len(seen),len(links),flush=True)
P={};stock=collections.Counter();stock_processes={}
for r in rows('Processo'):
 stock[r['IDFaseProcesso']]+=1
 p=proc(r['DSProcesso'])
 if r['IDFaseProcesso'] in ['8','15']:stock_processes[p]=r
 if p in seen:P[p]=r
people=collections.defaultdict(list);ids=set()
for r in rows('ProcessoPessoa'):
 p=proc(r['DSProcesso'])
 if p in seen and r['IDTipoRelacao'] in ['1','10']:
  people[p].append({'id':r['IDPessoa'],'role':r['IDTipoRelacao'],'start':r['DTInicioVigencia'][:10],'end':r['DTFimVigencia'][:10]});ids.add(r['IDPessoa'])
names={}
for r in rows('Pessoa'):
 if r['IDPessoa'] in ids:names[r['IDPessoa']]={'name':r['NMPessoa'],'type':r['TPPessoa']}
ev=collections.defaultdict(list);bad=0;total=0;stock_events=collections.defaultdict(list)
stock_codes={k for k,v in events.items() if any(s in fold(v) for s in ['DISPONIB','RENUNCIA','CADUCIDADE','INDEF','RECURSO','DESONER','S/EFEITO','AREA LIVRE'])}
for r in rows('ProcessoEvento'):
 total+=1;p=proc(r['DSProcesso'])
 if p not in seen and p not in stock_processes:continue
 if None in r or any(v is None for v in r.values()):bad+=1;continue
 if r['DTEvento'][:10]>'2026-10-02':continue
 if p in stock_processes and r['IDEvento'] in stock_codes:stock_events[p].append({'code':r['IDEvento'],'date':r['DTEvento'][:10]})
 if p not in seen:continue
 # Texto documental fica no extrato local, não é publicado sem revisão.
 ev[p].append({'code':r['IDEvento'],'date':r['DTEvento'][:10],'note':r['OBEvento'],'dou':r['DSPublicacaoDOU']})
 if total%2000000==0:print('eventos percorridos',total,flush=True)
subnames={r['IDSubstancia']:r['NMSubstancia'] for r in rows('Substancia')};subs=collections.defaultdict(list)
for r in rows('ProcessoSubstancia'):
 p=proc(r['DSProcesso'])
 if p in seen:subs[p].append({**r,'name':subnames.get(r['IDSubstancia'],r['IDSubstancia'])})
tax=[]
for code,name in events.items():
 f=fold(name)
 if re.search(r'\bCESSAO\b|\bINCORP|\bFUSAO\b|\bCAUSA MORTIS\b|\bCISAO\b',f):
  stage='outro'
  if any(t in f for t in ['ANULAD','CANCELAD','S/EFEITO','NEGAD','NEGA ','CASSAD','DISTRATO']):stage='reversao_ou_negativa'
  elif 'EFETIV' in f or re.search(r'AVERB(?:AD|$)',f):stage='efetivacao'
  elif 'APROV' in f or 'CADEIA SUCESS' in f:stage='aprovacao'
  elif 'PROTOC' in f:stage='pedido'
  family='cessao_parcial' if 'PARC' in f else 'incorporacao' if 'INCORP' in f else 'fusao' if 'FUSAO' in f else 'sucessao' if 'CAUSA MORTIS' in f else 'cisao' if 'CISAO' in f else 'cessao_total'
  tax.append({'code':code,'label':name,'stage':stage,'family':family})
out={'cutoff':'2026-10-02','zip_dates':{x.filename:str(x.date_time) for x in z.infolist()},'origins':sorted(origins),'links':links,'processes':P,'owners':people,'people':names,'events':ev,'event_names':events,'taxonomy':tax,'substances':subs,'phase_names':phase,'association_types':types,'audit':{'malformed_relevant_events':bad,'all_events':total,'phase_counts':dict(stock)}}
(R/'data/derived/stock_extract.json').write_text(json.dumps({'processes':stock_processes,'events':stock_events,'event_names':events,'phase_names':phase},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(R/'data/derived/scm_extract.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('EXTRAÍDO',len(P),sum(map(len,ev.values())),len(tax),out['audit'])
