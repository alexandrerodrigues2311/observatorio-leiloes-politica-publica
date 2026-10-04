/* Territorial selections use the same audited rows for map, indicators and export. */
let territorySelection='', territoryPage=0;
const territoryOriginal=territory;
territory=function(){
 territorySelection='';territoryPage=0;mapLayer=null;
 territoryOriginal();
 const filters=app.querySelector('.filters');
 filters.insertAdjacentHTML('beforeend',`<label>Estado<select id="geoState"><option value="">Todos os estados</option></select></label><label>Município<select id="geoCity"><option value="">Todos os municípios</option></select></label><label>Ordenar por<select id="geoSort"><option value="area_ha">Área (ha)</option><option value="age_days">Tempo no estoque</option><option value="block_ha">Interseção com bloqueio (ha)</option><option value="same_mineral_inside">Ocorrências compatíveis</option><option value="process">Processo</option><option value="city">Município</option></select></label><label>Ordem<select id="geoDirection"><option value="desc">Maior para menor / Z–A</option><option value="asc">Menor para maior / A–Z</option></select></label><button id="geoReset">Limpar filtros</button>`);
 $('#geoScope').value='all';
 const options=values=>values.sort((a,b)=>a.localeCompare(b,'pt-BR')).map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
 $('#geoState').insertAdjacentHTML('beforeend',options([...new Set(XA.map(x=>x.state).filter(Boolean))]));
 const cities=()=>{$('#geoCity').innerHTML='<option value="">Todos os municípios</option>'+options([...new Set(XA.filter(x=>!$('#geoState').value||x.state===$('#geoState').value).map(x=>x.city).filter(Boolean))]);};cities();
 ['geoQuery','geoScope','geoEvidence','geoState','geoCity','geoSort','geoDirection'].forEach(id=>$('#'+id).oninput=()=>{if(id==='geoState')cities();territorySelection='';territoryPage=0;geoFilter();});
 $('#geoReset').onclick=()=>territory();
 $('#geoExport').onclick=()=>download(geoSelected(),'selecao-territorial.json');
 app.querySelector('.legend').innerHTML='<button data-evidence="block">🟠 Interseção com bloqueio</button> <button data-evidence="mineral">🔵 Ocorrência compatível (pode coexistir com bloqueio)</button> <button data-evidence="all">🟢 Todas as categorias</button><p>Cor do polígono: âmbar quando há bloqueio; azul quando há ocorrência compatível sem bloqueio; verde nos demais casos. Clique na legenda para filtrar.</p>';
 app.querySelectorAll('[data-evidence]').forEach(b=>b.onclick=()=>{$('#geoEvidence').value=b.dataset.evidence;territorySelection='';territoryPage=0;geoFilter();});
 $('#stockMap').insertAdjacentHTML('beforebegin','<p>Passe o mouse sobre uma área para consultar seus dados. Clique para selecionar a trajetória e atualizar os indicadores e a tabela. Os nomes de estados e municípios aparecem no mapa conforme o zoom. Use os filtros para localizar o território.</p><div id="geoSelection" role="status"></div>');
 geoFilter();
};
geoSelected=function(){
 const value=id=>$('#'+id)?.value||'';
 const q=value('geoQuery').toLocaleLowerCase('pt-BR'),scope=value('geoScope'),e=value('geoEvidence'),state=value('geoState'),city=value('geoCity');
 const rows=XA.filter(x=>(!q||[x.process,x.city,x.state,x.sigmine_substance,x.minerals].join(' ').toLocaleLowerCase('pt-BR').includes(q))&&(!state||x.state===state)&&(!city||x.city===city)&&(scope==='all'||x.sople==='Apta para Disponibilidade'&&(scope==='apt'||!!x.minerals))&&(e==='all'||e==='block'&&x.block_ha>.01||e==='mineral'&&x.same_mineral_inside>0||e==='missing'&&!x.geometry));
 const key=value('geoSort')||'area_ha',direction=value('geoDirection')==='asc'?1:-1;
 rows.sort((a,b)=>{if(['process','city'].includes(key))return direction*String(a[key]||'').localeCompare(String(b[key]||''),'pt-BR',{numeric:true});const av=a[key],bv=b[key];if(av===''||av==null)return bv===''||bv==null?0:1;if(bv===''||bv==null)return -1;return direction*(Number(av)-Number(bv));});
 return territorySelection?rows.filter(x=>x.process===territorySelection):rows;
};
geoFilter=function(){
 if(!$('#geoCount'))return;
 const rows=geoSelected(),ids=new Set(rows.map(x=>x.process));
 $('#geoCount').textContent=fmt(rows.length)+' registros selecionados · '+fmt(rows.filter(x=>x.geometry).length)+' com geometria';
 app.querySelector('.cards').innerHTML=card(fmt(rows.length),'registros na seleção','Filtros territoriais e temáticos',true)+card(fmt(rows.filter(x=>x.geometry).length),'com geometria','Polígonos disponíveis')+card(fmt(rows.filter(x=>x.block_ha>.01).length),'com interseção de bloqueio','Não é decisão jurídica')+card(fmt(rows.filter(x=>x.same_mineral_inside>0).length),'com ocorrência compatível','Não comprova reserva mineral');
 if($('#geoSelection')){$('#geoSelection').innerHTML=territorySelection?`<p>Área selecionada: <b>${esc(territorySelection)}</b> <button id="clearGeoSelection">Voltar ao conjunto filtrado</button></p>`:'';if($('#clearGeoSelection'))$('#clearGeoSelection').onclick=()=>{territorySelection='';geoFilter();};}
 const start=territoryPage*30;
 $('#geoRows').innerHTML=table(['Processo','Estado','Município','Substância SIGMINE','Área ha','Bloqueio ha','Ocorrências compatíveis'],rows.slice(start,start+30).map(x=>[`<button data-process="${esc(x.process)}">${esc(x.process)}</button>`,esc(x.state),esc(x.city),esc(x.sigmine_substance||'Não informada'),x.geometry?fmt(Math.round(x.area_ha)):'Sem geometria',fmt(Math.round(x.block_ha||0)),fmt(x.same_mineral_inside||0)]))+`<p>Página ${territoryPage+1} de ${Math.max(1,Math.ceil(rows.length/30))}. A ordenação considera toda a seleção. <button id="geoPrev" ${!territoryPage?'disabled':''}>Anterior</button> <button id="geoNext" ${start+30>=rows.length?'disabled':''}>Próxima</button></p>`;
 $('#geoPrev').onclick=()=>{territoryPage--;geoFilter();};$('#geoNext').onclick=()=>{territoryPage++;geoFilter();};
 $('#geoRows').querySelectorAll('[data-process]').forEach(b=>b.onclick=()=>{territorySelection=b.dataset.process;territoryPage=0;geoFilter();});
 if(!XGeo||!mapPP)return;if(mapLayer)mapPP.removeLayer(mapLayer);
 const lookup=new Map(rows.map(x=>[x.process,x]));
 mapLayer=L.geoJSON(XGeo.features.filter(f=>ids.has(f.properties.process)),{style:f=>({color:f.properties.block?'#bd8940':f.properties.same_mineral?'#246bab':'#176e61',weight:2,fillOpacity:.38}),onEachFeature:(f,l)=>{const x=lookup.get(f.properties.process);const info=`<b>${esc(x.process)}</b><br>${esc(x.city||'Município não informado')} · ${esc(x.state||'UF não informada')}<br>Substância: ${esc(x.sigmine_substance||'Não informada')}<br>SOPLE: ${esc(x.sople||'Não informado')}<br>Fase: ${esc(x.phase_name||'Não informada')}<br>Área: ${fmt(Math.round(x.area_ha))} ha<br>Interseção com bloqueio: ${fmt(Math.round(x.block_ha||0))} ha<br>Ocorrências compatíveis: ${fmt(x.same_mineral_inside||0)}<br>Tempo no estoque: ${x.age_days!==''&&x.age_days!=null?fmt(x.age_days)+' dias':'não identificado'}`;l.bindTooltip(info,{sticky:true,opacity:.97});l.on('click',()=>{territorySelection=x.process;territoryPage=0;geoFilter();});}}).addTo(mapPP);
 if(mapLayer.getBounds().isValid())mapPP.fitBounds(mapLayer.getBounds(),{maxZoom:13,padding:[25,25]});
};
