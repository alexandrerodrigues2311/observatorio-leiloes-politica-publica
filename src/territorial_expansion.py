"""Exact portfolio geometry operations; simplified geometries are display-only."""
from pathlib import Path
import sys,json,csv,zipfile,io,re,hashlib,collections,unicodedata,logging
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'tmp/geo-libs'))
import shapefile,shapely
from shapely.geometry import shape,mapping,Point
from shapely.ops import transform,unary_union
from shapely import STRtree,make_valid
from pyproj import Transformer,Geod
logging.getLogger('shapefile').setLevel(logging.ERROR)
D=R/'data/expansion';RAW=D/'raw';D.mkdir(exist_ok=True)
def save(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf8')
def fold(s):return ''.join(c for c in unicodedata.normalize('NFKD',str(s)) if not unicodedata.combining(c)).upper()
def proc(s):
 m=re.fullmatch(r'(\d{1,6})/(\d{4})',str(s).replace('.','').strip())
 return m[1].zfill(6)[:3]+'.'+m[1].zfill(6)[3:]+'/'+m[2] if m else ''
rows=list(csv.DictReader((R/'data/complete/stock_process_audit.csv').open(encoding='utf-8-sig'),delimiter=';'))
stock={r['process']:r for r in rows if r['sople']=='Apta para Disponibilidade' or (r['active']=='True' and r['phase'] in ['8','15'])}
assert len(stock)==30861
cfg=json.loads((R/'data/complete/mineral_config.json').read_bytes())
def minerals(s):
 f=fold(s);out={m for m,terms in cfg['tokens'].items() if any(re.search(r'\b'+fold(t)+r'\b',f) for t in terms)}
 if 'COLUMBITA' in f:out.add('nióbio')
 return out
def reader(file,stem):
 z=zipfile.ZipFile(RAW/file)
 return z,shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),shx=io.BytesIO(z.read(stem+'.shx')),dbf=io.BytesIO(z.read(stem+'.dbf')),encoding='utf8')
forward=Transformer.from_crs('EPSG:4674','+proj=laea +lat_0=-15 +lon_0=-54 +ellps=GRS80 +units=m +no_defs',always_xy=True).transform
reverse=Transformer.from_crs('+proj=laea +lat_0=-15 +lon_0=-54 +ellps=GRS80 +units=m +no_defs','EPSG:4674',always_xy=True).transform
geod=Geod(ellps='GRS80')
def polygon(g):
 if not g.is_valid:g=make_valid(g)
 if g.geom_type in ['Polygon','MultiPolygon']:return g
 if hasattr(g,'geoms'):return unary_union([p for p in g.geoms if p.geom_type in ['Polygon','MultiPolygon']])
 return None
z,s=reader('SIGMINE_BRASIL.zip','BRASIL');seen=collections.defaultdict(list);metadata={};invalid=0;empty=0
for i,rec in enumerate(s.iterRecords(fields=['PROCESSO','AREA_HA','FASE','SUBS','UF'])):
 r=rec.as_dict();key=proc(r['PROCESSO'])
 if key not in stock:continue
 g=shape(s.shape(i).__geo_interface__)
 if not g.is_valid:invalid+=1
 g=polygon(g)
 if g is None or g.is_empty:empty+=1;continue
 pg=polygon(transform(forward,g))
 if pg is None or pg.is_empty:empty+=1;continue
 seen[key].append(pg);metadata[key]={'sigmine_phase':r['FASE'],'sigmine_substance':r['SUBS'],'sigmine_uf':r['UF'],'area_declared_ha':float(r['AREA_HA'] or 0)}
geoms={k:unary_union(gs) for k,gs in seen.items()};print('matched',len(geoms),'invalid repaired',invalid,flush=True)
zb,b=reader('BLOQUEIO.zip','BLOQUEIO');blocks=[];blockmeta=[]
for sr in b.iterShapeRecords():
 g=polygon(shape(sr.shape.__geo_interface__))
 if g is None or g.is_empty:continue
 blocks.append(polygon(transform(forward,g)));blockmeta.append({k:str(v) for k,v in sr.record.as_dict().items()})
bt=STRtree(blocks);geo_context=json.loads((RAW/'sgb_occurrences.json').read_bytes()) if (RAW/'sgb_occurrences.json').exists() else {}
points=[];pointmeta=[]
if geo_context.get('exceededTransferLimit'):raise RuntimeError('SGB truncated')
for feat in geo_context.get('features',[]):
 if not feat.get('geometry'):continue
 g=shape(feat['geometry'])
 if g.geom_type!='Point' or g.is_empty:continue
 points.append(transform(forward,g));pointmeta.append(feat['properties'])
