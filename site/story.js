const studyStory=[
 ['panorama','Visão geral','Qual problema de gestão queremos resolver?','Acompanhar a destinação da área e separar seleção, continuidade dos direitos e evidência fiscal.'],
 ['jornada','Entender o percurso','Como uma área percorre o sistema?','Explore decisões e caminhos alternativos. As etapas não são obrigatoriamente lineares.'],
 ['estoque','Examinar o estoque','O que aguarda destinação?','Confronte aptidão, nominação, oferta e tempo de espera. O retrato atual não representa toda a fila histórica.'],
 ['territorio','Localizar as áreas','Onde estão as oportunidades e restrições?','Filtre o território e consulte polígonos, substâncias e evidências geológicas.'],
 ['minerais','Recorte mineral','Como os minerais estratégicos se inserem no conjunto?','Compare o recorte com o universo geral, observando sobreposição de substâncias e critérios de enquadramento.'],
 ['participantes','Conhecer participantes','Quem participa e quais trajetórias observamos?','Distinga vencedor, titular e sócio. Características atuais não são necessariamente as existentes no leilão.'],
 ['trajetorias','Seguir os direitos','O que acontece após a seleção?','Examine continuidade, cessões e ramificações sem transformar transferência em prova de especulação.'],
 ['fiscal','Verificar obrigações','Quais resultados têm evidência fiscal?','Separe lance, TAH, CFEM e dívida ativa. Ausência de registro não confirma inadimplência.'],
 ['incentivos','Discutir instrumentos','Como traduzir evidência em política pública?','Explore hipóteses de incentivos e condições de participação, distinguindo simulações de efeitos demonstrados.'],
 ['validacao','Avaliar confiança','Até onde podemos concluir?','Consulte cobertura, validação e limitações antes de usar o resultado em decisões.'],
 ['fontes','Consultar fundamentos','De onde vêm os dados e as regras?','Confira fontes e fundamentos jurídicos da análise.'],
 ['guia','Guia e FAQ','Como explorar e interpretar?','Consulte as orientações e os cuidados de leitura.']
];
const storyBaseRender=render;
render=function(){storyBaseRender();const current=location.hash.slice(1)||'panorama',i=studyStory.findIndex(s=>s[0]===current);if(i<0)return;const s=studyStory[i];app.insertAdjacentHTML('afterbegin',`<aside class="story-context"><span class="eyebrow">Percurso de leitura · ${i+1}/${studyStory.length}</span><details><summary>${esc(s[2])}</summary><p>${esc(s[3])}</p><div class="journey">${studyStory.map((x,j)=>`<a href="#${x[0]}" ${i===j?'aria-current="step"':''}>${j+1}. ${esc(x[1])}</a>`).join('')}</div></details></aside>`);app.insertAdjacentHTML('beforeend',`<nav class="story-next" aria-label="Continuar a leitura">${i?`<a href="#${studyStory[i-1][0]}">← ${studyStory[i-1][1]}</a>`:'<span></span>'}${i<studyStory.length-1?`<a href="#${studyStory[i+1][0]}">Próxima etapa: ${studyStory[i+1][1]} →</a>`:''}</nav>`);
 if(current==='panorama')app.querySelector('.hero')?.insertAdjacentHTML('afterend',`<section class="story-start"><h2>Da área à decisão pública</h2><p>Explore o estudo em sequência ou escolha uma pergunta. O universo geral permanece como referência e os minerais críticos e estratégicos constituem um recorte específico.</p><div class="journey">${studyStory.slice(1,10).map((x,j)=>`<a href="#${x[0]}"><b>${j+1}. ${x[1]}</b><br>${x[2]}</a>`).join('')}</div></section>`);
 if(current==='jornada'){const links=['fontes','estoque','estoque','panorama','trajetorias','trajetorias','fiscal'];const stage=$('#journey-stage');if(stage){const addLinks=()=>{stage.querySelector('.stage-links')?.remove();const selected=app.querySelector('[data-step][aria-pressed="true"]');const n=Number(selected?.dataset.step||0);stage.insertAdjacentHTML('beforeend',`<p class="stage-links"><a href="#${links[n]}">Explorar os dados desta etapa →</a> · <a href="#fontes">Conferir fontes e regras</a></p>`);};addLinks();app.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',addLinks));}}
};
const storyNav=document.querySelector('header nav')||document.querySelector('nav');
if(storyNav)studyStory.forEach(s=>{const a=storyNav.querySelector(`a[href="#${s[0]}"]`);if(a)storyNav.append(a);});
