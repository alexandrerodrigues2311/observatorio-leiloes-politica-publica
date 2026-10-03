from pathlib import Path
import urllib.request,urllib.parse,json,hashlib,concurrent.futures
R=Path(__file__).resolve().parents[1]/'data/expansion/raw'
queries={
'sgb_occurrences.json':('https://geoportal.sgb.gov.br/server/rest/services/geologia/ocorrencias/MapServer/0/query',{'where':'1=1','outFields':'OBJECTID,ID_OCORRENCIA,STATUS_ECONOMICO,SUBSTANCIAS,PROJETO,DATA_CADASTRO,METODO_GEOPOSICIONAMENTO','returnGeometry':'true','outSR':'4674','f':'geojson'}),
'sgb_power.json':('https://geoportal.sgb.gov.br/server/rest/services/dados_plataforma/plataforma_economia_mineral/MapServer/3/query',{'where':'1=1','outFields':'*','returnGeometry':'true','outSR':'4674','f':'geojson'}),
}
def get(kv):
 name,(base,q)=kv;url=base+'?'+urllib.parse.urlencode(q)
 try:
  b=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=100).read();x=json.loads(b);(R/name).write_bytes(b)
  return {'file':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'features':len(x.get('features',[])),'exceeded':x.get('exceededTransferLimit',False),'error':x.get('error')}
 except Exception as e:return {'file':name,'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:rows=list(ex.map(get,queries.items()))
(R/'geo_context_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows,ensure_ascii=True))

