from pathlib import Path
import json,csv,io,gzip,base64,hashlib,shutil
R=Path(__file__).resolve().parents[1];N=R/'notebooks/Observatorio_Leiloes_PP_reproducao.ipynb'
nb=json.loads(N.read_text(encoding='utf8'))
# Idempotent replacement of this expansion only.
idx=next((i for i,c in enumerate(nb['cells']) if ''.join(c['source']).startswith('## 5. Ampliação territorial')),len(nb['cells']))
nb['cells']=nb['cells'][:idx]
def md(s):nb['cells'].append(dict(cell_type='markdown',metadata={},source=s.splitlines(True)))
def code(s):nb['cells'].append(dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=s.splitlines(True)))
scripts={n:(R/'src'/n).read_text(encoding='utf8') for n in ['statistics_pp.py','territorial_expansion.py','statistical_expansion.py','evaluate_audit.py']}
# Safe analytical inputs. Winner names are not needed by these routines.
rows=list(csv.DictReader((R/'data/complete/award_analysis.csv').open(encoding='utf-8-sig'),delimiter=';'))
fields=[k for k in rows[0] if k!='winner'];out=io.StringIO();w=csv.DictWriter(out,fields,delimiter=';');w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
inputs={'data/complete/award_analysis.csv':out.getvalue()}
for p in ['data/complete/stock_process_audit.csv','data/complete/mineral_config.json','data/complete/results.json','site/inventory.json']:
 inputs[p]=(R/p).read_text(encoding='utf-8-sig')
payload=base64.b64encode(gzip.compress(json.dumps(inputs,ensure_ascii=False).encode(),mtime=0)).decode()
md('## 5. Ampliação territorial e estatística de 03/10/2026\n\nEsta seção reproduz os cruzamentos e diagnósticos da revisão 4. Contém insumos analíticos sem nomes de vencedores ou identificadores fiscais pessoais. As geometrias originais devem corresponder aos hashes preservados. As rotinas foram executadas localmente; este caderno não declara execução na nuvem. A revisão humana e o piloto de campo não foram realizados.\n\nInstale as dependências antes de executar. O processamento espacial usa memória substancial. A falha de uma fonte ou uma mudança de hash deve ser investigada, não ignorada.')
code("subprocess.run([sys.executable, '-m', 'pip', 'install', 'numpy', 'scipy', 'statsmodels', 'shapely>=2.1', 'pyproj', 'pyshp'], check=True)\n")
code('EXPANSION_SCRIPTS = '+repr(scripts)+'\nfor name, source in EXPANSION_SCRIPTS.items():\n    (ROOT/"src"/name).write_text(source, encoding="utf8")\nPACKED_INPUTS = '+repr(payload)+'\nfor name, content in json.loads(gzip.decompress(base64.b64decode(PACKED_INPUTS))).items():\n    p=ROOT/name\n    p.parent.mkdir(parents=True,exist_ok=True)\n    p.write_text(content,encoding="utf-8-sig" if p.suffix==".csv" else "utf8")\n')
sources=[]
urls={'SIGMINE_BRASIL.zip':'https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/BRASIL.zip','BLOQUEIO.zip':'https://dadosabertos.anm.gov.br/SIGMINE/BLOQUEIO.zip','sgb_occurrences.json':'https://geoportal.sgb.gov.br/server/rest/services/geologia/ocorrencias/MapServer/0/query?where=1%3D1&outFields=OBJECTID%2CID_OCORRENCIA%2CSTATUS_ECONOMICO%2CSUBSTANCIAS%2CPROJETO%2CDATA_CADASTRO%2CMETODO_GEOPOSICIONAMENTO&returnGeometry=true&outSR=4674&f=geojson'}
for name,url in urls.items():sources.append(dict(file=name,url=url,sha256=hashlib.sha256((R/'data/expansion/raw'/name).read_bytes()).hexdigest()))
code('GEO_MANIFEST = '+repr(sources)+'\nPERMITIR_NOVA_EXTRAÇÃO_ESPACIAL = False\nfor item in GEO_MANIFEST:\n    p=ROOT/"data/expansion/raw"/item["file"]\n    p.parent.mkdir(parents=True,exist_ok=True)\n    if not p.exists():\n        req=urllib.request.Request(item["url"],headers={"User-Agent":"Mozilla/5.0"})\n        with urllib.request.urlopen(req,timeout=240) as res, p.open("wb") as dst:\n            import shutil\n            shutil.copyfileobj(res,dst)\n    equal=hashlib.sha256(p.read_bytes()).hexdigest()==item["sha256"]\n    print(item["file"], "idêntico" if equal else "diferente")\n    if not equal and not PERMITIR_NOVA_EXTRAÇÃO_ESPACIAL:\n        raise RuntimeError("Fonte alterada. Use o arquivo preservado para reproduzir os resultados publicados.")\n')
code('for script in ["territorial_expansion.py","statistical_expansion.py"]:\n    subprocess.run([sys.executable,str(ROOT/"src"/script)],cwd=ROOT,check=True)\nprint("Resultados em",ROOT/"data/expansion")\n')
md('## 6. Revisão documental e uso responsável\n\nOs arquivos audit_stock_sample.csv e audit_cession_sample.csv contêm o sorteio, os estratos e os pesos. Os campos de revisão ficam vazios. A rotina evaluate_audit.py recusa estimar erro enquanto a revisão estiver incompleta. Dois revisores devem registrar fonte, data, conclusão e justificativa.\n\nA taxa de erro não foi medida. As ocorrências geológicas não certificam reservas. A ausência de bloqueio na camada não certifica área livre. O modelo financeiro tem desempenho temporal limitado. Os cálculos de poder dimensionam hipóteses de um piloto ainda não executado.')
code('subprocess.run([sys.executable,str(ROOT/"src/evaluate_audit.py"),str(ROOT/"data/expansion/audit_stock_sample.csv")],check=True)\n')
for c in nb['cells']:
 if c['cell_type']=='code':compile(''.join(c['source']),'<cell>','exec')
N.write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf8')
(R/'data/expansion/geo_input_manifest.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf8')
print('Notebook syntax verified',N.stat().st_size,'bytes')