pt=STRtree(points) if points else None
power=json.loads((RAW/'sgb_power.json').read_bytes()) if (RAW/'sgb_power.json').exists() else {};power_complete=bool(power.get('features')) and not power.get('exceededTransferLimit')
powergeoms=[transform(forward,shape(f['geometry'])) for f in power.get('features',[]) if f.get('geometry')] if power_complete else []
power_tree=STRtree(powergeoms) if powergeoms else None
audit=[];features=[]
for k,r in stock.items():
 row={k2:r[k2] for k2 in ['process','sople','phase_name','state','city','minerals','age_days','apt_conflict']}
 row.update({'geometry':k in geoms,'area_ha':None,'block_ha':None,'block_count':None,'occurrences_inside':None,'same_mineral_inside':None,'nearest_occurrence_km':None,'power_distance_km':None})
 if k in geoms:
  g=geoms[k];matches=bt.query(g,predicate='intersects');ints=[g.intersection(blocks[int(i)]) for i in matches];blocked=unary_union(ints) if ints else None
  blockha=blocked.area/10000 if blocked is not None else 0
  ids=pt.query(g,predicate='covers').tolist() if pt is not None else []
  mset=set(r['minerals'].split(' | '))-{''};same=[i for i in ids if mset & minerals(pointmeta[i].get('SUBSTANCIAS',''))]
  nearest=float(g.distance(points[int(pt.nearest(g))])/1000) if pt is not None else None
  pd=float(g.distance(powergeoms[int(power_tree.nearest(g))])/1000) if power_tree is not None else None
  row.update(metadata[k]);row.update({'area_ha':g.area/10000,'block_ha':blockha,'block_count':sum(x.area>100 for x in ints),'occurrences_inside':len(ids),'same_mineral_inside':len(same),'nearest_occurrence_km':nearest,'power_distance_km':pd,'geological_ids':[pointmeta[i].get('ID_OCORRENCIA') for i in same],'block_categories':sorted({blockmeta[int(i)].get('CATEGORIA','') for i in matches if g.intersection(blocks[int(i)]).area>100})})
  display=transform(reverse,g.simplify(100,preserve_topology=True));c=transform(reverse,g.representative_point())
  row.update({'lon':c.x,'lat':c.y})
  features.append({'type':'Feature','properties':{'process':k,'apt':r['sople']=='Apta para Disponibilidade','strategic':bool(r['minerals']),'block':blockha>.01,'same_mineral':len(same),'area_ha':round(row['area_ha'],2)},'geometry':mapping(display)})
 audit.append(row)
lookup={r['process']:r for r in audit}
groups={'union':list(stock),'scm_active':[k for k,r in stock.items() if r['active']=='True' and r['phase'] in ['8','15']],'sople_apt':[k for k,r in stock.items() if r['sople']=='Apta para Disponibilidade'],'strategic_apt':[k for k,r in stock.items() if r['sople']=='Apta para Disponibilidade' and r['minerals']]}
summary={}
for label,keys in groups.items():
 gs=[geoms[k] for k in keys if k in geoms];u=unary_union(gs);idx=bt.query(u,predicate='intersects');blockunion=unary_union([u.intersection(blocks[int(j)]) for j in idx]) if len(idx) else None
 summa=sum(g.area for g in gs)/10000;area=u.area/10000;over=blockunion.area/10000 if blockunion is not None else 0
 summary[label]={'records':len(keys),'matched':len(gs),'missing':len(keys)-len(gs),'coverage':len(gs)/len(keys),'sum_process_ha':summa,'union_ha':area,'duplicate_coverage_ha':summa-area,'block_union_ha':over,'outside_block_layer_ha':area-over,'processes_block_overlap':sum((lookup[k]['block_ha'] or 0)>.01 for k in keys),'same_mineral_occurrence':sum((lookup[k]['same_mineral_inside'] or 0)>0 for k in keys)}
 print(label,summary[label],flush=True)
bymineral={}
for m in cfg['tokens']:
 rr=[x for x in audit if x['sople']=='Apta para Disponibilidade' and m in x['minerals'].split(' | ')]
 if not rr:continue
 bymineral[m]={'records':len(rr),'matched':sum(x['geometry'] for x in rr),'with_block':sum((x['block_ha'] or 0)>.01 for x in rr),'with_same_mineral_evidence':0,'over730':sum(int(x['age_days'] or 0)>730 for x in rr),'area_ha':sum(x['area_ha'] or 0 for x in rr)}
 # Match the specific mineral, not any other substance in a multi-mineral process.
 for x in rr:
  if x['process'] in geoms and pt is not None:
   ii=pt.query(geoms[x['process']],predicate='covers')
   bymineral[m]['with_same_mineral_evidence']+=int(any(m in minerals(pointmeta[int(i)].get('SUBSTANCIAS','')) for i in ii))
# Spatial QA uses undensified geodesic polygon edges as an independent approximation.
checks=[]
for k in sorted(geoms)[::max(1,len(geoms)//100)][:100]:
 g=geoms[k];back=transform(reverse,g);ga=abs(geod.geometry_area_perimeter(shapely.orient_polygons(back))[0]);checks.append(abs(ga-g.area)/max(1,ga))
report={'date':'2026-10-03','sigmine_shape_date':z.getinfo('BRASIL.shp').date_time,'block_shape_date':zb.getinfo('BLOQUEIO.shp').date_time,'source_records':len(s),'block_features':len(blocks),'geological_points':len(points),'projection':'LAEA GRS80 centered at 15S 54W; area in hectares','display_simplification_m':100,'invalid_repaired':invalid,'empty_excluded':empty,'duplicate_process_geometries':sum(len(v)>1 for v in seen.values()),'groups':summary,'minerals':bymineral,'power_layer_usable':power_complete,'qa_geodesic_relative_max':max(checks,default=None),'qa_geodesic_relative_median':float(np.median(checks)) if checks else None,'sources':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in RAW.glob('*.zip')],'scope':'Spatial screening. Not certification of availability, reserves, legal impediment or infrastructure capacity.'}
assert all(v['union_ha']<=v['sum_process_ha']+1 and v['block_union_ha']<=v['union_ha']+1 for v in summary.values())
save('territorial_results.json',report);save('territorial_audit.json',audit);save('stock_polygons.geojson',{'type':'FeatureCollection','features':features})
save('stock_missing_geometry.json',[r for r in audit if not r['geometry']])
print('saved',len(audit),len(features),flush=True)
