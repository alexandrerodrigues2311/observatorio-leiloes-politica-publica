from pathlib import Path
import urllib.request,json,hashlib,datetime,concurrent.futures
R=Path(__file__).resolve().parents[1]/'data/expansion/raw';R.mkdir(parents=True,exist_ok=True)
sources={
 'sgb_layers.json':'https://geoportal.sgb.gov.br/server/rest/services/geologia/ocorrencias/MapServer/layers?f=pjson',
 'sgb_infra_layers.json':'https://geoportal.sgb.gov.br/server/rest/services/dados_plataforma/plataforma_economia_mineral/MapServer/layers?f=pjson',
 'pnomce.html':'https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/lei/l15506.htm',
 'cimce.html':'https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d13118.htm',
 'codigo.html':'https://www.planalto.gov.br/ccivil_03/decreto-lei/del0227.htm',
 'air.html':'https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/decreto/d10411.htm',
 'processo_administrativo.html':'https://www.planalto.gov.br/ccivil_03/leis/l9784.htm',
 'dou_20220530_104.pdf':'https://pesquisa.in.gov.br/imprensa/servlet/INPDFViewer?captchafield=firstAccess&data=30%2F05%2F2022&jornal=515&pagina=104',
 'dou_20221207_154.pdf':'https://pesquisa.in.gov.br/imprensa/servlet/INPDFViewer?captchafield=firstAccess&data=07%2F12%2F2022&jornal=515&pagina=154',
 'alvara_salinas.pdf':'https://www.gov.br/anm/pt-br/assuntos/exploracao-mineral/titulos-minerarios/alvara-de-pesquisa/2021/8223-a-8256-60213-alv-529mg.pdf',
 'licenca_salinas.pdf':'https://sistemas.meioambiente.mg.gov.br/licenciamento/uploads/GuKJRHhCzE9JdvA9_lWIcMVxyv9DiK3X.pdf'
}
def get(kv):
 name,url=kv
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=55) as res:b=res.read()
  (R/name).write_bytes(b)
  return {'file':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'pdf_valid_magic':b.startswith(b'%PDF') if name.endswith('.pdf') else None}
 except Exception as e:return {'file':name,'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(get,sources.items()))
(R/'sources_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
for x in rows:print(x['file'],x.get('bytes',x.get('error')),x.get('pdf_valid_magic',''))
